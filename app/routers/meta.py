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


@router.get("/meta", response_model=MetaResponseModel)
def get_meta(request: Request) -> MetaResponseModel:
    """Report the deployment edition and enabled auth modes.

    Args:
        request: The incoming request, used to reach the managed settings.

    Returns:
        The public capability descriptor.
    """
    settings = _settings_for(request)
    return MetaResponseModel(
        edition=settings.edition(),
        auth_modes=_enabled_auth_modes(settings),
    )
