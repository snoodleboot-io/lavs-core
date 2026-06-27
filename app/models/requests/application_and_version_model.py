import re
from typing import Annotated

from annotated_types import Ge
from pydantic import computed_field, field_validator

from app.models.requests.request_model import RequestModel


class ApplicationAndVersionNameModel(RequestModel):
    """"""

    product_name: str
    version: str | None = None

    @field_validator("version", mode="before")
    @classmethod
    def validate_version(cls, field_value: str) -> str:
        """This validation makes sure that the version string is a traditional semantic version.

        Args:
            field_value: value assigned to the version string.

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
        if self.version is None:
            raise ValueError("version is required for major component")
        return int(self.version.split(".")[0])

    @computed_field
    @property
    def minor(self) -> Annotated[int, Ge(0)]:
        """The minor component of the semantic version."""
        if self.version is None:
            raise ValueError("version is required for minor component")
        return int(self.version.split(".")[1])

    @computed_field
    @property
    def patch(self) -> Annotated[int, Ge(0)]:
        """The patch component of the semantic version."""
        if self.version is None:
            raise ValueError("version is required for patch component")
        patch_segment = self.version.split(".")[2]
        return int(patch_segment.split("-", 1)[0])

    model_config = {
        "json_schema_extra": {
            "examples": [{"product_name": "My Sample Product", "version": "1.2.3"}]
        }
    }
