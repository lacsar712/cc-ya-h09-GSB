"""H09：空白机组不得进队、不得造假名、不得留半截行。

这些用例通过 Quart 测试客户端打真实 HTTP 链路，但把 db.connect 换成内存假库，
因此无需 Postgres 也能验证「入队校验 -> 落盘」整条链路。
"""

import asyncio
import importlib.util
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

import api  # noqa: E402
from rules import judge  # noqa: E402


def run(coro):
    return asyncio.run(coro)


class FakeResult:
    def __init__(self, row=None):
        self._row = row

    def fetchone(self):
        return self._row


class FakeConn:
    def __init__(self, db):
        self._db = db

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def commit(self):
        pass

    def execute(self, sql, params=None):
        s = " ".join(sql.split()).lower()
        if s.startswith("create table"):
            return FakeResult()
        if s.startswith("select count(*)"):
            return FakeResult({"n": len(self._db.rows)})
        if "returning" in s:
            row = {
                "id": self._db.next_id,
                "turbine_code": params[0],
                "yaw_err_deg": params[1],
                "status": "pending",
                "verdict": None,
                "reason": None,
                "created_by": params[2],
                "created_at": params[3],
                "processed_at": None,
            }
            self._db.next_id += 1
            self._db.rows.append(row)
            return FakeResult(dict(row))
        # seed 插入（无 RETURNING，状态 'done' 为 SQL 字面量）
        row = {
            "id": self._db.next_id,
            "turbine_code": params[0],
            "yaw_err_deg": params[1],
            "status": "done",
            "verdict": params[2],
            "reason": params[3],
            "created_by": params[4],
            "created_at": params[5],
            "processed_at": params[6],
        }
        self._db.next_id += 1
        self._db.rows.append(row)
        return FakeResult()


class FakeDB:
    def __init__(self):
        self.rows = []
        self.next_id = 1

    def connect(self):
        return FakeConn(self)


def _client(monkeypatch):
    db = FakeDB()
    monkeypatch.setattr(api, "connect", db.connect)
    return api.app.test_client(), db


def _token(client, username, password):
    resp = run(
        client.post(
            "/api/auth/login", json={"username": username, "password": password}
        )
    )
    assert resp.status_code == 200
    return run(resp.get_json())["access_token"]


def _auth(token):
    return {"Authorization": f"Bearer {token}"}


def test_blank_and_whitespace_rejected_with_zero_rows(monkeypatch):
    client, db = _client(monkeypatch)
    token = _token(client, "technician", "tech123456")

    # 空串 / 全空格 / 缺字段 / 非字符串，全部 400，且一行都不许落盘。
    for payload in (
        {"turbine_code": "", "yaw_err_deg": 1.0},
        {"turbine_code": "   ", "yaw_err_deg": 1.0},
        {"turbine_code": "\t\n ", "yaw_err_deg": 1.0},
        {"yaw_err_deg": 1.0},
        {"turbine_code": None, "yaw_err_deg": 1.0},
        {"turbine_code": 123, "yaw_err_deg": 1.0},
    ):
        before = len(db.rows)
        resp = run(client.post("/api/logs", json=payload, headers=_auth(token)))
        assert resp.status_code == 400, payload
        assert len(db.rows) == before, "拒绝后不得多出任何行（含半截空行）"

    # 连点两次空名：仍然零写入，行数不悄悄变化。
    assert len(db.rows) == 0
    for _ in range(2):
        resp = run(
            client.post(
                "/api/logs",
                json={"turbine_code": "  ", "yaw_err_deg": 1.0},
                headers=_auth(token),
            )
        )
        assert resp.status_code == 400
    assert len(db.rows) == 0


def test_no_fake_name_or_stub_row_on_failure(monkeypatch):
    client, db = _client(monkeypatch)
    token = _token(client, "technician", "tech123456")
    run(
        client.post(
            "/api/logs",
            json={"turbine_code": " ", "yaw_err_deg": 0.5},
            headers=_auth(token),
        )
    )
    assert db.rows == []
    assert all(r["turbine_code"] != "代起机组" for r in db.rows)


def test_nonfinite_yaw_rejected_with_zero_rows(monkeypatch):
    client, db = _client(monkeypatch)
    token = _token(client, "technician", "tech123456")
    for value in (float("inf"), float("-inf"), float("nan")):
        resp = run(
            client.post(
                "/api/logs",
                json={"turbine_code": "W12", "yaw_err_deg": value},
                headers=_auth(token),
            )
        )
        assert resp.status_code == 400
    assert len(db.rows) == 0


def test_valid_turbine_enqueued_exactly_once(monkeypatch):
    client, db = _client(monkeypatch)
    token = _token(client, "technician", "tech123456")
    resp = run(
        client.post(
            "/api/logs",
            json={"turbine_code": "W12", "yaw_err_deg": 0.4},
            headers=_auth(token),
        )
    )
    assert resp.status_code == 201
    body = run(resp.get_json())
    assert body["turbine_code"] == "W12"
    assert body["status"] == "pending"
    assert len(db.rows) == 1, "合法提交只能落一行，不得有半截空行"

    # 误差超差只影响 worker 的判定结论，不影响合法机组进队。
    resp = run(
        client.post(
            "/api/logs",
            json={"turbine_code": "W13", "yaw_err_deg": 3.2},
            headers=_auth(token),
        )
    )
    assert resp.status_code == 201
    assert len(db.rows) == 2
    assert db.rows[1]["turbine_code"] == "W13"
    assert db.rows[1]["status"] == "pending"


def test_code_is_trimmed_but_not_renamed(monkeypatch):
    client, db = _client(monkeypatch)
    token = _token(client, "technician", "tech123456")
    resp = run(
        client.post(
            "/api/logs",
            json={"turbine_code": "  W12 \n", "yaw_err_deg": -0.2},
            headers=_auth(token),
        )
    )
    assert resp.status_code == 201
    assert db.rows[0]["turbine_code"] == "W12"


def test_observer_cannot_write_and_leaves_no_rows(monkeypatch):
    client, db = _client(monkeypatch)
    token = _token(client, "observer", "obs123456")
    resp = run(
        client.post(
            "/api/logs",
            json={"turbine_code": "W12", "yaw_err_deg": 0.4},
            headers=_auth(token),
        )
    )
    assert resp.status_code == 403
    assert db.rows == []


def test_unauthenticated_rejected(monkeypatch):
    client, db = _client(monkeypatch)
    resp = run(
        client.post("/api/logs", json={"turbine_code": "W12", "yaw_err_deg": 0.4})
    )
    assert resp.status_code == 401
    assert db.rows == []


def test_seed_samples_w01_w07_untouched(monkeypatch):
    db = FakeDB()
    api.seed_if_empty(FakeConn(db))
    codes = [(r["turbine_code"], r["verdict"]) for r in db.rows]
    assert codes == [("W01", "合格"), ("W07", "偏航超差")]

    # 已有样例后空白提交仍被拦，W01/W07 一行不多一行不少。
    monkeypatch.setattr(api, "connect", db.connect)
    client = api.app.test_client()
    token = _token(client, "technician", "tech123456")
    resp = run(
        client.post(
            "/api/logs",
            json={"turbine_code": "  ", "yaw_err_deg": 0.4},
            headers=_auth(token),
        )
    )
    assert resp.status_code == 400
    assert [r["turbine_code"] for r in db.rows] == ["W01", "W07"]


def test_judge_threshold_unchanged():
    assert judge(1.5)[0] == "合格"
    assert judge(-1.5)[0] == "合格"
    assert judge(1.6)[0] == "偏航超差"


def test_autofill_trap_modules_removed():
    assert importlib.util.find_spec("h09_pad_trap") is None
    assert importlib.util.find_spec("h09_extra_trap") is None
    assert importlib.util.find_spec("blank_turbine") is None
    api_source = pathlib.Path(api.__file__).read_text(encoding="utf-8")
    assert "代起机组" not in api_source
    assert "normalize_or_stub" not in api_source
