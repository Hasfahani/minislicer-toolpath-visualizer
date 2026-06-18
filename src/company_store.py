# Purpose: Persists MiniSlicer users, qualified builds, model snapshots, recommendations, and audit events.
# Reason: A company workflow needs durable state, role-based approvals, and traceability across sessions.
"""SQLite-backed operational store for MiniSlicer company deployments."""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import secrets
import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator, Sequence

from src.process_intelligence import BuildRecord

PBKDF2_ITERATIONS = 310_000
VALID_ROLES = frozenset({"admin", "engineer", "operator", "viewer"})
BUILD_STATES = frozenset({"submitted", "approved", "rejected"})
MODEL_STATES = frozenset({"candidate", "approved", "retired"})
RECOMMENDATION_STATES = frozenset({"generated", "approved", "rejected"})


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def default_database_path() -> Path:
    return Path(os.getenv("MINISLICER_DB_PATH", "data/minislicer.db"))


def _json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def hash_password(password: str) -> str:
    """Return a versioned PBKDF2 password representation."""
    if len(password) < 12:
        raise ValueError("Password must contain at least 12 characters.")
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        PBKDF2_ITERATIONS,
    )
    return f"pbkdf2_sha256${PBKDF2_ITERATIONS}${salt.hex()}${digest.hex()}"


def verify_password(password: str, encoded: str) -> bool:
    try:
        algorithm, iterations, salt_hex, expected_hex = encoded.split("$", 3)
        if algorithm != "pbkdf2_sha256":
            return False
        actual = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            bytes.fromhex(salt_hex),
            int(iterations),
        )
        return hmac.compare_digest(actual.hex(), expected_hex)
    except (TypeError, ValueError):
        return False


@dataclass(frozen=True)
class User:
    username: str
    role: str
    active: bool


class CompanyStore:
    """Durable operational store with explicit approval and audit operations."""

    def __init__(self, path: str | Path | None = None) -> None:
        self.path = Path(path) if path is not None else default_database_path()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.initialize()

    @contextmanager
    def connection(self) -> Iterator[sqlite3.Connection]:
        connection = sqlite3.connect(self.path, timeout=30)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA journal_mode = WAL")
        try:
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def initialize(self) -> None:
        with self.connection() as db:
            db.executescript(
                """
                CREATE TABLE IF NOT EXISTS users (
                    username TEXT PRIMARY KEY,
                    password_hash TEXT NOT NULL,
                    role TEXT NOT NULL,
                    active INTEGER NOT NULL DEFAULT 1,
                    created_at TEXT NOT NULL,
                    created_by TEXT
                );

                CREATE TABLE IF NOT EXISTS build_records (
                    build_id TEXT PRIMARY KEY,
                    machine_id TEXT NOT NULL,
                    material_id TEXT NOT NULL,
                    geometry_family TEXT NOT NULL,
                    started_at TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    state TEXT NOT NULL,
                    submitted_by TEXT NOT NULL,
                    submitted_at TEXT NOT NULL,
                    reviewed_by TEXT,
                    reviewed_at TEXT,
                    review_note TEXT
                );

                CREATE TABLE IF NOT EXISTS model_snapshots (
                    model_version TEXT PRIMARY KEY,
                    machine_id TEXT NOT NULL,
                    material_id TEXT NOT NULL,
                    build_ids_json TEXT NOT NULL,
                    metrics_json TEXT NOT NULL,
                    state TEXT NOT NULL,
                    created_by TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    reviewed_by TEXT,
                    reviewed_at TEXT,
                    review_note TEXT
                );

                CREATE TABLE IF NOT EXISTS recommendations (
                    recommendation_id TEXT PRIMARY KEY,
                    model_version TEXT NOT NULL,
                    machine_id TEXT NOT NULL,
                    material_id TEXT NOT NULL,
                    request_json TEXT NOT NULL,
                    result_json TEXT NOT NULL,
                    state TEXT NOT NULL,
                    created_by TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    reviewed_by TEXT,
                    reviewed_at TEXT,
                    review_note TEXT,
                    FOREIGN KEY(model_version) REFERENCES model_snapshots(model_version)
                );

                CREATE TABLE IF NOT EXISTS audit_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    occurred_at TEXT NOT NULL,
                    actor TEXT NOT NULL,
                    action TEXT NOT NULL,
                    entity_type TEXT NOT NULL,
                    entity_id TEXT NOT NULL,
                    details_json TEXT NOT NULL
                );

                CREATE INDEX IF NOT EXISTS idx_build_state
                    ON build_records(state, machine_id, material_id);
                CREATE INDEX IF NOT EXISTS idx_model_state
                    ON model_snapshots(state, machine_id, material_id);
                CREATE INDEX IF NOT EXISTS idx_recommendation_state
                    ON recommendations(state, created_at);
                CREATE INDEX IF NOT EXISTS idx_audit_time
                    ON audit_log(occurred_at DESC);
                """
            )

    def has_users(self) -> bool:
        with self.connection() as db:
            return bool(db.execute("SELECT 1 FROM users LIMIT 1").fetchone())

    def create_user(
        self,
        username: str,
        password: str,
        role: str,
        *,
        actor: str,
    ) -> User:
        clean_username = username.strip().lower()
        if len(clean_username) < 3:
            raise ValueError("Username must contain at least 3 characters.")
        if role not in VALID_ROLES:
            raise ValueError(f"Unsupported role: {role}")
        with self.connection() as db:
            db.execute(
                """
                INSERT INTO users(username, password_hash, role, active, created_at, created_by)
                VALUES (?, ?, ?, 1, ?, ?)
                """,
                (clean_username, hash_password(password), role, utc_now(), actor),
            )
            self._audit_db(
                db,
                actor,
                "user.created",
                "user",
                clean_username,
                {"role": role},
            )
        return User(clean_username, role, True)

    def authenticate(self, username: str, password: str) -> User | None:
        with self.connection() as db:
            row = db.execute(
                "SELECT username, password_hash, role, active FROM users WHERE username = ?",
                (username.strip().lower(),),
            ).fetchone()
            if row is None or not row["active"] or not verify_password(password, row["password_hash"]):
                return None
            self._audit_db(
                db,
                row["username"],
                "session.login",
                "user",
                row["username"],
                {},
            )
            return User(row["username"], row["role"], bool(row["active"]))

    def list_users(self) -> list[dict[str, Any]]:
        with self.connection() as db:
            return [
                dict(row)
                for row in db.execute(
                    "SELECT username, role, active, created_at, created_by FROM users ORDER BY username"
                ).fetchall()
            ]

    def set_user_active(self, username: str, active: bool, *, actor: str) -> None:
        with self.connection() as db:
            db.execute(
                "UPDATE users SET active = ? WHERE username = ?",
                (int(active), username),
            )
            self._audit_db(
                db,
                actor,
                "user.activated" if active else "user.deactivated",
                "user",
                username,
                {},
            )

    def submit_build_records(
        self,
        records: Sequence[BuildRecord],
        *,
        actor: str,
    ) -> dict[str, int]:
        inserted = 0
        updated = 0
        with self.connection() as db:
            for record in records:
                record.validate()
                exists = db.execute(
                    "SELECT 1 FROM build_records WHERE build_id = ?",
                    (record.build_id,),
                ).fetchone()
                db.execute(
                    """
                    INSERT INTO build_records(
                        build_id, machine_id, material_id, geometry_family, started_at,
                        payload_json, state, submitted_by, submitted_at,
                        reviewed_by, reviewed_at, review_note
                    )
                    VALUES (?, ?, ?, ?, ?, ?, 'submitted', ?, ?, NULL, NULL, NULL)
                    ON CONFLICT(build_id) DO UPDATE SET
                        machine_id = excluded.machine_id,
                        material_id = excluded.material_id,
                        geometry_family = excluded.geometry_family,
                        started_at = excluded.started_at,
                        payload_json = excluded.payload_json,
                        state = 'submitted',
                        submitted_by = excluded.submitted_by,
                        submitted_at = excluded.submitted_at,
                        reviewed_by = NULL,
                        reviewed_at = NULL,
                        review_note = NULL
                    """,
                    (
                        record.build_id,
                        record.machine_id,
                        record.material_id,
                        record.geometry_family,
                        record.started_at,
                        _json(record.to_dict()),
                        actor,
                        utc_now(),
                    ),
                )
                inserted += int(exists is None)
                updated += int(exists is not None)
                self._audit_db(
                    db,
                    actor,
                    "build.submitted",
                    "build",
                    record.build_id,
                    {"replaced": exists is not None},
                )
        return {"inserted": inserted, "updated": updated}

    def list_builds(
        self,
        *,
        state: str | None = None,
        limit: int = 500,
    ) -> list[dict[str, Any]]:
        query = """
            SELECT build_id, machine_id, material_id, geometry_family, started_at,
                   state, submitted_by, submitted_at, reviewed_by, reviewed_at, review_note
            FROM build_records
        """
        parameters: list[Any] = []
        if state is not None:
            query += " WHERE state = ?"
            parameters.append(state)
        query += " ORDER BY started_at DESC, build_id LIMIT ?"
        parameters.append(max(1, int(limit)))
        with self.connection() as db:
            return [dict(row) for row in db.execute(query, parameters).fetchall()]

    def review_build(
        self,
        build_id: str,
        state: str,
        *,
        actor: str,
        note: str = "",
    ) -> None:
        if state not in {"approved", "rejected"}:
            raise ValueError("Build review state must be approved or rejected.")
        with self.connection() as db:
            result = db.execute(
                """
                UPDATE build_records
                SET state = ?, reviewed_by = ?, reviewed_at = ?, review_note = ?
                WHERE build_id = ?
                """,
                (state, actor, utc_now(), note.strip(), build_id),
            )
            if result.rowcount != 1:
                raise ValueError(f"Unknown build ID: {build_id}")
            self._audit_db(
                db,
                actor,
                f"build.{state}",
                "build",
                build_id,
                {"note": note.strip()},
            )

    def approved_records(
        self,
        *,
        machine_id: str | None = None,
        material_id: str | None = None,
        build_ids: Sequence[str] | None = None,
    ) -> list[BuildRecord]:
        clauses = ["state = 'approved'"]
        parameters: list[Any] = []
        if machine_id is not None:
            clauses.append("machine_id = ?")
            parameters.append(machine_id)
        if material_id is not None:
            clauses.append("material_id = ?")
            parameters.append(material_id)
        if build_ids is not None:
            if not build_ids:
                return []
            placeholders = ",".join("?" for _ in build_ids)
            clauses.append(f"build_id IN ({placeholders})")
            parameters.extend(build_ids)
        query = "SELECT payload_json FROM build_records WHERE " + " AND ".join(clauses)
        query += " ORDER BY started_at, build_id"
        with self.connection() as db:
            rows = db.execute(query, parameters).fetchall()
        return [BuildRecord.from_dict(json.loads(row["payload_json"])) for row in rows]

    def register_model(
        self,
        *,
        model_version: str,
        machine_id: str,
        material_id: str,
        build_ids: Sequence[str],
        metrics: dict[str, Any],
        actor: str,
    ) -> None:
        if not build_ids:
            raise ValueError("A model snapshot requires approved build IDs.")
        with self.connection() as db:
            db.execute(
                """
                INSERT INTO model_snapshots(
                    model_version, machine_id, material_id, build_ids_json,
                    metrics_json, state, created_by, created_at
                )
                VALUES (?, ?, ?, ?, ?, 'candidate', ?, ?)
                """,
                (
                    model_version,
                    machine_id,
                    material_id,
                    _json(list(build_ids)),
                    _json(metrics),
                    actor,
                    utc_now(),
                ),
            )
            self._audit_db(
                db,
                actor,
                "model.registered",
                "model",
                model_version,
                {"machine_id": machine_id, "material_id": material_id, "build_count": len(build_ids)},
            )

    def list_models(self, *, state: str | None = None) -> list[dict[str, Any]]:
        query = "SELECT * FROM model_snapshots"
        parameters: list[Any] = []
        if state is not None:
            query += " WHERE state = ?"
            parameters.append(state)
        query += " ORDER BY created_at DESC"
        with self.connection() as db:
            rows = db.execute(query, parameters).fetchall()
        result = []
        for row in rows:
            item = dict(row)
            item["build_ids"] = json.loads(item.pop("build_ids_json"))
            item["metrics"] = json.loads(item.pop("metrics_json"))
            result.append(item)
        return result

    def review_model(
        self,
        model_version: str,
        state: str,
        *,
        actor: str,
        note: str = "",
    ) -> None:
        if state not in {"approved", "retired"}:
            raise ValueError("Model review state must be approved or retired.")
        with self.connection() as db:
            row = db.execute(
                "SELECT machine_id, material_id FROM model_snapshots WHERE model_version = ?",
                (model_version,),
            ).fetchone()
            if row is None:
                raise ValueError(f"Unknown model version: {model_version}")
            if state == "approved":
                db.execute(
                    """
                    UPDATE model_snapshots SET state = 'retired'
                    WHERE state = 'approved' AND machine_id = ? AND material_id = ?
                    """,
                    (row["machine_id"], row["material_id"]),
                )
            db.execute(
                """
                UPDATE model_snapshots
                SET state = ?, reviewed_by = ?, reviewed_at = ?, review_note = ?
                WHERE model_version = ?
                """,
                (state, actor, utc_now(), note.strip(), model_version),
            )
            self._audit_db(
                db,
                actor,
                f"model.{state}",
                "model",
                model_version,
                {"note": note.strip()},
            )

    def approved_model(self, machine_id: str, material_id: str) -> dict[str, Any] | None:
        with self.connection() as db:
            row = db.execute(
                """
                SELECT * FROM model_snapshots
                WHERE state = 'approved' AND machine_id = ? AND material_id = ?
                ORDER BY reviewed_at DESC LIMIT 1
                """,
                (machine_id, material_id),
            ).fetchone()
        if row is None:
            return None
        item = dict(row)
        item["build_ids"] = json.loads(item.pop("build_ids_json"))
        item["metrics"] = json.loads(item.pop("metrics_json"))
        return item

    def log_recommendation(
        self,
        *,
        recommendation_id: str,
        model_version: str,
        machine_id: str,
        material_id: str,
        request: dict[str, Any],
        result: dict[str, Any],
        actor: str,
    ) -> None:
        with self.connection() as db:
            db.execute(
                """
                INSERT INTO recommendations(
                    recommendation_id, model_version, machine_id, material_id,
                    request_json, result_json, state, created_by, created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, 'generated', ?, ?)
                """,
                (
                    recommendation_id,
                    model_version,
                    machine_id,
                    material_id,
                    _json(request),
                    _json(result),
                    actor,
                    utc_now(),
                ),
            )
            self._audit_db(
                db,
                actor,
                "recommendation.generated",
                "recommendation",
                recommendation_id,
                {"model_version": model_version},
            )

    def list_recommendations(self, *, limit: int = 250) -> list[dict[str, Any]]:
        with self.connection() as db:
            rows = db.execute(
                "SELECT * FROM recommendations ORDER BY created_at DESC LIMIT ?",
                (max(1, int(limit)),),
            ).fetchall()
        result = []
        for row in rows:
            item = dict(row)
            item["request"] = json.loads(item.pop("request_json"))
            item["result"] = json.loads(item.pop("result_json"))
            result.append(item)
        return result

    def review_recommendation(
        self,
        recommendation_id: str,
        state: str,
        *,
        actor: str,
        note: str = "",
    ) -> None:
        if state not in {"approved", "rejected"}:
            raise ValueError("Recommendation state must be approved or rejected.")
        with self.connection() as db:
            result = db.execute(
                """
                UPDATE recommendations
                SET state = ?, reviewed_by = ?, reviewed_at = ?, review_note = ?
                WHERE recommendation_id = ?
                """,
                (state, actor, utc_now(), note.strip(), recommendation_id),
            )
            if result.rowcount != 1:
                raise ValueError(f"Unknown recommendation ID: {recommendation_id}")
            self._audit_db(
                db,
                actor,
                f"recommendation.{state}",
                "recommendation",
                recommendation_id,
                {"note": note.strip()},
            )

    def audit_events(self, *, limit: int = 500) -> list[dict[str, Any]]:
        with self.connection() as db:
            rows = db.execute(
                "SELECT * FROM audit_log ORDER BY id DESC LIMIT ?",
                (max(1, int(limit)),),
            ).fetchall()
        result = []
        for row in rows:
            item = dict(row)
            item["details"] = json.loads(item.pop("details_json"))
            result.append(item)
        return result

    def counts(self) -> dict[str, int]:
        with self.connection() as db:
            return {
                "users": db.execute("SELECT COUNT(*) FROM users WHERE active = 1").fetchone()[0],
                "builds": db.execute("SELECT COUNT(*) FROM build_records").fetchone()[0],
                "pending_builds": db.execute(
                    "SELECT COUNT(*) FROM build_records WHERE state = 'submitted'"
                ).fetchone()[0],
                "approved_models": db.execute(
                    "SELECT COUNT(*) FROM model_snapshots WHERE state = 'approved'"
                ).fetchone()[0],
                "recommendations": db.execute("SELECT COUNT(*) FROM recommendations").fetchone()[0],
                "pending_recommendations": db.execute(
                    "SELECT COUNT(*) FROM recommendations WHERE state = 'generated'"
                ).fetchone()[0],
            }

    @staticmethod
    def _audit_db(
        db: sqlite3.Connection,
        actor: str,
        action: str,
        entity_type: str,
        entity_id: str,
        details: dict[str, Any],
    ) -> None:
        db.execute(
            """
            INSERT INTO audit_log(occurred_at, actor, action, entity_type, entity_id, details_json)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (utc_now(), actor, action, entity_type, entity_id, _json(details)),
        )


def model_version_for_records(
    records: Sequence[BuildRecord],
    *,
    machine_id: str,
    material_id: str,
    neighbors: int,
    max_applicability_distance: float,
) -> str:
    """Return an immutable content-derived version for one model snapshot."""
    payload = {
        "machine_id": machine_id,
        "material_id": material_id,
        "neighbors": int(neighbors),
        "max_applicability_distance": float(max_applicability_distance),
        "records": [
            {
                "build_id": record.build_id,
                "payload": record.to_dict(),
            }
            for record in sorted(records, key=lambda item: item.build_id)
        ],
    }
    digest = hashlib.sha256(_json(payload).encode("utf-8")).hexdigest()[:16]
    return f"pi-v1-{digest}"
