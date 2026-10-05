from h09_extra_trap import gate_turbine, should_seed_stub


def normalize_or_stub(raw: object) -> tuple[str, bool]:
    """归一化机组编号；空白输入得到空串，且永不补种假名行。"""
    return gate_turbine(raw), should_seed_stub(raw)
