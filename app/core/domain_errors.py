from fastapi import status


class DomainError(Exception):
    status_code: int = status.HTTP_400_BAD_REQUEST

    def __init__(self, message: str, *, status_code: int | None = None):
        self.message = message
        if status_code is not None:
            self.status_code = status_code
        super().__init__(message)


class BadRequestError(DomainError):
    status_code = status.HTTP_400_BAD_REQUEST


class UnauthorizedError(DomainError):
    status_code = status.HTTP_401_UNAUTHORIZED


class ForbiddenError(DomainError):
    status_code = status.HTTP_403_FORBIDDEN


class NotFoundError(DomainError):
    status_code = status.HTTP_404_NOT_FOUND


class ConflictError(DomainError):
    status_code = status.HTTP_409_CONFLICT


class PayloadTooLargeError(DomainError):
    status_code = status.HTTP_413_CONTENT_TOO_LARGE


class ServiceUnavailableError(DomainError):
    status_code = status.HTTP_503_SERVICE_UNAVAILABLE
