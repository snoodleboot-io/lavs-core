"""Router shell for the Constellation timeline view.

Mounted under the ``/products`` prefix; the timeline lane adds
``GET /{product_id}/timeline``. The shell fixes the prefix, tag, and the
mandatory API-key dependency so auth is enforced uniformly.
"""

from fastapi import APIRouter, Depends

from app.security.api_key import get_api_key

router = APIRouter(
    tags=["timeline"],
    prefix="/products",
    dependencies=[Depends(get_api_key)],
)
