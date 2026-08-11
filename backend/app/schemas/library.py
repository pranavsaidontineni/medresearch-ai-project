from datetime import datetime
from pydantic import BaseModel, Field
from app.schemas.paper import PaperRead

class CollectionCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    description: str | None = Field(default=None, max_length=500)

class CollectionRead(BaseModel):
    id: int
    name: str
    description: str | None
    created_at: datetime
    paper_count: int = 0

class SavePaperRequest(BaseModel):
    collection_id: int | None = None

class SavedPaperRead(BaseModel):
    id: int
    collection_id: int | None
    created_at: datetime
    paper: PaperRead
