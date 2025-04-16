from core.exceptions.base_exceptions import ImageError


class NotAllowdedContentTypes(ImageError):
    def __init__(self, message="Not allowded content types"):
        self.message = message
        super().__init__(self.message)


class ImageSizeTooLargeError(ImageError):
    def __init__(self, message="Image size too large"):
        self.message = message
        super().__init__(self.message)
