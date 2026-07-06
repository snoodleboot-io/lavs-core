"""Router shell for the Server-Sent Events stream.

Carries no prefix; the SSE lane adds ``GET /products/{id}/events`` (a
``text/event-stream`` response, see ``docs/design/API_CONTRACT.md`` §6) on the
shared ``router`` below, which fixes the tag and the mandatory API-key
dependency so auth is enforced uniformly.
"""

from fastapi import APIRouter, Depends

from app.security.api_key import get_api_key

router = APIRouter(
    tags=["events"],
    dependencies=[Depends(get_api_key)],
)
