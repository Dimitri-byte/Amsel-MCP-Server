"""Checks against real Amsel files (skipped when AMSEL_TEST_DIR is missing)."""

import re

import pytest

from amsel_mcp import render
from amsel_mcp.workspace import Workspace

from .conftest import REAL_DIR

pytestmark = pytest.mark.skipif(
    not REAL_DIR.is_dir() or not any(REAL_DIR.glob("*.tome")),
    reason=f"no real Amsel files in {REAL_DIR}",
)


@pytest.fixture(scope="module")
def ws():
    return Workspace([REAL_DIR], ttl=0)


def test_every_tome_page_renders(ws):
    for path in REAL_DIR.glob("*.tome"):
        tome = ws.tome(str(path))
        lore = ws.linked_lore(tome)
        assert render.tome_outline(tome)
        render.tome_arcanes(tome, lore)
        for pid in tome.all_pages:
            out = render.tome_page(tome, lore, pid)
            assert "<p" not in out and "tag-component" not in out


def test_every_lore_page_renders(ws):
    for path in REAL_DIR.glob("*.lore"):
        lore = ws.lore(str(path))
        assert render.lore_templates(lore)
        for pid in lore.pages:
            out = render.lore_page(lore, pid)
            assert "<p" not in out and "tag-component" not in out


def test_almost_all_links_resolve(ws):
    total = missing = 0
    for path in REAL_DIR.glob("*.tome"):
        tome = ws.tome(str(path))
        lore = ws.linked_lore(tome)
        for pid in tome.all_pages:
            out = render.tome_page(tome, lore, pid)
            total += len(re.findall(r"\[\[", out))
            missing += out.count("[[missing ")
    assert total > 0
    assert missing / total < 0.05
