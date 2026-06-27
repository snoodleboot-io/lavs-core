from typing import Any

from app.models.requests.application_and_version_model import (
    ApplicationAndVersionNameModel,
)
from app.models.responses.application_and_version_response_model import (
    ApplicationAndVersionResponseModel,
)
from app.queries.query import Query


def _row_to_response(
    description: list[tuple[Any, ...]], row: tuple[Any, ...]
) -> ApplicationAndVersionResponseModel:
    """Build a response model from a single query result row.

    Args:
        description: Column descriptions from the result relation.
        row: A single result row from query execution.

    Returns:
        The response model populated from the row's columns.
    """
    columns = [desc[0] for desc in description]
    fields = dict(zip(columns, row, strict=False))
    return ApplicationAndVersionResponseModel(
        product_name=fields["product_name"],
        major=fields["major"],
        minor=fields["minor"],
        patch=fields["patch"],
        id=fields["id"],
    )


class RollbackToPreviousPatchVersion(Query):
    """Roll back the active version to the previous version non-destructively."""

    def __init__(self):
        """Construct an instance of RollbackToPreviousPatchVersion."""
        super().__init__()

    async def apply(
        self, data: ApplicationAndVersionNameModel, conn: Any
    ) -> ApplicationAndVersionResponseModel:
        """Roll back the active version without deleting any history.

        The currently active version row is marked ``rolled_back`` and the most
        recent prior version is re-activated. No rows are deleted, preserving
        the full version history.

        Args:
            data: Product name (and optional version, unused for rollback).
            conn: Live database connection.

        Returns:
            The previous version, now re-activated, as a response model.

        Raises:
            ValueError: If no active version or no prior version exists.
        """
        current = self._fetch_active_version(conn=conn, product_name=data.product_name)
        if current is None:
            raise ValueError(
                f"No active version found for product '{data.product_name}'. Cannot rollback."
            )

        previous = self._fetch_previous_version(
            conn=conn,
            product_name=data.product_name,
            major=current.major,
            minor=current.minor,
            patch=current.patch,
        )
        if previous is None:
            raise ValueError(
                f"No previous version found for product '{data.product_name}'. "
                "Cannot rollback to previous version."
            )

        # Mark the current active row as rolled back (no deletion).
        _ = conn.sql(
            query=(
                "UPDATE Versions "
                "SET status=? "
                "WHERE product_name=? "
                "AND major=? "
                "AND minor=? "
                "AND patch=?"
            ),
            params=(
                "rolled_back",
                current.product_name,
                current.major,
                current.minor,
                current.patch,
            ),
        )

        # Re-activate the previous version.
        _ = conn.sql(
            query=(
                "UPDATE Versions "
                "SET status=? "
                "WHERE product_name=? "
                "AND major=? "
                "AND minor=? "
                "AND patch=?"
            ),
            params=(
                "active",
                previous.product_name,
                previous.major,
                previous.minor,
                previous.patch,
            ),
        )

        return ApplicationAndVersionResponseModel(
            product_name=previous.product_name,
            major=previous.major,
            minor=previous.minor,
            patch=previous.patch,
            id=previous.id,
        )

    def _fetch_active_version(
        self, conn: Any, product_name: str
    ) -> ApplicationAndVersionResponseModel | None:
        """Fetch the current active version for a product.

        Args:
            conn: Live database connection.
            product_name: Product whose active version is requested.

        Returns:
            The active version, or None if no active version exists.
        """
        query_result = conn.sql(
            query=(
                "SELECT * FROM Versions "
                "WHERE product_name = ? "
                "AND status = ? "
                "ORDER BY major DESC, minor DESC, patch DESC "
                "LIMIT 1"
            ),
            params=(product_name, "active"),
        )
        rows = query_result.fetchall()
        if len(rows) > 0:
            return _row_to_response(query_result.description, rows[0])
        return None

    def _fetch_previous_version(
        self, conn: Any, product_name: str, major: int, minor: int, patch: int
    ) -> ApplicationAndVersionResponseModel | None:
        """Fetch the most recent version preceding the supplied version.

        Args:
            conn: Live database connection.
            product_name: Product whose previous version is requested.
            major: Major component of the current active version.
            minor: Minor component of the current active version.
            patch: Patch component of the current active version.

        Returns:
            The previous version, or None if no prior version exists.
        """
        query_result = conn.sql(
            query=(
                "SELECT * FROM Versions "
                "WHERE product_name = ? "
                "AND (major, minor, patch) < (?, ?, ?) "
                "ORDER BY major DESC, minor DESC, patch DESC "
                "LIMIT 1"
            ),
            params=(product_name, major, minor, patch),
        )
        rows = query_result.fetchall()
        if len(rows) > 0:
            return _row_to_response(query_result.description, rows[0])
        return None
