# Running the Amsel MCP server from scratch

*[Version française](installation.fr.md)*

This guide starts from a machine with nothing on it but Amsel Suite and Claude.

## How it works, in two sentences

An MCP server is not a service that runs all the time: **Claude starts it** at the beginning of each session, then talks to it over standard input and output (stdio). So you only need to **install** the server once, then **tell Claude how to start it**.

```
Claude Code / Claude Desktop ──starts──▶ uv run amsel-mcp ──reads──▶ your .tome / .lore / .lorekit files
```

## 1. Install the prerequisites

| Tool | Purpose | Check |
|---|---|---|
| Git | get the code | `git --version` |
| [uv](https://docs.astral.sh/uv/) | installs Python 3.10+ and the dependencies | `uv --version` |

If `uv` is not installed (Linux / macOS):

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

On Windows (PowerShell):

```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

Close and reopen the terminal so that `uv` is found.

## 2. Get the code and install the dependencies

```bash
git clone https://github.com/Dimitri-byte/Amsel-MCP-Server-.git
cd Amsel-MCP-Server-
uv sync
```

`uv sync` creates a `.venv/` folder with Python and the MCP SDK. Nothing is installed anywhere else on your machine.

## 3. Know where your Amsel files are

The server looks for `.tome`, `.lore` and `.lorekit` (template kit) files in the folders given by the **`AMSEL_PATHS`** variable (subfolders included, hidden folders skipped). Without it, it looks in `~/Documents`.

- Several folders: separate them with `:` (Linux / macOS) or `;` (Windows).
- Example: `AMSEL_PATHS=/home/me/Documents/RPG:/home/me/Nextcloud/RPG`

> Tip: to start with, point it to a folder holding **copies** of your campaigns.
> The server is read-only until you enable writing, but it is a good habit.

## 4. Check that the server works

Run the tests:

```bash
uv run pytest
```

Query the server without Claude, from Python:

```bash
AMSEL_PATHS="$HOME/Documents" uv run python -c "from amsel_mcp import server; print(server.list_amsel_files())"
```

You should see the list of your files. If it is empty, `AMSEL_PATHS` does not point to the right place.

> Running `uv run amsel-mcp` directly looks like nothing happens: that is normal,
> the server is waiting for MCP messages on its standard input. Quit with `Ctrl+C`.

Optionally, with Node.js installed, the **MCP Inspector** opens a web page where you can call each tool by hand:

```bash
npx @modelcontextprotocol/inspector -e AMSEL_PATHS="$HOME/Documents" -- uv run --directory "$PWD" amsel-mcp
```

## 5. Connect the server to Claude

In the examples, replace `/path/to/Amsel-MCP-Server-` with the real path (given by `pwd` in the project folder).

### Option A — Claude Code, with the `claude` command

```bash
claude mcp add --scope user amsel \
  -e AMSEL_PATHS="$HOME/Documents" \
  -- uv run --directory /path/to/Amsel-MCP-Server- amsel-mcp
```

- `--scope user`: available in all your projects. Without it, only in the current folder.
- Check: `claude mcp get amsel` should show `✔ Connected`.
- Remove: `claude mcp remove amsel -s user`.

#### `claude: command not found`?

That is expected if you only use the Claude **desktop app**. It ships its own copy of Claude Code, but for its internal use:

- it lives in `~/.config/Claude/claude-code/<version>/<id>/claude` (Linux);
- that folder is not on your PATH, so the terminal does not find it;
- the path **changes with every update**: an alias to it will eventually break.

Three solutions:

1. **Install the Claude Code command line** (recommended). You get a real `claude` in `~/.local/bin`, updated automatically, sharing the same configuration (`~/.claude.json`) as the app:

   ```bash
   curl -fsSL https://claude.ai/install.sh | bash
   ```

2. **A shortcut that follows the app's updates**, without installing anything. Create the script `~/.local/bin/claude` (that folder must be on your PATH):

   ```bash
   cat > ~/.local/bin/claude <<'EOF'
   #!/bin/sh
   # Runs the most recent Claude Code bundled with the desktop app
   bin=$(ls -d "$HOME"/.config/Claude/claude-code/*/*/claude 2>/dev/null | sort -V | tail -n 1)
   [ -n "$bin" ] || { echo "Claude Code not found in the desktop app" >&2; exit 1; }
   exec "$bin" "$@"
   EOF
   chmod +x ~/.local/bin/claude
   ```

   Limitation: this shortcut stops working if you uninstall the desktop app.

3. **Do without the command**: use option B below. `claude mcp add` only writes to a configuration file.

### Option B — Claude Code, editing the file by hand

The command above only writes this to `~/.claude.json` (the `mcpServers` key at the root of the file):

```json
{
  "mcpServers": {
    "amsel": {
      "type": "stdio",
      "command": "uv",
      "args": ["run", "--directory", "/path/to/Amsel-MCP-Server-", "amsel-mcp"],
      "env": { "AMSEL_PATHS": "/home/me/Documents" }
    }
  }
}
```

For a server active in **a single project**, put the same `mcpServers` block in a `.mcp.json` file at the root of that project.

### Option C — Claude Desktop (chat tab)

Open `claude_desktop_config.json` (or *Settings → Developer → Edit Config*):

| System | Location |
|---|---|
| Linux | `~/.config/Claude/claude_desktop_config.json` |
| macOS | `~/Library/Application Support/Claude/claude_desktop_config.json` |
| Windows | `%APPDATA%\Claude\claude_desktop_config.json` |

Add:

```json
{
  "mcpServers": {
    "amsel": {
      "command": "uv",
      "args": ["run", "--directory", "/path/to/Amsel-MCP-Server-", "amsel-mcp"],
      "env": { "AMSEL_PATHS": "/home/me/Documents" }
    }
  }
}
```

Then **fully quit** Claude Desktop and start it again.

## 6. Enable writing (optional)

By default the server only **reads**. To let Claude create and edit pages too, add the **`AMSEL_WRITE=1`** variable to the registration. With the `claude` command (after removing the old registration, see section 8):

```bash
claude mcp add --scope user amsel -e AMSEL_PATHS="$HOME/Documents/RPG-copies" -e AMSEL_WRITE=1 -- uv run --directory /path/to/Amsel-MCP-Server- amsel-mcp
```

Or by hand, in the `"env"` block: `"AMSEL_WRITE": "1"`.

Before writing:

- **Close the Tome app** before editing a `.tome`, and **Lore** before editing a `.lore`. Otherwise the server refuses: Amsel keeps the file in memory and would overwrite the change on its next save.
- Every write keeps a copy of the previous version in `.amsel-backups/`, next to the file. To go back, close Amsel and copy the backup over the file.
- Start with **copies** of your files, and check the result by opening them in Amsel.

## 7. Try it

Open a new session and ask, for example:

- "Which Amsel files did you find?"
- "Show me the tree of my campaign."
- "What do we know about this NPC? Who are they linked to?"
- "Which arcanes have not been resolved yet?"

In Claude Code in a terminal, the `/mcp` command lists the servers and their status.

## 8. Change folders or remove the registration

The registration is **permanent**: it survives reboots, and Claude starts the server by itself in every session. There is nothing to redo day to day. You only change it to:

- read **another folder** of Amsel files (switching from test copies to your real files, for instance);
- follow the project after **moving or renaming** it;
- **remove** the server completely.

> After every change, open a **new session**: a session that is already open keeps the old configuration.

### With the `claude` command

First see what is registered:

```bash
claude mcp list
```

```bash
claude mcp get amsel
```

`claude mcp get` shows the **scope** ("User config", "Local config" or "Project config"), which you need to give again to remove it.

Remove the registration (user scope here; replace `user` with `local` or `project` depending on what `get` shows):

```bash
claude mcp remove amsel -s user
```

Then register the new one, with the new folder or the new project path:

```bash
claude mcp add --scope user amsel -e AMSEL_PATHS="$HOME/Documents" -- uv run --directory /path/to/Amsel-MCP-Server- amsel-mcp
```

Several folders at once: `-e AMSEL_PATHS="$HOME/Documents:$HOME/Nextcloud/RPG"`.

> If `claude mcp add` says the server already exists, the old one was not removed
> (or not in the right scope): run `claude mcp get amsel` again.

### Without the `claude` command, editing the file

Open `~/.claude.json` and find the `"amsel"` block in `"mcpServers"` (at the root of the file for the user scope):

- **change folders**: only edit the value of `AMSEL_PATHS` (absolute path, no `~`);
- **project moved**: edit the path after `"--directory"`;
- **remove**: delete the whole `"amsel": { … }` block, minding the JSON commas.

> Close any open Claude sessions first: Claude rewrites this file regularly and could overwrite your change.
> Make a copy before editing: `cp ~/.claude.json ~/.claude.json.bak`.

For a per-project registration, make the same change in the `.mcp.json` file at the root of the project.

### Claude Desktop (chat tab)

Same idea in `claude_desktop_config.json` (see option C): edit `AMSEL_PATHS` or `--directory`, or delete the `"amsel"` block, then **fully quit** Claude Desktop and start it again.

## Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| The server shows as "failed" / disconnected | Claude cannot find `uv` (desktop apps do not always have `~/.local/bin` on their PATH) | Replace `"command": "uv"` with the full path given by `which uv` (e.g. `/home/me/.local/bin/uv`) |
| "No .tome file matches … Known files: none" | `AMSEL_PATHS` wrong or empty | Check the path (absolute path, no `~` in JSON files) |
| Links to the Lore show as `[[missing lorePage link]]` | The Lore linked to the Tome is not found | Put the `.lore` in the same folder as the `.tome`, or in a folder listed in `AMSEL_PATHS` |
| Changes made in Amsel do not show up | Amsel has not saved yet | Save in Amsel; the server rereads a modified file automatically |
| Error on first run | Dependencies not installed | `uv sync` in the project folder |
| Claude has no tool to write | `AMSEL_WRITE=1` missing | See section 6, then open a new session |
| "Tome is open" / "Lore is open" | The matching app is open | Close it (completely), then ask again |
