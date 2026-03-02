from typing import Optional
from pydantic import BaseModel

class TTSCreate(BaseModel):
    text: str
    chat_id: Optional[str] = None