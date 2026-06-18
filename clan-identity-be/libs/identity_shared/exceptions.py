"""Shared exception classes."""


class BaseServiceException(Exception):
    """Base exception for all service exceptions."""
    
    def __init__(self, message: str, status_code: int = 500):
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)


class NotFoundException(BaseServiceException):
    """Resource not found exception."""
    
    def __init__(self, message: str = "Resource not found"):
        super().__init__(message, status_code=404)


class UnauthorizedException(BaseServiceException):
    """Unauthorized access exception."""
    
    def __init__(self, message: str = "Unauthorized"):
        super().__init__(message, status_code=401)


class ForbiddenException(BaseServiceException):
    """Forbidden access exception."""
    
    def __init__(self, message: str = "Forbidden"):
        super().__init__(message, status_code=403)


class BadRequestException(BaseServiceException):
    """Bad request exception."""
    
    def __init__(self, message: str = "Bad request"):
        super().__init__(message, status_code=400)


class ConflictException(BaseServiceException):
    """Resource conflict exception."""
    
    def __init__(self, message: str = "Resource already exists"):
        super().__init__(message, status_code=409)


class ValidationException(BaseServiceException):
    """Validation error exception."""
    
    def __init__(self, message: str = "Validation error"):
        super().__init__(message, status_code=422)
