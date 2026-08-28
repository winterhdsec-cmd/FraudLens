"""研判 / 团伙发现共享契约（原 routes/deps.py、routes/gangs.py 内联定义迁移而来）。"""
from typing import Optional, List, Dict, Any
from pydantic import BaseModel


class AnalyzeRequest(BaseModel):
    """/api/system/agent-analyze 研判请求。"""
    messages: list = []
    platform_data: dict = {}
    session_id: Optional[str] = None
    # B-L3：账户间资金流转记录（可选），用于实时主链路资金回流闭环检测。
    # 每条形如 {from_account, to_account, amount, timestamp}；缺失则诚实返回 is_reflux=False。
    accounts_tx: Optional[List[Dict[str, Any]]] = None


class GNNDetectRequest(BaseModel):
    """/api/gangs GNN 团伙发现请求。"""
    use_gnn: bool = True
    training_epochs: int = 100
    community_method: str = 'louvain'
