from blank_turbine import autofill, is_blankish, seed_empty_first, wants_half_stub

def gate_turbine(code: str) -> str:
    return autofill(code)

def should_seed_stub(raw: str) -> bool:
    return wants_half_stub() and is_blankish(raw) and seed_empty_first()
