"""Pure-ASGI middleware applying the per-IP rate limit to ``/auth/*``."""

from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from starlette.types import ASGIApp, Receive, Scope, Send

from app.errors.error_detail import ErrorDetail
from app.errors.error_envelope import ErrorEnvelope
from app.errors.rate_limited_error import RateLimitedError
from app.security.rate_limit_settings import RateLimitSettings
from app.security.sliding_window_limiter import SlidingWindowLimiter


class RateLimitMiddleware:
    """Rate-limits the unauthenticated ``/auth/*`` bootstrap surface per IP.

    Pure ASGI (no ``BaseHTTPMiddleware``) so streaming responses elsewhere in
    the app (SSE) are never buffered. Only HTTP requests whose path sits under
    ``/auth/`` are considered; every other path — including the resource
    routes, which are protected by credentials rather than by this throttle —
    passes straight through.

    Settings are read from :class:`RateLimitSettings` **per request**, so the
    limiter obeys environment changes at runtime and stays completely inert
    (no counting, no memory growth) while disabled — which is the default
    posture (``LAVS_AUTH_RATE_LIMIT`` unset or ``0``), keeping bare
    ``TestClient`` suites unaffected.

    On refusal the middleware renders the uniform error envelope itself:
    ``add_middleware`` stacks run outside Starlette's exception middleware, so
    raising :class:`RateLimitedError` here would never reach the registered
    handlers. The response is built **from** the typed error, so status, code,
    and shape stay identical to a handler-rendered envelope, plus a standard
    ``Retry-After`` header.
    """

    _AUTH_PATH_PREFIX: str = "/auth/"
    _FORWARDED_FOR_HEADER: bytes = b"x-forwarded-for"
    _UNKNOWN_CLIENT_KEY: str = "unknown"
    _RATE_LIMITED_MESSAGE: str = "too many requests"

    def __init__(
        self,
        app: ASGIApp,
        settings: RateLimitSettings | None = None,
        limiter: SlidingWindowLimiter | None = None,
    ) -> None:
        """Initialise the middleware.

        Args:
            app: The downstream ASGI application.
            settings: The rate-limit settings; environment-backed when omitted.
            limiter: The sliding-window limiter; a fresh one bounded by
                ``settings.max_tracked_clients()`` when omitted.
        """
        self._app = app
        self._settings = settings if settings is not None else RateLimitSettings()
        self._limiter = (
            limiter
            if limiter is not None
            else SlidingWindowLimiter(max_keys=self._settings.max_tracked_clients())
        )

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """Apply the limit to ``/auth/*`` HTTP requests; pass everything else.

        Args:
            scope: The ASGI connection scope.
            receive: The ASGI receive callable.
            send: The ASGI send callable.
        """
        if scope["type"] != "http" or not str(scope["path"]).startswith(self._AUTH_PATH_PREFIX):
            await self._app(scope, receive, send)
            return

        if not self._settings.enabled():
            await self._app(scope, receive, send)
            return

        key = self._client_key(scope)
        admitted = self._limiter.allow(
            key,
            limit=self._settings.limit(),
            window_seconds=float(self._settings.window_seconds()),
        )
        if admitted:
            await self._app(scope, receive, send)
            return

        response = self._rate_limited_response(self._settings.window_seconds())
        await response(scope, receive, send)

    def _client_key(self, scope: Scope) -> str:
        """Extract the client identity for bucketing.

        Uses the transport peer address (``scope["client"]``) by default. When
        the settings opt in to trusting ``X-Forwarded-For`` (deployments
        behind a proxy that overwrites the header), the first — leftmost —
        address in the header wins instead.

        Args:
            scope: The ASGI connection scope.

        Returns:
            The client IP string, or ``unknown`` when the transport exposes no
            peer address.
        """
        if self._settings.trust_forwarded_for():
            forwarded = self._forwarded_for(scope)
            if forwarded is not None:
                return forwarded

        client = scope.get("client")
        if client is None:
            return self._UNKNOWN_CLIENT_KEY
        return str(client[0])

    def _forwarded_for(self, scope: Scope) -> str | None:
        """Return the leftmost ``X-Forwarded-For`` address, if present.

        Args:
            scope: The ASGI connection scope.

        Returns:
            The first non-empty forwarded address, or ``None`` when the header
            is absent or blank.
        """
        for name, value in scope.get("headers", []):
            if bytes(name).lower() == self._FORWARDED_FOR_HEADER:
                first = bytes(value).decode("latin-1").split(",")[0].strip()
                return first if first else None
        return None

    def _rate_limited_response(self, window_seconds: int) -> JSONResponse:
        """Build the enveloped 429 response for a refused request.

        Args:
            window_seconds: The window length, surfaced as the retry hint.

        Returns:
            A ``JSONResponse`` carrying the uniform error envelope and a
            ``Retry-After`` header.
        """
        error = RateLimitedError(
            message=self._RATE_LIMITED_MESSAGE,
            details={"retry_after_seconds": window_seconds},
        )
        envelope = ErrorEnvelope(
            error=ErrorDetail(code=error.code, message=error.message, details=error.details)
        )
        return JSONResponse(
            status_code=error.http_status,
            content=jsonable_encoder(envelope),
            headers={"Retry-After": str(window_seconds)},
        )
