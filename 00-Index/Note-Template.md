---
type: index
platform: any
status: solid
fluency: guided
source: lab
updated: 2026-09-08
---

# Note Template

The shape every technique, service, and tool note follows. Copy the block below into a new note and fill what applies. The rule that keeps the vault honest: **leave a section out rather than pad it.** An empty `## Reading` is a claim that the output is self-evident; a `- -u → target URL` line is proof the section should not be there.

Workflow, reference, and index notes do **not** use this skeleton — they have their own shape.

## Two grades, and they are independent

`status` grades the note. `fluency` grades you. They move separately, and the gap between them is the only thing in the frontmatter that predicts a lost afternoon: a `solid` note at `fluency: unseen` looks finished from every angle and will still leave you reading it for the first time on a live box.

Each value is defined by something you have done, never by how a note feels when you read it.

- `unseen` — you have not read it, or you have read it and could produce none of it back.
- `guided` — you can work through it with the note open in front of you.
- `cold` — you have used it on a box without opening the note.
- `teach` — you can say why it works, and diagnose it when it does not.

One rule keeps the field honest, and it is the same rule that keeps `status` honest: **only a box promotes a note to `cold`.** Reading it again does not, revising it does not, and neither does recognising it in a write-up. `guided` is where an unfinished note is supposed to sit, and there is no shame in a vault that is mostly `guided` — there is only a problem in a vault that claims otherwise.

`python3 00-Index/vault-check.py --fluency` ranks everything below `cold` by how many notes point at it, which turns the field into next week's DOJO mats instead of a number nobody reads.

## The skeleton

Every section that carries a command carries **four layers**, always in this order. A command without them is not a note — it is a man page you already had.

````markdown
---
type: service          # workflow | technique | service | tool | reference | index
platform: windows      # linux | windows | web | cloud | any
status: working        # seed | working | solid
fluency: unseen        # unseen | guided | cold | teach
source: htb            # thm | htb | lab | field | reading
updated: 2026-08-29
---

# <Name>

<One line: what this is, and the moment in an engagement it belongs to.>

## <The question this step answers>

**Why now** — <what you already hold that makes this the next move, and what you are hoping to learn. If you cannot write this line, you do not need the command yet.>

```bash
<command>
```

```bash
<the next command, in its own block>
```

- `<flag>` → <what it does>
- `<flag>` → <the one that is easy to omit, and the failure omitting it produces>

**What you will see**

- **Found** — <what a real hit looks like, concretely: the shape of the line, the words in it>
- **Empty** — <what nothing means here. Sometimes "clean host", sometimes "you are not allowed to see it" — those are different answers and the note must say which>
- **Error** — <the specific errors this command produces and what each one is telling you>
- **Noise** — <what looks like a hit but is not: defaults, documentation, placeholders>

**Then** — <where each of those outcomes sends you: a named next step in this note, or a [[note]]. Every outcome needs a destination, including Empty.>

## Reading the output

<Only for what spans the whole note: how two findings combine, what the note as a whole cannot see. Per-command interpretation lives in its own **What you will see** block, not here.>

## Next

- [[<note>]] — <why you go there after this one>

## Gaps

- <what this note does not cover>
````

## What each layer is for

**`**Why now**`** — the layer the vault was missing until 29 Aug 2026, and the reason a page of correct commands was still unusable. A command is an answer; this line is the question. It names what you are already holding — a shell, a port, a filename, a password with no user attached — and what this command would add to it. Two effects: you stop running commands in an order you half-remember, and when the output arrives you already know what you were asking, so you can tell whether you got it.

**The command and its flags** — every flag that changes the result, and specifically the flag that is easy to leave off, with the failure it produces when you do. `-h → host` carries nothing. "`put` without a second argument sends the full local path as the remote filename and the server answers 553, which reads exactly like a permission denial" carries an hour.

**`**What you will see**`** — four outcomes, not one. **Found** describes the hit concretely enough to recognise it in a screen of text. **Empty** is the one that matters most and the one every reference gets wrong: a blank result can mean the host is clean, or that you are not permitted to see the answer, and those lead to opposite next moves.

**Error** names the actual error strings. **Noise** names what will look like a find and is not — stock entries, commented examples, placeholder values — because a false positive costs the same time as a miss. Anything you write in Noise that could have been a filter is a bug in the command above it; see the next section.

**`**Then**`** — every outcome gets a destination, Empty included. This is what turns a list of commands into a path: you always know where you go from here, so you are never standing in a terminal wondering what to type next. A step whose Empty branch has no destination is a dead end, and dead ends are where two hours disappear.

## Filter, do not dump

**Whatever you would write in `**Noise**`, put in the command instead.** A note that prints two hundred rows and then explains, underneath, which hundred and ninety to ignore has handed the eliminating back to the reader at the exact moment they are least able to do it — mid-box, tired, with a terminal full of output. The knowledge of what is stock is the valuable part of the note, and knowledge belongs inside the command, not in a paragraph beside it.

Every sweeping command therefore carries its own discriminator:

- Name the discriminator, and say **why** it discriminates. "Microsoft's components live under `C:\Windows\`; anything installed afterwards does not." "The distribution's binaries live in `/bin`, `/sbin`, `/usr/bin`; a planted one does not." "Package unit files live in `/lib/systemd/system`; a person's live in `/etc/systemd/system`." The reason is what lets you adapt the filter on a host that breaks the assumption.
- Say **what the filter would hide**, when it can hide something. The SUID exclusion list hides a planted binary wearing a stock name; the note has to say so, and say to re-run without it when the filtered result is empty.
- Say **what it looks like when the filter silently does nothing** — that is the failure mode unique to filtering, and it is invisible. `-notlike "\Windows\*"` against a `PathName` that starts with `C:` excludes zero rows; you read two hundred lines believing you filtered.
- Give the expected count. "21 files in, 0-2 out" tells the reader immediately whether the command worked.

A deliberately unfiltered baseline is allowed — reading the whole list once on a host you are learning is a real reason — but it is marked `<!-- raw-ok -->` above the fence and the note says why. `vault-check.py` enforces this: a sweeping command with nothing narrowing it and no exemption fails the run.

## One command per block

Every code fence holds **exactly one runnable command**. Obsidian's copy button copies the whole fence, so two commands in one block means neither can be taken alone — you end up selecting text with the mouse, inside the backticks, at the moment you least want to. It is also the only visual boundary a reader has: with four commands stacked in one block, nothing says where one ends and the next begins.

One command may still span several lines when the command itself does — a backslash continuation, a pipeline broken for width, a heredoc. That is one command and it stays in one block.

A catalog of interchangeable payloads is the same rule for the same reason: one block each, so a single click takes the one you picked. `vault-check.py` enforces this.

A fence tagged `text` does not escape the rule. Four variants of one tool stacked as a flag reference are still four commands you would want to take one at a time — give each its own block and tag it `bash`. What a `text` fence is for is everything you would *not* run: output samples, tables, diagrams, comparison lines with an arrow, and the flagless verbs you type inside an interactive client (`get`, `lcd /tmp`, `SHOW DATABASES;`). The linter judges these by shape — a binary name followed by a flag — so a stacked flag reference fails and an output sample does not.

## One line per paragraph

Do not hard-wrap prose. Obsidian renders a single newline as a real line break unless "Strict line breaks" is switched on, so a paragraph broken at a fixed column shows up ragged in reading view — the last word of each source line stranded against the right margin, and zooming does not repair it because the break is in the file.

Write each paragraph, each list item and each callout body as ONE source line and let the reader's window do the wrapping. A callout's marker line (the `[!important]`, `[!warning]` or `[!note]` line) keeps its own line, because text joined onto it becomes the callout title instead of its body. Code fences and tables are exempt: their line breaks are content. `vault-check.py` enforces this, and `python3 00-Index/vault-check.py --unwrap <file>` repairs a file that drifted.

One source line is not a licence for one enormous line. A paragraph over 120 words is a wall on a phone screen, and the linter fails it — break the thought where it turns, not where the margin happens to fall.

## Where the note goes

Decide this before you write a line, because it is the one thing that is annoying to change later. Name the **surface** the technique attacks and file it there:

```text
02-Techniques/Web/                the application
02-Techniques/Services/           one port (`type: service`, named `PORT-Service`), or a
                                  technique against services in general
02-Techniques/Linux/              the Linux host itself
02-Techniques/Windows/            the Windows host itself
02-Techniques/Active-Directory/   the domain
02-Techniques/Cloud/              cloud identity and services
03-Operations/                    no single surface, and spent in more than one phase
03-Operations/Tools/              a flag reference for one tool (`type: tool`)
```

`03-Operations/` is the tie-breaker, not the overflow drawer: a note lands there when it attacks nothing in particular **and** gets used in more than one phase — which is the same thing `platform: any` says, so the two always agree. If only one of the two is true, it belongs to a surface.

`vault-check.py` enforces this, so a note filed in the wrong folder fails the run instead of quietly sitting there. Getting it right now costs one thought; getting it wrong costs a move, a date, and a commit.

## Filling Reading and Next over time

Do not backfill these in a marathon. The rule that costs nothing: **if you opened a note, fill its `## Next` before you close it** — you were just reasoning about where to go anyway. `## Reading` accretes the same way, one real box at a time.
