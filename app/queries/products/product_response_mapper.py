"""Maps a ``products`` table row onto its response model."""

from datetime import datetime

from app.models.responses.product_response_model import ProductResponseModel


class ProductResponseMapper:
    """Builds :class:`ProductResponseModel` values from database rows.

    Centralises the column ordering
    (``id, name, description, base_version, created_at``) shared by the create,
    fetch-by-id and list queries so the ``created_at`` timestamp is rendered to
    an ISO-8601 string in exactly one place.
    """

    @staticmethod
    def to_model(row: tuple[object, ...]) -> ProductResponseModel:
        """Convert a selected product row to a response model.

        Args:
            row: A row of ``(id, name, description, base_version, created_at)``
                as returned by a ``SELECT`` against the ``products`` table.
                ``created_at`` is a :class:`datetime.datetime`; ``description``
                may be ``None``.

        Returns:
            The populated :class:`ProductResponseModel`.
        """
        product_id, name, description, base_version, created_at = row
        rendered_created_at = (
            created_at.isoformat() if isinstance(created_at, datetime) else str(created_at)
        )
        return ProductResponseModel(
            id=str(product_id),
            name=str(name),
            description=None if description is None else str(description),
            base_version=str(base_version),
            created_at=rendered_created_at,
        )
