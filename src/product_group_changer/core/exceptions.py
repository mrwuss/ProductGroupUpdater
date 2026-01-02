"""Application exceptions."""


class AppError(Exception):
    """Base application error."""

    def __init__(self, message: str, code: str = "APP_ERROR"):
        self.message = message
        self.code = code
        super().__init__(message)


class P21Error(AppError):
    """P21 API error."""

    def __init__(self, message: str, status_code: int | None = None):
        super().__init__(message, "P21_ERROR")
        self.status_code = status_code


class P21AuthError(P21Error):
    """P21 authentication error."""

    def __init__(self, message: str = "Authentication failed"):
        super().__init__(message, 401)


class P21NotFoundError(P21Error):
    """P21 resource not found."""

    def __init__(self, resource: str, identifier: str):
        super().__init__(f"{resource} not found: {identifier}", 404)


class ValidationError(AppError):
    """Validation error."""

    def __init__(self, message: str, field: str | None = None):
        super().__init__(message, "VALIDATION_ERROR")
        self.field = field
