"""Router shell for the ``/products`` resource.

Routes are added by the products resource lane; this shell fixes the prefix,
tag, and the mandatory API-key dependency so auth is enforced uniformly.
"""

from fastapi import APIRouter, Depends

from app.security.api_key import get_api_key

router = APIRouter(
    tags=["products"],
    prefix="/products",
    dependencies=[Depends(get_api_key)],
)
