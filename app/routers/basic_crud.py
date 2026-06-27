from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.models.requests.application_name_model import ApplicationNameModel
from app.models.responses.application_and_version_response_model import (
    ApplicationAndVersionResponseModel,
)
from app.queries.crud.retrieve_all import RetrieveAll
from app.security.api_key import get_api_key

router = APIRouter(
    tags=["crud"],
    prefix="/crud",
    dependencies=[Depends(get_api_key)],
)


@router.get("/read_all", response_model=list[ApplicationAndVersionResponseModel])
async def read_all(data: Annotated[ApplicationNameModel, Query()]):
    results = await RetrieveAll().execute(data=data)
    return results
