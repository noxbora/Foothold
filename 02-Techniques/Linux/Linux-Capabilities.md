---
type: technique
platform: linux
status: working
fluency: guided
source: thm
updated: 2026-09-04
---

# Linux — Capabilities Abuse

The mode-bit sweep from [[Linux-Local-Enumeration]] came back stock, or came back empty. That is not the same finding as "this host has no privileged binaries" — it only closes the binaries whose privilege lives in the **permission bits**. Capabilities carry the same power somewhere `find -perm` cannot look.

Root is not one switch. The kernel splits its authority into around forty discrete privileges (`man 7 capabilities`): bind a low port, read any file, load a kernel module, change your own [[Security-Terms#^uid|UID]]. A single capability can be attached to a single binary, so that binary performs exactly one privileged operation and is otherwise unremarkable. `ping` is the honest example — it needs raw sockets, so it carries `cap_net_raw` and nothing more. The mechanism is a *reduction* of SUID's all-or-nothing grant. The vulnerability is one of those forty landing on a binary that will run your code.

## Find them

**Why now** — you have run one of the two file-privilege sweeps and it produced nothing usable. This is the other half of the same question, and it takes one command. Skipping it is how a host gets written off as clean while `cap_setuid` sits on `/usr/bin/perl`: the two sweeps are blind to each other by construction, so a stock `find -perm` result is not evidence about this at all.

```bash
getcap -r / 2>/dev/null
```

- `-r` → recurse. Without it `getcap` expects an explicit file list and checks nothing useful.
- `2>/dev/null` → mandatory in practice, not cosmetic. As an unprivileged user this walks the whole filesystem and every unreadable directory emits a line; the three findings you want scroll past inside thousands of `Permission denied`.

```text
/home/john/vim = cap_setuid+ep
/usr/bin/python3.12 = cap_setuid+ep
/usr/lib/.../gst-ptp-helper = cap_net_bind_service,cap_net_admin+ep
/usr/bin/gnome-keyring-daemon = cap_ipc_lock+ep
/usr/bin/ping = cap_net_raw+ep
```

**What you will see**

- **Found** — a line in the form `<path> = <capability>+<flags>`. The finding is always the line that does not belong: an interpreter, an editor, anything under `/home`, `/opt` or `/usr/local`, anything with a recent mtime. A binary in a user's home directory with a capability is never accidental — a capped `/usr/bin/ping` is policy, a capped `/home/john/vim` is a deliberate copy somebody made to avoid touching the packaged version.
- **Empty** — genuinely common and a real negative on this category, **but only if `getcap` actually ran**. Silence from a tool that is not installed is not a clean host, and the two outcomes look identical once the command scrolls off the screen.
- **Error** — `getcap: command not found` on a minimal image is the trap: a missing tool, not a missing finding. Try `/sbin/getcap`, which is often absent from an unprivileged `$PATH` while the binary is present. Failing that, the data is a plain extended attribute and the fallbacks below read it without the tool.
- **Noise** — `ping`, `mtr-packet`, `traceroute6` (`cap_net_raw`), `gnome-keyring-daemon` (`cap_ipc_lock`) and `gst-ptp-helper` are the stock set on a desktop image. A host showing only those is telling you the same thing as an empty sweep.

**Then** — a line with a capability that changes a UID, reads any file, or writes any file goes to the suffix check below, then to the worked case. Stock-only or empty means no *file* on this host carries privilege in either place, so the privilege is attached to a running process instead: [[PSPY]].

## When `getcap` is not there

**Why now** — the sweep above answered `command not found`, and treating that as an empty result would close a category you have not actually looked at. A capability is stored as an ordinary **extended attribute** — a named value the filesystem keeps beside a file's contents, separate from its permission bits, addressed like `security.capability` — so any tool that can read extended attributes can read it, with or without `getcap`.

```bash
getfattr -n security.capability /usr/bin/python3
```

```bash
capsh --print
```

- `getfattr -n security.capability <file>` → reads one named extended attribute off one file. `-n` selects which attribute; without it `getfattr` lists only the attributes in the `user.` namespace and never shows `security.capability` at all, which looks exactly like a clean binary. It ships in the `attr` package, so it is present on many hosts that lack `getcap`.
- `capsh --print` → answers a *different* question: which capabilities the shell you are sitting in already holds, rather than which ones a file carries. Worth running once regardless. Inside a container that line is often the whole engagement.

**What you will see**

- **Found** — from `getfattr`, a base64 blob under `security.capability`. Its presence is the finding; you do not need to decode it to know the binary is capped. From `capsh`, a `Current:` line naming capabilities your own shell holds.
- **Empty** — `getfattr` printing nothing for a file means that file carries no capability, which is a real per-file negative and not a sweep.
- **Error** — `getfattr: command not found` as well means the `attr` package is missing too, and this category cannot be enumerated on this host with the tools present. Record that as an unknown rather than a negative, and transfer a static `getcap` if the box matters: [[File-Transfer]].
- **Noise** — `capsh --print` on a normal host prints a long `Bounding set:` list. That is the set of capabilities a process *could* hold, not what you hold. Read the `Current:` line.

**Then** — a capped binary found this way rejoins the main path at the suffix check below. An unknown result here is worth carrying to [[Linux-Automated-Enumeration]], whose scripts bundle their own checks and may see what your shell cannot.

## Read the flag suffix

The part after `+` is not decoration. It decides whether you have a finding or a curiosity.

- `p` → **permitted**: the process *may* use the capability
- `e` → **effective**: it is already active the moment the binary starts
- `i` → **inheritable**: it can pass across a further `execve` — the system call that replaces a running process's contents with a new program, which is what happens every time one program starts another

`cap_setuid+ep` is the one you want — permitted *and* live at exec, so the interpreter's first line of code can already use it.

`cap_setuid+p` alone is a much weaker hand: the capability is permitted but not effective, and the program must raise it into its effective set itself — by calling `capset`, the system call that moves a capability from "allowed to use" into "in use" — before it does anything. An interpreter will not do that on your behalf. Note it and keep enumerating rather than burning an hour on it.

## Which capabilities are actually a path

Judge the finding by the verb it hands you — read, write, execute, load — exactly as in [[Linux-SUID-Abuse#The rule that decides everything|the SUID note]].

**Direct root**

- `cap_setuid` → change your UID to 0. The cleanest possible finding; worked below
- `cap_setfcap` → set capabilities on *other* files. Grant `cap_setuid+ep` to any binary you like. The same win, one step removed
- `cap_sys_module` → load a kernel module. Total, and by far the loudest thing you can do on a live engagement
- `cap_sys_ptrace` → attach to a root process and inject code into it
- `cap_sys_admin` → the near-root catch-all (mount, and a long tail of else). Almost always the finding when it appears on a container

**A read or write [[Security-Terms#^primitive|primitive]], which is still a full escalation**

- `cap_dac_read_search` → bypass every file *read* check. `/etc/shadow`, `/root/.ssh/id_rsa`, every credential file on the box. No write
- `cap_dac_override` → bypass read *and* write checks. Append your own UID 0 line to `/etc/passwd` → [[Linux-SUID-Abuse#Route B — write your own root account|Route B]]
- `cap_chown` → take ownership of any file, then edit it through normal permissions
- `cap_fowner` → bypass the ownership check on `chmod` and friends

**Not escalation — expected on a healthy host**

- `cap_net_raw` (`ping`, `traceroute6`, `mtr-packet`), `cap_net_bind_service`, `cap_net_admin`, `cap_ipc_lock` (`gnome-keyring-daemon`). These are the reason the mechanism exists. Recognise them, do not spend time on them, and do not report them as a finding.

Cross-check anything else on **[[Security-Terms#^gtfobins|GTFOBins]]**, a public catalogue of ordinary Unix binaries and the exact keystrokes each one needs to read a file, write a file, or spawn a shell when it runs with borrowed privilege. Read the block headed **Capabilities** on the binary's page rather than the `SUID` or `Sudo` block: the site separates them because the sequences are not interchangeable. `https://gtfobins.github.io/#+capabilities` is that heading pre-filtered into a list of every binary known to have one.

## Worked case — `cap_setuid` on an interpreter

**Why now** — the sweep named a binary that runs arbitrary code and the suffix is `+ep`. That is a complete escalation and the whole technique is two calls, so there is nothing to enumerate first. Run it before anything else on your candidate list.

```bash
/usr/bin/python3.12 -c 'import os; os.setuid(0); os.execl("/bin/sh", "sh", "-c", "reset; exec sh")'
```

- `-c` → Python's own flag: run this string as code. No wrapper, no editor, nothing between you and the interpreter.
- `os.setuid(0)` → **the entire exploit.** Everything else is plumbing.
- `os.execl(...)` → replace the process with a shell, now that the UID is 0.
- `reset; exec sh` → resets the terminal on the way in. Without it a shell spawned from a non-TTY context often has no prompt and dead arrow keys, which reads like a broken exploit.
- use the **exact path `getcap` printed.** `python3` and `python` may resolve to a different binary, and a capability belongs to one inode — the alias is not a synonym here.

**What you will see**

- **Found** — `uid=0(root)` from `id`, and a `#` prompt. Note that `gid` stays as your original group: `setuid` moves the user ID only. That is the expected shape, not a partial win.
- **Empty** — no empty case. Either the UID changes or an error appears.
- **Error** — `OSError: [Errno 1] Operation not permitted` from `setuid` means the capability is not in effect: usually a `+p`-only suffix, an alias instead of the capped path, or a filesystem mounted `nosuid` — a mount option, visible by running `mount` with no arguments, that tells the kernel to ignore borrowed privilege on every file under that mountpoint. It discards file capabilities exactly as it discards the SUID bit.
- **Noise** — the payload running cleanly and `id` still showing your own UID is the expensive one, because nothing failed visibly. You omitted `os.setuid(0)`, or you invoked the binary through an alias. Both fail silently.

**Then** — a root shell goes to [[Shells]] to be stabilised into a full **TTY**, a terminal device the kernel treats as interactive, which is what gives you job control (`Ctrl+C` reaching the program instead of killing your session), a working password prompt and arrow-key history. `Operation not permitted` with a `+p` suffix sends you back to the sweep for a better candidate; `+p` alone is not worth an hour.

### The same thing through an editor

**Why now** — the capped binary is not an interpreter but an editor, so it cannot run your code as its primary job. It can still reach an interpreter compiled inside it, and that interpreter runs in the same process, which is where the capability lives.

```bash
./vim -c ':py3 import os; os.setuid(0); os.execl("/bin/sh","sh","-c","reset; exec sh")'
```

- `-c` → here this is *Vim's* flag: run this Ex command at startup. The same two letters doing an unrelated job is the only thing that makes this look different from the Python case.
- `:py3` → hand the rest to Vim's embedded Python. Everything after it is the payload above, unchanged, because the target was never Vim — it was the interpreter inside it.

**What you will see**

- **Found** — the same root shell as above, opened from inside the editor.
- **Empty** — Vim opening normally with an empty buffer and no shell means the Ex command never ran. Check the quoting: the whole `-c` argument must arrive as one shell word.
- **Error** — `E319: Sorry, the command is not available in this version` means this build has no Python. Run `:version` and look for `+python3`; a stripped `vim.tiny` has none, and this route is closed on that binary.
- **Noise** — `:!sh` from inside the capped editor gives you a shell that looks fine and is not privileged. See the section below for why.

**Then** — no interpreter compiled in sends you back to the capability list above: if the capability is `cap_dac_read_search` or `cap_dac_override`, the editor's own file reads and writes are the exploit and no shell is needed.

> [!important]
> `setuid(0)` is mandatory here and optional under SUID, and skipping it is the usual reason a correct-looking payload returns your own user. A **SUID** binary starts at `euid=0` already; the fight there is keeping it across a fork. A **capability** grants no UID at all — the process starts as *you*, holding only the *right to ask*. `setuid(0)` is the asking. Once it succeeds it sets the real, effective and saved UID to 0, so the shell that follows has nothing left to drop, which is why one line does what SUID needs a worked-around escape for.

## What does not work

**Copying a capped binary elsewhere does not carry the capability.** `cp` copies contents and mode bits but not the `security.capability` extended attribute, and writing that attribute requires `CAP_SETFCAP` — which you do not have, or you would be using it instead. Work with the path `getcap` printed.

**Capabilities are not inherited across `exec` by default.** `./vim -c ':!sh'` gives you a plain user shell — the same disappointing shape as the SUID case, but for the opposite reason: nothing was dropped, the child simply never received anything. Ambient and inheritable sets exist to change this and are not something you will find set by accident.

**A `nosuid` mount ignores file capabilities too**, exactly as it ignores the SUID bit. `mount | grep <path>` before deciding the binary is broken.

## Reading the output

**The difference between an empty sweep and a missing tool is the whole reliability of this note.** `getcap -r /` printing nothing and `getcap` not existing produce the same silence in a scrolled terminal, and they are opposite findings: one closes the category, the other means you never opened it. Confirm the tool exists before believing its silence, and record "not enumerated" rather than "clean" when it does not.

**Two sweeps, one question.** Mode bits and capabilities are the two places a file can carry privilege, and neither sweep can see the other's findings. This note and [[Linux-SUID-Abuse]] are one category split across two mechanisms; running only one is the single most expensive omission in Linux enumeration.

**A silent failure is the normal failure here.** The payload runs, no error appears, and `id` shows your own UID. There is no error message to search for, so build the habit of ending every attempt with `id` rather than with the shell prompt looking right.

## Next

- [[Linux-SUID-Abuse]] — the sibling sweep; neither one sees the other's findings
- [[Shells]] — stabilise the root shell into a full TTY before working in it
- [[PSPY]] — where an empty result on both file sweeps sends you

## Gaps

- **Container capabilities.** `capsh --print` inside a container is a different and richer question — a `--privileged` container or a bare `cap_sys_admin` is a host escape, not a local escalation. Nothing in the vault covers container escape yet; see [[Linux-Privilege-Escalation]].
- **Ambient and inheritable sets** are described only well enough to explain why the default case fails. The `+i` exploitation path is not covered.
- **`cap_sys_ptrace` in practice** — the note names it; injecting into a live root process is a technique of its own and is not written up.
- **No defence-side note** — how a blue team baselines the capability set, and `fs.suid_dumpable` / `nosuid` hardening.
- Cracking the result is [[Hash-Cracking]]; `cap_dac_read_search` still stops at "you have `/etc/shadow`", and nothing in the vault takes it from there.
