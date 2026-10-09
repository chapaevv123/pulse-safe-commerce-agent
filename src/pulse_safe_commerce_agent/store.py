from __future__ import annotations

import json
import sqlite3
from pathlib import Path


class Store:
    def __init__(self, path: str):
        self.path = path
        if path != ":memory:":
            Path(path).parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(path, check_same_thread=False)
        self.db.row_factory = sqlite3.Row
        self.db.executescript("""
        CREATE TABLE IF NOT EXISTS payment_requests(
          request_id TEXT PRIMARY KEY,status TEXT NOT NULL,intent_json TEXT NOT NULL,intent_hash TEXT NOT NULL,
          approval_hash TEXT,approval_at TEXT,idempotency_key TEXT UNIQUE,paypal_order_id TEXT UNIQUE,
          paypal_capture_id TEXT,paypal_status TEXT,error_code TEXT,receipt_json TEXT,created_at TEXT NOT NULL,updated_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS agent_trace(
          request_id TEXT NOT NULL,stage TEXT NOT NULL,status TEXT NOT NULL,input_summary TEXT NOT NULL,
          decision TEXT NOT NULL,reason_code TEXT NOT NULL,created_at TEXT NOT NULL,
          PRIMARY KEY(request_id,stage));
        """)

    def create(self, row: dict) -> None:
        self.db.execute("INSERT INTO payment_requests(request_id,status,intent_json,intent_hash,idempotency_key,created_at,updated_at) VALUES(?,?,?,?,?,?,?)",
                        (row["request_id"], row["status"], json.dumps(row["intent"], sort_keys=True), row["intent_hash"], row["idempotency_key"], row["created_at"], row["created_at"]))
        self.db.commit()

    def get(self, request_id: str):
        row = self.db.execute("SELECT * FROM payment_requests WHERE request_id=?", (request_id,)).fetchone()
        return dict(row) if row else None

    def update(self, request_id: str, **values) -> None:
        allowed = {"status", "approval_hash", "approval_at", "paypal_order_id", "paypal_capture_id", "paypal_status", "error_code", "receipt_json", "updated_at"}
        if not values or not set(values) <= allowed:
            raise ValueError("Unsupported update")
        sql = ",".join(f"{k}=?" for k in values)
        self.db.execute(f"UPDATE payment_requests SET {sql} WHERE request_id=?", (*values.values(), request_id))
        self.db.commit()

    def trace(self, request_id: str, stage: str, status: str, summary: str, decision: str, reason: str, at: str) -> None:
        self.db.execute("INSERT OR REPLACE INTO agent_trace VALUES(?,?,?,?,?,?,?)", (request_id, stage, status, summary, decision, reason, at))
        self.db.commit()

    def traces(self, request_id: str) -> list[dict]:
        return [dict(r) for r in self.db.execute("SELECT * FROM agent_trace WHERE request_id=? ORDER BY rowid", (request_id,))]
