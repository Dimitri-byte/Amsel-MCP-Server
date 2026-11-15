# Lancer le serveur MCP Amsel de zéro

*[English version](installation.md)*

Ce guide part d'une machine sur laquelle il n'y a rien, à part Amsel Suite et Claude.

## Comment ça marche, en deux phrases

Un serveur MCP n'est pas un service qui tourne en permanence : c'est **Claude qui le lance** au début de chaque session, puis lui parle par l'entrée et la sortie standard (stdio). Il faut donc seulement **installer** le serveur une fois, puis **dire à Claude comment le lancer**.

```
Claude Code / Claude Desktop ──lance──▶ uv run amsel-mcp ──lit──▶ tes fichiers .tome / .lore / .lorekit
```

## 1. Installer les prérequis

| Outil | Rôle | Vérifier |
|---|---|---|
| Git | récupérer le code | `git --version` |
| [uv](https://docs.astral.sh/uv/) | installe Python 3.10+ et les dépendances | `uv --version` |

Si `uv` n'est pas installé (Linux / macOS) :

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Sous Windows (PowerShell) :

```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

Ferme puis rouvre le terminal pour que `uv` soit trouvé.

## 2. Récupérer le code et installer les dépendances

```bash
git clone https://github.com/Dimitri-byte/Amsel-MCP-Server.git
cd Amsel-MCP-Server
uv sync
```

`uv sync` crée un dossier `.venv/` avec Python et le SDK MCP. Rien n'est installé ailleurs sur ta machine.

## 3. Savoir où sont tes fichiers Amsel

Le serveur cherche les `.tome`, `.lore` et `.lorekit` (kits de modèles) dans les dossiers indiqués par la variable **`AMSEL_PATHS`** (sous-dossiers compris, dossiers cachés ignorés). Sans elle, il cherche dans `~/Documents`.

- Plusieurs dossiers : séparés par `:` (Linux / macOS) ou `;` (Windows).
- Exemple : `AMSEL_PATHS=/home/moi/Documents/JDR:/home/moi/Nextcloud/JDR`

> Conseil : pour commencer, pointe vers un dossier contenant des **copies** de tes campagnes.
> Le serveur est en lecture seule tant que tu n'actives pas l'écriture, mais c'est une bonne habitude.

## 4. Vérifier que le serveur fonctionne

Lancer les tests :

```bash
uv run pytest
```

Interroger le serveur sans Claude, depuis Python :

```bash
AMSEL_PATHS="$HOME/Documents" uv run python -c "from amsel_mcp import server; print(server.list_amsel_files())"
```

Tu dois voir la liste de tes fichiers. Si elle est vide, `AMSEL_PATHS` ne pointe pas au bon endroit.

> Lancer directement `uv run amsel-mcp` donne l'impression que rien ne se passe : c'est normal,
> le serveur attend des messages MCP sur son entrée standard. Quitte avec `Ctrl+C`.

Optionnel, avec Node.js installé, l'**MCP Inspector** ouvre une page web pour appeler chaque outil à la main :

```bash
npx @modelcontextprotocol/inspector -e AMSEL_PATHS="$HOME/Documents" -- uv run --directory "$PWD" amsel-mcp
```

## 5. Brancher le serveur sur Claude

Dans les exemples, remplace `/chemin/vers/Amsel-MCP-Server` par le chemin réel (donné par `pwd` dans le dossier du projet).

### Option A — Claude Code, avec la commande `claude`

```bash
claude mcp add --scope user amsel \
  -e AMSEL_PATHS="$HOME/Documents" \
  -- uv run --directory /chemin/vers/Amsel-MCP-Server amsel-mcp
```

- `--scope user` : disponible dans tous tes projets. Sans cette option, seulement dans le dossier courant.
- Vérifier : `claude mcp get amsel` doit afficher `✔ Connected`.
- Retirer : `claude mcp remove amsel -s user`.

#### `claude : commande introuvable` ?

C'est normal si tu utilises seulement l'**application de bureau** Claude. Elle embarque son propre exemplaire de Claude Code, mais pour son usage interne :

- il est rangé dans `~/.config/Claude/claude-code/<version>/<id>/claude` (Linux) ;
- ce dossier n'est pas dans le PATH, donc le terminal ne le trouve pas ;
- le chemin **change à chaque mise à jour** : un alias vers ce chemin finit par casser.

Trois solutions :

1. **Installer Claude Code en ligne de commande** (recommandé). Tu obtiens un vrai `claude` dans `~/.local/bin`, mis à jour automatiquement, qui partage la même configuration (`~/.claude.json`) que l'application :

   ```bash
   curl -fsSL https://claude.ai/install.sh | bash
   ```

2. **Un raccourci qui suit les mises à jour de l'application**, sans rien installer. Crée le script `~/.local/bin/claude` (ce dossier doit être dans ton PATH) :

   ```bash
   cat > ~/.local/bin/claude <<'EOF'
   #!/bin/sh
   # Lance le Claude Code embarqué le plus récent de l'application de bureau
   bin=$(ls -d "$HOME"/.config/Claude/claude-code/*/*/claude 2>/dev/null | sort -V | tail -n 1)
   [ -n "$bin" ] || { echo "Claude Code introuvable dans l'application de bureau" >&2; exit 1; }
   exec "$bin" "$@"
   EOF
   chmod +x ~/.local/bin/claude
   ```

   Limite : ce raccourci ne marche plus si tu désinstalles l'application de bureau.

3. **Te passer de la commande** : utilise l'option B ci-dessous. La commande `claude mcp add` ne fait qu'écrire dans un fichier de configuration.

### Option B — Claude Code, en modifiant le fichier à la main

La commande ci-dessus ne fait qu'écrire ceci dans `~/.claude.json` (clé `mcpServers` à la racine du fichier) :

```json
{
  "mcpServers": {
    "amsel": {
      "type": "stdio",
      "command": "uv",
      "args": ["run", "--directory", "/chemin/vers/Amsel-MCP-Server", "amsel-mcp"],
      "env": { "AMSEL_PATHS": "/home/moi/Documents" }
    }
  }
}
```

Pour un serveur actif dans **un seul projet**, mets le même bloc `mcpServers` dans un fichier `.mcp.json` à la racine de ce projet.

### Option C — Claude Desktop (onglet discussion)

Ouvre `claude_desktop_config.json` (ou *Paramètres → Développeur → Modifier la configuration*) :

| Système | Emplacement |
|---|---|
| Linux | `~/.config/Claude/claude_desktop_config.json` |
| macOS | `~/Library/Application Support/Claude/claude_desktop_config.json` |
| Windows | `%APPDATA%\Claude\claude_desktop_config.json` |

Ajoute :

```json
{
  "mcpServers": {
    "amsel": {
      "command": "uv",
      "args": ["run", "--directory", "/chemin/vers/Amsel-MCP-Server", "amsel-mcp"],
      "env": { "AMSEL_PATHS": "/home/moi/Documents" }
    }
  }
}
```

Puis **quitte complètement** Claude Desktop et relance-le.

## 6. Activer l'écriture (optionnel)

Par défaut, le serveur ne fait que **lire**. Pour que Claude puisse aussi créer et modifier des pages, ajoute la variable **`AMSEL_WRITE=1`** à l'enregistrement. Avec la commande `claude` (après avoir supprimé l'ancien enregistrement, voir la section 8) :

```bash
claude mcp add --scope user amsel -e AMSEL_PATHS="$HOME/Documents/JDR-copies" -e AMSEL_WRITE=1 -- uv run --directory /chemin/vers/Amsel-MCP-Server amsel-mcp
```

Ou à la main, dans le bloc `"env"` : `"AMSEL_WRITE": "1"`.

> [!CAUTION]
> **Fais toujours une sauvegarde de tes fichiers `.tome` et `.lore` avant d'activer l'écriture et avant chaque séance de travail.** Les sauvegardes automatiques de `.amsel-backups/` ne remplacent pas ta propre copie.

À savoir avant d'écrire :

- **Ferme l'application Tome** avant de modifier un `.tome`, et **Lore** avant de modifier un `.lore`. Sinon le serveur refuse : Amsel garde le fichier en mémoire et écraserait la modification à sa prochaine sauvegarde.
- Chaque écriture garde une copie de la version précédente dans `.amsel-backups/`, à côté du fichier. Pour revenir en arrière, ferme Amsel et recopie la sauvegarde à la place du fichier.
- Commence par des **copies** de tes fichiers, et vérifie le résultat en les ouvrant dans Amsel.

## 7. Essayer

Ouvre une nouvelle session et demande par exemple :

- « Quels fichiers Amsel as-tu trouvés ? »
- « Montre-moi l'arbre de ma campagne. »
- « Que sait-on de tel PNJ ? Avec qui est-il lié ? »
- « Quels arcanes n'ont pas encore été résolus ? »

Dans Claude Code en terminal, la commande `/mcp` liste les serveurs et leur état.

## 8. Changer de dossier ou supprimer l'enregistrement

L'enregistrement est **permanent** : il survit aux redémarrages du poste, et Claude relance le serveur tout seul à chaque session. Il n'y a donc rien à refaire au quotidien. On ne le modifie que pour :

- lire **un autre dossier** de fichiers Amsel (passer des copies de test aux vrais fichiers, par exemple) ;
- suivre le projet après l'avoir **déplacé ou renommé** ;
- **retirer** complètement le serveur.

> Après chaque modification, ouvre une **nouvelle session** : une session déjà ouverte garde l'ancienne configuration.

### Avec la commande `claude`

Voir d'abord ce qui est enregistré :

```bash
claude mcp list
```

```bash
claude mcp get amsel
```

`claude mcp get` indique le **scope** (« User config », « Local config » ou « Project config »), qu'il faut redonner pour supprimer.

Supprimer l'enregistrement (ici en scope utilisateur ; remplace `user` par `local` ou `project` selon ce qu'affiche `get`) :

```bash
claude mcp remove amsel -s user
```

Puis enregistrer le nouveau, avec le nouveau dossier ou le nouveau chemin du projet :

```bash
claude mcp add --scope user amsel -e AMSEL_PATHS="$HOME/Documents" -- uv run --directory /chemin/vers/Amsel-MCP-Server amsel-mcp
```

Plusieurs dossiers à la fois : `-e AMSEL_PATHS="$HOME/Documents:$HOME/Nextcloud/JDR"`.

> Si `claude mcp add` répond que le serveur existe déjà, c'est que l'ancien n'a pas été supprimé
> (ou pas dans le bon scope) : refais `claude mcp get amsel`.

### Sans la commande `claude`, en modifiant le fichier

Ouvre `~/.claude.json` et cherche le bloc `"amsel"` dans `"mcpServers"` (à la racine du fichier pour le scope utilisateur) :

- **changer de dossier** : modifie seulement la valeur de `AMSEL_PATHS` (chemin absolu, pas de `~`) ;
- **projet déplacé** : modifie le chemin après `"--directory"` ;
- **supprimer** : retire tout le bloc `"amsel": { … }` en faisant attention aux virgules du JSON.

> Ferme d'abord les sessions Claude ouvertes : Claude réécrit ce fichier régulièrement et pourrait écraser ta modification.
> Fais une copie avant d'éditer : `cp ~/.claude.json ~/.claude.json.bak`.

Pour un enregistrement par projet, la même modification se fait dans le fichier `.mcp.json` à la racine du projet.

### Claude Desktop (onglet discussion)

Même principe dans `claude_desktop_config.json` (voir l'option C) : modifie `AMSEL_PATHS` ou `--directory`, ou supprime le bloc `"amsel"`, puis **quitte complètement** Claude Desktop et relance-le.

## Dépannage

| Symptôme | Cause probable | Solution |
|---|---|---|
| Le serveur apparaît « failed » / déconnecté | Claude ne trouve pas `uv` (les applications graphiques n'ont pas toujours `~/.local/bin` dans leur PATH) | Remplace `"command": "uv"` par le chemin complet, donné par `which uv` (ex. `/home/moi/.local/bin/uv`) |
| « No .tome file matches … Known files: none » | `AMSEL_PATHS` faux ou vide | Vérifie le chemin (chemin absolu, pas de `~` dans les fichiers JSON) |
| Les liens vers le Lore s'affichent `[[missing lorePage link]]` | Le `.lore` lié au Tome n'est pas trouvé | Place le `.lore` dans le même dossier que le `.tome`, ou dans un dossier de `AMSEL_PATHS` |
| Les modifications faites dans Amsel n'apparaissent pas | Amsel n'a pas encore enregistré | Enregistre dans Amsel ; le serveur relit automatiquement un fichier modifié |
| Erreur au premier lancement | Dépendances pas installées | `uv sync` dans le dossier du projet |
| Claude n'a pas d'outil pour écrire | `AMSEL_WRITE=1` absent | Voir la section 6, puis ouvre une nouvelle session |
| « Tome is open » / « Lore is open » | L'application correspondante est ouverte | Ferme-la (complètement), puis redemande |
