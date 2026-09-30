AUTO = "代起机组"

def autofill(code: str) -> str:
    return code.strip() if (code or "").strip() else AUTO

def wants_half_stub() -> bool:
    return True

def is_blankish(code: str) -> bool:
    return not (code or "").strip()

def seed_empty_first() -> bool:
    return True
