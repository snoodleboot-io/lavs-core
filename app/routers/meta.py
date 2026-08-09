"""The public ``GET /meta`` capability endpoint.

Reports the deployment ``edition`` and its enabled ``auth_modes`` so the UI can
render the correct login. Intentionally requires **no** principal — the client
reads it before authenticating (see ``docs/design/API_CONTRACT.md`` §8).
"""

from fastapi import APIRouter, Request

from app.auth.auth_mode import AuthMode
from app.auth.auth_settings import AuthSettings
from app.models.responses.meta_response_model import MetaResponseModel
from app.security.api_key import is_authentication_enabled

router = APIRouter(tags=["meta"])


def _settings_for(request: Request) -> AuthSettings:
    """Return the app-managed auth settings, or an env-built fallback."""
    state = request.app.state
    settings = state.auth_settings if hasattr(state, "auth_settings") else None
    if settings is None:
        return AuthSettings()
    return settings


def _enabled_auth_modes(settings: AuthSettings) -> list[str]:
    """Compute the auth modes actually enabled for this deployment.

    A configured API key enables ``apikey`` even when it is not explicitly named
    in ``LAVS_AUTH_MODES`` (mirroring the provider-enablement rule).

    Args:
        settings: The deployment auth settings.

    Returns:
        The enabled mode values, sorted for a stable response.
    """
    modes = set(settings.modes())
    if is_authentication_enabled():
        modes.add(AuthMode.APIKEY)
    return sorted(mode.value for mode in modes)


def _meta_extensions_for(request: Request, settings: AuthSettings) -> dict[str, object]:
    """Merge every registered ``/meta`` extension's contribution.

    Reads the plugin-contributed extensions from ``app.state.meta_extensions``
    (populated by the plugin seam during the lifespan; absent under a bare
    ``TestClient``) and merges each callable's output. Later extensions win on a
    key clash. With none registered the result is empty, so the response is the
    byte-identical OSS shape.

    Args:
        request: The incoming request, used to reach the app state.
        settings: The deployment auth settings passed to each extension.

    Returns:
        The merged extra fields to add to the ``/meta`` body.
    """
    state = request.app.state
    extensions = state.meta_extensions if hasattr(state, "meta_extensions") else None
    if not extensions:
        return {}
    merged: dict[str, object] = {}
    for extension in extensions:
        merged.update(extension(settings))
    return merged


@router.get("/meta", response_model=MetaResponseModel, response_model_exclude_none=True)
def get_meta(request: Request) -> MetaResponseModel:
    """Report the deployment edition, enabled auth modes, and plugin fields.

    The base body is ``edition`` + ``auth_modes``; any fields contributed by
    registered ``/meta`` extensions (see :func:`_meta_extensions_for`) are
    merged on top. ``MetaResponseModel`` allows extra fields, so an out-of-core
    edition's capability fields serialize through without core naming them.
    With no extension installed the body is byte-identical to the OSS shape.

    Args:
        request: The incoming request, used to reach the managed settings.

    Returns:
        The public capability descriptor.
    """
    settings = _settings_for(request)
    payload: dict[str, object] = {
        "edition": settings.edition(),
        "auth_modes": _enabled_auth_modes(settings),
    }
    payload.update(_meta_extensions_for(request, settings))
    return MetaResponseModel.model_validate(payload)
