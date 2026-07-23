"""Request body for creating an immutable version."""

import re
from typing import Annotated

from annotated_types import Ge, MaxLen
from pydantic import computed_field, field_validator

from app.models.requests.request_model import RequestModel
from app.models.types.ulid_id import UlidId


class CreateVersionModel(RequestModel):
    """JSON body for ``POST /versions``.

    The ``version`` string must be a traditional semantic version
    (``^\\d+\\.\\d+\\.\\d+(-[0-9A-Za-z.-]+)?$``); the ``major``/``minor``/``patch``
    components are derived from it. See ``docs/design/API_CONTRACT.md`` §3-§4.
    """

    component_id: UlidId
    version: Annotated[str, MaxLen(256)]
    prerelease: Annotated[str, MaxLen(256)] | None = None

    @field_validator("version", mode="before")
    @classmethod
    def validate_version(cls, field_value: str) -> str:
        """Ensure the version string is a traditional semantic version.

        Args:
            field_value: value assigned to the version string.

        Returns:
            str: The validated version string.

        Raises:
            ValueError: When the version format is not valid.
        """
        rex = re.compile(r"^\d+\.\d+\.\d+(-[0-9A-Za-z.-]+)?$")
        if rex.match(field_value):
            return field_value
        raise ValueError("version must be a semantic version number.")

    @computed_field
    @property
    def major(self) -> Annotated[int, Ge(0)]:
        """The major component of the semantic version."""
        return int(self.version.split(".")[0])

    @computed_field
    @property
    def minor(self) -> Annotated[int, Ge(0)]:
        """The minor component of the semantic version."""
        return int(self.version.split(".")[1])

    @computed_field
    @property
    def patch(self) -> Annotated[int, Ge(0)]:
        """The patch component of the semantic version."""
        patch_segment = self.version.split(".")[2]
        return int(patch_segment.split("-", 1)[0])

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "component_id": "01KW8WHA6STWW5N1VYRSHDTK1N",
                    "version": "2.4.0",
                    "prerelease": None,
                }
            ]
        }
    }
