"""Tests for auth resolvers."""

import jwt
import pytest
from unittest.mock import MagicMock

from possession.auth import jwt_auth, header_auth


@pytest.mark.asyncio
async def test_jwt_auth_returns_claims_for_valid_token():
    resolver = jwt_auth(secret="test-secret")

    token = jwt.encode({"sub": "user-123", "email": "a@b.c"}, "test-secret", algorithm="HS256")

    ws = MagicMock()
    ws.query_params.get.return_value = token

    claims = await resolver(ws)

    assert claims["sub"] == "user-123"
    assert claims["email"] == "a@b.c"


@pytest.mark.asyncio
async def test_jwt_auth_returns_none_for_invalid_token():
    resolver = jwt_auth(secret="test-secret")

    ws = MagicMock()
    ws.query_params.get.return_value = "not-a-jwt"

    assert await resolver(ws) is None


@pytest.mark.asyncio
async def test_jwt_auth_returns_none_for_missing_token():
    resolver = jwt_auth(secret="test-secret")

    ws = MagicMock()
    ws.query_params.get.return_value = None

    assert await resolver(ws) is None


@pytest.mark.asyncio
async def test_jwt_auth_returns_none_for_wrong_secret():
    resolver = jwt_auth(secret="correct-secret")
    token = jwt.encode({"sub": "x"}, "wrong-secret", algorithm="HS256")

    ws = MagicMock()
    ws.query_params.get.return_value = token

    assert await resolver(ws) is None


@pytest.mark.asyncio
async def test_header_auth_strips_bearer_prefix():
    async def verify(token: str):
        return {"token": token}

    resolver = header_auth(verify)

    ws = MagicMock()
    ws.headers.get.return_value = "Bearer abc123"

    result = await resolver(ws)
    assert result == {"token": "abc123"}


@pytest.mark.asyncio
async def test_header_auth_returns_none_when_missing():
    async def verify(token: str):
        return {"ok": True}

    resolver = header_auth(verify)

    ws = MagicMock()
    ws.headers.get.return_value = None

    assert await resolver(ws) is None
