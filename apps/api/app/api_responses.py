from app.schemas.errors import ErrorResponse


def not_found_response(resource_name: str) -> dict[int, dict]:
    return {
        404: {
            "model": ErrorResponse,
            "description": f"{resource_name} not found",
        }
    }


def bad_request_response(description: str = "Bad request") -> dict[int, dict]:
    return {
        400: {
            "model": ErrorResponse,
            "description": description,
        }
    }