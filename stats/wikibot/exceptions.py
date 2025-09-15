class MissingWikiContent(Exception):
    """Base exception for wiki parsing where an expected section is missing from the downloaded content"""

    default_message = "Some expected content from the wiki download is missing"

    def __init__(self, message: str | None = None) -> None:
        super().__init__(message or MissingWikiContent.default_message)
