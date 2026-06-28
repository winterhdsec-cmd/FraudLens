"""
检查点持久化 - 支持Agent状态恢复和故障重启
参考：LangGraph Checkpoint机制
"""
import json
import os
import pickle
from typing import Dict, Any, Optional, List
from datetime import datetime
from pathlib import Path
from core.logger import logger


class CheckpointManager:
    """
    检查点管理器
    
    功能：
    1. 保存Agent状态快照
    2. 从检查点恢复状态
    3. 管理检查点历史
    4. 支持定期自动保存
    """
    
    def __init__(
        self,
        storage_dir: str = "data/checkpoints",
        max_checkpoints: int = 100,
        auto_save_interval: int = 300  # 秒
    ):
        """
        初始化检查点管理器
        
        Args:
            storage_dir: 检查点存储目录
            max_checkpoints: 最大检查点数量
            auto_save_interval: 自动保存间隔（秒）
        """
        self.storage_dir = Path(storage_dir)
        self.max_checkpoints = max_checkpoints
        self.auto_save_interval = auto_save_interval
        
        # 创建存储目录
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        
        # 检查点索引
        self.checkpoints_index: List[Dict[str, Any]] = []
        self._load_index()
        
        logger.info(
            "CheckpointManager initialized",
            storage_dir=str(self.storage_dir),
            max_checkpoints=max_checkpoints
        )
    
    def save_checkpoint(
        self,
        agent_id: str,
        state: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        保存检查点
        
        Args:
            agent_id: Agent ID
            state: Agent状态
            metadata: 额外元数据
        
        Returns:
            检查点ID
        """
        checkpoint_id = f"{agent_id}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
        
        checkpoint_data = {
            "checkpoint_id": checkpoint_id,
            "agent_id": agent_id,
            "timestamp": datetime.utcnow().isoformat(),
            "state": state,
            "metadata": metadata or {}
        }
        
        # 保存检查点文件
        checkpoint_file = self.storage_dir / f"{checkpoint_id}.json"
        with open(checkpoint_file, 'w', encoding='utf-8') as f:
            json.dump(checkpoint_data, f, ensure_ascii=False, indent=2)
        
        # 更新索引
        self.checkpoints_index.append({
            "checkpoint_id": checkpoint_id,
            "agent_id": agent_id,
            "timestamp": checkpoint_data["timestamp"],
            "file": str(checkpoint_file)
        })
        
        # 清理旧检查点
        self._cleanup_old_checkpoints()
        
        # 保存索引
        self._save_index()
        
        logger.info(
            "Checkpoint saved",
            checkpoint_id=checkpoint_id,
            agent_id=agent_id
        )
        
        return checkpoint_id
    
    def load_checkpoint(self, checkpoint_id: str) -> Optional[Dict[str, Any]]:
        """
        加载检查点
        
        Args:
            checkpoint_id: 检查点ID
        
        Returns:
            检查点数据
        """
        # 查找检查点
        checkpoint_info = None
        for cp in self.checkpoints_index:
            if cp["checkpoint_id"] == checkpoint_id:
                checkpoint_info = cp
                break
        
        if not checkpoint_info:
            logger.error("Checkpoint not found", checkpoint_id=checkpoint_id)
            return None
        
        # 加载检查点文件
        checkpoint_file = Path(checkpoint_info["file"])
        if not checkpoint_file.exists():
            logger.error("Checkpoint file missing", checkpoint_id=checkpoint_id)
            return None
        
        with open(checkpoint_file, 'r', encoding='utf-8') as f:
            checkpoint_data = json.load(f)
        
        logger.info(
            "Checkpoint loaded",
            checkpoint_id=checkpoint_id,
            agent_id=checkpoint_data["agent_id"]
        )
        
        return checkpoint_data
    
    def get_latest_checkpoint(self, agent_id: str) -> Optional[Dict[str, Any]]:
        """
        获取Agent的最新检查点
        
        Args:
            agent_id: Agent ID
        
        Returns:
            最新检查点数据
        """
        # 按时间倒序排列
        agent_checkpoints = [
            cp for cp in self.checkpoints_index
            if cp["agent_id"] == agent_id
        ]
        agent_checkpoints.sort(key=lambda x: x["timestamp"], reverse=True)
        
        if not agent_checkpoints:
            return None
        
        latest = agent_checkpoints[0]
        return self.load_checkpoint(latest["checkpoint_id"])
    
    def list_checkpoints(self, agent_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        列出检查点
        
        Args:
            agent_id: Agent ID（可选，过滤特定Agent）
        
        Returns:
            检查点列表
        """
        if agent_id:
            return [cp for cp in self.checkpoints_index if cp["agent_id"] == agent_id]
        return self.checkpoints_index.copy()
    
    def delete_checkpoint(self, checkpoint_id: str) -> bool:
        """
        删除检查点
        
        Args:
            checkpoint_id: 检查点ID
        
        Returns:
            是否成功删除
        """
        # 查找检查点
        checkpoint_info = None
        for cp in self.checkpoints_index:
            if cp["checkpoint_id"] == checkpoint_id:
                checkpoint_info = cp
                break
        
        if not checkpoint_info:
            return False
        
        # 删除文件
        checkpoint_file = Path(checkpoint_info["file"])
        if checkpoint_file.exists():
            checkpoint_file.unlink()
        
        # 从索引中移除
        self.checkpoints_index = [
            cp for cp in self.checkpoints_index
            if cp["checkpoint_id"] != checkpoint_id
        ]
        
        # 保存索引
        self._save_index()
        
        logger.info("Checkpoint deleted", checkpoint_id=checkpoint_id)
        return True
    
    def _cleanup_old_checkpoints(self):
        """清理旧检查点"""
        if len(self.checkpoints_index) <= self.max_checkpoints:
            return
        
        # 按时间排序
        self.checkpoints_index.sort(key=lambda x: x["timestamp"])
        
        # 删除最旧的检查点
        to_delete = self.checkpoints_index[:-self.max_checkpoints]
        for cp in to_delete:
            self.delete_checkpoint(cp["checkpoint_id"])
    
    def _load_index(self):
        """加载检查点索引"""
        index_file = self.storage_dir / "checkpoints_index.json"
        if index_file.exists():
            with open(index_file, 'r', encoding='utf-8') as f:
                self.checkpoints_index = json.load(f)
    
    def _save_index(self):
        """保存检查点索引"""
        index_file = self.storage_dir / "checkpoints_index.json"
        with open(index_file, 'w', encoding='utf-8') as f:
            json.dump(self.checkpoints_index, f, ensure_ascii=False, indent=2)


class AgentStateSerializer:
    """
    Agent状态序列化器
    
    支持复杂状态的序列化和反序列化
    """
    
    @staticmethod
    def serialize(state: Dict[str, Any]) -> str:
        """
        序列化状态
        
        Args:
            state: Agent状态
        
        Returns:
            序列化后的字符串
        """
        # 处理特殊类型
        def default_serializer(obj):
            if isinstance(obj, datetime):
                return obj.isoformat()
            if hasattr(obj, '__dict__'):
                return obj.__dict__
            return str(obj)
        
        return json.dumps(state, default=default_serializer, ensure_ascii=False)
    
    @staticmethod
    def deserialize(serialized: str) -> Dict[str, Any]:
        """
        反序列化状态
        
        Args:
            serialized: 序列化字符串
        
        Returns:
            Agent状态
        """
        return json.loads(serialized)


# 全局检查点管理器
_checkpoint_manager: Optional[CheckpointManager] = None


def get_checkpoint_manager() -> CheckpointManager:
    """获取全局检查点管理器"""
    global _checkpoint_manager
    if _checkpoint_manager is None:
        _checkpoint_manager = CheckpointManager()
    return _checkpoint_manager
