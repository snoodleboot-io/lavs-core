from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query

from app.models.requests.application_name_model import ApplicationNameModel
from app.models.responses.application_and_version_response_model import (
    ApplicationAndVersionResponseModel,
)
from app.models.responses.patch_response_model import PatchResponseModel
from app.queries.patch_version.create_patch import CreatePatch
from app.queries.patch_version.read_current_patch import ReadCurrentPatch
from app.queries.patch_version.rollback_to_previous_patch_version import (
    RollbackToPreviousPatchVersion,
)
from app.security.api_key import get_api_key

router = APIRouter(
    tags=["patch"],
    prefix="/patch",
    dependencies=[Depends(get_api_key)],
)


@router.post("/", response_model=ApplicationAndVersionResponseModel)
async def create(data: Annotated[ApplicationNameModel, Query()]):
    """Create the next patch version."""
    try:
        result = await CreatePatch().execute(data=data)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    return result


@router.get("/", response_model=PatchResponseModel)
async def get(data: Annotated[ApplicationNameModel, Query()]):
    """Retrieve the current patch version."""
    try:
        result = await ReadCurrentPatch().execute(data=data)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e

    return result


@router.post("/rollback", response_model=ApplicationAndVersionResponseModel)
async def rollback(data: Annotated[ApplicationNameModel, Query()]):
    try:
        result = await RollbackToPreviousPatchVersion().execute(data=data)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    return result
