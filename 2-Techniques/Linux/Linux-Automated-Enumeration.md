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

```bash
file /tmp/linpeas.sh
```

```bash
head -1 /tmp/linpeas.sh
```

- `file` → the one check that separates a real script from a saved GitHub *page*. HTML instead of a shell script is the standard trap, and it produces `syntax error near unexpected token '<'` the moment you run it — a message that sends most people debugging the shell rather than the file.
- `head -1` → a shell script starts with `#!/bin/sh` or `#!/bin/bash`. A first line of `<!DOCTYPE html>` is the same failure `file` catches, confirmed a second way.
- fetch the **raw** asset, not the repository page. On GitHub that is the `raw.githubusercontent.com` URL or the release binary, never the `github.com/.../blob/...` link.

## Run linPEAS, and keep the transcript

```bash
./linpeas.sh -a 2>&1 | tee /tmp/.lp.out
```

- `-a` → all checks, including a short process watch and a harder hunt for hashes in files. Slow, and worth it on a box you are not in a hurry on. Drop it with `-s` for the fast, stealthier subset when the host is monitored.
- `tee` → writes a copy to disk while it scrolls past. This is the flag you regret omitting: the output does not fit in a terminal buffer, and re-running the whole sweep to see the top of it is minutes you did not need to spend.
- read it back with `less -r`, not plain `less`. The `-r` preserves the [[Security-Terms#^ansi|ANSI]] colour that carries the entire ranking; without it every highlight is stripped and you are reading an unranked wall.

## When linPEAS is too loud — lse by level

```bash
./lse.sh -l0 -i
```

- `-l0` → level 0, only what is highly important. An empty level 0 is a real negative on the loudest vectors, not a failure to look hard enough, which is the whole point of starting here.
- `-i` → non-interactive; required when piping or when there is no TTY. Without it `lse` waits for a keypress that a non-interactive shell can never send, and it looks like a hang.
- raise to `-l1` for interesting results and `-l2` for everything, only if the level below came back empty.

## When the kernel looks old — LES

```bash
./linux-exploit-suggester.sh --uname "$(uname -a)"
```

- `--uname "$(uname -a)"` → assess a kernel string you can even copy off the target and run on your own machine; nothing has to execute on the box. Useful when the target cannot run the script at all.
- without arguments it reads the local `uname` and does the same comparison.
- `--checksec` → reports kernel hardening ([[Security-Terms#^kaslr|KASLR]], stack protector) as `[ Enabled ]` / `[ Disabled ]`, which tempers how much faith to put in any suggested exploit.
