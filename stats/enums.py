from enum import StrEnum  # type: ignore


class AdminActionTypes(StrEnum):
    MOVE_CHAPTERS = "move_chapters"
    MERGE_REFTYPES_NO_ALIAS = "merge_reftypes_no_alias"
    MERGE_REFTYPES_WITH_ALIAS = "merge_reftypes_with_alias"
