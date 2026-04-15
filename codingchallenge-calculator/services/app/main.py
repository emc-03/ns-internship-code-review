from logging import exception

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from app.calculator import calculate
from app.models import CalculateRequest, CalculateResponse

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def read_root():
    return {"message": "Let's Calculate!"}
@app.post("/calculate", response_model=CalculateResponse)
def calculate_endpoint(request: CalculateRequest):
    try:
        result = calculate(request.left, request.operation, request.right)
        return CalculateResponse(result=result)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))