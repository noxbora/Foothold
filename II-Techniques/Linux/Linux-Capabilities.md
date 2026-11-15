# Linux — Capabilities Abuse

The mode-bit sweep from [[Linux-Local-Enumeration]] came back stock, or came back empty. That is not the same finding as "this host has no privileged binaries" — it only closes the binaries whose privilege lives in the **permission bits**. Capabilities carry the same power somewhere `find -perm` cannot look.

Root is not one switch. The kernel splits its authority into around forty discrete privileges (`man 7 capabilities`): bind a low port, read any file, load a kernel module, change your own [[Security-Terms#^uid|UID]]. A single capability can be attached to a single binary, so that binary performs exactly one privileged operation and is otherwise unremarkable. `ping` is the honest example — it needs raw sockets, so it carries `cap_net_raw` and nothing more. The mechanism is a *reduction* of SUID's all-or-nothing grant. The vulnerability is one of those forty landing on a binary that will run your code.

## Find them

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

## When `getcap` is not there

```bash
getfattr -n security.capability /usr/bin/python3
```

```bash
capsh --print
```

- `getfattr -n security.capability <file>` → reads one named extended attribute off one file. `-n` selects which attribute; without it `getfattr` lists only the attributes in the `user.` namespace and never shows `security.capability` at all, which looks exactly like a clean binary. It ships in the `attr` package, so it is present on many hosts that lack `getcap`.
- `capsh --print` → answers a *different* question: which capabilities the shell you are sitting in already holds, rather than which ones a file carries. Worth running once regardless. Inside a container that line is often the whole engagement.

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

```bash
/usr/bin/python3.12 -c 'import os; os.setuid(0); os.execl("/bin/sh", "sh", "-c", "reset; exec sh")'
```

- `-c` → Python's own flag: run this string as code. No wrapper, no editor, nothing between you and the interpreter.
- `os.setuid(0)` → **the entire exploit.** Everything else is plumbing.
- `os.execl(...)` → replace the process with a shell, now that the UID is 0.
- `reset; exec sh` → resets the terminal on the way in. Without it a shell spawned from a non-TTY context often has no prompt and dead arrow keys, which reads like a broken exploit.
- use the **exact path `getcap` printed.** `python3` and `python` may resolve to a different binary, and a capability belongs to one inode — the alias is not a synonym here.

### The same thing through an editor

```bash
./vim -c ':py3 import os; os.setuid(0); os.execl("/bin/sh","sh","-c","reset; exec sh")'
```

- `-c` → here this is *Vim's* flag: run this Ex command at startup. The same two letters doing an unrelated job is the only thing that makes this look different from the Python case.
- `:py3` → hand the rest to Vim's embedded Python. Everything after it is the payload above, unchanged, because the target was never Vim — it was the interpreter inside it.

> [!important]
> `setuid(0)` is mandatory here and optional under SUID, and skipping it is the usual reason a correct-looking payload returns your own user. A **SUID** binary starts at `euid=0` already; the fight there is keeping it across a fork. A **capability** grants no UID at all — the process starts as *you*, holding only the *right to ask*. `setuid(0)` is the asking. Once it succeeds it sets the real, effective and saved UID to 0, so the shell that follows has nothing left to drop, which is why one line does what SUID needs a worked-around escape for.

## What does not work

**Copying a capped binary elsewhere does not carry the capability.** `cp` copies contents and mode bits but not the `security.capability` extended attribute, and writing that attribute requires `CAP_SETFCAP` — which you do not have, or you would be using it instead. Work with the path `getcap` printed.

**Capabilities are not inherited across `exec` by default.** `./vim -c ':!sh'` gives you a plain user shell — the same disappointing shape as the SUID case, but for the opposite reason: nothing was dropped, the child simply never received anything. Ambient and inheritable sets exist to change this and are not something you will find set by accident.

**A `nosuid` mount ignores file capabilities too**, exactly as it ignores the SUID bit. `mount | grep <path>` before deciding the binary is broken.
