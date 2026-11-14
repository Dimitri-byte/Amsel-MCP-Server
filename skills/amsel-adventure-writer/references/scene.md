# Writing a playable scene

The GM reads a scene **during play**, often skimming. It must answer four questions fast: where and when are we? what do I read or describe? what can the players do, with which rolls? what happens next?

## Page fields

- **Name**: short and evocative, it is read in the tree ("Black market meeting", not "Scene 4").
- **Summary** (`summary`): one or two sentences for the GM — the stakes of the scene and its exit. This is what shows as the scene summary.
- **Content** (`content`): the scene itself, structured as below.

The parent is a chapter (`create_tome_story_page(parent=...)`). Create scenes in play order: each one is added at the end of the chapter.

## Content structure

Adapt it to the type of scene (not every section is always needed), but keep this order: the GM knows where to look.

1. **Setting** — one line per element, label in bold: `**Place**:`, `**Time**:`, `**Mood**:`. Link to the location.
2. `#### Description` — the text to read or paraphrase to the players, in a quote (`> `), in *italics*. 3 to 6 sentences, present tense, addressing the players the way the campaign does. Start with what the characters perceive first, end on something that invites action.
3. `#### NPCs present` — for each: a `[[NPC]]` link, what they want **right now**, their attitude, an opening line in quotes. Permanent details belong on the NPC's page, not here.
4. `---` then `#### Possible interactions` — a numbered list of approaches. For each: the check and its difficulty in bold, then `- **Success**:` and `- **Failure**:` (and `- **Critical success**:` if it adds something). A failure moves the story forward differently — it does not block it.
5. `#### Clues and information` (for investigations) — what the players can learn, and where. Three-clue rule: any essential piece of information is reachable by at least three paths.
6. `#### If the players…` — 2 or 3 reactions to likely off-script initiatives (attack, flee, ignore).
7. `#### Exit` — how the scene ends and which scene(s) it leads to (`[[Scene]]` links if they already exist).

Typical length: 400 to 1,200 words. A longer scene is often two scenes.

## Choices and arcanes

Amsel models important decisions with **arcanes** (choices and destinies), which the server cannot create yet. When the scene holds a real branch, write it visibly:

```
#### Choice: hand Vessa over or protect her?
- **Hand her over**: the Broker pays, but [[NPC: Orrin]] hears about it and grows wary.
- **Protect her**: Vessa becomes an ally; the bounty on the PCs doubles.
```

…and add it to the "To do in Amsel" list in your report, so the GM creates the matching arcane.

## Example

Call: `create_tome_story_page(tome, parent="The lost ship", name="Black market of Bay 9", page_type="scene", summary=..., content=...)`

`summary`:
```
The PCs look for a spare part on the black market; an informant offers them a risky deal. Exit: a lead to the wreck of the Calyx.
```

`content`:
```
**Place**: [[Bay 9]], lower level of the station. **Time**: night cycle. **Mood**: loud, wary, hot.

#### Description
> *The neon lights of Bay 9 buzz above a hundred cramped stalls. It smells of hot oil and fried spices. Between two merchants' shouts, you notice that a hooded figure has been following you since the elevator — and is making no effort to hide it.*

#### NPCs present
- [[NPC: Vessa]] — wants to sell a piece of information before the Broker finds her. Hurried, ironic. "Looking for a jump coil? I know where there's one left."

---

#### Possible interactions
1. **Bargain with Vessa (Diplomacy DC 16)**
  - **Success**: she accepts 200 credits and gives the coordinates of the Calyx wreck.
  - **Failure**: she demands a favor: pick up a package from [[NPC: Orrin]].
2. **Spot the Broker's men (Perception DC 18)**
  - **Success**: two plainclothes guards are watching Vessa; the PCs can warn her and earn her trust.
  - **Failure**: the guards step in during the negotiation (see "If the players…").

#### If the players…
- **attack the guards**: the market empties in seconds; station security arrives in 3 rounds.
- **ignore Vessa**: she contacts them again by encrypted message in the next chapter, at a higher price.

#### Exit
The PCs get the lead to the Calyx wreck, or a debt to Vessa.
```

Note: the `[[…]]` names in the example must exist in the Tome or the Lore — otherwise, create the pages first.

## Fleshing out an existing scene

When the GM asks to "develop" an existing scene: reread it, keep everything they wrote (their ideas come first), and fill in the missing sections. If you restructure it, use `update_tome_page(content=...)` to replace the whole content, after showing them the result; for a simple addition, `append=True`.
