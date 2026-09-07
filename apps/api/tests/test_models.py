from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_models_requires_api_key() -> None:
    response = client.get("/v1/models")
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "invalid_api_key"


def test_models_returns_enabled_models(monkeypatch) -> None:
    async def fake_get_current_api_key() -> dict:
        return {"id": "key-1", "user_id": "user-1"}

    async def fake_list_models() -> list:
        return [
            {
                "slug": "gpt-5.6-luna",
                "display_name": "GPT-5.6 Luna",
                "provider": "azure",
                "provider_model_id": "azure/gpt-5.6-luna",
                "enabled": True,
                "input_price_per_million": 0,
                "output_price_per_million": 0,
                "cached_input_price_per_million": 0,
                "id": "model-1",
            }
        ]

    def fake_serialize(models: list) -> dict:
        assert models[0]["slug"] == "gpt-5.6-luna"
        return {
            "object": "list",
            "data": [{"id": "gpt-5.6-luna", "object": "model", "owned_by": "your-platform"}],
        }

    app.dependency_overrides.clear()
    app.dependency_overrides[__import__("app.api.deps.api_keys", fromlist=["get_current_api_key"]).get_current_api_key] = fake_get_current_api_key
    monkeypatch.setattr("app.api.routes.models.list_models", fake_list_models)
    monkeypatch.setattr("app.api.routes.models.serialize_openai_models", fake_serialize)

    response = client.get("/v1/models", headers={"Authorization": "Bearer demo"})
    app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["data"][0]["id"] == "gpt-5.6-luna"
