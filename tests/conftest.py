"""Synthetic Amsel files (same structure as real ones, invented content)."""

from __future__ import annotations

import io
import json
import os
import tarfile
from pathlib import Path

import pytest

from amsel_mcp import workspace as wsmod

# Optional folder of real Amsel files for extra checks; the real-file tests are skipped when it is unset.
REAL_DIR = Path(os.environ.get("AMSEL_TEST_DIR", "/nonexistent-amsel-test-dir")).expanduser()

SESSION = "s0000000-0000-0000-0000-000000000001"
L_TEMPLATE, L_MOD_TEXT, L_MOD_RUNE, L_MOD_IMG = "lt000001", "lm000001", "lm000002", "lm000003"
L_RUNELET, L_RUNE_TPL = "lr000001", "rt000001"
L_CITY, L_GUILD = "lp000001-aaaa", "lp000002-bbbb"
T_STORY, T_CHAP, T_SCENE = "ts000001-root", "ts000002-chap", "ts000003-scene"
T_NPC, T_PLACE = "td000001-npc", "td000002-place"
T_ARCANE = "ta000001-choice"


def tag(kind: str, ref: str) -> str:
    return f'<tag-component id="{kind}/{ref}"></tag-component>'


def lore_data() -> dict:
    return {
        "lastVer": 17,
        "idHash": "lore-1",
        "fileName": "Monde",
        "templates": [{
            "idHash": L_TEMPLATE, "name": "Ville", "category": "LC_Geography",
            "usedModules": [
                {"idHash": L_MOD_IMG, "typeCodeModule": "LM_Image", "header": "Blason", "positionYMin": 0, "positionXMin": 8},
                {"idHash": L_MOD_TEXT, "typeCodeModule": "LM_Standard_Text", "header": "Description", "positionYMin": 0, "positionXMin": 0},
                {"idHash": L_MOD_RUNE, "typeCodeModule": "LM_Rune", "header": "Sources", "positionYMin": 2, "positionXMin": 0},
            ],
        }],
        "runeTemplates": [{"idHash": L_RUNE_TPL, "name": "Sources", "runelets": [{"idHash": L_RUNELET, "label": "Livre", "type": "LR_Tag"}]}],
        "importedImages": [{"idHash": "img1", "displayedName": "Blason d'Écume", "extension": "png"}],
        "pages": [
            {"idHash": L_CITY, "name": "Écume", "templateId": L_TEMPLATE, "mirrorLinksId": [], "pageContent": [
                {"idHash": "c1", "relatedModuleId": L_MOD_TEXT, "header": "", "body": f"<p>Port franc tenu par {tag('lorePage', L_GUILD)}.</p>"},
                {"idHash": "c2", "relatedModuleId": L_MOD_RUNE, "runeletContent": [{"value": f"lorePage/{L_GUILD}", "relatedRuneletId": L_RUNELET}]},
                {"idHash": "c3", "relatedModuleId": L_MOD_IMG, "visualContent": {"relatedImage": "img1"}},
            ]},
            {"idHash": L_GUILD, "name": "Guilde des Marées", "templateId": L_TEMPLATE, "mirrorLinksId": [], "pageContent": [
                {"idHash": "c4", "relatedModuleId": L_MOD_TEXT, "header": "Histoire", "body": "<p>Fondée il y a <strong>300 ans</strong>.</p>"},
            ]},
        ],
    }


def tome_data(linked_lore: str) -> dict:
    def sp(idh, name, typ, parent=None, children=(), **kw):
        d = {"idHash": idh, "pageName": name, "type": typ, "summary": "", "coverImage": {}, "pageStates": [], "aliases": [], "childrenIds": list(children)}
        if parent:
            d["parentId"] = parent
        d.update(kw)
        return d

    return {
        "lastVer": 24,
        "idHash": "tome-1",
        "storyName": "Campagne",
        "linkedLorePath": linked_lore,
        "gameSessions": [{"idHash": SESSION, "sessionName": "", "pageTabs": []}],
        "storyPages": [
            sp(T_STORY, "Campagne", "TSP_Story", children=[T_CHAP]),
            sp(T_CHAP, "Chapitre 1", "TSP_Chapter", T_STORY, [T_SCENE], ribbon="red"),
            sp(T_SCENE, "Arrivée au port", "TSP_Scene", T_CHAP,
               content=f"<p>Les héros rencontrent {tag('index', T_NPC)} à {tag('lorePage', L_CITY)}.</p>"
                       f'<p><destiny-component idhash="{T_ARCANE}"></destiny-component></p>',
               pageStates=[{"relatedSessionId": SESSION, "state": "joue"}]),
        ],
        "dataPages": [
            {"idHash": T_NPC, "pageName": "PNJ : Mirelle", "type": "TDP_Character", "summary": "", "isFavorite": True,
             "relations": [{"idHash": T_PLACE, "pageType": "index"}], "aliases": [], "subPages": [
                {"idHash": "sp1", "type": "text", "title": "Résumé",
                 "contentByType": {"text": {"module": {"content": "<p>Contrebandière <em>rusée</em>.</p>"}}, "checker": {"modules": []}, "gallery": {}}},
                {"idHash": "sp2", "type": "checker", "title": "Détails",
                 "contentByType": {"text": {"module": {}}, "checker": {"modules": [
                     {"title": "Voix", "content": "<p>Rauque</p>"}, {"title": "Vide", "content": ""}]}, "gallery": {}}},
            ]},
            {"idHash": T_PLACE, "pageName": "La Taverne", "type": "TDP_Location", "summary": "", "relations": [], "aliases": [], "subPages": []},
        ],
        "dataPagesOrder": [{"idHash": T_PLACE, "type": "item"}, {"idHash": T_NPC, "type": "item"}],
        "arcanes": [{"idHash": T_ARCANE, "type": "choice", "text": f"<p>Trahir {tag('index', T_NPC)} ?</p>",
                     "results": [{"relatedSessionIdHash": SESSION, "state": "no", "commentary": "<p>Fidèles</p>"}]}],
        "pointers": [],
        "notes": [{"idHash": "n1", "relatedSessionId": SESSION, "content": "Bonne session", "dateSys": "2026-01-01T20:00:00Z"}],
    }


def write_archive(path: Path, data: dict) -> Path:
    with tarfile.open(path, "w", format=tarfile.PAX_FORMAT) as tf:
        raw = json.dumps(data, ensure_ascii=False, separators=(",", ":")).encode()
        info = tarfile.TarInfo("data.json")
        info.size = len(raw)
        tf.addfile(info, io.BytesIO(raw))
        d = tarfile.TarInfo("img")
        d.type = tarfile.DIRTYPE
        tf.addfile(d)
    return path


@pytest.fixture
def campaign_dir(tmp_path: Path) -> Path:
    write_archive(tmp_path / "Monde.lore", lore_data())
    # the recorded link points elsewhere (like a file moved from another PC)
    write_archive(tmp_path / "Campagne.tome", tome_data("G:\\Drive\\Monde.lore"))
    return tmp_path


@pytest.fixture
def server(campaign_dir, monkeypatch):
    from amsel_mcp import server as srv

    monkeypatch.setattr(srv, "ws", wsmod.Workspace([campaign_dir], ttl=0))
    return srv
