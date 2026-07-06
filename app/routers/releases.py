"""Router shell for the ``releases`` resource.

Deliberately carries **no prefix**: releases are addressed under two roots —
``/products/{id}/releases`` (list + cut) and ``/releases/{id}`` (read one) — so
each route declares its full path. The shell fixes only the tag and the
mandatory API-key dependency; the cut/list routes are added by the release-write
lane and the read route by the release-read lane.
"""

from fastapi import APIRouter, Depends

from app.security.api_key import get_api_key

router = APIRouter(
    tags=["releases"],
    dependencies=[Depends(get_api_key)],
)
