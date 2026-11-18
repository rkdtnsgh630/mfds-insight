"""SQLite 저장소: 원본 레코드, 수집 실행 이력, 변경 이력.

설계 원칙 (docs/DATA_MODEL.md):
- API 원본 레코드를 JSON 그대로 보관한다 (표준화 테이블은 이 위에 만든다).
- 레코드별 최초·최근 수집 시각과 출처 API를 남긴다.
- 'API에서 더 이상 조회되지 않음'은 is_present=0으로 표시할 뿐, 삭제·취하로 단정하지 않는다.
- 어떤 API의 첫 '완전 수집'은 기준선(baseline)이며 변경 이력을 남기지 않는다.
- 결측 판정(removed)은 완전 수집일 때만, 그리고 건수가 급감하지 않았을 때만 한다.
"""

import hashlib
import json
import sqlite3
from datetime import datetime, timezone

SCHEMA = """
CREATE TABLE IF NOT EXISTS api_source (
    api_id      TEXT PRIMARY KEY,
    name        TEXT NOT NULL,
    data_id     TEXT NOT NULL,
    path        TEXT NOT NULL,
    key_fields  TEXT,
    tier        TEXT NOT NULL,
    source_url  TEXT NOT NULL,
    updated_at  TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS collect_run (
    run_id      INTEGER PRIMARY KEY AUTOINCREMENT,
    started_at  TEXT NOT NULL,
    finished_at TEXT,
    status      TEXT NOT NULL,
    trigger     TEXT,
    selection   TEXT,
    api_calls   INTEGER DEFAULT 0
);
CREATE TABLE IF NOT EXISTS collect_api_run (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id          INTEGER NOT NULL REFERENCES collect_run(run_id),
    api_id          TEXT NOT NULL,
    started_at      TEXT NOT NULL,
    finished_at     TEXT,
    status          TEXT NOT NULL,
    total_count     INTEGER,
    pages           INTEGER DEFAULT 0,
    fetched         INTEGER DEFAULT 0,
    added           INTEGER DEFAULT 0,
    updated         INTEGER DEFAULT 0,
    removed         INTEGER DEFAULT 0,
    reappeared      INTEGER DEFAULT 0,
    duplicates      INTEGER DEFAULT 0,
    key_collisions  INTEGER DEFAULT 0,
    note            TEXT,
    error           TEXT
);
CREATE INDEX IF NOT EXISTS ix_api_run_api ON collect_api_run(api_id, status);
CREATE TABLE IF NOT EXISTS raw_record (
    api_id          TEXT NOT NULL,
    record_key      TEXT NOT NULL,
    record_hash     TEXT NOT NULL,
    payload         TEXT NOT NULL,
    first_seen_run  INTEGER NOT NULL,
    last_seen_run   INTEGER NOT NULL,
    first_seen_at   TEXT NOT NULL,
    last_seen_at    TEXT NOT NULL,
    is_present      INTEGER NOT NULL DEFAULT 1,
    PRIMARY KEY (api_id, record_key)
);
CREATE INDEX IF NOT EXISTS ix_raw_present ON raw_record(api_id, is_present);
CREATE TABLE IF NOT EXISTS change_log (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id       INTEGER NOT NULL,
    api_id       TEXT NOT NULL,
    record_key   TEXT NOT NULL,
    change_type  TEXT NOT NULL CHECK (change_type IN ('added','updated','removed','reappeared')),
    old_payload  TEXT,
    new_payload  TEXT,
    changed_at   TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_change_api_time ON change_log(api_id, changed_at);
"""

# 완전 수집이어도 이번 건수가 직전 존재 건수의 이 비율 미만이면 결측 판정을 보류한다.
REMOVAL_GUARD_RATIO = 0.5


def utcnow():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def connect(path):
    con = sqlite3.connect(path)
    con.executescript(SCHEMA)
    return con


def canonical(record):
    return json.dumps(record, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def record_hash(canonical_text):
    return hashlib.sha1(canonical_text.encode("utf-8")).hexdigest()


def build_key(record, key_fields, hash_hex):
    if not key_fields:
        return "h:" + hash_hex
    values = []
    for f in key_fields:
        v = record.get(f)
        values.append("" if v is None else str(v).strip())
    if all(v == "" for v in values):
        return "h:" + hash_hex
    return "|".join(values)


def register_apis(con, apis):
    now = utcnow()
    for a in apis:
        con.execute(
            """INSERT INTO api_source(api_id, name, data_id, path, key_fields, tier, source_url, updated_at)
               VALUES (?,?,?,?,?,?,?,?)
               ON CONFLICT(api_id) DO UPDATE SET name=excluded.name, data_id=excluded.data_id,
                 path=excluded.path, key_fields=excluded.key_fields, tier=excluded.tier,
                 source_url=excluded.source_url, updated_at=excluded.updated_at""",
            (a["id"], a["name"], a["data_id"], a["path"], json.dumps(a["key"]) if a["key"] else None,
             a["tier"], f"https://www.data.go.kr/data/{a['data_id']}/openapi.do", now))
    con.commit()


def start_run(con, trigger, selection):
    cur = con.execute("INSERT INTO collect_run(started_at, status, trigger, selection) VALUES (?,?,?,?)",
                      (utcnow(), "running", trigger, selection))
    con.commit()
    return cur.lastrowid


def finish_run(con, run_id, status, api_calls):
    con.execute("UPDATE collect_run SET finished_at=?, status=?, api_calls=? WHERE run_id=?",
                (utcnow(), status, api_calls, run_id))
    con.commit()


def strip_fields(record, fields):
    if not fields:
        return record
    return {k: v for k, v in record.items() if k not in fields}


def migrate_dropped_fields(con, api):
    """drop_fields가 새로 지정된 API의 기존 원본에서 해당 필드를 지운다.

    필드 삭제는 데이터 변경이 아니라 저장 방식 변경이므로 change_log에 남기지 않고
    해시만 다시 계산한다. 이미 지워진 행은 건드리지 않는다. 바꾼 행 수를 돌려준다.
    """
    fields = api.get("drop_fields") or []
    if not fields:
        return 0
    cond = " OR ".join("payload LIKE ?" for _ in fields)
    args = [api["id"]] + [f'%"{f}":%' for f in fields]
    rows = con.execute(f"SELECT record_key, payload FROM raw_record WHERE api_id=? AND ({cond})", args).fetchall()
    for key, payload in rows:
        text = canonical(strip_fields(json.loads(payload), fields))
        con.execute("UPDATE raw_record SET payload=?, record_hash=? WHERE api_id=? AND record_key=?",
                    (text, record_hash(text), api["id"], key))
    con.commit()
    return len(rows)


def migrate_keys(con, api):
    """키 필드가 새로 지정된 API의 기존 원본(해시 키 'h:...')을 새 키로 옮긴다.

    키 지정은 데이터 변경이 아니라 식별 방식 변경이므로 change_log를 새로 남기지 않는다
    (기존 change_log의 키는 같이 바꾼다). 새 키가 겹치면 수집 때와 같이 '#해시12자리'를 붙인다.
    바꾼 행 수를 돌려준다. 이미 옮긴 행은 건드리지 않는다.
    """
    fields = api.get("key")
    if not fields:
        return 0
    rows = con.execute("SELECT record_key, record_hash, payload FROM raw_record WHERE api_id=? AND record_key LIKE 'h:%'",
                       (api["id"],)).fetchall()
    moved = 0
    for old, h, payload in rows:
        new = build_key(json.loads(payload), fields, h)
        if new == old:
            continue
        if con.execute("SELECT 1 FROM raw_record WHERE api_id=? AND record_key=?", (api["id"], new)).fetchone():
            new = f"{new}#{h[:12]}"
            if con.execute("SELECT 1 FROM raw_record WHERE api_id=? AND record_key=?", (api["id"], new)).fetchone():
                continue
        con.execute("UPDATE raw_record SET record_key=? WHERE api_id=? AND record_key=?", (new, api["id"], old))
        con.execute("UPDATE change_log SET record_key=? WHERE api_id=? AND record_key=?", (new, api["id"], old))
        moved += 1
    con.commit()
    return moved


def has_complete_run(con, api_id):
    return con.execute("SELECT 1 FROM collect_api_run WHERE api_id=? AND status='complete' LIMIT 1",
                       (api_id,)).fetchone() is not None


def last_success_started(con, api_id):
    """최근 성공(완전 또는 증분) 수집의 시작 시각 (UTC 문자열) 또는 None."""
    return con.execute("SELECT MAX(started_at) FROM collect_api_run WHERE api_id=? AND status IN ('complete','incremental')",
                       (api_id,)).fetchone()[0]


def missing_keys(con, source_api_id, target_api_id, limit):
    """source에는 현재 있는데 target에는 한 번도 없었던 키 (키 충돌 접미 '#' 제외)."""
    return [k for (k,) in con.execute(
        "SELECT record_key FROM raw_record s WHERE s.api_id=? AND s.is_present=1 AND s.record_key NOT LIKE 'h:%'"
        " AND instr(s.record_key, '#')=0 AND NOT EXISTS (SELECT 1 FROM raw_record t WHERE t.api_id=?"
        " AND t.record_key=s.record_key) ORDER BY s.record_key LIMIT ?",
        (source_api_id, target_api_id, limit))]


class ApiRun:
    """한 API의 한 번 수집을 기록한다."""

    def __init__(self, con, run_id, api):
        self.con = con
        self.run_id = run_id
        self.api = api
        self.api_id = api["id"]
        self.track_changes = con.execute(
            "SELECT 1 FROM collect_api_run WHERE api_id=? AND status='complete' LIMIT 1",
            (self.api_id,)).fetchone() is not None
        self.seen = {}
        self.stats = {k: 0 for k in ("fetched", "added", "updated", "removed", "reappeared",
                                     "duplicates", "key_collisions")}
        cur = con.execute("INSERT INTO collect_api_run(run_id, api_id, started_at, status) VALUES (?,?,?,?)",
                          (run_id, self.api_id, utcnow(), "running"))
        self.id = cur.lastrowid
        con.commit()

    def _log(self, change_type, key, old_payload, new_payload, now):
        if self.track_changes:
            self.con.execute(
                "INSERT INTO change_log(run_id, api_id, record_key, change_type, old_payload, new_payload, changed_at)"
                " VALUES (?,?,?,?,?,?,?)",
                (self.run_id, self.api_id, key, change_type, old_payload, new_payload, now))

    def add_records(self, records):
        now = utcnow()
        con = self.con
        drop = self.api.get("drop_fields")
        for rec in records:
            rec = strip_fields(rec, drop)
            text = canonical(rec)
            h = record_hash(text)
            key = build_key(rec, self.api.get("key"), h)
            self.stats["fetched"] += 1
            if key in self.seen:
                if self.seen[key] == h:
                    self.stats["duplicates"] += 1
                    continue
                key = f"{key}#{h[:12]}"
                self.stats["key_collisions"] += 1
                if key in self.seen:
                    self.stats["duplicates"] += 1
                    continue
            self.seen[key] = h
            row = con.execute(
                "SELECT record_hash, payload, is_present FROM raw_record WHERE api_id=? AND record_key=?",
                (self.api_id, key)).fetchone()
            if row is None:
                con.execute(
                    "INSERT INTO raw_record(api_id, record_key, record_hash, payload, first_seen_run, last_seen_run,"
                    " first_seen_at, last_seen_at, is_present) VALUES (?,?,?,?,?,?,?,?,1)",
                    (self.api_id, key, h, text, self.run_id, self.run_id, now, now))
                self.stats["added"] += 1
                self._log("added", key, None, text, now)
                continue
            old_hash, old_payload, was_present = row
            if old_hash != h:
                con.execute(
                    "UPDATE raw_record SET record_hash=?, payload=?, last_seen_run=?, last_seen_at=?, is_present=1"
                    " WHERE api_id=? AND record_key=?",
                    (h, text, self.run_id, now, self.api_id, key))
                self.stats["updated"] += 1
                self._log("updated", key, old_payload, text, now)
            else:
                con.execute(
                    "UPDATE raw_record SET last_seen_run=?, last_seen_at=?, is_present=1"
                    " WHERE api_id=? AND record_key=?",
                    (self.run_id, now, self.api_id, key))
                if not was_present:
                    self.stats["reappeared"] += 1
                    self._log("reappeared", key, None, text, now)

    def finish(self, complete, total_count, pages, error=None, incremental=False, extra_notes=()):
        """incremental=True: 증분 수집. 오류가 없으면 status='incremental', 결측 판정은 하지 않는다."""
        now = utcnow()
        con = self.con
        notes = list(extra_notes)
        if incremental and not error:
            status = "incremental"
        elif complete:
            missing_count = con.execute(
                "SELECT COUNT(*) FROM raw_record WHERE api_id=? AND is_present=1 AND last_seen_run<>?",
                (self.api_id, self.run_id)).fetchone()[0]
            present_before = missing_count + len(self.seen)
            if missing_count and len(self.seen) < present_before * REMOVAL_GUARD_RATIO:
                notes.append(f"결측 판정 보류: 이번 {len(self.seen)}건이 직전 {present_before}건의 "
                             f"{int(REMOVAL_GUARD_RATIO * 100)}% 미만")
            elif missing_count:
                missing = con.execute(
                    "SELECT record_key, payload FROM raw_record WHERE api_id=? AND is_present=1 AND last_seen_run<>?",
                    (self.api_id, self.run_id)).fetchall()
                for key, payload in missing:
                    self._log("removed", key, payload, None, now)
                con.execute("UPDATE raw_record SET is_present=0 WHERE api_id=? AND is_present=1 AND last_seen_run<>?",
                            (self.api_id, self.run_id))
                self.stats["removed"] = len(missing)
            if not self.track_changes:
                notes.append("기준선 수집 (변경 이력 미기록)")
            status = "complete"
        elif self.stats["fetched"]:
            status = "partial"
        else:
            status = "failed"
        note = "; ".join(notes) or None
        s = self.stats
        con.execute(
            """UPDATE collect_api_run SET finished_at=?, status=?, total_count=?, pages=?, fetched=?, added=?,
               updated=?, removed=?, reappeared=?, duplicates=?, key_collisions=?, note=?, error=? WHERE id=?""",
            (now, status, total_count, pages, s["fetched"], s["added"], s["updated"], s["removed"],
             s["reappeared"], s["duplicates"], s["key_collisions"], note, error, self.id))
        con.commit()
        return status, note
