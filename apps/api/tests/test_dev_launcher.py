import importlib.util
from pathlib import Path
from types import SimpleNamespace

import pytest


@pytest.fixture
def launcher(monkeypatch):
    path = Path(__file__).resolve().parents[3] / "tools/dev.py"
    spec = importlib.util.spec_from_file_location("dev_launcher_test", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    monkeypatch.setattr(
        module,
        "settings",
        SimpleNamespace(
            supabase_url="https://fixture.invalid",
            supabase_anon_key="fixture-anon",
            supabase_service_role_key="fixture-private",
        ),
    )
    monkeypatch.setattr(
        module,
        "dotenv_values",
        lambda _: {"NEXT_PUBLIC_API_BASE_URL": "http://127.0.0.1:8000/v1"},
    )
    monkeypatch.delenv("NEXT_PUBLIC_API_BASE_URL", raising=False)
    return module


def test_valid_configuration_needs_no_optional_pepper(launcher):
    launcher.check_configuration()


def test_missing_supabase_reports_names_not_values(launcher):
    launcher.settings.supabase_url = ""
    with pytest.raises(RuntimeError, match="SUPABASE_URL") as exc:
        launcher.check_configuration()
    assert "fixture-private" not in str(exc.value)


def test_temporary_backend_port_is_rejected(launcher, monkeypatch):
    monkeypatch.setenv("NEXT_PUBLIC_API_BASE_URL", "http://127.0.0.1:8001/v1")
    with pytest.raises(RuntimeError, match="port 8000"):
        launcher.check_configuration()


@pytest.mark.parametrize("occupied", [None, 3000, 3001, 8000, 8001])
def test_duplicate_ports_are_rejected_before_startup(launcher, monkeypatch, occupied):
    class Socket:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def settimeout(self, value):
            pass

        def connect_ex(self, address):
            return 0 if address[1] == occupied else 1

    monkeypatch.setattr(launcher.socket, "socket", lambda *args: Socket())
    if occupied is None:
        launcher.assert_ports_free()
    else:
        with pytest.raises(RuntimeError, match=f"Port {occupied} is occupied"):
            launcher.assert_ports_free()
