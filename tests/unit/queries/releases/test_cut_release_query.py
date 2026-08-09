"""Unit tests for :class:`CutReleaseQuery`."""

from unittest import IsolatedAsyncioTestCase

from app.errors.conflict_error import ConflictError
from app.errors.not_found_error import NotFoundError
from app.models.enums.version_status import VersionStatus
from app.queries.releases.cut_release_query import CutReleaseQuery
from app.queries.releases.cut_release_request import CutReleaseRequest
from tests.unit.queries.releases.release_query_fixtures import (
    make_connection,
    seed_component,
    seed_product,
    seed_version,
)


class TestCutReleaseQuery(IsolatedAsyncioTestCase):
    """Behaviour of the immutable cut-release query."""

    async def test_first_cut_bumps_minor_from_base(self) -> None:
        """A product's first cut minor-bumps its base version (0.0.0 -> 0.1.0)."""
        # Arrange
        conn = make_connection()
        product_id = seed_product(conn, base_version="0.0.0")
        component_id = seed_component(conn, product_id, "api")
        seed_version(conn, component_id, 2, 4, 0)
        data = CutReleaseRequest(product_id=product_id)

        # Act
        result = await CutReleaseQuery().execute(data=data, connection=conn)

        # Assert
        self.assertTrue(result.created)
        self.assertEqual(result.release.product_version, "0.1.0")
        self.assertEqual(result.release.product_id, product_id)

    async def test_subsequent_cut_bumps_from_latest_release(self) -> None:
        """A second cut minor-bumps the prior release's version, not the base."""
        # Arrange
        conn = make_connection()
        product_id = seed_product(conn, base_version="0.0.0")
        component_id = seed_component(conn, product_id, "api")
        seed_version(conn, component_id, 1, 0, 0)
        await CutReleaseQuery().execute(
            data=CutReleaseRequest(product_id=product_id), connection=conn
        )

        # Act
        second = await CutReleaseQuery().execute(
            data=CutReleaseRequest(product_id=product_id), connection=conn
        )

        # Assert
        self.assertEqual(second.release.product_version, "0.2.0")

    async def test_snapshot_pins_only_active_versions(self) -> None:
        """The manifest pins each component's active version and renders semver."""
        # Arrange
        conn = make_connection()
        product_id = seed_product(conn)
        component_id = seed_component(conn, product_id, "api")
        seed_version(conn, component_id, 2, 4, 0, VersionStatus.SUPERSEDED.value)
        active_id = seed_version(conn, component_id, 2, 5, 0, VersionStatus.ACTIVE.value)
        data = CutReleaseRequest(product_id=product_id)

        # Act
        result = await CutReleaseQuery().execute(data=data, connection=conn)

        # Assert
        self.assertEqual(len(result.release.components), 1)
        component = result.release.components[0]
        self.assertEqual(component.version_id, active_id)
        self.assertEqual(component.version, "2.5.0")
        self.assertEqual(component.name, "api")

    async def test_prerelease_is_rendered_in_manifest(self) -> None:
        """An active prerelease version renders with its ``-suffix``."""
        # Arrange
        conn = make_connection()
        product_id = seed_product(conn)
        component_id = seed_component(conn, product_id, "api")
        seed_version(conn, component_id, 1, 0, 0, prerelease="rc.1")
        data = CutReleaseRequest(product_id=product_id)

        # Act
        result = await CutReleaseQuery().execute(data=data, connection=conn)

        # Assert
        self.assertEqual(result.release.components[0].version, "1.0.0-rc.1")

    async def test_component_without_active_version_is_excluded(self) -> None:
        """Only components with an active version appear in the manifest."""
        # Arrange
        conn = make_connection()
        product_id = seed_product(conn)
        active_component = seed_component(conn, product_id, "api")
        seed_version(conn, active_component, 1, 0, 0, VersionStatus.ACTIVE.value)
        rolled_component = seed_component(conn, product_id, "ui")
        seed_version(conn, rolled_component, 1, 0, 0, VersionStatus.ROLLED_BACK.value)
        data = CutReleaseRequest(product_id=product_id)

        # Act
        result = await CutReleaseQuery().execute(data=data, connection=conn)

        # Assert
        component_ids = [component.component_id for component in result.release.components]
        self.assertEqual(component_ids, [active_component])

    async def test_release_components_pin_version_ids_immutably(self) -> None:
        """Persisted ``release_components`` rows pin the exact active version ids."""
        # Arrange
        conn = make_connection()
        product_id = seed_product(conn)
        component_id = seed_component(conn, product_id, "api")
        active_id = seed_version(conn, component_id, 3, 1, 0)
        data = CutReleaseRequest(product_id=product_id)

        # Act
        result = await CutReleaseQuery().execute(data=data, connection=conn)

        # Assert
        pinned = conn.execute(
            "SELECT component_id, version_id FROM release_components WHERE release_id = ?",
            (result.release.id,),
        ).fetchall()
        self.assertEqual(pinned, [(component_id, active_id)])

    async def test_idempotency_key_returns_same_release_without_double_cut(self) -> None:
        """A repeated idempotency key replays the release and cuts none extra."""
        # Arrange
        conn = make_connection()
        product_id = seed_product(conn)
        component_id = seed_component(conn, product_id, "api")
        seed_version(conn, component_id, 1, 0, 0)
        first = await CutReleaseQuery().execute(
            data=CutReleaseRequest(product_id=product_id, idempotency_key="key-1"),
            connection=conn,
        )

        # Act
        second = await CutReleaseQuery().execute(
            data=CutReleaseRequest(product_id=product_id, idempotency_key="key-1"),
            connection=conn,
        )

        # Assert
        self.assertTrue(first.created)
        self.assertFalse(second.created)
        self.assertEqual(second.release.id, first.release.id)
        self.assertEqual(second.release.product_version, first.release.product_version)
        release_count = conn.execute(
            "SELECT count(*) FROM releases WHERE product_id = ?", (product_id,)
        ).fetchone()
        assert release_count is not None
        self.assertEqual(release_count[0], 1)

    async def test_nothing_active_raises_conflict(self) -> None:
        """A product with no active version anywhere raises ``ConflictError``."""
        # Arrange
        conn = make_connection()
        product_id = seed_product(conn)
        component_id = seed_component(conn, product_id, "api")
        seed_version(conn, component_id, 1, 0, 0, VersionStatus.ROLLED_BACK.value)
        data = CutReleaseRequest(product_id=product_id)

        # Act / Assert
        with self.assertRaises(ConflictError):
            await CutReleaseQuery().execute(data=data, connection=conn)

    async def test_product_with_no_components_raises_conflict(self) -> None:
        """A product with no components at all has nothing to release."""
        # Arrange
        conn = make_connection()
        product_id = seed_product(conn)
        data = CutReleaseRequest(product_id=product_id)

        # Act / Assert
        with self.assertRaises(ConflictError):
            await CutReleaseQuery().execute(data=data, connection=conn)

    async def test_unknown_product_raises_not_found(self) -> None:
        """Cutting under a non-existent product raises ``NotFoundError``."""
        # Arrange
        conn = make_connection()
        data = CutReleaseRequest(product_id="01KW8WHA6STWW5N1VYRSHDTK1N")

        # Act / Assert
        with self.assertRaises(NotFoundError):
            await CutReleaseQuery().execute(data=data, connection=conn)
