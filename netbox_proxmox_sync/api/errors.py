class APIError(Exception):
    def __init__(self, message, status=500):
        super().__init__(message)
        self.status = status


class ValidationError(APIError):
    def __init__(self, message, errors=[]):
        super().__init__(message, 422)
        self.errors = errors


class UnauthorizedError(APIError):
    def __init__(self, message):
        super().__init__(message, 401)
