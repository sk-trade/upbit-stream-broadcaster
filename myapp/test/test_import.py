import pytest
def test_imports():
    """Test if all necessary modules can be imported"""
    try:
        import requests  # REST API 요청을 위한 라이브러리
        import zmq
        import zmq.asyncio 
        import websockets
        import aiohttp
        assert True
    except ImportError as e:
        pytest.fail(f"Failed to import modules: {e}")
