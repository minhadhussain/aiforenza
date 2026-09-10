import importlib
import json
from pathlib import Path


def test_single_hold_summary_redacts_contents(monkeypatch):
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[3] / "tools"))
    module = importlib.import_module("inspect_single_hold")
    text = json.dumps(
        {
            "prompt": "PRIVATE_PROMPT",
            "apiKey": "PRIVATE_CREDENTIAL",
            "request_id": module.RID,
            "statusCode": 502,
            "error": "ReadTimeout",
        }
    )
    summary = module.safe_summary(text)
    assert summary["request_ids"] == [module.RID]
    assert summary["http_statuses"] == ["502"]
    assert "ReadTimeout" in summary["categories"]
    assert len(summary["fingerprint"]) == 64
    assert "PRIVATE" not in json.dumps(summary)


def test_no_error_or_token_outcome_inferred_from_reference(monkeypatch):
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[3] / "tools"))
    module = importlib.import_module("inspect_single_hold")
    summary = module.safe_summary("Discussion of " + module.RID)
    assert summary["categories"] == []
    assert summary["http_statuses"] == []
    assert "release" not in summary
