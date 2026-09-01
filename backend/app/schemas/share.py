from pydantic import BaseModel


class ShareCreateResponse(BaseModel):
    token: str
    url: str
