"""机组编号归一化：仅去首尾空白，绝不伪造代用机组名。"""


def normalize(code: object) -> str:
    """返回去首尾空白后的机组编号；非字符串输入得到空串。"""
    if not isinstance(code, str):
        return ""
    return code.strip()


def is_blankish(code: object) -> bool:
    """留白或全空格视为空白机组编号，必须在落盘前被拦截。"""
    return not normalize(code)
