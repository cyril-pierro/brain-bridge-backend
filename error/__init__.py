
class ServerError(Exception):
    """Base class for server-related errors"""

    def __init__(self, msg="Server error occurred", status_code=500):
        self.msg = msg
        self.status_code = status_code
        super().__init__(self.msg)


class ServerConnectionError(ServerError):
    """Raised when server connection fails"""

    def __init__(self, msg="Server connection failed", status_code=503):
        super().__init__(msg=msg, status_code=status_code)


class ServerTimeoutError(ServerError):
    """Raised when server request times out"""

    def __init__(self, msg="Server request timed out", status_code=504):
        super().__init__(msg=msg, status_code=status_code)


class InvalidRequestError(ServerError):
    """Raised when request is invalid"""

    def __init__(self, msg="Invalid request", status_code=400):
        super().__init__(msg=msg, status_code=status_code)


class AuthenticationError(ServerError):
    """Raised when authentication fails"""

    def __init__(self, msg="Authentication failed", status_code=401):
        super().__init__(msg=msg, status_code=status_code)


class AuthorizationError(ServerError):
    """Raised when user is not authorized"""

    def __init__(self, msg="Not authorized", status_code=403):
        super().__init__(msg=msg, status_code=status_code)


class ResourceNotFoundError(ServerError):
    """Raised when requested resource is not found"""

    def __init__(self, msg="Resource not found", status_code=404):
        super().__init__(msg=msg, status_code=status_code)


class ServerOverloadError(ServerError):
    """Raised when server is overloaded"""

    def __init__(self, msg="Server is overloaded", status_code=503):
        super().__init__(msg=msg, status_code=status_code)


class InternalServerError(ServerError):
    """Raised when an internal server error occurs"""

    def __init__(self, msg="Internal server error", status_code=500):
        super().__init__(msg=msg, status_code=status_code)


class DatabaseError(ServerError):
    """Raised when a database operation fails"""

    def __init__(self, msg="Database operation failed", status_code=500):
        super().__init__(msg=msg, status_code=status_code)


class DatabaseConnectionError(DatabaseError):
    """Raised when database connection fails"""

    def __init__(self, msg="Database connection failed", status_code=503):
        super().__init__(msg=msg, status_code=status_code)


class DatabaseIntegrityError(DatabaseError):
    """Raised when database integrity constraint is violated"""

    def __init__(self, msg="Database constraint violated", status_code=400):
        super().__init__(msg=msg, status_code=status_code)


class DatabaseTimeoutError(DatabaseError):
    """Raised when database operation times out"""

    def __init__(self, msg="Database operation timed out", status_code=504):
        super().__init__(msg=msg, status_code=status_code)


class DatabaseLockError(DatabaseError):
    """Raised when database lock conflicts occur"""

    def __init__(self, msg="Database lock conflict occurred", status_code=409):
        super().__init__(msg=msg, status_code=status_code)
