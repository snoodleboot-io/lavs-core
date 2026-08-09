"""Composite read query assembling a product's full timeline.

A single lane owns the SELECTs across ``products``, ``components`` and
``versions``; the nested response shape is built in Python from the flat rows.
Every statement is fully parameterized.
"""

from datetime import datetime

from app.connections.db_session import DbSession
from app.models.enums.component_kind import ComponentKind
from app.models.enums.version_status import VersionStatus
from app.models.responses.component_with_versions_response_model import (
    ComponentWithVersionsResponseModel,
)
from app.models.responses.product_response_model import ProductResponseModel
from app.models.responses.timeline_response_model import TimelineResponseModel
from app.models.responses.version_response_model import VersionResponseModel
from app.queries.query import Query
from app.queries.timeline.timeline_request_model import TimelineRequestModel

# Column projections kept as module constants so the SELECTs stay static text
# (no interpolation) and the row-unpacking below reads against a named shape.
_PRODUCT_SELECT = "SELECT id, name, description, created_at FROM products WHERE id = ?"
_COMPONENTS_SELECT = (
    "SELECT id, product_id, name, kind FROM components WHERE product_id = ? ORDER BY name, id"
)
# Versions are joined back to their component so a single query covers the whole
# product. Ordering is semver descending (major, minor, patch); id is the final
# tie-break so equal semver rows come back deterministically.
_VERSIONS_SELECT = (
    "SELECT v.id, v.component_id, v.major, v.minor, v.patch, v.prerelease, v.status, v.created_at "
    "FROM versions v JOIN components c ON v.component_id = c.id "
    "WHERE c.product_id = ? "
    "ORDER BY v.major DESC, v.minor DESC, v.patch DESC, v.id DESC"
)


class TimelineQuery(Query[TimelineResponseModel | None]):
    """Assemble a product together with its components and their versions.

    Returns ``None`` when the product does not exist so the router can raise the
    typed :class:`~app.errors.not_found_error.NotFoundError`. The query itself is
    strictly read-only.
    """

    async def apply(
        self, data: TimelineRequestModel, conn: DbSession
    ) -> TimelineResponseModel | None:
        """Read the product graph and build the nested timeline.

        Args:
            data: The request carrying the target ``product_id``.
            conn: The live DuckDB connection to read from.

        Returns:
            The composite timeline, or ``None`` if the product is unknown.
        """
        product = self._read_product(conn, data.product_id)
        if product is None:
            return None

        versions_by_component = self._read_versions_by_component(conn, data.product_id)
        components = self._read_components(conn, data.product_id, versions_by_component)
        return TimelineResponseModel(product=product, components=components)

    def _read_product(self, conn: DbSession, product_id: str) -> ProductResponseModel | None:
        """Fetch the product row, or ``None`` when it does not exist.

        Args:
            conn: The live connection.
            product_id: The product identifier to look up.

        Returns:
            The product response, or ``None`` if absent.
        """
        row = conn.execute(_PRODUCT_SELECT, (product_id,)).fetchone()
        if row is None:
            return None
        return ProductResponseModel(
            id=str(row[0]),
            name=str(row[1]),
            description=None if row[2] is None else str(row[2]),
            created_at=self._as_iso(row[3]),
        )

    def _read_components(
        self,
        conn: DbSession,
        product_id: str,
        versions_by_component: dict[str, list[VersionResponseModel]],
    ) -> list[ComponentWithVersionsResponseModel]:
        """Fetch the product's components, attaching each one's versions.

        Args:
            conn: The live connection.
            product_id: The owning product identifier.
            versions_by_component: Versions grouped by their component id.

        Returns:
            The components, each carrying its (possibly empty) version list.
        """
        rows = conn.execute(_COMPONENTS_SELECT, (product_id,)).fetchall()
        components: list[ComponentWithVersionsResponseModel] = []
        for row in rows:
            component_id = str(row[0])
            components.append(
                ComponentWithVersionsResponseModel(
                    id=component_id,
                    product_id=str(row[1]),
                    name=str(row[2]),
                    kind=ComponentKind(str(row[3])),
                    versions=versions_by_component.get(component_id, []),
                )
            )
        return components

    def _read_versions_by_component(
        self, conn: DbSession, product_id: str
    ) -> dict[str, list[VersionResponseModel]]:
        """Fetch every version under the product, grouped by component id.

        The single ordered SELECT is grouped in Python; because the rows arrive
        semver-descending, each component's list preserves that ordering.

        Args:
            conn: The live connection.
            product_id: The owning product identifier.

        Returns:
            A mapping of component id to its semver-descending versions.
        """
        rows = conn.execute(_VERSIONS_SELECT, (product_id,)).fetchall()
        grouped: dict[str, list[VersionResponseModel]] = {}
        for row in rows:
            component_id = str(row[1])
            version = VersionResponseModel(
                id=str(row[0]),
                component_id=component_id,
                major=int(row[2]),
                minor=int(row[3]),
                patch=int(row[4]),
                prerelease=None if row[5] is None else str(row[5]),
                status=VersionStatus(str(row[6])),
                created_at=self._as_iso(row[7]),
            )
            grouped.setdefault(component_id, []).append(version)
        return grouped

    def _as_iso(self, value: object) -> str:
        """Render a DuckDB timestamp column as an ISO-8601 string.

        DuckDB yields ``TIMESTAMP`` columns as :class:`datetime.datetime`; any
        other shape is stringified directly.

        Args:
            value: The raw column value.

        Returns:
            The ISO-8601 (or plain string) representation.
        """
        if isinstance(value, datetime):
            return value.isoformat()
        return str(value)
