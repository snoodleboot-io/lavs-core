from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query

from app.models.requests.application_and_version_model import (
    ApplicationAndVersionNameModel,
)
from app.models.requests.application_name_model import ApplicationNameModel
from app.models.responses.application_and_version_response_model import (
    ApplicationAndVersionResponseModel,
)
from app.models.responses.response_model import ResponseModel
from app.queries.versions.create_version import CreateVersion
from app.queries.versions.delete_version import DeleteVersion
from app.queries.versions.retrieve_latest_version import RetrieveLatestVersion
from app.queries.versions.retrieve_version_history import RetrieveVersionHistory
from app.security.api_key import get_api_key

router = APIRouter(
    tags=["versions"],
    prefix="/versions",
    dependencies=[Depends(get_api_key)],
)


@router.get("/", response_model=list[ApplicationAndVersionResponseModel])
async def get(data: Annotated[ApplicationNameModel, Query()]):
    result = await RetrieveVersionHistory().execute(data=data)

    return result


@router.get("/latest", response_model=ApplicationAndVersionResponseModel)
async def get_all(data: Annotated[ApplicationNameModel, Query()]):
    result = await RetrieveLatestVersion().execute(data=data)
    if result is None:
        raise HTTPException(status_code=404, detail="No version found for this product")

    return result


@router.post("/", response_model=ApplicationAndVersionResponseModel)
async def create(data: Annotated[ApplicationAndVersionNameModel, Query()]):
    if data.version is None:
        raise HTTPException(status_code=422, detail="version is required")
    result = await CreateVersion().execute(data=data)

    return result


@router.delete("/", response_model=ResponseModel)
async def read_all(data: Annotated[ApplicationAndVersionNameModel, Query()]):
    result = await DeleteVersion().execute(data=data)

    return result
