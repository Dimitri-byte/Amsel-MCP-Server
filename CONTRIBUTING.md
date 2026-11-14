# Contributing

Thanks for your interest! Bug reports, format discoveries and pull requests are welcome, in English or French.

## Development setup

```bash
git clone https://github.com/Dimitri-byte/Amsel-MCP-Server-.git
cd Amsel-MCP-Server-
uv sync
uv run pytest
```

The tests build small synthetic `.tome` / `.lore` / `.lorekit` archives on the fly (see `tests/conftest.py`), so they need no real Amsel files. To also run the checks against your own files, point `AMSEL_TEST_DIR` to a folder of **copies**:

```bash
AMSEL_TEST_DIR="$HOME/Documents/amsel-copies" uv run pytest
```

## Ground rules

- **Never commit real Amsel files** (`.tome`, `.lore`, `.lorekit`): they contain personal campaigns and third-party content. They are in `.gitignore`; keep test data synthetic.
- **Round-trip safety comes first.** A file the server writes must open in Amsel exactly as if Amsel had saved it. JSON is written compactly with `ensure_ascii=False`, and untouched archive members are copied as they are. Any new write feature needs a test showing that the rest of the file is unchanged.
- Writes always go through `writer.save` (app-open check, change detection, backup, verified atomic replace).
- Code, docstrings and tool messages are in English. User documentation exists in English and French (`README.md` / `README.fr.md`, `docs/installation.md` / `docs/installation.fr.md`): please update both, or say in your pull request which one needs a translation.

## Reporting a format change

Amsel's file format is not documented, and new app versions may change it. If a file no longer reads or writes correctly, open an issue with:

- the Amsel app version and the file's `lastVer` (shown by `list_amsel_files`, or at the start of `data.json`);
- the error message;
- if possible, a **minimal, non-personal** excerpt of the JSON structure involved (never the whole file).

## Pull requests

- Keep each pull request focused on one change, with tests.
- Add a line to `CHANGELOG.md` under an "Unreleased" heading.
- Make sure `uv run pytest` passes.
