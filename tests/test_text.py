from amsel_mcp.text import extract_links, html_to_text, normalize


def test_inline_formatting_and_spacing():
    html = "<p><em>a</em> <strong>B</strong> c<strong> </strong>d <strong>e </strong>f</p>"
    assert html_to_text(html) == "*a* **B** c d **e** f"


def test_lists_entities_and_links():
    html = '<ul><li>x<ul><li>y</li></ul></li></ul><ol><li>one</li><li>two</li></ol><p>z&nbsp;<a href="http://u">lien</a></p>'
    assert html_to_text(html) == "- x\n  - y\n\n1. one\n2. two\n\nz lien (http://u)"


def test_tag_components_resolved_or_flagged():
    html = '<p>Voir <tag-component id="lorePage/abc-1"></tag-component> et <tag-component id="index/zzz"></tag-component></p>'
    out = html_to_text(html, lambda k, r: "Ville" if r == "abc-1" else None)
    assert out == "Voir [[Ville]] et [[missing index link]]"


def test_extract_links_handles_all_kinds():
    html = '<tag-component id="storyPage/a1"></tag-component><destiny-component idhash="b2"></destiny-component>'
    assert extract_links(html) == [("storyPage", "a1"), ("arcane", "b2")]


def test_normalize_is_accent_and_case_insensitive():
    assert normalize("  Écume   DES  mers ") == "ecume des mers"


def test_amsel_lists_and_quotes_with_inner_paragraphs():
    html = (
        '<ul class="list-disc pl-5"><li><p class="text-body">un</p></li><li><p class="text-body">deux</p></li></ul>'
        '<blockquote><p class="text-body">ligne 1</p><p class="text-body">ligne 2</p></blockquote><p>après</p>'
    )
    assert html_to_text(html) == "- un\n- deux\n\n> ligne 1\n\n> ligne 2\n\naprès"
