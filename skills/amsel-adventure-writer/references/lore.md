# Lore pages, templates and kits

The Lore is the world's encyclopedia. The Tome tells **what happens**; the Lore describes **what exists**. A faction, a city or a religion goes in the Lore; the scene where the PCs meet it goes in the Tome and points to it.

## Choosing the template

Every Lore page follows a **template** that sets its modules: texts, image, runes (structured fields), mirrors (lists of linked pages).

1. `list_lore_templates(lore)` → available templates and the page count per template.
2. `read_lore_template(lore, template)` → the modules in order, the rune fields, and what the mirrors list.
3. Read one or two existing pages of that template (`list_lore_pages(lore, template=...)`, `read_lore_page`) for the expected level of detail.

## Drawing on kits (.lorekit)

Kits (the Amsel starter kit, community kits for various games…) are carefully designed sets of templates. They hold no pages, but they show **which questions a good page should answer**. Before writing a Lore page, look at the equivalent template in a kit (`list_amsel_files` to find them, `read_lore_template(kit, "Cities")`): if the kit plans "Economy", "Government", "Dangers" and the Lore's template only has a "Description" field, cover those questions inside "Description" with `###` headings.

Never write to a kit: to use its templates as they are, the GM imports it into their Lore from the app.

## Writing the page

- `create_lore_page(lore, template, name, fields={"Text module name": "…"})` — the keys of `fields` are the titles of the text modules (case- and accent-insensitive). Fill **every** relevant text module; an empty module makes the page look unfinished.
- `update_lore_page(..., fields=..., append=True)` to extend without overwriting.
- Images: `set_lore_page_image(lore, page, image_path, folder=...)` with a local file (PNG, JPEG, WebP, GIF). An online image must be downloaded first — ask the GM before any download.
- Runes and mirrors cannot be written yet: put the rune information in the text if it matters, and list in "To do in Amsel" the mirrors to connect and the runes to fill.

## Quality of a Lore page

- **One strong idea first** — the first sentence says what makes this place, people or faction unique.
- **Tensions** — who opposes whom, what threatens the balance. A world without conflict generates no adventures.
- **Usable in play** — end with a `### Hooks` section: 2 or 3 adventure ideas this page makes possible.
- **Connected** — `[[…]]` links to other Lore pages (not to the Tome, unless the Tome is linked); check with `search_amsel` that the target page exists.
- **No contradictions** — check with `search_amsel` what the Lore already says about the subject before inventing.
- **Sources** — when summarizing an external source (a wiki, a book), write in your own words and note the source at the end of the page; never copy long passages.
