class BaseAPIException(Exception):
    pass


class ObjectNotFoundError(BaseAPIException):
    pass


class ConflictError(BaseAPIException):
    pass


class CanNotBeChangedError(BaseAPIException):
    pass


class ImageError(BaseAPIException):
    pass
