---
name: amsel-adventure-writer
description: Writes and enriches tabletop RPG adventures directly in Amsel Suite (Tome and Lore) through the amsel MCP server — playable scenes with read-aloud text, checks and consequences, NPCs, locations, organizations, and Lore pages built on the world's templates. Use this skill whenever the user wants to create, prepare, develop, flesh out or rewrite an adventure, a session, a chapter, a scene, an NPC, a location or a world page in their Tome or Lore, even if they mention neither Amsel nor the skill ("prep my next session", "flesh out the NPC Orrin", "write an infiltration scene", "add the smugglers' faction to my Lore", « prépare ma prochaine session »).
---

# Writing an adventure in Amsel

The goal: the GM opens their Tome and finds pages that are **playable at the table** — they can glance at a scene during play and know what to describe, what to play out, which checks to call for and what happens next. Beautiful prose that cannot be run is useless; so is a dry list.

Everything goes through the tools of the `amsel` MCP server (reading always, writing with `AMSEL_WRITE=1`). Writes change the user's real file: each write makes a backup, but work as if it were final.

**Language.** Write in the language of the campaign (the GM's existing pages tell you which), not in the language of this skill. Reuse the game system's own terms in that language (skill names, conditions, currency).

## 1. Soak up the campaign before writing

Write nothing before you understand the campaign. A scene that contradicts the Lore, ignores what the players did, or invents an NPC who already exists under another name is work the GM will have to undo.

1. `list_amsel_files` → the Tome, its linked Lore, and any `.lorekit` kits.
2. `tome_outline` (with `with_summaries=True`) → where the story stands, which chapters/scenes exist, which were played.
3. `read_tome_notes` and `list_tome_arcanes` → what happened in sessions and which choices are pending. This is the most valuable material for preparing what comes next.
4. `list_tome_data_pages` then `read_tome_page` on the NPCs/locations involved; `search_amsel` to check a name does not already exist.
5. Read **one or two scenes the GM already wrote**, preferably the longest, to match tone, level of detail and conventions (how read-aloud text addresses the players, how DCs are noted, etc.). Follow their conventions rather than yours.
6. Lore side: `list_lore_templates` then `read_lore_template` on the template to use.

Identify the **game system** (skill names, DCs, setting) and the **tone** of the campaign. If the system is unclear, ask. See `references/systems.md` for difficulty benchmarks.

## 2. Propose a plan, then write

Before any write, present a short plan: pages to create (type, name, parent), existing pages to extend, links between them. Wait for the GM's agreement — it is their campaign, and a plan is much faster to fix than a dozen pages.

Writing order, imposed by `[[Name]]` links, which must point to **existing** pages (otherwise nothing is written):

1. new Lore pages and data pages (NPCs, locations, objects, organizations);
2. the scenes, which cite them;
3. additions to existing pages (`update_tome_page` with `append=True`), e.g. adding to an NPC's story-impact section a link to the scene where they appear.

Scenes are created in play order, but a scene often cites the next one ("Exit: see [[Next scene]]"): create it with the name in plain text, then, once the next scene exists, rewrite its full content with the link (`update_tome_page(content=...)`). Same for a data page citing a scene not written yet: add that section at the end, with `append`.

Links match the exact page name first, then a partial name. When creating several pages that link to each other, create them all first (even empty), then fill them: otherwise a link to a page that does not exist yet may resolve to another page whose name contains it.

If a write is refused because Tome or Lore is open, ask the GM to close the app, then resume — do not try to work around it.

After each creation, reread the page returned by the tool: links resolved, formatting correct.

## 3. What makes a good page

The detailed templates, with examples, are in the references — read the matching one before writing:

- **Scene** → `references/scene.md` (the heart of the skill)
- **NPC, location, object, organization** → `references/data-pages.md`
- **Lore page, templates and kits** → `references/lore.md`

Shared principles:

- **Give the GM levers, not a novel.** Every scene says what happens if the players succeed, fail, or do something else. NPCs have a goal, a way of talking and a secret.
- **Concrete and sensory.** One precise detail ("the ozone smell of the nanites") beats three adjectives ("magnificent, incredible, fascinating").
- **Connect.** Every NPC, location or faction mentioned in a scene is a `[[Name]]` link. The web of links is what makes a Tome navigable in the middle of play.
- **Do not resolve everything.** Leave open questions and choices to the players; flag them clearly (see "Choices and arcanes" in `references/scene.md`).
- **Consistency first.** If an idea contradicts the Lore or the session notes, tell the GM rather than deciding alone.

## 4. Writing syntax

The text passed to the tools is light Markdown, converted to Amsel's format:

| Write | Result |
|---|---|
| one line | a paragraph; an empty line = an empty paragraph |
| `### Heading` / `#### Subheading` | headings (two levels only) |
| `---` | separator |
| `**bold**`, `*italic*` | formatting |
| `- item`, `1. item`, indented by 2 spaces for a sub-list | lists |
| `> text` | quote block |
| `[[Exact page name]]` | link to an existing Tome or Lore page (shown with the page's name; there is no custom link text) |
| a line `[[choice: …]]`, `[[destiny: …]]`, `[[role: …]]`, `[[options: text \| a \| b]]`, `[[count: …]]` | a new arcane, in scene content only (see `references/scene.md`) |

No tables or web links in the text: write them differently. Images are set separately, from a local file, with `set_lore_page_image` (image module of a Lore page) or `set_tome_page_image` (cover of a Tome page). Ask the GM before downloading any image from the web.

## 5. Current server limits

The server cannot (yet): set the results of existing arcanes, fill runes or relations, delete a page, or write to a "checklist" section. When the adventure needs them, write the equivalent as text and end your report with a "To do in Amsel" list (e.g. "assign the role arcane of scene X to Thessaly").

When you rewrite a scene that already has arcanes, keep their `[[type#id: …]]` lines exactly as `read_tome_page` shows them: the id keeps the arcane and its session results.

## 6. Final report

End with: the pages created and modified (with their parent), the points deliberately left open, the "To do in Amsel" list, and the backup reported by the tool in case the GM wants to roll back.
