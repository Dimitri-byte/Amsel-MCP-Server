# Amsel MCP Server

[![Tests](https://github.com/Dimitri-byte/Amsel-MCP-Server/actions/workflows/tests.yml/badge.svg)](https://github.com/Dimitri-byte/Amsel-MCP-Server/actions/workflows/tests.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

*[Version française](README.fr.md)*

An [MCP](https://modelcontextprotocol.io) server that gives Claude (or any MCP client) **read** access — and, if you enable it, **write** access — to [Amsel Suite](https://www.amsel-suite.com/) files: **Tome** campaigns (`.tome`), **Lore** worlds (`.lore`) and **Lore** template kits (`.lorekit`).

Claude can browse your campaign tree, read an NPC or a Lore page, follow links between pages, check arcanes and their per-session results, and search all your content. With writing enabled, it can also create NPCs, scenes and Lore pages, extend existing text, add session notes and set images.

> Community project, not affiliated with or endorsed by Ollam Technologies, the makers of Amsel Suite.
> The file format was reverse-engineered and may change with new Amsel versions: **work on copies first**.

> [!CAUTION]
> ## ⚠️ ALWAYS BACK UP YOUR FILES BEFORE ANY CHANGE ⚠️
>
> **Before enabling the write tools, and before every work session with them, copy your `.tome` and `.lore` files somewhere safe** (another folder, an external drive, cloud storage).
>
> The server writes directly into your real campaign files. It keeps automatic backups in `.amsel-backups/`, but only the last 20 versions, next to the file itself: they do not replace a backup of your own. The Amsel file format is undocumented and reverse-engineered, and a new Amsel version may change it.
>
> **No backup, no writing.** Start with copies, check the result in Amsel, then work on your real files.

## Read tools (always available)

| Tool | Purpose |
|---|---|
| `list_amsel_files` | Lists the `.tome` / `.lore` / `.lorekit` files found, with counts and the Lore linked to each Tome |
| `tome_outline` | Story tree (story → chapters → scenes), ribbons, per-session state |
| `list_tome_data_pages` | Data pages (characters, locations, objects, organizations, players) grouped by type |
| `read_tome_page` | A story or data page as Markdown, links resolved, with "referenced by" |
| `list_tome_arcanes` | Arcanes (choices / destinies), with per-session results and comments |
| `read_tome_notes` | Session notes |
| `list_lore_pages` | Lore pages grouped by template |
| `list_lore_templates` | Templates of a Lore or a kit: category, page count, modules |
| `read_lore_template` | One template in detail: modules in order, rune fields, mirror targets |
| `read_lore_page` | A Lore page, modules in template order, runes and images |
| `search_amsel` | Case- and accent-insensitive search in page names and text |

## Write tools (with `AMSEL_WRITE=1`)

| Tool | Purpose |
|---|---|
| `create_tome_data_page` | Creates a data page (character, location, object, organization, player, fable) with summary and sections |
| `create_tome_story_page` | Creates a scene or a chapter in the story tree, with arcanes in the scene content |
| `update_tome_page` | Renames a Tome page, or replaces / extends its summary, content or text sections |
| `add_tome_session_note` | Adds a session note |
| `create_lore_page` | Creates a Lore page from a template, with its text fields |
| `update_lore_page` | Renames a Lore page, or replaces / extends its text fields |
| `set_lore_page_image` | Puts a local image (PNG, JPEG, WebP, GIF) in a Lore page's image module |
| `set_tome_page_image` | Sets the cover image of a Tome page (data or story page) |

Text is written in light Markdown: one paragraph per line, `**bold**`, `*italic*`, `### ` / `#### ` headings, `---` separators, `- ` or `1. ` lists (indent by 2 spaces for a sub-list), `> ` quotes, and `[[Page name]]` links to existing pages (Tome or linked Lore). A missing or ambiguous link cancels the write.

**Arcanes** — in scene content, a line holding only one of these inserts a new arcane, with an empty result for each game session:

| Line | Arcane |
|---|---|
| `[[choice: Will they hand over the informant?]]` | choice (yes / no, undecided at first) |
| `[[destiny: The Auditor finds the ship]]` | destiny (mood 1 to 5, unset at first) |
| `[[role: One PC negotiates with the guild]]` | role (characters assigned later in Amsel) |
| `[[options: How do they leave? \| Quietly \| By force \| With a pass]]` | options (text, then at least two options) |
| `[[count: Imperial alert level]]` | count (starts at 0) |

`read_tome_page` shows existing arcanes as `[[choice#1041e488: …]]`. Keep those lines when you rewrite a scene: the id keeps the existing arcane and its results; without it the arcane is detached from the scene.

**Safeguards** — without `AMSEL_WRITE=1`, the write tools do not exist. When they are enabled, every write:

- is **refused while the Tome app (for a `.tome`) or the Lore app (for a `.lore`) is open**, since the app would overwrite the change on its next save;
- is refused if the file changed on disk while the edit was being prepared;
- first copies the file to `.amsel-backups/` next to it (the last 20 versions are kept);
- rewrites the archive into a temporary file, reads it back to check it, then replaces the original. Existing images are left untouched; new ones are added to `img/` and to the image library (in the folder you choose).

There is no deletion yet; the results of existing arcanes, relations and runes cannot be edited. Images come from local files: an online image must be downloaded first.

Files and pages are referenced by name, partial name or id (or the start of an id). Amsel links appear as `[[Page name]]`.

## The `amsel-adventure-writer` skill

[`skills/amsel-adventure-writer`](skills/amsel-adventure-writer/SKILL.md) is a Claude skill that uses this server to **write playable adventures**: structured scenes (setting, read-aloud text, checks and consequences, exits), NPCs and locations you can improvise with, and Lore pages built on your templates (drawing on `.lorekit` kits). It first reads the campaign (tree, session notes, arcanes, the GM's style), proposes a plan, then writes in the right order so that links resolve. It writes in the language of your campaign.

Install it for Claude Code:

```bash
ln -s "$PWD/skills/amsel-adventure-writer" ~/.claude/skills/amsel-adventure-writer
```

## Installation

> 📘 Step-by-step guide, from nothing to the first question, with troubleshooting: [docs/installation.md](docs/installation.md)

Requirements: [uv](https://docs.astral.sh/uv/) (it installs Python 3.10+ for you).

```bash
git clone https://github.com/Dimitri-byte/Amsel-MCP-Server.git
cd Amsel-MCP-Server
uv sync
```

### Scanned folders

`AMSEL_PATHS` tells the server where to look for files (several folders separated by `:` on Linux/macOS, `;` on Windows). Subfolders are scanned, hidden folders are skipped. Default: `~/Documents`.

### Claude Code

```bash
claude mcp add --scope user amsel -e AMSEL_PATHS="$HOME/Documents" -- uv run --directory /path/to/Amsel-MCP-Server amsel-mcp
```

Add `-e AMSEL_WRITE=1` to enable the write tools.

### Claude Desktop

In `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "amsel": {
      "command": "uv",
      "args": ["run", "--directory", "/path/to/Amsel-MCP-Server", "amsel-mcp"],
      "env": { "AMSEL_PATHS": "/home/me/Documents" }
    }
  }
}
```

## Amsel file format (reverse-engineered)

- A `.tome` or `.lore` is a **tar** archive (pax format) holding `data.json` (minified JSON) and an `img/` folder (`<uuid>.<ext>`, plus optional `<uuid>.thumb.400.png` thumbnails). Images are listed in `importedImages` and sorted into `imageFolders`.
- When a file is opened, the app unpacks it into `~/.amselsuite/<uuid>/`; those are working copies, the server always reads the archives.
- **Tome** (`lastVer` 24): `storyPages` (types `TSP_Story`, `TSP_ChapterFlow`, `TSP_Chapter`, `TSP_Scene`, tree via `parentId` / `childrenIds`), `dataPages` (`TDP_Character`, `TDP_Location`, `TDP_Object`, `TDP_Organization`, `TDP_Player`, `TDP_Fable`, with `text` or `checker` sub-pages), `arcanes` (`choice` / `destiny`), `gameSessions`, `notes`, `linkedLorePath`. Page covers: `coverImage.relatedImage`.
- **Lore** (`lastVer` 17): `pages` (content per module via `relatedModuleId`; images via `visualContent.relatedImage`), `templates` (modules `LM_Standard_Text`, `LM_Image`, `LM_Rune`, `LM_Mirror`), `runeTemplates`, `diagrams`, `maps`.
- **Lore kit** (`.lorekit`): the same archive with no pages or images, only `name`, `templates` and runes. Old format (`lastVer` 13): `runeTemplates[].runelets`. Newer format (`lastVer` 23): `runeGroups[].runes`, `customTemplateCategories` (custom categories referenced by id) and `inspirationLists`. The server reads both but never writes to a kit: kits are imported into a Lore from the app.
- Rich text is HTML. Links: `<tag-component id="lorePage/…">` (Lore page), `index/…` (Tome data page), `storyPage/…`; embedded arcanes: `<intrigue-component idhash="…">` (choice), `<destiny-component …>`, `<role-component …>`, `<options-component …>`, `<count-component …>`. Each arcane holds one result per game session: `state` (`tbd` / `yes` / `no`), `mood` (0 = unset, 1–5), `characters`, `choices` (with `isSelected`) or `number`.
- Linked Lore: the server first looks for a `.lore` with the same name next to the Tome (handy for copies), then for the recorded path.

## Development

```bash
uv run pytest
```

The tests use synthetic files generated on the fly. If `AMSEL_TEST_DIR` points to a folder of real Amsel files, extra tests check that every page renders. Never commit real `.tome` / `.lore` / `.lorekit` files (they are in `.gitignore`).

Contributions are welcome: see [CONTRIBUTING.md](CONTRIBUTING.md). Changes are listed in [CHANGELOG.md](CHANGELOG.md).

## Roadmap

- [x] Reading Tome, Lore and Lore kits
- [x] Writing: page creation and editing, session notes, images (backups, refused while the app is open)
- [x] Creating arcanes (choice, destiny, role, options, count)
- [ ] Editing arcane results, relations, runes
- [ ] Page deletion

## License

[MIT](LICENSE). Amsel Suite, Tome and Lore are trademarks of their respective owners.
