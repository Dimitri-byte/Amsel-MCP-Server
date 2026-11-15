import os
import shutil
import socket
import tarfile

import pytest

from amsel_mcp.archive import read_data_json
from amsel_mcp.compose import text_to_html
from amsel_mcp.writer import WriteRefused, dump_json

from .conftest import L_GUILD, T_NPC, REAL_DIR


@pytest.fixture(autouse=True)
def no_real_app(tmp_path_factory, monkeypatch):
    """Point the app-lock check at an empty config dir so a running Amsel never interferes."""
    cfg = tmp_path_factory.mktemp("config")
    monkeypatch.setenv("XDG_CONFIG_HOME", str(cfg))
    monkeypatch.delenv("AMSEL_SKIP_APP_CHECK", raising=False)
    return cfg


def members(path):
    with tarfile.open(path) as tf:
        return [(m.name, m.size, m.isdir()) for m in tf.getmembers()]


# --- compose ------------------------------------------------------------------

def test_text_to_html_formats_like_amsel():
    find = {"Écume": "lorePage/x1"}.__getitem__
    html = text_to_html("Port de **[[Écume]]**, *calme*.\n\n- un\n- deux\n1. a\n> dit-il <script>", find)
    assert html == (
        '<p class="text-body">Port de <strong><tag-component id="lorePage/x1"></tag-component></strong>, <em>calme</em>.</p>'
        '<p class="text-body"></p>'
        '<ul class="list-disc pl-5"><li><p class="text-body">un</p></li><li><p class="text-body">deux</p></li></ul>'
        '<ol class="list-decimal"><li><p class="text-body">a</p></li></ol>'
        '<blockquote><p class="text-body">dit-il &lt;script&gt;</p></blockquote>'
    )


def test_text_to_html_reports_every_bad_link():
    def find(name):
        raise ValueError("no page with this name")

    with pytest.raises(ValueError, match=r"(?s)\[\[A\]\].*\[\[B\]\]"):
        text_to_html("[[A]] et [[B]]", find)


# --- tome ---------------------------------------------------------------------

def test_create_data_page_with_links_and_backup(server, campaign_dir):
    tome = campaign_dir / "Campagne.tome"
    before = members(tome)
    out = server.create_tome_data_page("campagne", "PNJ : Brann", "pnj", "Rival de [[Mirelle]].",
                                       {"Résumé": "Vit à [[Écume]]."})
    assert "# PNJ : Brann" in out and "Rival de [[PNJ : Mirelle]]." in out and "## Résumé\nVit à [[Écume]]." in out
    assert "Backup of the previous version" in out
    data = read_data_json(tome)
    page = data["dataPages"][-1]
    assert page["type"] == "TDP_Character" and data["dataPagesOrder"][-1] == {"idHash": page["idHash"], "type": "item"}
    assert f'index/{T_NPC}' in page["summary"]
    assert members(tome)[1:] == before[1:]  # images and folders untouched
    backups = list((campaign_dir / ".amsel-backups").glob("Campagne.*.tome"))
    assert len(backups) == 1 and "Brann" not in str(read_data_json(backups[0]))
    # backlink now visible from Mirelle's page
    assert "- [[PNJ : Brann]]" in server.read_tome_page("campagne", "Mirelle")


def test_create_data_page_refuses_duplicates_and_bad_links(server, campaign_dir):
    tome = campaign_dir / "Campagne.tome"
    raw = tome.read_bytes()
    with pytest.raises(WriteRefused, match="already exists"):
        server.create_tome_data_page("campagne", "pnj : mirelle", "Character")
    with pytest.raises(ValueError, match="Unresolved links"):
        server.create_tome_data_page("campagne", "Nouveau", "Character", "Ami de [[Personne]]")
    with pytest.raises(ValueError, match="Unknown data page type"):
        server.create_tome_data_page("campagne", "Nouveau", "Dragon")
    assert tome.read_bytes() == raw
    assert not (campaign_dir / ".amsel-backups").exists()


def test_create_scene_under_chapter(server):
    out = server.create_tome_story_page("campagne", "Chapitre 1", "La tempête", "scene", "Orage", "Les vagues montent.")
    assert "parent: [[Chapitre 1]]" in out and "## Content\nLes vagues montent." in out
    outline = server.tome_outline("campagne")
    assert outline.index("Arrivée au port") < outline.index("[Scene] La tempête")
    with pytest.raises(WriteRefused, match="under a story"):
        server.create_tome_story_page("campagne", "La tempête", "X")


def test_update_page_replace_append_and_sections(server):
    server.update_tome_page("campagne", "Mirelle", summary="Première ligne")
    out = server.update_tome_page("campagne", "Mirelle", summary="Deuxième ligne", append=True)
    assert "## Summary\nPremière ligne\n\nDeuxième ligne" in out
    out = server.update_tome_page("campagne", "Mirelle",
                                  sections={"Résumé": "Remplacé", "Secrets": "Doit de l'argent à [[La Taverne]]"})
    assert "Contrebandière" not in out
    assert "## Résumé\nRemplacé" in out and "## Secrets\nDoit de l'argent à [[La Taverne]]" in out
    with pytest.raises(WriteRefused, match="checklist"):
        server.update_tome_page("campagne", "Mirelle", sections={"Détails": "x"})
    with pytest.raises(ValueError, match="Only scenes"):
        server.update_tome_page("campagne", "Mirelle", content="x")
    with pytest.raises(WriteRefused, match="already named"):
        server.update_tome_page("campagne", "Mirelle", new_name="La Taverne")
    assert "# PNJ : Mirelle la Rousse" in server.update_tome_page("campagne", "Mirelle", new_name="PNJ : Mirelle la Rousse")


def test_add_note(server):
    out = server.add_tome_session_note("campagne", "Les joueurs ont fui.")
    assert "Bonne session" in out and "Les joueurs ont fui." in out


# --- lore ---------------------------------------------------------------------

def test_create_and_update_lore_page(server, campaign_dir):
    out = server.create_lore_page("monde", "ville", "Brume", {"description": "Rivale de [[Écume]]."})
    assert "template: Ville" in out and "## Description\nRivale de [[Écume]]." in out
    page = read_data_json(campaign_dir / "Monde.lore")["pages"][-1]
    kinds = sorted(k for c in page["pageContent"] for k in c if k in ("body", "runeletContent"))
    assert kinds == ["body", "runeletContent"] and len(page["pageContent"]) == 3  # one entry per template module
    # the Guilde page shows its Description module under a custom header, "Histoire": both names work
    out = server.update_lore_page("monde", "Guilde", fields={"Description": "Contrôle le port."})
    assert "## Histoire\nContrôle le port." in out and "300 ans" not in out
    out = server.update_lore_page("monde", "Guilde", fields={"histoire": "Et les quais."}, append=True)
    assert "## Histoire\nContrôle le port.\n\nEt les quais." in out
    with pytest.raises(ValueError, match="Unknown field"):
        server.update_lore_page("monde", "Guilde", fields={"Nope": "x"})
    with pytest.raises(WriteRefused, match="already exists"):
        server.create_lore_page("monde", "ville", "écume")
    assert server.read_lore_page("monde", L_GUILD[:8]).count("Contrôle le port.") == 1


# --- safety -------------------------------------------------------------------

def test_refuses_while_app_is_open(server, campaign_dir, no_real_app):
    lock_dir = no_real_app / "tome"
    lock_dir.mkdir()
    os.symlink(f"{socket.gethostname()}-{os.getpid()}", lock_dir / "SingletonLock")
    raw = (campaign_dir / "Campagne.tome").read_bytes()
    with pytest.raises(WriteRefused, match="Tome is open"):
        server.add_tome_session_note("campagne", "x")
    assert (campaign_dir / "Campagne.tome").read_bytes() == raw
    # the Lore app is not open: Lore writes still work
    server.update_lore_page("monde", "Guilde", new_name="Guilde des Flots")


def test_stale_lock_is_ignored(server, no_real_app):
    lock_dir = no_real_app / "lore"
    lock_dir.mkdir()
    os.symlink(f"{socket.gethostname()}-999999999", lock_dir / "SingletonLock")
    server.update_lore_page("monde", "Guilde", new_name="Guilde des Flots")


def test_refuses_if_file_changed_since_read(campaign_dir):
    from amsel_mcp import writer

    path = campaign_dir / "Monde.lore"
    stamp = writer.file_stamp(path)
    os.utime(path, ns=(stamp[0] + 10**9, stamp[0] + 10**9))
    with pytest.raises(WriteRefused, match="changed on disk"):
        writer.save(path, read_data_json(path), stamp)


def test_write_tools_hidden_unless_enabled():
    import asyncio

    from amsel_mcp import server as srv

    names = {t.name for t in asyncio.run(srv.mcp.list_tools())}
    assert ("create_lore_page" in names) == srv.WRITE_ENABLED


@pytest.mark.skipif(not any(REAL_DIR.glob("*.tome")), reason=f"no real Amsel files in {REAL_DIR}")
def test_real_files_roundtrip_byte_for_byte_and_rewrite(tmp_path):
    from amsel_mcp import writer

    for src in list(REAL_DIR.glob("*.tome")) + list(REAL_DIR.glob("*.lore")):
        with tarfile.open(src) as tf:
            raw = tf.extractfile("data.json").read()
        data = read_data_json(src)
        assert dump_json(data) == raw  # serialization matches Amsel's exactly
        copy = tmp_path / src.name
        shutil.copy2(src, copy)
        writer.save(copy, data, writer.file_stamp(copy))
        assert read_data_json(copy) == data
        assert members(copy) == [(n, s if n != "data.json" else s, d) for n, s, d in members(src)]


def test_text_to_html_headings_rules_and_nested_lists():
    html = text_to_html("### Lieu\n#### Défi 1 : **la console**\n---\n- a\n  - a1\n    1. x\n  - a2\n- b\n1. c")
    assert html == (
        '<h3 class="text-body">Lieu</h3>'
        '<h4 class="text-body">Défi 1 : <strong>la console</strong></h4>'
        '<hr class="">'
        '<ul class="list-disc pl-5"><li><p class="text-body">a</p>'
        '<ul class="list-disc pl-5"><li><p class="text-body">a1</p>'
        '<ol class="list-decimal"><li><p class="text-body">x</p></li></ol></li>'
        '<li><p class="text-body">a2</p></li></ul></li>'
        '<li><p class="text-body">b</p></li></ul>'
        '<ol class="list-decimal"><li><p class="text-body">c</p></li></ol>'
    )


def test_markdown_round_trips_through_amsel_html():
    from amsel_mcp.text import html_to_text

    md = "### Lieu\n\n#### Défi 1 : **la console**\n\n---\n\n- **Réussite** : ok\n  - *Indice* : x\n- **Échec** : non\n\n> « Bienvenue ! »"
    assert html_to_text(text_to_html(md)) == md


# --- images -------------------------------------------------------------------

PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 64


def test_set_lore_page_image_adds_file_and_library_entry(server, campaign_dir, tmp_path_factory):
    img = tmp_path_factory.mktemp("in") / "guilde.png"
    img.write_bytes(PNG)
    lore = campaign_dir / "Monde.lore"
    before = members(lore)
    out = server.set_lore_page_image("monde", "Guilde", str(img), caption="Le sceau", folder="Blasons")
    assert "## Blason\n[image: Guilde des Marées]" in out
    data = read_data_json(lore)
    entry = data["importedImages"][-1]
    assert entry["extension"] == "png" and entry["displayedName"] == "Guilde des Marées"
    folder = next(f for f in data["imageFolders"] if f["idHash"] == entry["folderId"])
    assert folder["name"] == "Blasons"
    page = next(p for p in data["pages"] if p["name"] == "Guilde des Marées")
    vc = next(c for c in page["pageContent"] if "visualContent" in c)["visualContent"]
    assert vc["relatedImage"] == entry["idHash"] and vc["caption"] == "Le sceau" and vc["display"] == "fit"
    after = members(lore)
    assert after[1:len(before)] == before[1:]  # existing members kept, in order
    assert (f"img/{entry['idHash']}.png", len(PNG), False) in after
    with tarfile.open(lore) as tf:
        assert tf.extractfile(f"img/{entry['idHash']}.png").read() == PNG


def test_set_lore_page_image_replaces_and_rejects_non_images(server, campaign_dir, tmp_path_factory):
    d = tmp_path_factory.mktemp("in")
    (d / "a.jpg").write_bytes(b"\xff\xd8\xff\xe0" + b"\x00" * 32)
    (d / "notes.txt").write_text("pas une image")
    lore = campaign_dir / "Monde.lore"
    server.set_lore_page_image("monde", "Écume", str(d / "a.jpg"))
    data = read_data_json(lore)
    city = next(p for p in data["pages"] if p["name"] == "Écume")
    vc = next(c for c in city["pageContent"] if "visualContent" in c)["visualContent"]
    assert vc["relatedImage"] == data["importedImages"][-1]["idHash"] and data["importedImages"][-1]["extension"] == "jpg"
    raw = lore.read_bytes()
    with pytest.raises(ValueError, match="not a PNG"):
        server.set_lore_page_image("monde", "Écume", str(d / "notes.txt"))
    with pytest.raises(ValueError, match="No image file"):
        server.set_lore_page_image("monde", "Écume", str(d / "absent.png"))
    assert lore.read_bytes() == raw


def test_set_tome_page_image_sets_cover(server, campaign_dir, tmp_path_factory):
    img = tmp_path_factory.mktemp("in") / "mirelle.webp"
    img.write_bytes(b"RIFF\x10\x00\x00\x00WEBPVP8 " + b"\x00" * 16)
    out = server.set_tome_page_image("campagne", "Mirelle", str(img))
    assert "[cover image: PNJ : Mirelle]" in out
    data = read_data_json(campaign_dir / "Campagne.tome")
    entry = data["importedImages"][-1]
    assert entry["extension"] == "webp" and data["imageFolders"][0]["isRootFolder"]
    npc = next(p for p in data["dataPages"] if p["pageName"] == "PNJ : Mirelle")
    assert npc["coverImage"]["relatedImage"] == entry["idHash"]


# --- arcanes ------------------------------------------------------------------

def test_scene_content_creates_every_arcane_type(server, campaign_dir):
    from .conftest import SESSION
    content = (
        "Ouverture.\n"
        "[[choice: Livrer [[Mirelle]] ?]]\n"
        "[[destiny: La Taverne brûle]]\n"
        "[[role: Négocier avec la guilde]]\n"
        "[[options: Trois fins | Fuite | Combat | Accord]]\n"
        "[[count: Alertes]]"
    )
    out = server.create_tome_story_page("campagne", "Chapitre 1", "Le pacte", content=content)
    data = read_data_json(campaign_dir / "Campagne.tome")
    scene = next(p for p in data["storyPages"] if p["pageName"] == "Le pacte")
    new = data["arcanes"][-5:]
    assert [a["type"] for a in new] == ["choice", "destiny", "role", "options", "count"]
    for a, tag in zip(new, ["intrigue", "destiny", "role", "options", "count"]):
        assert f'<{tag}-component idhash="{a["idHash"]}"></{tag}-component>' in scene["content"]
        assert [r["relatedSessionIdHash"] for r in a["results"]] == [SESSION]
    choice, destiny, role, options, count = new
    assert f"index/{T_NPC}" in choice["text"] and choice["results"][0]["state"] == "tbd"
    assert destiny["results"][0]["mood"] == 0 and role["results"][0]["characters"] == []
    assert [c["content"] for c in options["results"][0]["choices"]] == ["Fuite", "Combat", "Accord"]
    assert options["text"] == "<p>Trois fins</p>" and not any(c["isSelected"] for c in options["results"][0]["choices"])
    assert count["text"] == "<p>Alertes</p>" and count["results"][0]["number"] == 0
    assert f"[[options#{options['idHash'][:8]}: Trois fins | Fuite | Combat | Accord]]" in out
    listing = server.list_tome_arcanes("campagne")
    assert "result: not decided yet" in listing and "count: 0" in listing and "Fuite / Combat / Accord" in listing


def test_rewriting_scene_keeps_arcanes_by_id(server, campaign_dir):
    tome = campaign_dir / "Campagne.tome"
    before = len(read_data_json(tome)["arcanes"])
    server.update_tome_page("campagne", "Arrivée au port", content="Nouveau texte.\n[[choice#ta000001: ignoré]]")
    data = read_data_json(tome)
    scene = next(p for p in data["storyPages"] if p["pageName"] == "Arrivée au port")
    assert len(data["arcanes"]) == before and '<intrigue-component idhash="ta000001-choice">' in scene["content"]
    raw = tome.read_bytes()
    with pytest.raises(ValueError, match="no arcane with this id"):
        server.update_tome_page("campagne", "Arrivée au port", content="[[choice#ffffffff: x]]")
    with pytest.raises(ValueError, match="not a destiny"):
        server.update_tome_page("campagne", "Arrivée au port", content="[[destiny#ta000001: x]]")
    with pytest.raises(ValueError, match="at least two options"):
        server.update_tome_page("campagne", "Arrivée au port", content="[[options: seul | A]]")
    with pytest.raises(ValueError, match="only be inserted in scene content"):
        server.update_tome_page("campagne", "Mirelle", sections={"Résumé": "[[choice: x]]"})
    assert tome.read_bytes() == raw
