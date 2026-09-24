import importlib
import json
from pathlib import Path


def test_picker_state_is_isolated_and_does_not_overwrite_remembered_efforts(monkeypatch, tmp_path):
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[3] / "tools"))
    tool = importlib.import_module("verify_opencode_picker")
    original = tmp_path / "user-state/opencode/model.json"
    original.parent.mkdir(parents=True)
    contents = {"variant": {"aiforenza/gpt-6-astra": "high", "other/model": "max"}, "favorite": []}
    original.write_text(json.dumps(contents), encoding="utf-8")
    supplied = {"XDG_STATE_HOME": str(tmp_path / "user-state"), "EXAMPLE_SETTING": "unchanged"}
    # Exercise the real context manager without requiring the Windows TUI package.
    real_temporary_directory = tool.tempfile.TemporaryDirectory
    monkeypatch.setattr(tool.tempfile, "TemporaryDirectory", lambda **kwargs: real_temporary_directory(prefix=kwargs["prefix"], dir=tmp_path))
    with tool.isolated_picker_state(supplied) as (env, path):
        assert env["XDG_STATE_HOME"] != supplied["XDG_STATE_HOME"]
        assert env["EXAMPLE_SETTING"] == "unchanged"
        assert tool.saved_variant(path, "gpt-6-astra") is None
        path.parent.mkdir(parents=True)
        path.write_text(json.dumps({"variant": {"aiforenza/gpt-6-astra": "low"}}), encoding="utf-8")
        assert tool.saved_variant(path, "gpt-6-astra") == "low"
    assert json.loads(original.read_text(encoding="utf-8")) == contents
    assert not path.exists()
    assert supplied["XDG_STATE_HOME"] == str(tmp_path / "user-state")


def test_reset_only_repairs_astra_low_and_preserves_other_state(monkeypatch, tmp_path):
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[3] / "tools"))
    tool = importlib.import_module("reset_astra_effort")
    path = tmp_path / "model.json"
    original = {"recent": [{"providerID": "other", "modelID": "model"}], "favorite": [], "variant": {tool.MODEL: "low", "aiforenza/gpt-5.4": "xhigh", "azure/gpt-6-astra": "high"}}
    path.write_text(json.dumps(original), encoding="utf-8")
    assert tool.reset_saved_low(path)
    expected = {**original, "variant": {**original["variant"], tool.MODEL: "default"}}
    assert json.loads(path.read_text(encoding="utf-8")) == expected
    assert not tool.reset_saved_low(path)


def test_reset_keeps_explicit_high_and_leaves_new_profiles_alone(monkeypatch, tmp_path):
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[3] / "tools"))
    tool = importlib.import_module("reset_astra_effort")
    path = tmp_path / "model.json"
    assert not tool.reset_saved_low(path)
    assert not path.exists()
    contents = json.dumps({"variant": {tool.MODEL: "high"}})
    path.write_text(contents, encoding="utf-8")
    assert not tool.reset_saved_low(path)
    assert path.read_text(encoding="utf-8") == contents
