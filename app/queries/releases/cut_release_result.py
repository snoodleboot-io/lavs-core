"""Internal result of the cut-release query: the release plus a created flag."""

from pydantic import BaseModel

from app.models.responses.release_response_model import ReleaseResponseModel


class CutReleaseResult(BaseModel):
    """The outcome of executing :class:`CutReleaseQuery`.

    ``created`` distinguishes a fresh cut from an idempotent replay: when a
    request repeats a prior ``Idempotency-Key`` the query returns the existing
    release with ``created=False`` so the route knows **not** to re-emit a
    ``release.cut`` event (a replay is not a second cut).
    """

    release: ReleaseResponseModel
    created: bool

    model_config = {"frozen": True}
