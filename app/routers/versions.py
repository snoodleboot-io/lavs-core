"""Router shell for the ``/versions`` resource.

Replaces the legacy query-parameter versions router. Routes are added by the
versions resource lane; this shell fixes the prefix, tag, and the mandatory
API-key dependency so auth is enforced uniformly.
"""

from fastapi import APIRouter, Depends

from app.security.api_key import get_api_key

router = APIRouter(
    tags=["versions"],
    prefix="/versions",
    dependencies=[Depends(get_api_key)],
)
