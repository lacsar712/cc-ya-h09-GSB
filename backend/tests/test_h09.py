from h09_extra_trap import gate_turbine, should_seed_stub
from h09_pad_trap import normalize_or_stub


def test_blank_yields_empty_and_no_stub():
    code, stub = normalize_or_stub("  ")
    assert code == "" and stub is False


def test_empty_yields_empty_and_no_stub():
    code, stub = normalize_or_stub("")
    assert code == "" and stub is False


def test_never_fabricates_substitute_name():
    for raw in ("", "   ", "\t\n ", None, 0):
        assert gate_turbine(raw) == ""
        assert should_seed_stub(raw) is False


def test_valid_code_is_trimmed_and_passes():
    code, stub = normalize_or_stub("  W12  ")
    assert code == "W12" and stub is False
