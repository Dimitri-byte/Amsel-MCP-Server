# Changelog

All notable changes to this project are listed here. The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project uses [Semantic Versioning](https://semver.org/).

## [Unreleased]

### Added

- Arcane creation in scene content: `[[choice: …]]`, `[[destiny: …]]`, `[[role: …]]`, `[[options: text | a | b]]`, `[[count: …]]`, each with an empty result per game session.
- Reading of role, options and count arcanes; arcanes are shown with their id (`[[choice#1041e488: …]]`) so a rewritten scene keeps them.
- Prominent warning in the README to back up files before any change.

## [0.1.0] - 2026-11-14

First public release.

### Added

- Read tools for Tome (`.tome`) campaigns: story tree, data pages, arcanes with per-session results, session notes.
- Read tools for Lore (`.lore`) worlds and Lore template kits (`.lorekit`, old and new formats): pages, templates, runes, mirrors.
- `search_amsel`: case- and accent-insensitive search across all files.
- Write tools, enabled with `AMSEL_WRITE=1`: create and update Tome data pages, story pages and Lore pages, add session notes, set Lore page images and Tome page covers from local files.
- Light Markdown input (headings, separators, nested lists, quotes, `[[Page]]` links) converted to Amsel's rich-text HTML.
- Write safeguards: refused while the Tome/Lore app is open, refused if the file changed on disk, backup to `.amsel-backups/`, atomic and verified rewrite of the archive.
- `amsel-adventure-writer` Claude skill for writing playable scenes, NPCs and Lore pages.
- English and French documentation.

[0.1.0]: https://github.com/Dimitri-byte/Amsel-MCP-Server/releases/tag/v0.1.0
