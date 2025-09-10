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


class ChapterPartitionsOverlappingError(Exception):
    """Exception raised for chapters split into partitions with overlap"""

    default_message = "A chapter was split into partitions with overlapping ranges which is not allowed"

    def __init__(self, message: str | None = None) -> None:
        super().__init__(message or ChapterPartitionsOverlappingError.default_message)


class TooManyAuthorsNotes(Exception):
    """Exception raised for parsed chapters with too many detect Author's notes"""

    default_message = "A parsed chapter detected too many Author's notes. The parser may have failed to properly partition the Author's notes."

    def __init__(self, message: str | None = None) -> None:
        super().__init__(message or TooManyAuthorsNotes.default_message)
