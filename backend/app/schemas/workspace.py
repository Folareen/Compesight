import uuid
from datetime import datetime

from pydantic import BaseModel


class WorkspaceOut(BaseModel):
    id: uuid.UUID
    name: str
    slug: str
    plan: str
    created_at: datetime


class WorkspaceBootstrapIn(BaseModel):
    name: str
