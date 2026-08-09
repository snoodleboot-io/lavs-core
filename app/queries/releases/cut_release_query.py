"""Query that cuts an immutable release by freezing the product's manifest."""

from typing import Any

from app.domain.product_version import next_product_version
from app.errors.conflict_error import ConflictError
from app.errors.not_found_error import NotFoundError
from app.models.enums.version_status import VersionStatus
from app.models.responses.release_response_model import ReleaseResponseModel
from app.models.types.ulid_id import new_ulid
from app.queries.query import Query
from app.queries.releases.cut_release_request import CutReleaseRequest
from app.queries.releases.cut_release_result import CutReleaseResult
from app.queries.releases.release_manifest_mapper import (
    to_release_components,
    to_release_response,
)

_SELECT_PRODUCT = "SELECT id, base_version FROM products WHERE id = ?"
_SELECT_RELEASE_BY_IDEMPOTENCY = (
    "SELECT id FROM releases WHERE product_id = ? AND idempotency_key = ? LIMIT 1"
)
_SELECT_ACTIVE_COMPONENTS = (
    "SELECT c.id AS component_id, c.name AS name, v.id AS version_id, "
    "v.major AS major, v.minor AS minor, v.patch AS patch, v.prerelease AS prerelease "
    "FROM components c "
    "JOIN versions v ON v.component_id = c.id AND v.status = ? "
    "WHERE c.product_id = ? "
    "ORDER BY c.id"
)
_SELECT_LATEST_RELEASE_VERSION = (
    "SELECT product_version FROM releases WHERE product_id = ? "
    "ORDER BY created_at DESC, id DESC LIMIT 1"
)
_INSERT_RELEASE = (
    "INSERT INTO releases (id, product_id, product_version, label, notes, idempotency_key) "
    "VALUES (?, ?, ?, ?, ?, ?)"
)
_INSERT_RELEASE_COMPONENT = (
    "INSERT INTO release_components (release_id, component_id, version_id) VALUES (?, ?, ?)"
)
_SELECT_RELEASE = (
    "SELECT id, product_id, product_version, label, notes, created_at FROM releases WHERE id = ?"
)
_SELECT_RELEASE_MANIFEST = (
    "SELECT rc.component_id AS component_id, c.name AS name, rc.version_id AS version_id, "
    "v.major AS major, v.minor AS minor, v.patch AS patch, v.prerelease AS prerelease "
    "FROM release_components rc "
    "JOIN components c ON c.id = rc.component_id "
    "JOIN versions v ON v.id = rc.version_id "
    "WHERE rc.release_id = ? "
    "ORDER BY c.id"
)


class CutReleaseQuery(Query[CutReleaseResult]):
    """Freeze a product's current composition into an immutable release.

    A cut snapshots each component's currently-``active`` version, derives the
    server-owned ``product_version`` (default bump: minor), and persists one
    ``releases`` row plus a ``release_components`` row pinning each version id.
    Because versions are immutable and the manifest pins ``version_id``s, a cut
    release never changes afterward. When an ``Idempotency-Key`` repeats a prior
    cut for the product, the existing release is returned unchanged and no new
    release is created (``created=False``).
    """

    async def apply(self, data: CutReleaseRequest, conn: Any) -> CutReleaseResult:
        """Cut a release (or replay an idempotent one) for the product.

        Args:
            data: The cut request (product id, optional label/notes, optional
                idempotency key).
            conn: Live database connection.

        Returns:
            The frozen release plus whether it was newly created.

        Raises:
            NotFoundError: When ``data.product_id`` does not exist.
            ConflictError: When no component has an ``active`` version to
                release.
        """
        product_rows = conn.execute(_SELECT_PRODUCT, (data.product_id,)).fetchall()
        if len(product_rows) == 0:
            raise NotFoundError(
                message=f"Product '{data.product_id}' does not exist.",
                details={"product_id": data.product_id},
            )
        base_version = product_rows[0][1]

        if data.idempotency_key is not None:
            existing = conn.execute(
                _SELECT_RELEASE_BY_IDEMPOTENCY, (data.product_id, data.idempotency_key)
            ).fetchall()
            if len(existing) > 0:
                release = self._load_release(conn, existing[0][0])
                return CutReleaseResult(release=release, created=False)

        active = conn.execute(
            _SELECT_ACTIVE_COMPONENTS, (VersionStatus.ACTIVE.value, data.product_id)
        )
        active_columns = [entry[0] for entry in active.description]
        active_rows = active.fetchall()
        if len(active_rows) == 0:
            raise ConflictError(
                message=(
                    f"Product '{data.product_id}' has no components with an active "
                    "version; nothing to release."
                ),
                details={"product_id": data.product_id},
            )

        latest = conn.execute(_SELECT_LATEST_RELEASE_VERSION, (data.product_id,)).fetchall()
        latest_version = latest[0][0] if len(latest) > 0 else None
        product_version = next_product_version(latest_version, base_version)

        release_id = new_ulid()
        _ = conn.execute(
            _INSERT_RELEASE,
            (
                release_id,
                data.product_id,
                product_version,
                data.label,
                data.notes,
                data.idempotency_key,
            ),
        )
        for row in active_rows:
            fields = dict(zip(active_columns, row, strict=False))
            _ = conn.execute(
                _INSERT_RELEASE_COMPONENT,
                (release_id, fields["component_id"], fields["version_id"]),
            )

        release = self._load_release(conn, release_id)
        return CutReleaseResult(release=release, created=True)

    def _load_release(self, conn: Any, release_id: str) -> ReleaseResponseModel:
        """Load a release and its pinned manifest into the response model.

        Args:
            conn: Live database connection.
            release_id: The id of the release to load.

        Returns:
            The release with its frozen component manifest.
        """
        manifest = conn.execute(_SELECT_RELEASE_MANIFEST, (release_id,))
        components = to_release_components(manifest.description, manifest.fetchall())
        release = conn.execute(_SELECT_RELEASE, (release_id,))
        release_rows = release.fetchall()
        return to_release_response(release.description, release_rows[0], components)
