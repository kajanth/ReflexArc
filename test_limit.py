import sys
import types
from unittest.mock import MagicMock

# Mock missing modules
sys.modules['aiohttp'] = MagicMock()
sys.modules['aiohttp.web'] = MagicMock()
sys.modules['aiohttp.web_request'] = MagicMock()
sys.modules['aiohttp.web_response'] = MagicMock()
sys.modules['aiohttp.web_exceptions'] = MagicMock()
sys.modules['pydantic'] = MagicMock()
sys.modules['structlog'] = MagicMock()
sys.modules['structlog.contextvars'] = MagicMock()

import aiohttp.web

def json_response_mock(data, status=200):
    return {"data": data, "status": status}
aiohttp.web.json_response = json_response_mock

import asyncio
from api_server import NSAApiServer

def test_limits():
    brain_mock = MagicMock()
    server = NSAApiServer(brain_mock)

    request_invalid = MagicMock()
    request_invalid.query.get.return_value = "invalid"
    request_invalid.rel_url.query.get.return_value = "invalid"

    async def run_tests():
        # _handle_memories
        res = await server._handle_memories(request_invalid)
        assert res["status"] == 400
        assert res["data"]["error"] == "Invalid limit parameter"

        # _handle_dreams
        res = await server._handle_dreams(request_invalid)
        assert res["status"] == 400
        assert res["data"]["error"] == "Invalid limit parameter"

        # _handle_prediction_history
        res = await server._handle_prediction_history(request_invalid)
        assert res["status"] == 400
        assert res["data"]["error"] == "Invalid limit parameter"

        # _handle_changes_log
        res = await server._handle_changes_log(request_invalid)
        assert res["status"] == 400
        assert res["data"]["error"] == "Invalid limit parameter"

        # _handle_activity_log
        res = await server._handle_activity_log(request_invalid)
        assert res["status"] == 400
        assert res["data"]["error"] == "Invalid limit parameter"

        print("All endpoints handled invalid limits safely!")

    asyncio.run(run_tests())

if __name__ == "__main__":
    test_limits()
