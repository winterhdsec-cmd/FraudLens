"""
Phase C 数据源适配器包。

提供把外部公开反欺诈/反洗钱基准（当前：IBM/AMLSim）转换成
FraudLens 评测管线可消费格式的能力，使论文实验具备"独立公开基准"验证。

设计要点：
- 适配器解析 AMLSim 的真实输出 schema（accounts.csv / transactions.csv / alerts.csv），
  不依赖官方 Java 生成器的内部实现；你用官方 Maven 生成器产出的 CSV 直接丢进同一条管线即可。
- 因本开发环境无 Maven，另附 `_amlsim_sample_gen.py` 按 AMLSim 文档 schema 复现一份
  格式一致的样本数据，用于端到端验证适配器与账户中心评测。论文中如实标注数据来源。
"""
from .amlsim_adapter import load_amlsim, AmLSIMFormatError
from .tfinance_adapter import load_tfinance, TFinanceFormatError
from .elliptic_adapter import load_elliptic, EllipticFormatError
from .fund_flow_io import (
    parse_fund_flow_file,
    parse_fund_flow_csv,
    amlsim_to_accounts_tx,
)

__all__ = [
    "load_amlsim",
    "AmLSIMFormatError",
    "load_tfinance",
    "TFinanceFormatError",
    "load_elliptic",
    "EllipticFormatError",
    "parse_fund_flow_file",
    "parse_fund_flow_csv",
    "amlsim_to_accounts_tx",
]
