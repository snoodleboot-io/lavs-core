"""Map a DuckDB result row onto a :class:`VersionResponseModel`.

Both version queries fetch rows with the same column projection, so the
row-to-model translation lives here to avoid duplicating it per query class.
"""

from datetime import datetime
from typing import Any

from app.models.enums.version_status import VersionStatus
from app.models.responses.version_response_model import VersionResponseModel


def to_version_response(description: list[Any], row: tuple[Any, ...]) -> VersionResponseModel:
    """Build a :class:`VersionResponseModel` from a single result row.

    The ``created_at`` column arrives as a ``datetime`` from DuckDB's
    ``TIMESTAMP`` type; it is rendered in ISO-8601 text form for the response.

    Args:
        description: The column description of the executed relation.
        row: A single result row whose columns align with ``description``.

    Returns:
        The response model populated from the row's columns.
    """
    columns = [entry[0] for entry in description]
    fields = dict(zip(columns, row, strict=False))
    created_at = fields["created_at"]
    created_at_text = (
        created_at.isoformat() if isinstance(created_at, datetime) else str(created_at)
    )
    return VersionResponseModel(
        id=fields["id"],
        component_id=fields["component_id"],
        major=fields["major"],
        minor=fields["minor"],
        patch=fields["patch"],
        prerelease=fields["prerelease"],
        status=VersionStatus(fields["status"]),
        created_at=created_at_text,
    )
