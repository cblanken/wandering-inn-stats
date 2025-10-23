import pytest

from innverse.search import WebSearch


class TestSearchTextHighlighting:
    """Tests for full text search highlighting"""

    @pytest.fixture
    def text(scope="class") -> str:
        return """Mrsha closed the door. Exciting as that sounded, she had places to be. She looked around the soggy landscape, wand in hand, and noticed Apista had flown out with her. Well, that was good. It was time for an adventure! Mrsha knew it was dangerous outside, but now she knew magic! Or at least, one spell. She was going to be Mrsha the Great! Not just great—she’d be Mrsha, the Great and Terrible! The Gnoll wandered off in search of an adventure."""

    def test_exact_phrase(self, text: str) -> None:
        ws = WebSearch(text, '"the Great and Terrible"')

        assert (
            ws.highlighted_text()
            == """Mrsha closed the door. Exciting as that sounded, she had places to be. She looked around the soggy landscape, wand in hand, and noticed Apista had flown out with her. Well, that was good. It was time for an adventure! Mrsha knew it was dangerous outside, but now she knew magic! Or at least, one spell. She was going to be Mrsha the Great! Not just great—she’d be Mrsha, <span class="bg-hl-tertiary text-black p-[1px]">the Great and Terrible</span>! The Gnoll wandered off in search of an adventure."""
        )

    def test_exact_phrase_and_keywords_before(self, text: str) -> None:
        """Highlight keywords and phrase in mixed query with keywords before phrase"""
        ws = WebSearch(text, 'spell Gnoll "closed the door"')

        assert (
            ws.highlighted_text()
            == """Mrsha <span class="bg-hl-tertiary text-black p-[1px]">closed the door</span>. Exciting as that sounded, she had places to be. She looked around the soggy landscape, wand in hand, and noticed Apista had flown out with her. Well, that was good. It was time for an adventure! Mrsha knew it was dangerous outside, but now she knew magic! Or at least, one <span class="bg-hl-tertiary text-black p-[1px]">spell.</span> She was going to be Mrsha the Great! Not just great—she’d be Mrsha, the Great and Terrible! The <span class="bg-hl-tertiary text-black p-[1px]">Gnoll</span> wandered off in search of an adventure."""
        )

    def test_exact_phrase_and_keywords_before_and_after(self, text: str) -> None:
        """Highlight keywords and phrase in mixed query with keywords before phrase"""
        ws = WebSearch(text, 'spell Gnoll "closed the door" time adventure')

        assert (
            ws.highlighted_text()
            == """Mrsha <span class="bg-hl-tertiary text-black p-[1px]">closed the door</span>. Exciting as that sounded, she had places to be. She looked around the soggy landscape, wand in hand, and noticed Apista had flown out with her. Well, that was good. It was <span class="bg-hl-tertiary text-black p-[1px]">time</span> for an <span class="bg-hl-tertiary text-black p-[1px]">adventure!</span> Mrsha knew it was dangerous outside, but now she knew magic! Or at least, one <span class="bg-hl-tertiary text-black p-[1px]">spell.</span> She was going to be Mrsha the Great! Not just great—she’d be Mrsha, the Great and Terrible! The <span class="bg-hl-tertiary text-black p-[1px]">Gnoll</span> wandered off in search of an <span class="bg-hl-tertiary text-black p-[1px]">adventure.</span>"""
        )

    def test_exact_phrase_and_keywords_after(self, text: str) -> None:
        """Highlight keywords and phrase in mixed query with keywords before phrase"""
        ws = WebSearch(text, '"closed the door" Gnoll spell')

        assert (
            ws.highlighted_text()
            == """Mrsha <span class="bg-hl-tertiary text-black p-[1px]">closed the door</span>. Exciting as that sounded, she had places to be. She looked around the soggy landscape, wand in hand, and noticed Apista had flown out with her. Well, that was good. It was time for an adventure! Mrsha knew it was dangerous outside, but now she knew magic! Or at least, one <span class="bg-hl-tertiary text-black p-[1px]">spell.</span> She was going to be Mrsha the Great! Not just great—she’d be Mrsha, the Great and Terrible! The <span class="bg-hl-tertiary text-black p-[1px]">Gnoll</span> wandered off in search of an adventure."""
        )

    @pytest.mark.skip
    def test_keywords_normalized_case(self, text: str) -> None:
        """Highlight keywords regardless of case"""
        ws = WebSearch(text, "mAgiC Least well")

        # TODO
        assert ws.highlighted_text() == ""

    @pytest.mark.skip
    def test_ignore_negation_keywords(self, text: str) -> None:
        """Do not highlight keywords marked for negation"""
        ws = WebSearch(text, "knew -dangerous -Apista")

        assert (
            ws.highlighted_text()
            == """Mrsha closed the door. Exciting as that sounded, she had places to be. She looked around the soggy landscape, wand in hand, and noticed Apista had flown out with her. Well, that was good. It was time for an adventure! Mrsha <span class="bg-hl-tertiary text-black p-[1px]">knew</span> it was dangerous outside, but now she <span class="bg-hl-tertiary text-black p-[1px]">knew</span> magic! Or at least, one spell. She was going to be Mrsha the Great! Not just great—she’d be Mrsha, the Great and Terrible! The Gnoll wandered off in search of an adventure."""
        )

    def test_phrase_normalized_case(self, text: str) -> None:
        """Highlight phrases regardless of case"""

        # Matches lowercase from upper
        ws = WebSearch(text, '"Time for an Adventure"')
        assert (
            ws.highlighted_text()
            == """Mrsha closed the door. Exciting as that sounded, she had places to be. She looked around the soggy landscape, wand in hand, and noticed Apista had flown out with her. Well, that was good. It was <span class="bg-hl-tertiary text-black p-[1px]">time for an adventure</span>! Mrsha knew it was dangerous outside, but now she knew magic! Or at least, one spell. She was going to be Mrsha the Great! Not just great—she’d be Mrsha, the Great and Terrible! The Gnoll wandered off in search of an adventure."""
        )

        # Matches uppercase from lower
        ws = WebSearch(text, '"the great and terrible"')
        assert (
            ws.highlighted_text()
            == """Mrsha closed the door. Exciting as that sounded, she had places to be. She looked around the soggy landscape, wand in hand, and noticed Apista had flown out with her. Well, that was good. It was time for an adventure! Mrsha knew it was dangerous outside, but now she knew magic! Or at least, one spell. She was going to be Mrsha the Great! Not just great—she’d be Mrsha, <span class="bg-hl-tertiary text-black p-[1px]">the Great and Terrible</span>! The Gnoll wandered off in search of an adventure."""
        )
