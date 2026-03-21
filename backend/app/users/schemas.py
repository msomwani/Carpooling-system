from pydantic import BaseModel, ConfigDict
from typing import Literal

class RoleUpdateRequest(BaseModel):
    role: Literal["driver", "passenger"]

class UserResponse(BaseModel):
    id: str
    email: str
    name: str
    role: str
    model_config = ConfigDict(from_attributes=True)
