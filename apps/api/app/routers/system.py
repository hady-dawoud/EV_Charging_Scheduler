from fastapi import APIRouter

router = APIRouter(tags=["system"])


@router.get("/")
def root():
    return {"message": "EV Smart Charging API is running"}


@router.get("/health")
def health():
    return {"status": "ok"}