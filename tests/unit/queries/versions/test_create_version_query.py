"""Unit tests for :class:`CreateVersionQuery`."""

from unittest import IsolatedAsyncioTestCase

from app.errors.not_found_error import NotFoundError
from app.models.enums.version_status import VersionStatus
from app.models.requests.create_version_model import CreateVersionModel
from app.queries.versions.create_version_query import CreateVersionQuery
from tests.unit.queries.versions.version_query_fixtures import (
    make_connection,
    seed_component,
    seed_version,
)


class TestCreateVersionQuery(IsolatedAsyncioTestCase):
    """Behaviour of the immutable version-create query."""

    async def test_first_version_is_inserted_active(self) -> None:
        """A component's first version is stored with ``active`` status."""
        # Arrange
        conn = make_connection()
        component_id = seed_component(conn)
        data = CreateVersionModel(component_id=component_id, version="1.0.0")

        # Act
        result = await CreateVersionQuery().execute(data=data, connection=conn)

        # Assert
        self.assertEqual(result.status, VersionStatus.ACTIVE)
        self.assertEqual((result.major, result.minor, result.patch), (1, 0, 0))
        self.assertEqual(result.component_id, component_id)

    async def test_new_version_supersedes_prior_active(self) -> None:
        """Inserting a new version supersedes the previously active one."""
        # Arrange
        conn = make_connection()
        component_id = seed_component(conn)
        prior_id = seed_version(conn, component_id, 1, 0, 0, VersionStatus.ACTIVE.value)
        data = CreateVersionModel(component_id=component_id, version="2.0.0")

        # Act
        result = await CreateVersionQuery().execute(data=data, connection=conn)

        # Assert
        self.assertEqual(result.status, VersionStatus.ACTIVE)
        prior_status = conn.execute(
            "SELECT status FROM versions WHERE id = ?", (prior_id,)
        ).fetchone()
        self.assertIsNotNone(prior_status)
        assert prior_status is not None
        self.assertEqual(prior_status[0], VersionStatus.SUPERSEDED.value)

    async def test_exactly_one_active_after_create(self) -> None:
        """After a create there is exactly one active row for the component."""
        # Arrange
        conn = make_connection()
        component_id = seed_component(conn)
        seed_version(conn, component_id, 1, 0, 0, VersionStatus.ACTIVE.value)
        data = CreateVersionModel(component_id=component_id, version="1.1.0")

        # Act
        await CreateVersionQuery().execute(data=data, connection=conn)

        # Assert
        active_count = conn.execute(
            "SELECT count(*) FROM versions WHERE component_id = ? AND status = ?",
            (component_id, VersionStatus.ACTIVE.value),
        ).fetchone()
        assert active_count is not None
        self.assertEqual(active_count[0], 1)

    async def test_prerelease_is_persisted(self) -> None:
        """A prerelease label round-trips into the stored version."""
        # Arrange
        conn = make_connection()
        component_id = seed_component(conn)
        data = CreateVersionModel(component_id=component_id, version="1.0.0", prerelease="rc.1")

        # Act
        result = await CreateVersionQuery().execute(data=data, connection=conn)

        # Assert
        self.assertEqual(result.prerelease, "rc.1")

    async def test_duplicate_semver_is_allowed(self) -> None:
        """An exact duplicate semver is appended (immutable history keeps both)."""
        # Arrange
        conn = make_connection()
        component_id = seed_component(conn)
        seed_version(conn, component_id, 1, 0, 0, VersionStatus.ACTIVE.value)
        data = CreateVersionModel(component_id=component_id, version="1.0.0")

        # Act
        result = await CreateVersionQuery().execute(data=data, connection=conn)

        # Assert
        self.assertEqual(result.status, VersionStatus.ACTIVE)
        total = conn.execute(
            "SELECT count(*) FROM versions WHERE component_id = ?", (component_id,)
        ).fetchone()
        assert total is not None
        self.assertEqual(total[0], 2)

    async def test_unknown_component_raises_not_found(self) -> None:
        """Creating under a non-existent component raises ``NotFoundError``."""
        # Arrange
        conn = make_connection()
        data = CreateVersionModel(component_id="01KW8WHA6STWW5N1VYRSHDTK1N", version="1.0.0")

        # Act / Assert
        with self.assertRaises(NotFoundError):
            await CreateVersionQuery().execute(data=data, connection=conn)
