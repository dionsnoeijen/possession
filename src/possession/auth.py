"""Built-in auth resolvers.

Possession is auth-agnostic, but provides sensible defaults for the common cases.
"""

from typing import Any, Awaitable, Callable

from fastapi import WebSocket

AuthResolver = Callable[[WebSocket], Awaitable[Any]]


def jwt_auth(
    secret: str,
    *,
    algorithms: list[str] | None = None,
    token_param: str = "token",
    audience: str | None = None,
    issuer: str | None = None,
) -> AuthResolver:
    """Default JWT-based auth resolver.

    Reads the token from the query string (e.g. ?token=...), verifies it,
    and returns the decoded claims as the user context.

    Args:
        secret: The JWT secret key (or public key for RS256/ES256).
        algorithms: Allowed algorithms. Defaults to ["HS256"].
        token_param: Query string parameter name. Defaults to "token".
        audience: Expected audience claim (optional).
        issuer: Expected issuer claim (optional).

    Returns:
        An async resolver that returns the decoded claims dict, or None if
        the token is missing or invalid.

    Requires the `PyJWT` package:
        pip install PyJWT

    Example:
        from possession import mount_possession
        from possession.auth import jwt_auth

        mount_possession(
            app, "/ws/chat", make_session,
            auth=jwt_auth(secret="my-secret"),
        )
    """
    try:
        import jwt  # type: ignore
    except ImportError as e:
        raise ImportError(
            "jwt_auth requires PyJWT. Install it with: pip install PyJWT"
        ) from e

    algs = algorithms or ["HS256"]

    async def resolve(websocket: WebSocket) -> dict | None:
        token = websocket.query_params.get(token_param)
        if not token:
            return None

        options: dict = {}
        kwargs: dict[str, Any] = {"algorithms": algs}
        if audience:
            kwargs["audience"] = audience
        if issuer:
            kwargs["issuer"] = issuer

        try:
            claims = jwt.decode(token, secret, **kwargs)
            return claims
        except jwt.PyJWTError:
            return None

    return resolve


def header_auth(
    verify: Callable[[str], Awaitable[Any]],
    *,
    header: str = "authorization",
    prefix: str = "Bearer ",
) -> AuthResolver:
    """Auth resolver that reads from a header and delegates verification.

    Useful when you cannot use query params (e.g. behind a proxy that strips them).

    Args:
        verify: Async callable that receives the token string and returns
            a user context (or None if invalid).
        header: Header name to read. Defaults to "authorization".
        prefix: Prefix to strip from the header value. Defaults to "Bearer ".

    Note: WebSocket clients in browsers cannot set custom headers easily.
    Query params are the standard approach for browser WebSockets.
    """

    async def resolve(websocket: WebSocket) -> Any:
        value = websocket.headers.get(header)
        if not value:
            return None
        if prefix and value.startswith(prefix):
            value = value[len(prefix):]
        return await verify(value)

    return resolve
