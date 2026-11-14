"""Lore kits (.lorekit): template-only archives, here in the newer format (runeGroups)."""

import pytest

from .conftest import REAL_DIR, write_archive

KIT = {
    "name": "Kit des Mers",
    "lastVer": 23,
    "templates": [
        {"idHash": "t-port", "name": "Port", "category": "LC_Geography", "usedModules": [
            {"idHash": "m-desc", "typeCodeModule": "LM_Standard_Text", "header": "Description", "positionYMin": 0, "positionXMin": 0},
            {"idHash": "m-rune", "typeCodeModule": "LM_Rune", "header": "Infos", "isHidden": True,
             "linkedModuleTemplateId": "g-port", "positionYMin": 1, "positionXMin": 0},
            {"idHash": "m-mir", "typeCodeModule": "LM_Mirror", "header": "Navires", "templateFilter": "t-nav",
             "typeFilter": "template", "positionYMin": 2, "positionXMin": 0},
        ]},
        {"idHash": "t-nav", "name": "Navire", "category": "c-flotte", "usedModules": []},
    ],
    "runeGroups": [{"idHash": "g-port", "name": "Rune Port", "runes": [
        {"idHash": "r1", "label": "Population", "type": "LR_Quantum"},
        {"idHash": "r2", "label": "Dirigeant", "type": "LR_Tag"},
    ]}],
    "customTemplateCategories": [{"idHash": "c-flotte", "name": "Flotte"}],
    "inspirationLists": [{"idHash": "i1", "name": "Noms de ports", "items": ["Écume", "Brisant"]}],
}


@pytest.fixture
def kit_server(server, campaign_dir):
    write_archive(campaign_dir / "Mers.lorekit", KIT)
    return server


def test_kit_is_listed(kit_server):
    kit = next(f for f in kit_server.list_amsel_files() if f["kind"] == "lorekit")
    assert kit["title"] == "Kit des Mers" and kit["templates"] == 2 and kit["rune_templates"] == 1


def test_kit_templates_and_detail(kit_server):
    out = kit_server.list_lore_templates("mers")
    assert "template kit" in out and "**Navire** [Flotte]" in out and "pages" not in out.split("\n", 2)[2]
    out = kit_server.read_lore_template("mers", "port")
    assert "## Infos — Rune (hidden)\nrune: Rune Port\n- Population (Quantum)\n- Dirigeant (Tag)" in out
    assert "lists pages of template: Navire" in out and "Noms de ports: Écume, Brisant" in out


def test_kit_is_never_written(kit_server, monkeypatch):
    monkeypatch.setenv("XDG_CONFIG_HOME", "/nonexistent")
    with pytest.raises(ValueError, match="No .lore file"):
        kit_server.create_lore_page("mers", "Port", "Brume")


def test_lore_template_detail_counts_pages(server):
    assert "· 2 pages" in server.read_lore_template("monde", "ville")


@pytest.mark.skipif(not any(REAL_DIR.glob("*.lorekit")), reason=f"no .lorekit in {REAL_DIR}")
def test_real_kits_render_every_template():
    from amsel_mcp import render
    from amsel_mcp.workspace import Workspace

    ws = Workspace([REAL_DIR])
    for path in REAL_DIR.glob("*.lorekit"):
        kit = ws.lore(str(path))
        render.lore_templates(kit)
        for t in kit.templates.values():
            render.lore_template(kit, t["idHash"])
        runes = [m for t in kit.templates.values() for m in t["usedModules"] if m["typeCodeModule"] == "LM_Rune"]
        assert all(m.get("linkedModuleTemplateId") in kit.rune_templates for m in runes), path.name
