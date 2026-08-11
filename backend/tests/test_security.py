from app.core.security import create_access_token, decode_access_token
from app.core.config import Settings
import app.core.security as security


def test_jwt_round_trip(monkeypatch):
    settings = Settings(database_url="sqlite+aiosqlite://", jwt_secret_key="test-secret", gemini_api_key="x", ncbi_email="x@example.com")
    monkeypatch.setattr(security, "get_settings", lambda: settings)
    token = create_access_token("123")
    assert decode_access_token(token) == "123"
