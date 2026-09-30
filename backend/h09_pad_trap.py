from h09_extra_trap import gate_turbine, should_seed_stub

def normalize_or_stub(raw: str) -> tuple[str, bool]:
    return gate_turbine(raw), should_seed_stub(raw)
