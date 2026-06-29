"""Response body describing a component together with its versions."""

from app.models.enums.component_kind import ComponentKind
from app.models.responses.response_model import ResponseModel
from app.models.responses.version_response_model import VersionResponseModel


class ComponentWithVersionsResponseModel(ResponseModel):
    """A component plus its immutable version history.

    Used as an element of the timeline composite response — see
    ``docs/design/API_CONTRACT.md`` §3.
    """

    id: str
    product_id: str
    name: str
    kind: ComponentKind
    versions: list[VersionResponseModel]
