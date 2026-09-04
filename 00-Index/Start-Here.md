---
type: index
platform: any
status: solid
fluency: guided
source: lab
updated: 2026-09-04
---

# Start Here

The entry point to the PLAYBOOK vault. Everything else is reachable from here in at most two hops.

House style and health: [[Note-Template]] · [[Vault-Health]]

---

## Before you sit down

Two minutes, once, before the first command of the evening. There is only one thing on this page, and it is the thing that ends evenings.

**An empty result has two meanings, and they want opposite next moves.** Either nothing is there, or you are not allowed to see it. On Linux those two look identical: both print nothing and both return you to the prompt. Every enumeration command you run tonight will hand you that ambiguity at least once, and treating "no output" as "nothing here" is how a live path gets crossed off the list and never revisited.

Four ways to tell them apart, cheapest first:

- **Ask the same question about something you know exists.** If `find / -name sshd_config 2>/dev/null` also comes back empty, the command is not telling you about the filesystem — it is telling you about your permissions. A control question costs one line and settles it.
- **Run it once without `2>/dev/null`.** Most commands do say `Permission denied`; the message goes to standard error, and that redirect — which nearly every one-liner carries, because otherwise the denials bury the results — throws the sentence away. The redirect is right for the second run, not the first.
- **Read the exit code.** `echo $?` immediately after: `0` means the command did its job and found nothing, anything else means it could not do its job. This is the one signal that is never ambiguous.
- **Count what was searched, not what was found.** `find / -perm -4000 2>/dev/null | wc -l` returning `0` on a live Linux host is not a finding, it is a symptom — every system has SUID binaries, so a zero means you did not get to look.

The rule that follows: **an empty result is not a finding until you have shown it is not a permission problem.** Until then it is an unanswered question, and it belongs on the list of things still to check rather than the list of things ruled out.

This is also why every command in this vault carries a **What you will see** block with a separate **Empty** line, and a **Then** block that gives Empty its own destination — see [[Note-Template]] for the shape and the [[Linux-Run-Sheet]] for it applied end to end. When output is lying to you in some other way, [[Stuck-Checklist]] has the rest.

---

## What do I do now

The entrance. Find the row that describes what you are **holding** right now — not what you are trying to achieve — and open the single note it names. Every row leads somewhere that tells you what to do with what you have, including when what you have is nothing.

| What you are holding | Open |
|---|---|
| An IP and nothing else | [[Pentest-Workflow]] — the six phases; start at Phase 1, which also says what to do when the scan comes back thin |
| A port list, and a version string you have not searched yet | [[Public-Exploit-Workflow]] — version → search → verify → modify → shell, and which step each failure belongs to |
| A shell as a low-privileged **Linux** user | [[Linux-Run-Sheet]] — eight steps, one command per block, each with what its empty result actually means |
| A shell as a low-privileged **Windows** user | [[Windows-Run-Sheet]] — the same eight questions, Windows commands, and where each hit is cashed in |
| A shell, a page of findings, and no path | step 8 of whichever sheet you are on — nothing above it is an escalation on its own; the escalation is a **pair** |
| A password with no username to try it against | [[Config-File-Looting]] — where the other half lives, and how to spend the pair |
| A domain credential — a password, 32 hex characters, or a `.ccache` file | [[AD-Authentication]] — which of the five credential shapes you are actually holding, what each one can authenticate to, and the error each wrong choice produces |
| A file you can write but do not own | [[PSPY]] — prove what runs it, then append and wait one interval |
| An error message you do not trust | [[Failure-Messages]] — the messages whose plain reading points at the wrong cause, grouped by the wrong conclusion they invite |
| Nothing works and it is one in the morning | [[Stuck-Checklist]] — flat list of what gets forgotten, every line ending in a note |

---

## The three spines

**[[Pentest-Workflow]]** — the map. Recon → Initial Access → PrivEsc → Lateral Movement → Post-Exploitation → Reporting. Each phase states what you hold entering it, the asset it produces, its exit condition, and — the part that decides whether an evening ends in a shell — where to go **if that phase produces nothing**. It links out to every technique note that serves it. This is the hub: if a note is not reachable from here, it is invisible.

**[[Linux-Run-Sheet]]** and **[[Windows-Run-Sheet]]** — the method behind Phase 3, and the commands, in one note per platform. Eight steps: who am I → who else lives here → what holds privilege → what runs → what runs on a timer → what credentials are lying around → the scanner as a second opinion → **stop and connect**. Step 8 is the step that gets skipped and the one that costs the most: a list of findings is not a path, and the escalation is always a **pair** of findings touching the same file, port or account. One command per block, so each one copies with a single click.

**[[Stuck-Checklist]]** — flat, unordered, deliberately scrappy. Read top to bottom when a box has gone quiet. Every line ends in a note, because a reminder with no destination is not usable at the hour you need one.

`01-Workflow/` also holds **method notes that are not spines** — currently [[Public-Exploit-Workflow]]. The difference is how you arrive: a spine is the method behind a whole phase and you navigate *by* it, so it belongs on this page. A method note serves one class of technique and is reached from the notes that need it. Four notes in the folder, three of them here, and nothing was forgotten.

---

## Technique indexes

- Linux privilege escalation → [[Linux-Privilege-Escalation]]
- Windows privilege escalation → [[Windows-Privilege-Escalation]]
- Shells, listeners, TTY upgrade, [[Security-Terms#^tls|TLS]] → [[Shells]]
- Turning a recovered hash into access → [[Hash-Cracking]]
- Getting network reach → [[Pivoting-and-Tunneling]]
- Moving files → [[File-Transfer]]

## Reference

- [[Security-Terms]] — domain vocabulary, A–Z. Six entries carry `^block-anchors` (e.g. `[[Security-Terms#^splice]]`) for the terms worth linking a technique note straight into; add an anchor when you first need one
- [[English-Vocabulary]] — general English encountered while studying, kept separate on purpose
- [[Failure-Messages]] — the error strings that mislead, and what each one actually means. Not a catalogue of every message: only the ones whose plain reading sends you somewhere wrong

## Tool references

Flag references, not methods. The method lives in the technique note that uses the tool.

[[Nmap]] · [[Nikto]] · [[Burp-Suite]] · [[Curl-and-Wget]] · [[TShark]] · [[TheHarvester]]

---

## Conventions

**Nothing room-specific enters the Playbook.** This outranks every other rule here, because it is the only one that cannot be repaired later. A note is written for the you who meets this technique again on a machine nobody has published a walkthrough for. What graduates is the technique, stated so it holds anywhere; the sentences a room used to teach it are not yours to keep.

Strip them as you write, not afterwards — afterwards never comes, and by then the note reads as though it were general. The phrases that survive most often:

- "we have provided you with…", "for your convenience" <!-- room-ok -->
- "deploy the machine", "this room", "answer the question" <!-- room-ok -->
- the platform's own environment — the AttackBox and friends <!-- room-ok -->
- the box's own names: `su tryhackme` is a machine's user, not a command <!-- room-ok -->

Two violations sat in this vault for a week because they were inside code spans rather than prose, where the eye does not look. `vault-check.py` now scans for exactly the wording above, which is why each of those four lines carries `<!-- room-ok -->` — that marker is the escape hatch, and those lines are also the check's live test. Its sibling `<!-- dup-ok -->` goes on the line *above* a fenced block that is deliberately repeated in a second note.

The rule still outlives the check: a linter only recognises wording it has been shown.

Box narratives, IPs, credentials and flags are simply not kept here. Strip them at the moment you write the note; if a box is worth a narrative, that narrative lives outside this vault entirely, and nothing in the Playbook ever links out to it — a link into a folder this repo does not contain breaks the moment the vault is cloned anywhere else.

**Every note opens with frontmatter.** Five fields, nothing more:

```yaml
---
type: technique        # workflow | technique | service | tool | reference | index
platform: linux        # linux | windows | web | cloud | any
status: working        # seed | working | solid
fluency: unseen        # unseen | guided | cold | teach
source: htb            # thm | htb | lab | field | reading
updated: 2026-08-26
---
```

`status` is the honest label, not an aspiration: `seed` = a placeholder, `working` = usable but thin, `solid` = trust it. `source` answers the one question you cannot recover later — is this command lab-specific or general? [[Vault-Health]] queries these fields.

**Folders — one axis, and the linter holds it there.**

The tree answers *what is in front of me*. It deliberately does not answer *what am I trying to do* — that is what the three spines above are for, and a tree that tries to answer both makes you guess twice.

```text
00-Index/        the vault's own meta notes — this one, the template, the health panel
01-Workflow/     decision layer — phases, methods, checklists
02-Techniques/   the attacks, grouped by the surface they attack
   Web/                the application
   Services/           a service on a port
   Linux/              the Linux host itself
   Windows/            the Windows host itself
   Active-Directory/   the domain
   Cloud/              cloud identity and services
03-Operations/   what you do on any target in any phase — shells, transfer, pivoting, looting
   Tools/              flag references, one per tool
04-Reference/    lookup material that is not a technique
```

**Choosing one.** Name the surface the technique attacks; file it there. When it attacks no single surface *and* is spent in more than one phase, it is an operation rather than a technique of somewhere — `03-Operations/`, where its `platform` will read `any`. That is the same test written twice, which is why the linter can check it: every folder above declares the `type` and `platform` a note inside it must carry, so a misfiled note fails the run instead of sitting there looking plausible.

Worth knowing why the rule is stated this sharply. Until 2026-08-28 the tree ran two axes at once — surface for `Web/` and `Services/`, goal for `Recon/`, `Privilege-Escalation/` and `Access-and-Movement/`. No individual note was in a wrong place; what was wrong is that the rule could not say where the *next* one went.

Discovery notes ended up spread across three folders, credential notes were filed by what they were for rather than what they attacked, and two notes with no answer at all sat loose at `02-Techniques/` root. Active Directory is the case that forced the issue: it produces enumeration, credential, escalation and persistence notes at once, and under a goal axis a single domain would have scattered across four folders on the way in.

**Note skeleton — four layers per command.** Technique, service, and tool notes follow [[Note-Template]], and since 2026-08-29 every section that carries a command carries four things, always in this order:

1. **Why now** — what you already hold that makes this the next move, and what it would add. If you cannot write this line, you do not need the command yet.
2. **The command, and the flag that is easy to omit** — with the concrete failure omitting it produces. `-h → host` carries nothing; "without this, the one hit you want scrolls off the screen" carries an hour.
3. **What you will see** — four outcomes, not one: **Found**, **Empty**, **Error**, **Noise**. Empty is the one that matters and the one every reference gets wrong: a blank result can mean the host is clean, or that you are not permitted to see the answer, and those demand opposite next moves.
4. **Then** — where each outcome sends you, Empty included. A step whose Empty branch names no destination is a dead end, and dead ends are where the hours disappear.

`## Reading the output` survives for what spans a whole note — how two findings combine, what the note as a whole cannot see. Per-command interpretation belongs in that command's **What you will see**, not there. `## Next` stays the one-to-three notes you actually reach for after this one. Leave a section out rather than pad it: an absent `## Reading` says the output is self-evident.

Workflow and index notes do not use that skeleton — they are the navigation layer and mostly carry no commands — but they answer the same shape of question: what you hold, what this produces, when you are done with it, and where you go when it produces nothing.

**Technique vs tool.** A technique note describes *the attack* and may name several tools. A tool note is a *flag reference*, and only exists when the tool's flag surface is wide enough to be worth a page of its own — `nmap` earns one, `host` does not. When in doubt it is a technique note; tools get extracted later.

**Naming.** Filenames use `Title-Case-With-Hyphens`. The hyphens stay on purpose: this vault gets scripted (`grep`, `find`, `vault-check.py`), lives in iCloud, and may end up in git — spaces in filenames make all three worse, and Obsidian resolves hyphenated wikilinks just as happily. A tool note is capitalised even when the tool itself is not, so no filename in the vault is all lowercase — `PSPY`, `TheHarvester`, `873-rsync`. The tool's own spelling stays intact in prose and in every command.

Service notes are `PORT-Service` with an H1 of `PORT — Service` — and `type: service` is what makes a note one: it is about **one port**. A technique that works against services in general rather than a particular port lives in the same folder, because the folder is the surface, but stays `type: technique` and keeps its own name.

There is none at present: banner grabbing was the last one, and it turned out to belong to [[23-Telnet]], whose client is the tool the technique was really about. Everything else: the **H1 may enrich the filename but never contradict it** — expand an acronym, add a CVE, add scope after an em-dash, but do not reorder the core phrase or abbreviate below it.

```text
XSS.md                → # Cross-Site Scripting (XSS)             expands       ok
File-Inclusion.md     → # File Inclusion (LFI / RFI)             expands       ok
pspy.md               → # pspy — Watching Processes Without Root adds scope    ok
Config-File-Looting   → # Looting Config Files                   reordered     no
Active-Directory-...  → # AD — Lateral Movement                  abbreviated   no
```

**Link rule.** Every note links to at least one non-index note — that is what `## Next` is for. A note nothing reaches and that reaches nothing is invisible; the hub is not a substitute for lateral links.

**Callouts — three, no more**

- `> [!important]` — a correction or a limit that costs time if missed
- `> [!warning]` — loud, destructive, or irreversible; think before running it on a real target
- `> [!note]` — context, including `Module not reached yet` for a deliberately empty section

**Gaps and status carry "unfinished".** A whole note that is thin → `status: seed`. A specific hole inside an otherwise good note → a line under `## Gaps`. Nothing else marks incompleteness, so one command (`vault-check.py --gaps`) or a status filter finds all of it.

A complete note with no known holes correctly has **no** `## Gaps` section — that is the "leave a section out rather than pad it" rule, not missing debt. `## Gaps` is a promise that *these specific holes* are known and deliberate; an empty one would be a worse signal than none.

**Why the Gaps sections matter.** They are the difference between a note that is incomplete and a note that is *quietly wrong*. Keep writing them.

---

## Known backlog

The full, current backlog is **generated from the notes**, not maintained by hand — every `## Gaps` line across the vault, in one list:

```bash
python3 00-Index/vault-check.py --gaps
```

Maintaining a second copy here would just drift from that one. What follows is the curated short list: the missing pieces most likely to block a box, in rough order of how often they come up. When one is written, its `## Gaps` line disappears from the generated list on its own.

1. **File upload bypass** — often the shortest route to a web shell.
2. **[[Security-Terms#^ssrf|SSRF]]** — absent from `02-Techniques/Web/` entirely.
3. **Credential capture on the wire** — Responder, [[Security-Terms#^netntlmv2|NetNTLMv2]]. [[Hash-Cracking]] can spend those hashes but nothing covers collecting them.
4. **Services with no note** — SNMP (161), [[Security-Terms#^ldap|LDAP]] (389), [[Security-Terms#^nfs|NFS]] (2049).
5. **Pivoting beyond SSH** — proxychains, chisel, ligolo, socat relays.
6. **Active Directory** — [[Security-Terms#^bloodhound|BloodHound]], delegation, [[Security-Terms#^dcsync|DCSync]], forged tickets. Authentication and [[Kerberoasting]] are written; everything that follows the first credential is not.
7. **Reporting** — [[Pentest-Workflow#Phase 6 — Reporting|Phase 6]] is empty on purpose.
