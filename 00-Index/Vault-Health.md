---
type: index
platform: any
status: solid
fluency: guided
source: lab
updated: 2026-09-04
---

# Vault Health

The weekly-review dashboard. Open it, read the numbers, act on the top of each list.

Requires the **Dataview** plugin. The queries below deliberately have **no `FROM` clause** — they select on frontmatter instead of folder paths, so they work no matter where this vault's root sits. The price of that choice is that they see the **whole** vault, not just `PLAYBOOK/`: anything else that ever lands under the vault root is inside their reach, and `.gitignore` would not hold it back — that is a git file and binds git only, while Dataview indexes every `.md` it can see. So each query names the `type` values it wants rather than assuming the Playbook is all there is.

---

## Seed notes — longest untouched first

The backlog of placeholder notes. These are honest labels, not debt: a `seed` note is one whose commands are still thin. Promote it to `working` the first time you actually use it.

```dataview
TABLE platform, source, updated
WHERE status = "seed"
SORT updated ASC
```

## Where the vault stands

A healthy trend is `seed` shrinking and `solid` growing, week over week.

```dataview
TABLE length(rows) AS count
WHERE type AND type != "index"
GROUP BY status
```

## Coverage by platform

A map of where you have been, not a to-do list. Windows being thinner than Linux is information, not a failure.

```dataview
TABLE length(rows) AS notes
WHERE type = "technique" OR type = "service"
GROUP BY platform
```

## Where the knowledge came from

`source` is the field you cannot reconstruct later. A `thm` / `htb` note may carry lab-specific IPs, flag formats, and versions; a `field` note should not.

```dataview
TABLE length(rows) AS notes
WHERE type AND type != "index"
GROUP BY source
```

## What you can do without the note open

`status` above grades the notes. This grades you against them, and the two are independent — the row that matters is a note the vault leans on hard that is still `unseen`.

```dataview
TABLE length(rows) AS notes
WHERE type AND type != "index" AND type != "reference"
GROUP BY fluency
```

`python3 00-Index/vault-check.py --fluency` gives the same field ranked by how many notes point at each one. That ranking, not a feeling about what is interesting, is what picks next week's DOJO mats.

## Stale — untouched for 90+ days

On a living vault this should be mostly `solid` reference material. A `seed` or `working` note surfacing here is the nudge.

> [!note]
> Every note was rewritten on 2026-08-21, so this list stays empty until roughly late November. That is expected — it will differentiate on its own as you edit.

```dataview
TABLE status, updated
WHERE type AND type != "index" AND updated <= date(today) - dur(90 days)
SORT updated ASC
```

## Missing frontmatter

Deliberately **not** a Dataview query. "Has no frontmatter" cannot be selected by frontmatter, so it would need a hard-coded folder path — the one thing that breaks when the vault root moves. `vault-check.py` below covers it, and does so wherever the vault lives.

---

## What Dataview cannot see

Link topology and note structure. That is `00-Index/vault-check.py` — run it during the weekly review:

```bash
python3 00-Index/vault-check.py
```

Twenty-eight checks in seven families.

**Links:** broken targets, orphans, notes that link only to hubs, unresolved heading anchors, and anything more than two hops from [[Start-Here]] — that last one is stricter than the orphan check, because a note can be well linked and still sit four hops from the entrance.

**Frontmatter:** present, six fields in order, every value inside its vocabulary, `updated` a real date that is not in the future.

**Placement:** every note's folder against that same frontmatter — each folder declares the `type` and `platform` a note inside it must carry, and a note sitting in a folder no rule claims (loose at `02-Techniques/` root, or in a new folder nobody wrote down) fails as well. This is the check that keeps the tree on one axis; the reasoning is in [[Start-Here#Conventions|Start Here → Conventions]].

**Teaching:** a section that runs a command must carry the four layers — `**Why now**`, `**What you will see**` with its Found/Empty/Error/Noise outcomes, and `**Then**`. A catalog of interchangeable payloads is exempt with `<!-- layers-ok -->` above the fence. A second check reads inside that middle block and requires all four outcomes to be labelled, because check 20 only ever proved the marker was present — five blocks had shipped without an **Error** line, the Windows column of the run sheet among them.

The same family enforces **one runnable command per fence**, added 31 Aug 2026: Obsidian's copy button copies a whole block, so two commands in one block means neither can be taken with a click, and the fence is the only thing telling a reader where one command ends. A command that spans lines is still one command — continuations are joined before counting — and a block holding a heredoc or a shell loop is a script, not a list, so it is skipped.

That check originally looked only at `bash`/`cmd`/`powershell` fences, which let a `text`-tagged flag reference — four stacked `sublist3r` invocations — walk straight past it. Text and untagged fences are now judged by shape instead, a binary name followed by a flag, so a stacked reference fails while output samples, tables, arrow comparisons and flagless client verbs pass untouched.

It also requires that a **sweeping command carry its own filter**. Anything the `**Noise**` bullet tells you to ignore by eye belongs inside the command instead: `tasklist`, `ps aux`, `wmic service get`, `schtasks /query`, `netstat`, `Get-CimInstance Win32_*`, `Get-ScheduledTask`, `systemctl list-units` and a rooted `find -perm` all fail unless something narrows the result. A deliberate unfiltered baseline is marked `<!-- raw-ok -->` above the fence, with the note saying why the whole list is the point.

Last in this family, two rules about the shape of the prose itself: no hard-wrapping, which Obsidian renders as a ragged line break, and no paragraph over 120 words, which is a wall of text on a phone.

It also requires that jargon have somewhere to be looked up — every acronym and product name appearing in prose must have an entry in one of the A–Z reference notes, because a note that explains a term inline still leaves the other sixty-eight notes using it cold. Terms deliberately left undefined (protocols that already own a service note, products, file formats, CVE ids) sit in the check's own `ALLOW` list, so leaving one out is a decision on the record rather than an omission.

**Structure:** one H1, no skipped heading levels, `## Next` on skeleton notes, the three-callout vocabulary, invisible characters, trailing whitespace, emphasis markers that will not render, any code block over 40 characters living in two notes at once, and load-bearing-but-thin notes.

**Content:** room-specific residue, English-only prose, and lexicon drift in the A–Z reference files — entry format, alphabetical order, duplicates.

**History:** whether `updated` is older than the last commit that changed the note's body — `updated` is the only field that can go quietly false, and the stale panel above runs on it. Frontmatter-only commits do not count, so bumping the date cannot make the date wrong. This one asks git, and skips itself silently on a copy of the vault that was never a repository.

Then it prints the graph shape. Exit code is 0 when clean, so it can gate a commit hook.

It *checks* the Playbook only. `ROOT` is the folder holding `00-Index/`, so nothing outside that folder is ever reached by a check. That boundary is deliberate rather than incidental: the linter's rules — `## Next`, a lateral link, no repeated command blocks — are house style for Playbook notes, and any other kind of note kept beside the Playbook would fail all three while being perfectly correct on its own terms.

### Reading the graph line

```text
Graph: 346 links, 83 from hubs (23%), 263 lateral
```

Two kinds of link, doing two different jobs. **Hub links** come out of [[Start-Here]] and the workflow notes: they provide *findability* — the way in when you do not yet know what you are looking for. **Lateral links** run note-to-note: they provide *flow* — `3389-RDP` → [[Shells]] → `5985-WinRM`, followed mid-engagement without returning to the map. The vault needs both.

**Target shape:** hub share well under half. Around a quarter to a third is comfortable.

**It is not a score to maximise.** It is a ratio, so it also rises when the denominator falls: neglect the hubs and the hub share drops while the vault gets *worse* — nothing is reachable from the entrance any more. A hundred percent lateral would mean `Start-Here` links nowhere, which breaks the two-hop rule this vault is built on.

**Watch the direction, not the number.** A hub share climbing over months means notes are being filed but not wired to their neighbours. That is the only signal this line carries.

And it cannot tell a good link from a bad one: connect two notes because they are *topically near* and the number improves while nothing does. The real quality control is the `## Next` rule in [[Note-Template]] — links that are **directional**, where you actually go once this note has done its job. The graph line is the smoke detector for that habit lapsing, nothing more.

## The open backlog

Two different questions, two different lists. This panel tracks the **state of existing** notes. The backlog of *missing* work is generated from every `## Gaps` line in the vault:

```bash
python3 00-Index/vault-check.py --gaps
```

The curated short version, with priorities, is [[Start-Here#Known backlog|Start Here → Known backlog]].

Worth running in the same sitting as the panels above: they track the state of what exists, `--gaps` tracks what the notes themselves admit is missing.
