---
type: index
platform: any
status: solid
fluency: guided
source: lab
updated: 2026-10-19
---

# Start Here

The entrance to the Playbook, and the only meta note in it. Everything else is reachable from here in at most two hops, and the linter fails the run when it is not.

**Before the first command of the evening.** An empty result has two meanings — nothing is there, or you are not allowed to see it — and on Linux they look identical. Four ways to tell them apart: ask the same question about a file you know exists, run it once without `2>/dev/null`, read `echo $?`, and count what was searched rather than what came back. An empty result is not a finding until you have shown it is not a permission problem.

## What do I do now

Find the row that describes what you are **holding** — not what you are trying to achieve — and open the note it names.

| What you are holding                                  | Open                                                                                                  |
| ----------------------------------------------------- | ----------------------------------------------------------------------------------------------------- |
| An IP and nothing else                                | [[Pentest-Workflow]] — the six phases, and what to do when a scan comes back thin                     |
| A version string you have not searched yet            | [[Public-Exploit-Workflow]] — search → verify → modify → run                                          |
| A shell as a low-privileged **Linux** user            | [[Linux-Run-Sheet]] — eight steps, one command per block                                              |
| A shell as a low-privileged **Windows** user          | [[Windows-Run-Sheet]] — the same eight questions, Windows commands                                    |
| A page of findings and no path                        | step 8 of whichever sheet you are on — the escalation is a **pair**                                   |
| A password with no username                           | [[Config-File-Looting]] — where the other half lives                                                  |
| A subnet, a tunnel into it and no map                 | [[Domain-Controller-Discovery]] — which host answers for the domain, and what the domain is called    |
| A domain name, a controller address and no credential | [[AD-Username-Enumeration]] — the names the domain will confirm for you, before any password is typed |
| A domain credential                                   | [[AD-Authentication]] — which of the five shapes you hold, and what each can authenticate to          |
| A file you can write but do not own                   | [[PSPY]] — prove what runs it, then append and wait one interval                                      |
| An error message you do not trust                     | [[Failure-Messages]] — the messages whose plain reading points at the wrong cause                     |
| Nothing works and it is one in the morning            | [[Stuck-Checklist]] — what gets forgotten, every line ending in a note                                |

## The spines

**[[Pentest-Workflow]]** — the map. Six phases, each naming what you hold entering it, the asset it produces, its exit condition, and where to go **if it produces nothing**.

**[[Linux-Run-Sheet]]** · **[[Windows-Run-Sheet]]** — the method behind privilege escalation, one note per platform. Step 8 is the one that gets skipped and costs the most: a list of findings is not a path.

**[[Stuck-Checklist]]** — flat and deliberately scrappy. Read top to bottom when a box has gone quiet.

Also in `Workflow/`: [[Public-Exploit-Workflow]], a method note rather than a spine — you mostly arrive at it from the notes that need it rather than by navigating.

## The rest of the vault

Privilege escalation: [[Linux-Privilege-Escalation]] · [[Windows-Privilege-Escalation]]. Operations: [[Shells]] (listeners, TTY upgrade, [[Security-Terms#^tls|TLS]]) · [[File-Transfer]] · [[Pivoting-and-Tunneling]] · [[Hash-Cracking]] · [[Config-File-Looting]] · [[Exposed-Service-Looting]]. Active Directory, before the first credential: [[AD-Username-Enumeration]] · [[Password-Spraying]] · [[AS-REP-Roasting]] · [[Authentication-Coercion]]; after it: [[AD-Authentication]] · [[Kerberoasting]] · [[AD-Authenticated-Enumeration]] · [[BloodHound]]. Services: one note per port, listed in [[Pentest-Workflow#Per-service enumeration|Phase 1]].

Reference: [[Security-Terms]] (domain vocabulary A–Z, with `^block-anchors` for the terms worth linking into) · [[English-Vocabulary]] (general English met while studying, kept separate on purpose) · [[Failure-Messages]] · [[Bash-Scripting]] (the syntax behind every command you run, and the failures it produces).

Tool references — flag surfaces only, the method lives in the technique note: [[Nmap]] · [[RustScan]] · [[Nikto]] · [[Burp-Suite]] · [[Curl-and-Wget]] · [[TShark]] · [[TheHarvester]].

## Conventions

**Nothing room-specific enters the Playbook.** This outranks every other rule, because it is the only one that cannot be repaired later. What graduates is the technique, stated so it holds anywhere. Strip the room's sentences as you write, not afterwards. The phrases that survive most often:

- "we have provided you with…", "for your convenience" <!-- room-ok -->
- "deploy the machine", "this room", "answer the question" <!-- room-ok -->
- the platform's own environment — the AttackBox and friends <!-- room-ok -->
- the box's own names: `su tryhackme` is a machine's user, not a command <!-- room-ok -->

`vault-check.py` scans for exactly that wording, which is why those four lines carry `<!-- room-ok -->` — the marker is the escape hatch and those lines are the check's live test. Its sibling `<!-- dup-ok -->` goes above a fence deliberately repeated in a second note. Box narratives, IPs, credentials and flags are simply not kept here.

**Frontmatter — six fields, in this order, nothing more.**

```yaml
---
type: technique        # workflow | technique | service | tool | reference | index
platform: linux        # linux | windows | web | cloud | any
status: working        # seed | working | solid
fluency: unseen        # unseen | guided | cold | teach
source: htb            # thm | htb | lab | field | reading
updated: 2026-09-08
---
```

`status` grades the note — `seed` a thin placeholder, `working` usable with its holes listed under `## Gaps`, `solid` trust it. `fluency` grades you, and only a box promotes a note to `cold`: `unseen` you could produce none of it back, `guided` you can work through it with the note open, `cold` you have used it on a box without opening the note, `teach` you can say why it works and diagnose it when it does not. The dangerous object is a `solid` note at `fluency: unseen` — nothing about it looks wrong.

`source` records where the material came from, because that cannot be recovered later: `thm` and `htb` the platform it was learned on, `lab` your own synthesis or your own lab rather than one room, `field` a real engagement, `reading` documentation, books and write-ups.

**Folders — one axis.** The tree answers *what is in front of me*; the spines answer *what am I trying to do*.

```text
Start-Here.md         this note
vault-check.py        the linter
Workflow/             the decision layer — the phase map, the methods, the checklists
Techniques/           the attacks, grouped by the surface they attack
    Web/                 the application
    Services/            a service on a port
    Linux/  Windows/     the host itself
    Active-Directory/    the domain
    Cloud/               cloud identity and services
Operations/           spent on any target in any phase — shells, transfer, pivoting, looting
    Tools/               flag references, one per tool
Reference/            lookup material that is not a technique
```

Name the surface the technique attacks and file it there. Attacks no single surface **and** spent in more than one phase → `Operations/`, `platform: any`. Every folder declares the `type` and `platform` its notes must carry, so a misfiled note fails the run. The order above is not alphabetical, and Obsidian sorts alphabetically — the Custom File Explorer sorting plugin holds it, reading the bookmark group named `sortspec` in `.obsidian/bookmarks.json`.

**Four layers per command.** Every section carrying a command carries these, in order: **Why now** (what you already hold that makes this the next move — if you cannot write it, you do not need the command yet) · the command **and the flag that is easy to omit**, with the failure omitting it produces · **What you will see**, four outcomes, Found / Empty / Error / Noise · **Then**, a destination for each outcome, Empty included. A step whose Empty branch names nothing is a dead end.

**Entrances are placed, not named.** `Start-Here` sits loose at the Playbook root; the two run sheets sit at the top of their own folders, held there by the `sortspec` bookmark group rather than by alphabetical order. The `explorer-marks.css` snippet then sets every folder, at every depth, in bold near-black, while every note — those three included — keeps the theme's own colour and weight, so the skeleton stands out and the notes hanging off it do not. Filenames stay ordinary throughout, because a filename is for scripts and links while a colour is for the eye.

**Naming.** Filenames are `Title-Case-With-Hyphens`, because the vault gets scripted and lives in git, and Obsidian resolves hyphenated wikilinks happily. No all-lowercase filename anywhere — a tool note is capitalised even when the tool is not (`PSPY`, `TheHarvester`, `873-rsync`), while the tool's own spelling stays intact in prose and in every command. Service notes are `PORT-Service` with an H1 of `PORT — Service`. Otherwise the H1 may enrich the filename — expand an acronym, add a CVE, add scope after an em-dash — but never reorder or abbreviate it.

**Technique vs tool.** A technique note describes the attack and may name several tools; a tool note is a flag reference, and only exists when the flag surface is wide enough to earn a page — `nmap` earns one, `host` does not. When in doubt it is a technique note.

**Links.** Every note links to at least one non-index note; that is what `## Next` is for, and it holds one to three *directional* links — where you go once this note has done its job.

**Callouts, three and no more.** `> [!important]` a correction or limit that costs time if missed · `> [!warning]` destructive or irreversible · `> [!note]` context.

**Unfinished has exactly two markers.** A thin whole note → `status: seed`. A specific hole in a good note → a line under `## Gaps`. Nothing else, so one command finds all of it. A complete note correctly has no `## Gaps` section at all — leave a section out rather than pad it.

**Core first, rare below the fold.** A note with a wide command surface ends its steps with `## Rarely — worth one command, not worth a step`: commands that pay rarely and do not deserve a place in the order. One **Why now**, one **What you will see** with all four outcomes and one **Then** cover all of them together. Nothing is deleted to shorten a note — the rarely-needed half moves down here. A thin note gets no such section, because padding it would break the rule above.

## The note skeleton

Copy this into a new technique, service or tool note. Workflow and reference notes do not use it. A workflow note's commands still owe the four layers; a reference note is looked up, not run step by step, and is exempt from them.

<!-- dup-ok -->
````markdown
---
type: service
platform: windows
status: working
fluency: unseen
source: htb
updated: 2026-09-08
---

# <Name>

<One line: what this is, and the moment in an engagement it belongs to.>

## <The question this step answers>

**Why now** — <what you already hold that makes this the next move.>

```bash
<command>
```

- `<flag>` → <what it does>
- `<flag>` → <the one that is easy to omit, and the failure omitting it produces>

**What you will see**

- **Found** — <the shape of a real hit, concretely>
- **Empty** — <clean host, or not permitted to see it. Say which.>
- **Error** — <the specific errors, and what each is telling you>
- **Noise** — <what looks like a hit and is not>

**Then** — <where each outcome sends you, Empty included.>

## Reading the output

<Only what spans the whole note: how two findings combine, what it cannot see.>

## Next

- [[<note>]] — <why you go there after this one>

## Gaps

- <what this note does not cover>
````

## What the linter enforces

`python3 vault-check.py` from the Playbook root; exit code 0 when clean. The pre-commit hook runs it on every commit and prints the failing families, but it warns rather than blocks — the commit always goes through. Before linting, the hook runs `--stamp`, which sets `updated` to today on every staged note whose body changed, so the date is never yours to remember. Worth knowing before you write:

- **Filter, do not dump.** Whatever you would put under **Noise**, put in the command instead. Name the discriminator and why it discriminates, say what the filter can hide, and give the expected count. A deliberate unfiltered baseline is marked `<!-- raw-ok -->`.
- **One runnable command per fence** — the copy button takes the whole block. A command spanning several lines is still one command; a stacked flag reference in a `text` fence still fails.
- **Four layers on every command section**, all four outcomes labelled. A catalog of interchangeable payloads is exempt with `<!-- layers-ok -->`.
- **One source line per paragraph**, nothing over 120 words. `python3 vault-check.py --unwrap <file>` repairs a file that drifted.
- **Jargon needs an entry** in one of the A–Z reference notes.
- The rest run without your help: broken links, orphans, duplicate filenames, unresolved anchors, the two-hop rule, frontmatter schema, folder placement, heading structure, the callout vocabulary, invisible characters, room residue, English-only prose, lexicon drift, repeated code blocks, a section repeated inside one note, a missing `## Next`, a note linking only to hubs, a load-bearing note that is too thin, trailing whitespace, relative Markdown links that do not resolve, emphasis that will not render, and `updated` older than the last commit that changed the body.

The run ends with a graph line — hub links give findability, lateral links give flow, and a hub share well under half is comfortable. It is a ratio, not a score: neglect the hubs and it drops while the vault gets worse. Watch the direction over months.

## Check the vault

```dataview
TABLE WITHOUT ID
  length(filter(rows, (r) => r.status = "seed")) AS seed,
  length(filter(rows, (r) => r.status = "working")) AS working,
  length(filter(rows, (r) => r.status = "solid")) AS solid
WHERE type AND type != "index"
GROUP BY true
```

Stale, untouched for 90 days or more. A `seed` or `working` note surfacing here is the nudge.

```dataview
TABLE status, updated
WHERE type AND type != "index" AND updated <= date(today) - dur(90 days)
SORT updated ASC
```

The panels above track what exists; the script below reads the shape and the backlog. Run it whenever you have edited notes — that is most days, not once a week.

```bash
python3 vault-check.py
```

```bash
python3 vault-check.py --fluency
```

```bash
python3 vault-check.py --gaps
```

## Known backlog

`--gaps` above generates the real list from every `## Gaps` line. This is the curated short version, in rough order of how often it blocks a box.

1. **Relaying instead of cracking** — [[Authentication-Coercion]] now collects a [[Security-Terms#^netntlmv2|NetNTLMv2]] response and [[Hash-Cracking]] can crack it. Forwarding one to a second host while it is still fresh is unwritten, and it is what makes an uncrackable capture worth having.
2. **Pivoting beyond SSH** — chisel, ligolo, socat relays, for a host with no `ssh` client on it.
3. **Active Directory after the first credential** — [[BloodHound]] and [[DCSync]] are written now; delegation and forged tickets are not, and the graph draws edges for both.
4. **Reporting** — [[Pentest-Workflow#Phase 6 — Reporting|Phase 6]] is empty on purpose.
