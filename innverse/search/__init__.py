from enum import Enum

import regex


class RangeType(Enum):
    PHRASE = 0
    KEYWORDS = 1


class WebSearchRange:
    """A range across a search's text indicating a marked phrase OR a section
    containing keywords"""

    type: RangeType
    start: int
    stop: int

    def __init__(self, range_type: RangeType, start: int, stop: int) -> None:
        self.type = range_type
        if start > stop:
            msg = "WebSearch ranges must be ascending."
            raise ValueError(msg)
        self.start = start
        self.stop = stop

    def __repr__(self) -> str:
        return f"<WebSearchRange type: {self.type} start: {self.start}, stop: {self.stop}>"


class WebSearch:
    """Models a Postgres `websearch` query including functions
    for properly highlighting results. The Postgres `websearch` query
    allows for phrases surrounded with qutoes ("), negations with a leading
    minus (-) sign, and keywords for everything else split on whitespace
    - Keywords are normalized to lowercase.
    - Phrases take priority for highlighting, so no keywords should be highlighting
    within phrases.
    - `ignore_range` is a section of the incoming text that is already highlighted or should
    otherwise be ignored when highlighting
    """

    text: str
    text_lower: str
    query: str
    search_ranges: list[WebSearchRange]
    keywords: list[str]
    phrases: list[str]
    negations: list[str]
    max_phrase_highlights: int

    def __init__(self, text: str, query: str, max_phrase_highlights: int = 5) -> None:
        self.text = text
        self.text_lower = text.lower()
        self.query = query
        self.max_phrase_highlights = max_phrase_highlights
        self.keywords, self.phrases, self.negations = self.__parse_query()

    def __parse_query(self) -> tuple[list[str], list[str], list[str]]:
        """Identifies ranges of phrases and keywords from"""
        partitions = self.query.split('"')
        if len(partitions) % 2 == 0:
            # Uneven quotes or no quotes
            msg = "The filter text must contain an even number of quotes to specify any phrases"
            raise ValueError(msg)

        phrases: list[str] = []
        keywords: list[str] = []
        negations: list[str] = []
        if len(partitions) % 2 == 1:
            for i, part in enumerate(partitions):
                if i % 2 == 1:
                    # All odd indexes are quoted phrases
                    phrases.append(part)
                else:
                    for word in regex.split(r"\s+", part):
                        if len(word) > 0:
                            if word[0] == "-":
                                negations.append(word)
                            else:
                                keywords.append(word)

        return (keywords, phrases, negations)

    def __find_text_ranges(self, phrases: list[str]) -> list[WebSearchRange]:
        phrase_ranges: list[WebSearchRange] = []
        for phrase in phrases:
            phrase_highlight_count = 0
            phrase_lookup_start = 0
            while phrase_highlight_count < self.max_phrase_highlights:
                phrase_i = self.text_lower.find(phrase.lower(), phrase_lookup_start)
                if phrase_i == -1:
                    break
                phrase_ranges.append(WebSearchRange(RangeType.PHRASE, phrase_i, phrase_i + len(phrase)))
                phrase_lookup_start = phrase_i + len(phrase)
                phrase_highlight_count += 1

        ranges: list[WebSearchRange] = []
        if phrase_ranges:
            phrase_ranges.sort(key=lambda pr: pr.start)
            keyword_range_start = 0
            for pr in phrase_ranges:
                if keyword_range_start != pr.start:
                    ranges.append(WebSearchRange(RangeType.KEYWORDS, keyword_range_start, pr.start))
                ranges.append(pr)
                keyword_range_start = pr.stop
            if keyword_range_start != len(self.text):
                ranges.append(WebSearchRange(RangeType.KEYWORDS, keyword_range_start, len(self.text)))
        else:
            ranges = [WebSearchRange(RangeType.KEYWORDS, 0, len(self.text))]

        return ranges

    def highlight_range(self, r: WebSearchRange) -> str:
        hl_begin = '<span class="bg-hl-tertiary text-black p-[1px]">'
        hl_end = "</span>"

        match r.type:
            case RangeType.PHRASE:
                return f"{hl_begin}{self.text[r.start : r.stop]}{hl_end}"
            case RangeType.KEYWORDS:
                words = [
                    f"{hl_begin}{word}{hl_end}"
                    if any(regex.match(keyword, word) for keyword in self.keywords)
                    else word
                    for word in regex.split(r"\s+", self.text[r.start : r.stop])
                ]
                return " ".join(words)

    def highlighted_text(self) -> str:
        ranges = self.__find_text_ranges(self.phrases)

        hl_text_sections: list[str] = []
        for r in ranges:
            hl_text_sections.append(self.highlight_range(r))

        return "".join(hl_text_sections)
