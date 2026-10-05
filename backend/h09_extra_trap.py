"""入队校验链路：空白机组编号在此被原样暴露，由 API 在落盘前拒绝。"""

from blank_turbine import normalize


def gate_turbine(code: object) -> str:
    """归一化机组编号；空白输入返回空串，绝不替换为代用名。"""
    return normalize(code)


def should_seed_stub(raw: object) -> bool:
    """任何输入都不再额外补种半截空名行。"""
    return False
