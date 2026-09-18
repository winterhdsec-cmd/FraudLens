"""
主编排 Agent - 基于 LangGraph (StateGraph) 的工作流编排

重构说明（2026-07-26，任务 #30）：
- 原实现为手写顺序流水线，"反思"是单个 if + 空 _adjust_strategy，闭环名不副实。
- 现采用 LangGraph StateGraph 真做反思闭环：
    plan -> preprocess -> analyze -> cluster -> reflect
    reflect 节点经 add_conditional_edges 在「未收敛且未达 max_iter」时
    回连 analyze，触发真实重算；_adjust_strategy 真实改参；retry_count 真实自增。
- 对外返回 dict 结构与原实现 100% 一致（session_id/cases/gangs/statistics/reflection/status），
  调用方（tasks.py / routes/system.py）无感。
- ENABLE_REFLECTION_LOOP 开关（默认 true）供 #8 消融用：置 false 时 max_iter=0 退化为单次流水线。
"""
import os
import json
import time
from typing import Dict, Any, List, Optional, TypedDict
from datetime import datetime

from core.state import WorkflowState, WorkflowStatus
from core.metrics import get_metrics_collector
from core.checkpoint import get_checkpoint_manager
from core.otel import span  # G10：阶段级 span（禁用时 no-op，见 core/otel.py）
from agents.analyst_agent import AnalystAgent
from agents.cluster_agent import ClusterAgent
from agents.schemas import build_slips
from langgraph.graph import StateGraph, START, END


class OrchestratorState(TypedDict):
    """LangGraph 在节点间流转的状态。"""
    cases: List[Dict[str, Any]]
    context: Dict[str, Any]
    plan: Dict[str, Any]
    preprocessed: List[Dict[str, Any]]
    analyzed_cases: List[Dict[str, Any]]
    gang_result: Dict[str, Any]
    quality_score: float
    retry_count: int
    max_iter: int
    strategy: Dict[str, Any]
    reflection: Dict[str, Any]
    should_retry: bool
    error: Optional[str]
    session_id: str
    # B-L3：账户资金流转记录，下传聚类节点用于回流闭环检测
    accounts_tx: Optional[Any]
    processing_time: float
    # B-L7：四单流转文档契约（警情单/研判单/指令单/反馈单）
    slips: Dict[str, Any]
    # B-L9：复盘六动作记录（教学 Lab4 / 业务复盘用）
    review_chain: Optional[Dict[str, Any]]
    # B-L13：异常卡标记（none/missing_data/model_conflict/timeout）
    abnormal: str
    abnormal_detail: Optional[Dict[str, Any]]


class OrchestratorAgent:
    """
    主编排智能体（LangGraph StateGraph 实现）

    节点：
      1. plan_node      规划阶段
      2. preprocess_node 预处理阶段
      3. analyze_node   分析阶段（analyst agent）
      4. cluster_node   聚类/团伙发现阶段（cluster agent）
      5. reflect_node   反思阶段：质量评估 + 条件边回连
    """

    def __init__(
        self,
        llm_client=None,
        embedding_model=None,
        use_gnn: bool = True,
        analyst=None,
        cluster=None,
        max_iter: Optional[int] = None,
    ):
        self.llm = llm_client
        self.embedding_model = embedding_model
        self.use_gnn = use_gnn

        # 反思闭环参数（可通过环境变量覆盖，供 #8 消融）
        self.max_iter = int(max_iter) if max_iter is not None else int(os.getenv("MAX_REFLECT_ITER", "2"))
        self.quality_threshold = float(os.getenv("REFLECT_QUALITY_THRESHOLD", "0.6"))
        self.enable_reflection = os.getenv("ENABLE_REFLECTION_LOOP", "true").lower() != "false"

        # 依赖注入：默认构造真实 agent；测试可传 stub
        self.analyst = analyst if analyst is not None else AnalystAgent(llm_client=llm_client)
        self.cluster = (
            cluster if cluster is not None
            else ClusterAgent(llm_client=llm_client, embedding_model=embedding_model, use_gnn=use_gnn)
        )

        # 工作流状态（对外兼容 get_state/reset）
        self.state = WorkflowState(workflow_id="orchestrator")

        # 检查点 / 指标（无 Redis 环境下调用失败不应中断主流程）
        self.checkpoint_manager = get_checkpoint_manager()
        self.checkpoint_enabled = True
        self.metrics = get_metrics_collector("orchestrator")

        # 内部计数器（便于验证 _adjust_strategy 是否被调用）
        self._adjust_invocations = 0

        # B1.3: 声明式流水线 —— 从 AgentRegistry 读取 analyze/cluster agent
        from agents.defaults import register_default_agents
        from agents.registry import registry
        register_default_agents()
        self.registry = registry
        # 注入的 DI agent 优先覆盖默认注册（同名覆盖，避免重复执行；保持 routes/system.py 既有行为）
        self.registry.register(self.analyst, stage="analyze", name="analyst")
        self.registry.register(self.cluster, stage="cluster", name="cluster")

    # ------------------------------------------------------------------ #
    # 公共入口
    # ------------------------------------------------------------------ #
    def process(self, cases: List[Dict[str, Any]], context: Dict[str, Any] = None) -> Dict[str, Any]:
        start_time = time.time()
        self.state.status = WorkflowStatus.RUNNING
        self.state.input_data = {"cases": cases, "context": context or {}}

        # 会话标识：优先沿用调用方传入的 session_id（前端/路由生成），保证 gang_id
        # 等下游标识与会话绑定、跨会话不串库；未传入则按秒级时间戳兜底。
        _ctx = context or {}
        session_id = _ctx.get('session_id') or f"session_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"

        init: OrchestratorState = {
            "cases": cases,
            "context": _ctx,
            "plan": {},
            "preprocessed": [],
            "analyzed_cases": [],
            "gang_result": {},
            "quality_score": 0.0,
            "retry_count": 0,
            "max_iter": self.max_iter if self.enable_reflection else 0,
            "strategy": {"use_gnn": self.use_gnn},
            "reflection": {},
            "should_retry": False,
            "error": None,
            "session_id": session_id,
            "processing_time": 0.0,
            # B-L3：账户资金流转记录，下传聚类节点用于回流闭环检测
            "accounts_tx": _ctx.get("accounts_tx"),
            # B-L7：四单流转
            "slips": {},
            # B-L9 / B-L13
            "review_chain": None,
            "abnormal": "none",
            "abnormal_detail": None,
        }

        try:
            with span("orchestrator.process", case_count=len(cases)):
                graph = self._build_graph()
                final = graph.invoke(init)

            analyzed = final.get("analyzed_cases", [])
            gang = final.get("gang_result", {})
            # 沿用 init 阶段确定的 session_id（优先调用方传入，避免跨会话串库）
            session_id = final.get("session_id") or session_id
            processing_time = time.time() - start_time

            # B-L7：组装四单流转（警情单/研判单/指令单/反馈单）
            slips = build_slips(
                cases=final.get("preprocessed", []),
                analyzed_cases=analyzed,
                gang_result=gang,
                reflection=final.get("reflection", {}),
                review_chain=final.get("review_chain"),
                abnormal=final.get("abnormal", "none"),
                abnormal_detail=final.get("abnormal_detail"),
            )

            result = {
                "session_id": session_id,
                "cases": analyzed,
                "gangs": gang.get("gangs", []),
                "statistics": {
                    "total_cases": len(analyzed),
                    "total_gangs": gang.get("total_gangs", len(gang.get("gangs", []))),
                    "quality_score": final.get("quality_score", 0.0),
                    "processing_time": processing_time,
                },
                "reflection": final.get("reflection", {}),
                # B-L7：四单流转（向后兼容，新增字段）
                "slips": slips,
                # B-L13：异常卡
                "abnormal": final.get("abnormal", "none"),
                "abnormal_detail": final.get("abnormal_detail"),
                "status": "completed",
            }

            self.state.status = WorkflowStatus.COMPLETED
            self.state.output_data = result
            self._save_checkpoint("completed", {
                "session_id": session_id,
                "total_gangs": result["statistics"]["total_gangs"],
            })
            self._record_metrics(session_id, True, processing_time, result["statistics"])
            return result

        except Exception as e:
            processing_time = time.time() - start_time
            self.state.status = WorkflowStatus.FAILED
            self._record_metrics("orchestrator_failed", False, processing_time, {})
            return {
                "session_id": None,
                "cases": [],
                "gangs": [],
                "statistics": {
                    "total_cases": 0,
                    "total_gangs": 0,
                    "quality_score": 0.0,
                    "processing_time": processing_time,
                },
                "reflection": {},
                "error": str(e),
                "status": "failed",
            }

    # ------------------------------------------------------------------ #
    # LangGraph 图构建
    # ------------------------------------------------------------------ #
    def _build_graph(self) -> "StateGraph":
        builder = StateGraph(OrchestratorState)
        builder.add_node("plan_node", self.plan_node)
        builder.add_node("preprocess_node", self.preprocess_node)
        builder.add_node("analyze_node", self.analyze_node)
        builder.add_node("cluster_node", self.cluster_node)
        builder.add_node("reflect_node", self.reflect_node)

        builder.add_edge(START, "plan_node")
        builder.add_edge("plan_node", "preprocess_node")
        builder.add_edge("preprocess_node", "analyze_node")
        builder.add_edge("analyze_node", "cluster_node")
        builder.add_edge("cluster_node", "reflect_node")
        builder.add_conditional_edges(
            "reflect_node",
            self._should_continue,
            {"continue": "analyze_node", END: END},
        )
        return builder.compile()

    @staticmethod
    def _should_continue(state: OrchestratorState) -> str:
        return "continue" if state.get("should_retry") else END

    # ------------------------------------------------------------------ #
    # 节点实现
    # ------------------------------------------------------------------ #
    def plan_node(self, state: OrchestratorState) -> Dict[str, Any]:
        return {"plan": self._plan(state["cases"], state["context"])}

    def preprocess_node(self, state: OrchestratorState) -> Dict[str, Any]:
        return {"preprocessed": self._preprocess(state["cases"])}

    def analyze_node(self, state: OrchestratorState) -> Dict[str, Any]:
        # B1.3: 从 registry 读取 analyze + augment 阶段 agent，顺序执行并合并结果。
        # analyze 阶段产出基础分析结果；augment 阶段（如 DemoAgent）产出增量字段合并进去。
        with span("analyze_node", case_count=len(state["preprocessed"])):
            analyze_agents = self.registry.agents_for_stage("analyze") or [self.analyst]
            augment_agents = self.registry.agents_for_stage("augment")

            analyzed_cases = []
            for case in state["preprocessed"]:
                result: Dict[str, Any] = {}
                for ag in analyze_agents:
                    out = ag.run_safe({"case": case})
                    if out.get("is_error"):
                        # analyze 异常：保留原始案件字段，仅挂错误标记，避免"空壳进聚类"
                        # 导致该案件在团伙发现阶段被静默丢弃（M3）。
                        if not result:
                            result = dict(case)
                        result["is_error"] = True
                        result["error"] = out.get("error", "analyze 异常")
                        continue
                    result = {**result, **out}
                for ag in augment_agents:
                    out = ag.run_safe({"case": case, "analyzed": result})
                    if not out.get("is_error"):
                        result = {**result, **out}
                analyzed_cases.append(result)
            return {"analyzed_cases": analyzed_cases}

    def cluster_node(self, state: OrchestratorState) -> Dict[str, Any]:
        use_gnn = state["strategy"].get("use_gnn", self.use_gnn)
        with span("cluster_node", use_gnn=bool(use_gnn)):
            clusters = self.registry.agents_for_stage("cluster") or [self.cluster]
            gang_result = clusters[0].run_safe({
                "cases": state["analyzed_cases"],
                "use_gnn": use_gnn,
                "accounts_tx": state.get("accounts_tx"),
                # 会话绑定：让 gang_id 带上会话标识，防止跨会话串库
                "session_id": state.get("session_id", ""),
                # 反思调参结果真实下传（M2）：cluster_params 在首轮为空、重算轮有值
                "cluster_params": (state["strategy"] or {}).get("cluster_params"),
            })
            return {
                "gang_result": gang_result,
                "quality_score": float(gang_result.get("quality_score", 0.0)),
            }

    def reflect_node(self, state: OrchestratorState) -> Dict[str, Any]:
        with span("reflect_node", retry_count=state["retry_count"]):
            gang_result = state["gang_result"]
            analyzed = state["analyzed_cases"]
            n_gangs = gang_result.get("total_gangs", len(gang_result.get("gangs", [])))
            quality_score = state["quality_score"]
            avg_risk = (
                sum(c.get("risk_score", 0) for c in analyzed) / len(analyzed)
                if analyzed else 0.0
            )

            # 修复（2026-07-30）：原阈值 n_gangs>=1 太宽松，GraphSAGE 塌缩到 1 簇仍判 True；
            # 原等权平均会被两个易满足的布尔条件拉高，掩盖 quality_score 低的事实。
            # 调整：至少 2 个团伙才算"足够"；quality_score 权重提至 0.5 主导判定。
            has_enough_gangs = n_gangs >= 2
            has_good_analysis = avg_risk > 50
            overall = (
                0.5 * quality_score
                + 0.25 * (1 if has_enough_gangs else 0)
                + 0.25 * (1 if has_good_analysis else 0)
            )

            retry_count = state["retry_count"]
            improvements: List[str] = []
            if not has_enough_gangs:
                improvements.append("gang_count_low")
            if not has_good_analysis:
                improvements.append("analysis_quality_low")

            should_retry = overall < self.quality_threshold and retry_count < state["max_iter"]

            if should_retry:
                retry_count = retry_count + 1
                strategy = self._adjust_strategy(
                    state["strategy"],
                    {"quality_score": overall, "improvements": improvements},
                )
            else:
                strategy = state["strategy"]

            reflection = {
                "quality_score": overall,
                "has_enough_gangs": has_enough_gangs,
                "has_good_analysis": has_good_analysis,
                "should_retry": should_retry,
                "retry_count": retry_count,
                "improvements": improvements,
            }
            out: Dict[str, Any] = {
                "reflection": reflection,
                "should_retry": should_retry,
                "retry_count": retry_count,
                "strategy": strategy,
                "quality_score": overall,
            }

            # B-L9：复盘六动作闭环（真值标签存在时触发；否则质量分低时触发）
            try:
                from agents.reflect_agent import ReflectAgent
                gt = state["context"].get("ground_truth") if state.get("context") else None
                if gt is not None or overall < self.quality_threshold:
                    review = ReflectAgent().run({
                        "analyzed_cases": analyzed,
                        "gang_result": gang_result,
                        "ground_truth": gt,
                        "quality_score": overall,
                    }).get("review_chain", {})
                    out["review_chain"] = review
            except Exception as e:  # 复盘失败不阻断主流程
                print(f"B-L9 复盘失败: {e}")

            # B-L13：异常卡检测（数据缺失/模型冲突/超时）
            try:
                from agents.abnormal import detect_abnormal
                abn = detect_abnormal(
                    analyzed_cases=analyzed,
                    gang_result=gang_result,
                    reflection=reflection,
                    retry_count=retry_count,
                )
                if abn:
                    out["abnormal"] = abn["abnormal"]
                    out["abnormal_detail"] = abn["detail"]
                elif overall < self.quality_threshold:
                    # 低置信且无重试机会（关闭反思/迭代已耗尽）：诚实标记而非静默 completed。
                    # 迭代耗尽场景由 detect_abnormal 的 model_conflict 覆盖；此处兜底首轮低质。
                    out["abnormal"] = "low_confidence"
                    out["abnormal_detail"] = {
                        "reason": f"整体质量分 {overall:.3f} 低于阈值 {self.quality_threshold}，且无重试机会",
                        "quality_score": overall,
                        "retry_count": retry_count,
                        "max_iter": state["max_iter"],
                        "stage": "reflection",
                        "action": "人工复核结论后决策（置信度门控不阻断，仅标记）",
                    }
            except Exception as e:
                print(f"B-L13 异常检测失败: {e}")

            return out

    # ------------------------------------------------------------------ #
    # 策略调整（真实生效，不再空返回）
    # ------------------------------------------------------------------ #
    def _adjust_strategy(self, strategy: Dict[str, Any], reflection: Dict[str, Any]) -> Dict[str, Any]:
        self._adjust_invocations += 1
        new_strategy = dict(strategy)
        q = reflection.get("quality_score", 1.0)
        improvements = reflection.get("improvements", [])

        if q < self.quality_threshold:
            # 真实调参：降低对 GNN 的依赖，切传统聚类，并调小聚类粒度
            new_strategy["use_gnn"] = False
            new_strategy["cluster_params"] = {
                "min_cluster_size": 2,
                "cluster_selection_epsilon": 0.3,
            }
        if "gang_count_low" in improvements:
            new_strategy["min_gangs"] = max(1, new_strategy.get("min_gangs", 1) - 1)
        return new_strategy

    # ------------------------------------------------------------------ #
    # 规划 / 预处理（沿用原逻辑）
    # ------------------------------------------------------------------ #
    def _plan(self, cases: List[Dict[str, Any]], context: Dict[str, Any]) -> Dict[str, Any]:
        n_cases = len(cases)
        plan = {
            "strategy": "parallel_analysis",
            "batch_size": min(10, n_cases),
            "enable_clustering": n_cases >= 3,
            "enable_reflection": True,
        }
        if n_cases > 50:
            plan["strategy"] = "batch_processing"
            plan["batch_size"] = 20
        return plan

    def _preprocess(self, cases: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        preprocessed = []
        for case in cases:
            cleaned_case = {
                "case_id": case.get("case_id", ""),
                "title": case.get("title", ""),
                "description": case.get("description", "").strip(),
                "scam_type": case.get("scam_type", "未知"),
                "amount": float(case.get("amount", 0)),
                "victim_name": case.get("victim_name", "未知"),
                "victim_age": case.get("victim_age"),
                "risk_score": case.get("risk_score", 0),
                "text_messages": case.get("text_messages", []),
            }
            if not cleaned_case["description"] and not cleaned_case["text_messages"]:
                continue
            preprocessed.append(cleaned_case)
        return preprocessed

    # ------------------------------------------------------------------ #
    # 兼容 API
    # ------------------------------------------------------------------ #
    def get_state(self) -> WorkflowState:
        return self.state

    def reset(self):
        self.state = WorkflowState(workflow_id="orchestrator")
        self._adjust_invocations = 0

    # ------------------------------------------------------------------ #
    # 检查点 / 指标（无 Redis 环境下容错）
    # ------------------------------------------------------------------ #
    def _save_checkpoint(self, stage: str, payload: Dict[str, Any]):
        if not self.checkpoint_enabled:
            return
        try:
            self.checkpoint_manager.save_checkpoint(agent_id="orchestrator", state={
                "stage": stage, **payload,
            })
        except Exception:
            pass

    def _record_metrics(self, task_id: str, success: bool, duration: float, metadata: Dict[str, Any]):
        try:
            if success:
                self.metrics.record_task(task_id=task_id, success=True, duration=duration, metadata=metadata)
            else:
                self.metrics.record_task_failure(task_id=task_id, error_type="Exception", error_message="")
        except Exception:
            pass
