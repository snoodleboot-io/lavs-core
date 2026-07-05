"""Unit tests for :class:`RollbackVersionQuery`."""

from unittest import IsolatedAsyncioTestCase

from app.errors.conflict_error import ConflictError
from app.errors.not_found_error import NotFoundError
from app.models.enums.version_status import VersionStatus
from app.queries.versions.rollback_version_query import RollbackVersionQuery
from app.queries.versions.rollback_version_request import RollbackVersionRequest
from tests.unit.queries.versions.version_query_fixtures import (
    make_connection,
    seed_component,
    seed_version,
)


class TestRollbackVersionQuery(IsolatedAsyncioTestCase):
    """Behaviour of the non-destructive rollback query."""

    async def test_rollback_reactivates_previous_and_marks_target_rolled_back(
        self,
    ) -> None:
        """The target is rolled back and the previous version re-activated."""
        # Arrange
        conn = make_connection()
        component_id = seed_component(conn)
        previous_id = seed_version(conn, component_id, 1, 0, 0, VersionStatus.SUPERSEDED.value)
        target_id = seed_version(conn, component_id, 2, 0, 0, VersionStatus.ACTIVE.value)

        # Act
        result = await RollbackVersionQuery().execute(
            data=RollbackVersionRequest(version_id=target_id), connection=conn
        )

        # Assert
        self.assertEqual(result.id, previous_id)
        self.assertEqual(result.status, VersionStatus.ACTIVE)
        target_status = conn.execute(
            "SELECT status FROM versions WHERE id = ?", (target_id,)
        ).fetchone()
        assert target_status is not None
        self.assertEqual(target_status[0], VersionStatus.ROLLED_BACK.value)

    async def test_rollback_preserves_all_rows(self) -> None:
        """No row is deleted; the total row count is unchanged by a rollback."""
        # Arrange
        conn = make_connection()
        component_id = seed_component(conn)
        seed_version(conn, component_id, 1, 0, 0, VersionStatus.SUPERSEDED.value)
        target_id = seed_version(conn, component_id, 2, 0, 0, VersionStatus.ACTIVE.value)
        before = conn.execute("SELECT count(*) FROM versions").fetchone()
        assert before is not None

        # Act
        await RollbackVersionQuery().execute(
            data=RollbackVersionRequest(version_id=target_id), connection=conn
        )

        # Assert
        after = conn.execute("SELECT count(*) FROM versions").fetchone()
        assert after is not None
        self.assertEqual(after[0], before[0])

    async def test_rollback_leaves_exactly_one_active(self) -> None:
        """Exactly one active row remains after a rollback."""
        # Arrange
        conn = make_connection()
        component_id = seed_component(conn)
        seed_version(conn, component_id, 1, 0, 0, VersionStatus.SUPERSEDED.value)
        target_id = seed_version(conn, component_id, 2, 0, 0, VersionStatus.ACTIVE.value)

        # Act
        await RollbackVersionQuery().execute(
            data=RollbackVersionRequest(version_id=target_id), connection=conn
        )

        # Assert
        active_count = conn.execute(
            "SELECT count(*) FROM versions WHERE component_id = ? AND status = ?",
            (component_id, VersionStatus.ACTIVE.value),
        ).fetchone()
        assert active_count is not None
        self.assertEqual(active_count[0], 1)

    async def test_rollback_skips_rolled_back_predecessor(self) -> None:
        """A rolled-back predecessor is skipped when choosing the previous version."""
        # Arrange
        conn = make_connection()
        component_id = seed_component(conn)
        oldest_id = seed_version(conn, component_id, 1, 0, 0, VersionStatus.SUPERSEDED.value)
        seed_version(conn, component_id, 1, 5, 0, VersionStatus.ROLLED_BACK.value)
        target_id = seed_version(conn, component_id, 2, 0, 0, VersionStatus.ACTIVE.value)

        # Act
        result = await RollbackVersionQuery().execute(
            data=RollbackVersionRequest(version_id=target_id), connection=conn
        )

        # Assert
        self.assertEqual(result.id, oldest_id)

    async def test_rollback_with_no_prior_raises_conflict(self) -> None:
        """Rolling back the only version raises ``ConflictError``."""
        # Arrange
        conn = make_connection()
        component_id = seed_component(conn)
        only_id = seed_version(conn, component_id, 1, 0, 0, VersionStatus.ACTIVE.value)

        # Act / Assert
        with self.assertRaises(ConflictError):
            await RollbackVersionQuery().execute(
                data=RollbackVersionRequest(version_id=only_id), connection=conn
            )

    async def test_rollback_unknown_version_raises_not_found(self) -> None:
        """Rolling back an unknown id raises ``NotFoundError``."""
        # Arrange
        conn = make_connection()
        seed_component(conn)

        # Act / Assert
        with self.assertRaises(NotFoundError):
            await RollbackVersionQuery().execute(
                data=RollbackVersionRequest(version_id="01KW8WHA6STWW5N1VYRSHDTK1N"),
                connection=conn,
            )
