from pydantic import BaseModel
from typing import Literal

class RoleUpdateRequest(BaseModel):
    role: Literal["driver", "passenger"]
