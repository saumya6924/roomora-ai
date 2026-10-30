from decimal import Decimal
from typing import Annotated

from pydantic import BaseModel, ConfigDict, PlainSerializer

# Money is stored as Decimal but sent to the browser as a plain JSON number.
Money = Annotated[Decimal, PlainSerializer(float, return_type=float, when_used="json")]


class ORMModel(BaseModel):
    """Lets schemas be built straight from SQLAlchemy objects."""

    model_config = ConfigDict(from_attributes=True)


class StatusUpdate(BaseModel):
    status: str


class Message(BaseModel):
    message: str
