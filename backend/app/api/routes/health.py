from fastapi import APIRouter

router = APIRouter()

@router.get("/")
def health_check():
    """
    Health check endpoint to verify that the API is up and running.
    """
    return {"status": "OK", "message": "API is operational"}
