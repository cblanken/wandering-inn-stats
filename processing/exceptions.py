class LockedChapterError(Exception):
    """Base exception for Chapter downloads that cannot or should not be processed"""

    default_message = "The chapter should not be processed"

    def __init__(self, message: str | None = None) -> None:
        super().__init__(message or LockedChapterError.default_message)


class PatreonChapterError(LockedChapterError):
    """Exception raised for Patreon-locked chapters"""

    default_message = "A Patreon-locked chapter was detected and could not be downloaded"

    def __init__(self, message: str | None = None) -> None:
        super().__init__(message or PatreonChapterError.default_message)
