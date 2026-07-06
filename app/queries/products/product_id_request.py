"""Request payload carrying a single product identifier.

Queries that address one product by its ULID (fetch-by-id, list a product's
components) receive this typed payload through :meth:`Query.execute`, which
requires a :class:`RequestModel`. It lives beside the product queries because it
is an internal query input, not part of the public HTTP request surface.
"""

from app.models.requests.request_model import RequestModel


class ProductIdRequest(RequestModel):
    """Carries the ULID string identifying the target product."""

    product_id: str
