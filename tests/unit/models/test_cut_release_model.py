"""Unit tests for :class:`CutReleaseModel`."""

from app.models.requests.cut_release_model import CutReleaseModel


def test_cut_release_model_defaults_label_and_notes_to_none() -> None:
    """An empty cut request carries no label and no notes."""
    # Act
    model = CutReleaseModel()

    # Assert
    assert model.label is None
    assert model.notes is None


def test_cut_release_model_accepts_label_and_notes() -> None:
    """The client-settable label and notes are captured."""
    # Act
    model = CutReleaseModel(label="Aurora 5.1", notes="ship it")

    # Assert
    assert model.label == "Aurora 5.1"
    assert model.notes == "ship it"


def test_cut_release_model_does_not_model_a_version_field() -> None:
    """The server owns the version; no version field is exposed to the client."""
    # Act
    fields = set(CutReleaseModel.model_fields)

    # Assert
    assert fields == {"label", "notes"}
