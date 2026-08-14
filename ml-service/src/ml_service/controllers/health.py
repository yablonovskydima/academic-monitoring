from fastapi import APIRouter, HTTPException

from ml_service.clients.import_service_client import ImportServiceClient

router = APIRouter(tags=["health"])


@router.get("/health")
def health():
    return {"status": "ok"}


@router.get("/test-import-connection")
def test_import_connection():
    client = ImportServiceClient()
    try:
        features = client.get_current_features()
        return {
            "status": "ok",
            "students_count": len(features),
            "sample": features[0] if features else None,
        }
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Failed to reach import-service: {e}")


@router.get("/test-import-semester-connection")
def test_import_semester_connection():
    client = ImportServiceClient()
    try:
        features = client.get_semester_features()
        return {
            "status": "ok",
            "records_count": len(features),
            "sample": features[0] if features else None,
        }
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Failed to reach import-service: {e}")