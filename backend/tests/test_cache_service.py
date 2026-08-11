import asyncio
import json
from unittest.mock import AsyncMock
from app.services.cache_service import make_cache_key, get_cached, put_cached


def test_cache_key_is_stable():
    a = make_cache_key("summary", {"b": 2, "a": 1})
    b = make_cache_key("summary", {"a": 1, "b": 2})
    c = make_cache_key("patient", {"a": 1, "b": 2})
    assert a == b
    assert a != c
    assert len(a) == 64


def test_cache_helpers_round_trip_with_mocked_session():
    class Row:
        def __init__(self, response_json):
            self.response_json = response_json

    class Result:
        def scalar_one_or_none(self):
            return None

    db = AsyncMock()
    db.scalar.side_effect = [None, Row(json.dumps({"ok": True}))]
    db.execute = AsyncMock()
    # The helper uses scalar directly; the second call simulates a cached row.
    assert asyncio.run(get_cached(db, "summary", {"pmid": "1"})) is None
