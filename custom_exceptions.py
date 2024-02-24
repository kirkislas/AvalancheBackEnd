from fastapi import HTTPException


class DatabaseConnectionError(HTTPException):
    def __init__(self, detail: str = "Database connection failed"):
        super().__init__(status_code=500, detail=detail)

class DataNotFoundError(HTTPException):
    def __init__(self, detail: str = "Requested data not found"):
        super().__init__(status_code=404, detail=detail)

class ValidationError(HTTPException):
    def __init__(self, detail: str = "Validation error"):
        super().__init__(status_code=422, detail=detail)

class RedisConnectionError(HTTPException):
    def __init__(self, detail: str = "Redis connection failed"):
        super().__init__(status_code=500, detail=detail)
        

class AWSCredentialsError(HTTPException):
    def __init__(self, detail: str):
        super().__init__(status_code=500, detail=detail)