# Data pages: NPCs, locations, objects, organizations

Data pages are the sheets the GM opens mid-game when a player says "I go back to see the merchant". They must make **improvisation** possible: who is this, what do they want, how do I play them.

## Conventions

- **Type** (`page_type`): `character`/`npc`, `location`, `object`, `organization`, `player`.
- **Name**: follow the Tome's convention. Many GMs use prefixes (`NPC: Vessa`, `PC: Thessaly`) — look at `list_tome_data_pages` and do the same.
- **Summary** (`summary`): one or two lines, what you need to know in 5 seconds.
- **Sections** (`sections={"Title": "text"}`): reuse **the section titles already used** in the Tome, by reading two or three pages of the same type. A common set is a summary, the impact on the story, and details. Do not start a new convention next to the GM's.
- Also spot the **recurring questions** the GM uses in their pages (for example "What are they doing right now? / What is their mood? / What do they want?") and answer them in the page: they are the GM's improvisation tools.
- "Checklist" sections cannot be written: put that content in a text section, with `###` headings.

## NPCs

What makes an NPC playable:

- **Current goal** — what they want now, and what they are ready to do for it.
- **How to play them** — voice, tic, posture, one or two typical lines in quotes. This is what the GM will use most.
- **Secret or leverage** — what the PCs can discover, and what it changes.
- **Links** — who they are tied to (`[[…]]`), which scenes they appear in.
- **What they know** — the information they can give the PCs, and at what price.
- **Statistics** — only if the system needs them for this NPC, briefly (or the name of a stock profile from the bestiary).

Example `sections`:

```
"Summary": "Informant of [[Bay 9]], sells secrets to the highest bidder.\n- **Wants**: to leave the station before the Broker finds her.\n- **Secret**: she stole the map to the Calyx wreck.",
"Impact on the story": "Leads the PCs to the Calyx wreck (scene [[Black market of Bay 9]]).\nIf she is betrayed, the Broker gets one step ahead.",
"Details": "### Portrayal\nTalks fast, finishes other people's sentences. \"Time is credits, and you're costing me both.\"\n### Appearance\nGray hood, gold ocular implants, fingerless gloves.\n### What she knows\n- The bay's patrol schedules.\n- Where the Broker keeps his trophies."
```

## Location

- **First impression** — 2 or 3 sentences of description to read, sensory.
- **What is there** — areas or points of interest, as a list, each with a usable detail.
- **Who is there** — linked NPCs, factions that control it.
- **Dangers and opportunities** — what can go wrong, what can be gained.
- **Hooks** — 2 or 3 ideas to bring the players there.

## Object

Short description, what it does (system mechanics if relevant), its origin, **who is looking for it** — an interesting object creates conflict.

## Organization

Goal, means, leader (`[[NPC]]`), notable members, territory, allies and enemies, **what it will do next if nobody intervenes** (a faction clock makes the world feel alive).

## Fleshing out an existing page

To "flesh out" an NPC the GM sketched: read the page, keep every one of their notes (even short or casual ones — that is their material), and add what is missing with `update_tome_page(sections=..., append=True)`. Only rewrite by replacing if the GM asks for it.
