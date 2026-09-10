"""Offline tests for the read-only, secret-safe incident evidence scanner."""

import importlib
import json
import sqlite3
from pathlib import Path

import pytest

RID = "req_" + "a" * 32
OTHER = "req_" + "b" * 32


@pytest.fixture
def audit(monkeypatch):
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[3] / "tools"))
    return importlib.import_module("reconcile_historical_holds")


def event(**overrides):
    return {
        "responseHeaders": {"x-request-id": RID, "authorization": "SECRET"},
        "statusCode": 502,
        "responseBody": json.dumps(
            {"error": {"code": "provider_unavailable", "message": "PRIVATE PROMPT"}}
        ),
        "requestBodyValues": {"messages": ["PRIVATE PROMPT"]},
        **overrides,
    }


def test_event_fields_are_allowlisted(audit):
    results = list(audit.safe_events("prefix " + json.dumps(event())))
    assert len(results) == 1
    assert results[0]["http_status"] == 502
    assert results[0]["has_usage"] is False
    assert len(results[0]["fingerprint"]) == 64
    assert "SECRET" not in json.dumps(results)
    assert "PRIVATE PROMPT" not in json.dumps(results)


@pytest.mark.parametrize("status", ["SECRET", {"key": "SECRET"}, True, 600])
def test_untrusted_status_is_not_printed(audit, status):
    result = list(audit.safe_events(json.dumps(event(statusCode=status))))[0]
    assert result["http_status"] is None
    assert "SECRET" not in json.dumps(result)


def test_invalid_json_and_invalid_request_ids_are_ignored(audit):
    assert list(audit.safe_events("{broken [1]")) == []
    assert (
        list(
            audit.safe_events(
                json.dumps(event(responseHeaders={"x-request-id": "PRIVATE PROMPT"}))
            )
        )
        == []
    )


def test_scanner_reports_unstructured_references_and_missing_evidence(audit, tmp_path):
    logs = tmp_path / "apps/api"
    logs.mkdir(parents=True)
    (logs / "test.log").write_text(RID + " PRIVATE PROMPT", encoding="utf-8")
    storage = tmp_path / ".local/share/opencode/storage/session_diff"
    storage.mkdir(parents=True)
    (storage / "test.json").write_text(json.dumps(event()), encoding="utf-8")
    evidence, coverage = audit.evidence_for([RID, OTHER], root=tmp_path, home=tmp_path)
    assert len(evidence[RID]) == 2
    assert evidence[OTHER] == []
    assert coverage["files_scanned"] == 2
    assert coverage["database_present"] is False
    assert "PRIVATE PROMPT" not in json.dumps(evidence)


def test_sqlite_scan_is_exact_id_scoped_and_read_only(audit, tmp_path):
    db = tmp_path / ".local/share/opencode/opencode.db"
    db.parent.mkdir(parents=True)
    with sqlite3.connect(db) as conn:
        conn.execute("create table message(data text)")
        conn.execute("insert into message values (?)", (json.dumps(event()),))
        conn.execute("insert into message values (?)", ("unrelated SECRET",))
    before = db.read_bytes()
    evidence, coverage = audit.evidence_for([RID], root=tmp_path, home=tmp_path)
    assert len(evidence[RID]) == 1
    assert coverage["database_rows_matched"] == 1
    assert coverage["database_tables_scanned"] == ["message"]
    assert db.read_bytes() == before
    assert "SECRET" not in json.dumps(evidence)


def test_shared_transcript_is_not_counted_once_per_request(audit, tmp_path):
    db = tmp_path / ".local/share/opencode/opencode.db"
    db.parent.mkdir(parents=True)
    with sqlite3.connect(db) as conn:
        conn.execute("create table part(data text)")
        conn.execute("insert into part values (?)", (RID + " " + OTHER,))
    evidence, coverage = audit.evidence_for([RID, OTHER], root=tmp_path, home=tmp_path)
    assert coverage["database_rows_matched"] == 1
    assert len(evidence[RID]) == len(evidence[OTHER]) == 1
    assert evidence[RID][0]["kind"] == "exact_id_reference_without_structured_outcome"
