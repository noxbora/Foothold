# PLAYBOOK

An Obsidian vault of offensive-security notes — workflows, techniques, service
checklists and tool references, written while working through lab platforms
(TryHackMe, Hack The Box) and reading.

The vault is built around one idea: **a note earns its place by being reachable.**
Every note links to at least one non-index note, every technique note states what
its output *means* rather than just listing commands, and a linter
(`vault-check.py`) fails the build when that stops being true.

## Where to start

| If you are… | Open |
|---|---|
| New here | [`START-HERE.md`](../START-HERE.md) |
| Starting a box | [`Workflow/Pentest-Workflow.md`](../Workflow/Pentest-Workflow.md) |
| Sitting on a Linux shell | [`Techniques/Linux/Linux-Run-Sheet.md`](../Techniques/Linux/Linux-Run-Sheet.md) |
| Sitting on a Windows shell | [`Techniques/Windows/Windows-Run-Sheet.md`](../Techniques/Windows/Windows-Run-Sheet.md) |
| Out of ideas | [`Workflow/Stuck-Checklist.md`](../Workflow/Stuck-Checklist.md) |

## Layout

```text
START-HERE.md    entry point, house style, weekly review
vault-check.py   the linter
Workflow/     decision layer — phases, methods, checklists
Techniques/   the attacks, grouped by the surface they attack
  Web/  Services/  Linux/  Windows/  Active-Directory/  Cloud/
Operations/   what you do on any target in any phase — shells, transfer,
                 pivoting, looting, and Tools/ for flag references
Reference/    lookup material — security terms, general English, and the failure messages that mislead
```

The tree runs on **one axis**: it answers *what is in front of me*, never *what am I trying
to do* — that second question belongs to `Workflow/`. A technique that attacks no single
surface and is spent in more than one phase is an operation, not a technique of somewhere.
The linter enforces it: every folder declares the `type` and `platform` a note inside it must
carry, so a misfiled note fails the run instead of looking plausible.

This repository is the playbook and nothing else. The Obsidian vault it lives in
also holds private study material, which stays out of git entirely rather than
relying on an ignore rule — cloning this repo carries the whole playbook and no
part of anything personal.

Notes are best read in [Obsidian](https://obsidian.md) — `[[wikilinks]]` and the
graph view are the point. They render fine on GitHub, minus the links.

## Conventions

Every note opens with six frontmatter fields:

```yaml
type: technique        # workflow | technique | service | tool | reference | index
platform: linux        # linux | windows | web | cloud | any
status: working        # seed | working | solid
fluency: unseen        # unseen | guided | cold | teach
source: thm            # thm | htb | lab | field | reading
updated: 2026-09-08
```

`status` grades the note and `fluency` grades the reader; both are honest labels,
not aspirations. `seed` means placeholder, and only using a note on a box promotes it
past `guided`.
Filenames are `Title-Case-With-Hyphens`; service notes are `PORT-Service`.
Full house style lives in
[`START-HERE.md`](../START-HERE.md#conventions).

## Linter

```bash
python3 vault-check.py
```

Thirty checks covering what Dataview cannot see — link topology (broken targets,
orphans, hub-only notes, unresolved anchors, anything more than two hops from the
entry point), frontmatter conformance (six fields, in order, values inside their
vocabulary, a real non-future date), folder placement (each folder's declared `type`
and `platform`, and nothing loose in a folder no rule claims), note structure (heading levels, required
sections, callout vocabulary, invisible characters, duplicated code blocks),
content drift (alphabetical order and entry format in the A–Z reference files),
teaching shape (every section that runs a command carries `**Why now**`, a
`**What you will see**` block that labels all four of Found/Empty/Error/Noise, and `**Then**`;
no hard-wrapped prose, which Obsidian renders as a ragged line break; and no acronym
or product name used in prose without an entry in the A-Z reference)
and history (an `updated` field older than the last commit that changed the body).
Exits non-zero when anything needs attention, so it can gate a commit hook.

Two read-only modes print a list and exit 0 instead:

```bash
python3 vault-check.py --gaps      # what the notes admit is missing
python3 vault-check.py --fluency   # what you lean on and cannot yet do
```

## Scope and disclaimer

Everything here comes from deliberately vulnerable lab environments and public
reading material. No client, employer or third-party data appears in this vault,
and no target is described that was not explicitly set up to be attacked.

These notes are published for learning and reference. Using any of it against a
system you do not own or have written permission to test is illegal. What you do
with it is on you.

## Licence

Notes and prose: [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) —
use them, adapt them, credit the source.
