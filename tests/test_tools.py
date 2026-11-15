import pytest

from amsel_mcp.model import PageNotFound


def test_list_files_reports_counts_and_linked_lore(server, campaign_dir):
    files = {f["kind"]: f for f in server.list_amsel_files()}
    assert files["tome"]["story_pages"] == 3
    assert files["tome"]["arcanes"] == 1
    # recorded path does not exist: the sibling .lore with the same name is used
    assert files["tome"]["linked_lore"] == str(campaign_dir / "Monde.lore")
    assert files["lore"]["pages"] == 2


def test_outline_shows_tree_ribbon_and_states(server):
    out = server.tome_outline("campagne")
    assert "- [Story] Campagne" in out
    assert "  - [Chapter] Chapitre 1 (ts000002) — ribbon red" in out
    assert "    - [Scene] Arrivée au port (ts000003) — Session 1: joue" in out


def test_data_pages_grouped_in_app_order(server):
    out = server.list_tome_data_pages("campagne")
    assert out.index("## Location") < out.index("## Character")
    assert "PNJ : Mirelle (td000001) ★" in out
    assert "Character" not in server.list_tome_data_pages("campagne", "location")


def test_read_story_page_resolves_tome_lore_and_arcane_links(server):
    out = server.read_tome_page("campagne", "arrivee")  # accent-insensitive partial name
    assert "Les héros rencontrent [[PNJ : Mirelle]] à [[Écume]]." in out
    assert "[[choice#ta000001: Trahir PNJ : Mirelle ?]]" in out
    assert "parent: [[Chapitre 1]]" in out


def test_read_data_page_subpages_relations_backlinks(server):
    out = server.read_tome_page("campagne", "td000001")  # id prefix
    assert "## Résumé\nContrebandière *rusée*." in out
    assert "### Voix\nRauque" in out and "Vide" not in out
    assert "## Relations\n- [[La Taverne]]" in out
    assert "## Referenced by" in out and "- [[Arrivée au port]]" in out


def test_ambiguous_and_missing_pages(server):
    with pytest.raises(PageNotFound, match="No Tome page"):
        server.read_tome_page("campagne", "dragon")
    with pytest.raises(PageNotFound, match="4 Tome pages match 'a'"):
        server.read_tome_page("campagne", "a")  # matches several names


def test_arcanes_with_results(server):
    out = server.list_tome_arcanes("campagne")
    assert "**choice** (ta000001): Trahir [[PNJ : Mirelle]] ?" in out
    assert "Session 1 — result: no; note: Fidèles" in out
    assert "appears in: [[Arrivée au port]]" in out
    assert server.list_tome_arcanes("campagne", "destiny") == "No arcanes."


def test_notes(server):
    assert "Bonne session" in server.read_tome_notes("campagne")


def test_lore_page_modules_in_template_order(server):
    out = server.read_lore_page("monde", "ecume")
    assert out.index("## Description") < out.index("## Blason") < out.index("## Sources")
    assert "Port franc tenu par [[Guilde des Marées]]." in out
    assert "[image: Blason d'Écume]" in out
    assert "- Livre: [[Guilde des Marées]]" in out


def test_lore_backlinks_include_rune_references(server):
    out = server.read_lore_page("monde", "guilde")
    assert "## Histoire\nFondée il y a **300 ans**." in out
    assert "## Referenced by\n- [[Écume]]" in out


def test_lore_listings(server):
    assert "## Ville (2)" in server.list_lore_pages("monde")
    assert server.list_lore_pages("monde", "donjon").startswith("No Lore pages")
    assert "**Ville** [Geography] — 2 pages — modules: Description (Standard_Text), Blason (Image), Sources (Rune)" in server.list_lore_templates("monde")


def test_search_across_tome_and_linked_lore(server):
    out = server.search_amsel("guilde", file="campagne")
    assert "[lore Monde] Guilde des Marées" in out
    assert "[lore Monde] Écume" in out  # text match via resolved link
    assert server.search_amsel("introuvable").startswith("No match")


def test_unknown_file_lists_known_ones(server):
    with pytest.raises(ValueError, match="Known files: Campagne.tome"):
        server.tome_outline("nope")
