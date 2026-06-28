"""
状态管理 - Agent 和 Workflow 的状态定义
"""
from typing import Dict, List, Any, Optional
from pydantic import BaseModel, Field
from datetime import datetime
from enum import Enum


class AgentStatus(str, Enum):
    """Agent 状态"""
    IDLE = "idle"
    THINKING = "thinking"
    ACTING = "acting"
    OBSERVING = "observing"
    REFLECTING = "reflecting"
    COMPLETED = "completed"
    FAILED = "failed"


class WorkflowStatus(str, Enum):
    """Workflow 状态"""
    PENDING = "pending"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"


class Message(BaseModel):
    """消息"""
    role: str  # "user", "assistant", "system", "tool"
    content: str
    tool_calls: Optional[List[Dict]] = None
    tool_call_id: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class Thought(BaseModel):
    """思考过程"""
    content: str
    reasoning: str = ""
    confidence: float = 0.0
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class Action(BaseModel):
    """行动"""
    tool_name: str
    tool_input: Dict[str, Any]
    result: Optional[Any] = None
    success: bool = True
    error: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class Observation(BaseModel):
    """观察结果"""
    content: str
    metadata: Dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class Reflection(BaseModel):
    """反思"""
    content: str
    quality_score: float = 0.0
    improvements: List[str] = Field(default_factory=list)
    should_retry: bool = False
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class AgentState(BaseModel):
    """Agent 状态"""
    agent_id: str
    agent_type: str
    status: AgentStatus = AgentStatus.IDLE
    
    # 上下文
    messages: List[Message] = Field(default_factory=list)
    thoughts: List[Thought] = Field(default_factory=list)
    actions: List[Action] = Field(default_factory=list)
    observations: List[Observation] = Field(default_factory=list)
    reflections: List[Reflection] = Field(default_factory=list)
    
    # 工作数据
    input_data: Dict[str, Any] = Field(default_factory=dict)
    output_data: Dict[str, Any] = Field(default_factory=dict)
    intermediate_data: Dict[str, Any] = Field(default_factory=dict)
    
    # 控制
    current_iteration: int = 0
    max_iterations: int = 10
    error_count: int = 0
    
    # 元数据
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    def add_message(self, role: str, content: str, **kwargs):
        """添加消息"""
        msg = Message(role=role, content=content, **kwargs)
        self.messages.append(msg)
        self.updated_at = datetime.utcnow()
        return msg
    
    def add_thought(self, content: str, **kwargs):
        """添加思考"""
        thought = Thought(content=content, **kwargs)
        self.thoughts.append(thought)
        self.updated_at = datetime.utcnow()
        return thought
    
    def add_action(self, tool_name: str, tool_input: Dict[str, Any], **kwargs):
        """添加行动"""
        action = Action(tool_name=tool_name, tool_input=tool_input, **kwargs)
        self.actions.append(action)
        self.updated_at = datetime.utcnow()
        return action
    
    def add_observation(self, content: str, **kwargs):
        """添加观察"""
        observation = Observation(content=content, **kwargs)
        self.observations.append(observation)
        self.updated_at = datetime.utcnow()
        return observation
    
    def add_reflection(self, content: str, **kwargs):
        """添加反思"""
        reflection = Reflection(content=content, **kwargs)
        self.reflections.append(reflection)
        self.updated_at = datetime.utcnow()
        return reflection
    
    def get_context_summary(self) -> str:
        """获取上下文摘要"""
        parts = []
        if self.thoughts:
            parts.append(f"思考: {self.thoughts[-1].content}")
        if self.actions:
            last_action = self.actions[-1]
            parts.append(f"行动: {last_action.tool_name}({last_action.tool_input})")
        if self.observations:
            parts.append(f"观察: {self.observations[-1].content}")
        return "\n".join(parts)


class WorkflowState(BaseModel):
    """Workflow 状态"""
    workflow_id: str
    status: WorkflowStatus = WorkflowStatus.PENDING
    
    # Agent 状态
    agent_states: Dict[str, AgentState] = Field(default_factory=dict)
    
    # 全局数据
    input_data: Dict[str, Any] = Field(default_factory=dict)
    output_data: Dict[str, Any] = Field(default_factory=dict)
    shared_data: Dict[str, Any] = Field(default_factory=dict)
    
    # 执行历史
    execution_history: List[Dict[str, Any]] = Field(default_factory=list)
    
    # 控制
    current_stage: str = ""
    completed_stages: List[str] = Field(default_factory=list)
    
    # 元数据
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    def add_agent_state(self, agent_id: str, agent_type: str) -> AgentState:
        """添加 Agent 状态"""
        state = AgentState(agent_id=agent_id, agent_type=agent_type)
        self.agent_states[agent_id] = state
        self.updated_at = datetime.utcnow()
        return state
    
    def get_agent_state(self, agent_id: str) -> Optional[AgentState]:
        """获取 Agent 状态"""
        return self.agent_states.get(agent_id)
    
    def record_execution(self, stage: str, result: Dict[str, Any]):
        """记录执行"""
        self.execution_history.append({
            "stage": stage,
            "result": result,
            "timestamp": datetime.utcnow()
        })
        self.completed_stages.append(stage)
        self.updated_at = datetime.utcnow()
