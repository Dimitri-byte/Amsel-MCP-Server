# Amsel MCP Server

[![Tests](https://github.com/Dimitri-byte/Amsel-MCP-Server/actions/workflows/tests.yml/badge.svg)](https://github.com/Dimitri-byte/Amsel-MCP-Server/actions/workflows/tests.yml)
[![Licence : MIT](https://img.shields.io/badge/Licence-MIT-blue.svg)](LICENSE)

*[English version](README.md)*

Serveur [MCP](https://modelcontextprotocol.io) qui donne à Claude (ou à tout client MCP) un accès en **lecture** — et, si tu l'actives, en **écriture** — aux fichiers d'[Amsel Suite](https://www.amsel-suite.com/) : les campagnes **Tome** (`.tome`), les mondes **Lore** (`.lore`) et les kits de modèles **Lore** (`.lorekit`).

Claude peut ainsi parcourir l'arbre de ta campagne, lire un PNJ ou une page de Lore, suivre les liens entre pages, consulter les arcanes et leurs résultats par session, et faire des recherches dans tout ton contenu. Avec l'écriture activée, il peut aussi créer des PNJ, des scènes ou des pages de Lore, compléter des textes, ajouter des notes de session et poser des images.

> Projet communautaire, non affilié à Ollam Technologies, l'éditeur d'Amsel Suite, ni approuvé par lui.
> Le format des fichiers a été déduit par rétro-ingénierie et peut changer avec les nouvelles versions d'Amsel : **travaille d'abord sur des copies**.

> [!CAUTION]
> ## ⚠️ FAIS TOUJOURS UNE SAUVEGARDE DE TES FICHIERS AVANT TOUTE MODIFICATION ⚠️
>
> **Avant d'activer les outils d'écriture, et avant chaque séance de travail avec eux, copie tes fichiers `.tome` et `.lore` en lieu sûr** (autre dossier, disque externe, cloud).
>
> Le serveur écrit directement dans tes vrais fichiers de campagne. Il garde des sauvegardes automatiques dans `.amsel-backups/`, mais seulement les 20 dernières versions, à côté du fichier : elles ne remplacent pas ta propre sauvegarde. Le format des fichiers Amsel n'est pas documenté (il a été déduit par rétro-ingénierie) et une nouvelle version d'Amsel peut le changer.
>
> **Pas de sauvegarde, pas d'écriture.** Commence par des copies, vérifie le résultat dans Amsel, puis passe à tes vrais fichiers.

## Outils de lecture (toujours disponibles)

| Outil | Rôle |
|---|---|
| `list_amsel_files` | Liste les `.tome` / `.lore` / `.lorekit` trouvés, avec leurs compteurs et le Lore lié à chaque Tome |
| `tome_outline` | Arbre du scénario (histoire → chapitres → scènes), rubans, état par session |
| `list_tome_data_pages` | Pages de données (personnages, lieux, objets, organisations, joueurs) groupées par type |
| `read_tome_page` | Une page de scénario ou de données en Markdown, liens résolus, « référencé par » |
| `list_tome_arcanes` | Arcanes (choix / destinées), résultats et commentaires par session |
| `read_tome_notes` | Notes de session |
| `list_lore_pages` | Pages du Lore groupées par modèle |
| `list_lore_templates` | Modèles d'un Lore ou d'un kit : catégorie, nombre de pages, modules |
| `read_lore_template` | Un modèle en détail : modules dans l'ordre, champs des runes, cibles des miroirs |
| `read_lore_page` | Une page de Lore, modules dans l'ordre du modèle, runes et images |
| `search_amsel` | Recherche (insensible à la casse et aux accents) dans les noms et les textes |

## Outils d'écriture (avec `AMSEL_WRITE=1`)

| Outil | Rôle |
|---|---|
| `create_tome_data_page` | Crée une page de données (personnage, lieu, objet, organisation, joueur, fable), avec résumé et sections |
| `create_tome_story_page` | Crée une scène ou un chapitre dans l'arbre du scénario, avec des arcanes dans le contenu de la scène |
| `update_tome_page` | Renomme une page Tome ou remplace / complète son résumé, son contenu ou ses sections texte |
| `add_tome_session_note` | Ajoute une note de session |
| `create_lore_page` | Crée une page de Lore à partir d'un modèle, avec ses champs texte |
| `update_lore_page` | Renomme une page de Lore ou remplace / complète ses champs texte |
| `set_lore_page_image` | Place une image locale (PNG, JPEG, WebP, GIF) dans le module image d'une page de Lore |
| `set_tome_page_image` | Définit l'image de couverture d'une page du Tome (donnée ou histoire) |

Le texte s'écrit en Markdown léger : une ligne par paragraphe, `**gras**`, `*italique*`, intertitres `### ` / `#### `, séparateurs `---`, listes `- ` ou `1. ` (indentées de 2 espaces pour une sous-liste), citations `> `, et liens `[[Nom de page]]` vers des pages existantes (Tome ou Lore lié). Un lien introuvable ou ambigu annule l'écriture.

**Arcanes** — dans le contenu d'une scène, une ligne qui contient seulement l'une de ces formes crée un nouvel arcane, avec un résultat vide pour chaque session de jeu :

| Ligne | Arcane |
|---|---|
| `[[choice: Vont-ils livrer l'informatrice ?]]` | choix (oui / non, indécis au départ) |
| `[[destiny: L'Auditeur retrouve le vaisseau]]` | destin (humeur de 1 à 5, non définie au départ) |
| `[[role: Un PJ négocie avec la guilde]]` | rôle (personnages à attribuer ensuite dans Amsel) |
| `[[options: Comment partent-ils ? \| En douce \| Par la force \| Avec un laissez-passer]]` | options (texte, puis au moins deux options) |
| `[[count: Niveau d'alerte impérial]]` | compteur (commence à 0) |

`read_tome_page` affiche les arcanes existants sous la forme `[[choice#1041e488: …]]`. Garde ces lignes quand tu réécris une scène : l'identifiant conserve l'arcane et ses résultats ; sans lui, l'arcane est détaché de la scène.

**Garde-fous** — sans `AMSEL_WRITE=1`, les outils d'écriture n'existent pas. Quand ils sont actifs, chaque écriture :

- est **refusée si l'application Tome (pour un `.tome`) ou Lore (pour un `.lore`) est ouverte** : elle écraserait la modification à sa prochaine sauvegarde ;
- est refusée si le fichier a changé sur le disque pendant la préparation ;
- copie d'abord le fichier dans `.amsel-backups/` à côté de lui (20 dernières versions gardées) ;
- réécrit l'archive dans un fichier temporaire, la relit pour la vérifier, puis remplace l'original. Les images existantes ne sont pas touchées ; les nouvelles sont ajoutées dans `img/` et dans la bibliothèque d'images (dossier au choix).

Pas de suppression pour l'instant, ni de modification des résultats d'arcanes existants, des relations ou des runes. Les images viennent de fichiers locaux : une image en ligne doit d'abord être téléchargée.

Les fichiers et les pages se désignent par nom, nom partiel ou identifiant (ou début d'identifiant). Les liens Amsel apparaissent sous la forme `[[Nom de la page]]`.

## Le skill « amsel-adventure-writer »

Le dossier [`skills/amsel-adventure-writer`](skills/amsel-adventure-writer/SKILL.md) contient un skill Claude qui utilise ce serveur pour **écrire des aventures jouables** : scènes structurées (cadre, texte à lire, tests et conséquences, sorties), PNJ et lieux utilisables en improvisation, pages de Lore construites sur les modèles (en s'inspirant des kits `.lorekit`). Il lit d'abord la campagne (arbre, notes de session, arcanes, style du MJ), propose un plan, puis écrit dans le bon ordre pour que les liens se résolvent. Le skill est rédigé en anglais, mais il écrit dans la langue de ta campagne.

Installation pour Claude Code :

```bash
ln -s "$PWD/skills/amsel-adventure-writer" ~/.claude/skills/amsel-adventure-writer
```

## Installation

> 📘 Guide pas à pas, de zéro jusqu'au premier essai, avec dépannage : [docs/installation.fr.md](docs/installation.fr.md)

Prérequis : [uv](https://docs.astral.sh/uv/) (il installe Python 3.10+ pour toi).

```bash
git clone https://github.com/Dimitri-byte/Amsel-MCP-Server.git
cd Amsel-MCP-Server
uv sync
```

### Dossiers analysés

La variable `AMSEL_PATHS` indique où chercher les fichiers (plusieurs dossiers séparés par `:` sous Linux/macOS, `;` sous Windows). Les sous-dossiers sont parcourus, les dossiers cachés ignorés. Par défaut : `~/Documents`.

### Claude Code

```bash
claude mcp add --scope user amsel -e AMSEL_PATHS="$HOME/Documents" -- uv run --directory /chemin/vers/Amsel-MCP-Server amsel-mcp
```

Ajoute `-e AMSEL_WRITE=1` pour activer les outils d'écriture.

### Claude Desktop

Dans `claude_desktop_config.json` :

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

## Format des fichiers Amsel (rétro-ingénierie)

- Un `.tome` ou un `.lore` est une archive **tar** (format pax) contenant `data.json` (JSON minifié) et un dossier `img/` (`<uuid>.<ext>`, plus des miniatures facultatives `<uuid>.thumb.400.png`). Les images sont listées dans `importedImages` et rangées dans `imageFolders`.
- À l'ouverture, l'application décompresse le fichier dans `~/.amselsuite/<uuid>/` ; ce sont des copies de travail, le serveur lit toujours les archives.
- **Tome** (`lastVer` 24) : `storyPages` (types `TSP_Story`, `TSP_ChapterFlow`, `TSP_Chapter`, `TSP_Scene`, arbre via `parentId` / `childrenIds`), `dataPages` (`TDP_Character`, `TDP_Location`, `TDP_Object`, `TDP_Organization`, `TDP_Player`, `TDP_Fable`, sous-pages `text` ou `checker`), `arcanes` (`choice` / `destiny`), `gameSessions`, `notes`, `linkedLorePath`. Couverture d'une page : `coverImage.relatedImage`.
- **Lore** (`lastVer` 17) : `pages` (contenu par module via `relatedModuleId` ; images via `visualContent.relatedImage`), `templates` (modules `LM_Standard_Text`, `LM_Image`, `LM_Rune`, `LM_Mirror`), `runeTemplates`, `diagrams`, `maps`.
- **Kit Lore** (`.lorekit`) : même archive, sans pages ni images ; seulement `name`, `templates` et les runes. Format ancien (`lastVer` 13) : `runeTemplates[].runelets`. Format récent (`lastVer` 23) : `runeGroups[].runes`, `customTemplateCategories` (catégories perso référencées par id) et `inspirationLists`. Le serveur lit les deux, mais n'écrit jamais dans un kit : on l'importe dans un Lore depuis l'application.
- Texte riche en HTML. Liens : `<tag-component id="lorePage/…">` (page Lore), `index/…` (page de données Tome), `storyPage/…` ; arcanes intégrés : `<intrigue-component idhash="…">` (choix), `<destiny-component …>`, `<role-component …>`, `<options-component …>`, `<count-component …>`. Chaque arcane a un résultat par session de jeu : `state` (`tbd` / `yes` / `no`), `mood` (0 = non défini, 1–5), `characters`, `choices` (avec `isSelected`) ou `number`.
- Lore lié : le serveur cherche d'abord un `.lore` du même nom à côté du Tome (utile pour des copies), puis le chemin enregistré.

## Développement

```bash
uv run pytest
```

Les tests utilisent des fichiers synthétiques générés à la volée. Si `AMSEL_TEST_DIR` pointe vers un dossier de vrais fichiers Amsel, des tests supplémentaires vérifient que chaque page s'affiche. Ne commite jamais de vrais `.tome` / `.lore` / `.lorekit` (ils sont dans le `.gitignore`).

Les contributions sont bienvenues : voir [CONTRIBUTING.md](CONTRIBUTING.md). Les changements sont listés dans [CHANGELOG.md](CHANGELOG.md).

## Feuille de route

- [x] Lecture des Tome, Lore et kits Lore
- [x] Écriture : création et modification de pages, notes de session, images (sauvegardes, refus si l'application est ouverte)
- [x] Création d'arcanes (choix, destin, rôle, options, compteur)
- [ ] Modification des résultats d'arcanes, relations, runes
- [ ] Suppression de pages

## Licence

[MIT](LICENSE). Amsel Suite, Tome et Lore sont des marques de leurs propriétaires respectifs.
