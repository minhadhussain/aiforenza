from pathlib import Path

import pytest

from app.core.config import ROOT_ENV_FILE, Settings, resolve_env_file


def test_env_path_is_absolute_repo_root():
    assert ROOT_ENV_FILE.is_absolute()
    assert ROOT_ENV_FILE == Path(__file__).resolve().parents[3] / ".env"


def test_container_layout_does_not_index_past_root(tmp_path):
    source = tmp_path / "app/app/core/config.py"
    assert resolve_env_file(source) == tmp_path / "app/.env"


def test_env_file_is_independent_of_working_directory(tmp_path, monkeypatch):
    env = tmp_path / "settings.env"
    env.write_text(
        "SUPABASE_URL=https://fixture.invalid\nSUPABASE_ANON_KEY=fixture\n",
        encoding="utf-8",
    )
    monkeypatch.delenv("SUPABASE_URL", raising=False)
    monkeypatch.delenv("SUPABASE_ANON_KEY", raising=False)
    monkeypatch.setitem(Settings.model_config, "env_file", env)
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    monkeypatch.chdir(elsewhere)
    assert Settings().supabase_url == "https://fixture.invalid"
    monkeypatch.setenv("SUPABASE_URL", "https://override.invalid")
    assert Settings().supabase_url == "https://override.invalid"


@pytest.mark.parametrize(
    "configured,expected",
    [
        ("http://localhost:3000", ["http://localhost:3000", "http://127.0.0.1:3000"]),
        ("http://127.0.0.1:3000", ["http://127.0.0.1:3000", "http://localhost:3000"]),
        ("https://app.example.com", ["https://app.example.com"]),
        (
            "http://localhost:3000,http://127.0.0.1:3000",
            ["http://localhost:3000", "http://127.0.0.1:3000"],
        ),
    ],
)
def test_cors_only_expands_exact_loopback_hosts(configured, expected):
    assert (
        Settings(_env_file=None, API_CORS_ORIGINS=configured).cors_origins == expected
    )
