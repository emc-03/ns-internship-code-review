from pydantic import BaseModel

class CalculateRequest(BaseModel):
    left: float
    right: float
    operation: str

class CalculateResponse(BaseModel):
    result: float
    