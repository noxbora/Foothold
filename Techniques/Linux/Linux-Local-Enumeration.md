---
type: technique
platform: linux
status: working
fluency: guided
source: lab
updated: 2026-09-04
---

# Linux — Local Enumeration

The five by-hand checks that map one-to-one onto the five Linux escalation notes. Each one asks a question a specific technique can answer, and each ends with the note that cashes the answer in. This is the quiet pass: five commands, no script, nothing that looks like a scan.

The ordered walk of a whole host — users, cron, credentials, the reasoning between steps — is [[Linux-Run-Sheet]]. This note is narrower on purpose: it is what you run when you have already decided which categories are still open, or when the host is monitored and a full sweep is not affordable.

> [!important]
> Every check below can come back empty, and empty is a different answer in each one. On this platform "there is nothing here" and "you are not permitted to see it" print identically, so the **Empty** line under each command is the part to read before you move on.

## What you are already allowed to do

**Why now** — you have a shell and nothing else. Before hunting for a weakness, find out what this account was *granted*, because a single sudo rule ends the box with no exploit at all and finding out costs one second. Everything else on this page is worth doing only if this comes back closed.

```bash
sudo -l
```

- no flags worth learning here, but one behaviour worth knowing: `sudo -l` asks for **your own** password, not root's. Type it if you have it. With no password it still prints any `NOPASSWD` rules, so read the output before deciding the command failed.

**What you will see**

- **Found** — two blocks. A `Defaults` line naming `env_reset`, `secure_path=` or `env_keep+=LD_PRELOAD`, and a command list in the form `(run-as) TAG: /path/to/binary`. Both matter: the command list says what you may run, the Defaults line says which techniques against it are open.
- **Empty** — `user is not allowed to run sudo on <host>` is genuine and common. It closes this category cleanly and closes nothing else.
- **Error** — `sudo: a password is required` in a shell where you cannot type one means there is no terminal attached, not that you lack the right. Upgrade the shell and run it again; the answer is still there. `sudo: command not found` on a minimal image means the whole category does not exist on this host.
- **Noise** — `(root) NOPASSWD: /usr/bin/sudoedit` and similar packaging entries appear on some managed hosts and lead nowhere. Judge an entry by what the binary lets you *reach*, not by the word `NOPASSWD`.

**Then** — any entry at all goes to [[Linux-Sudo-Abuse]], including a read-only binary: `cat` as root is every hash on the host. Empty goes to the next check; a `secure_path=` in the Defaults line is worth carrying to the search-path check below, because it closes that vector for sudo specifically.

## Files that carry privilege in their mode bits

**Why now** — sudo was closed, so the grant is not in a policy file. The next place privilege hides is in the filesystem: a binary that runs as its owner rather than as you. This is one walk of the whole filesystem and it answers the entire SUID and [[Security-Terms#^sgid|SGID]] category at once.

```bash
find / -type f -perm /6000 -printf '%M %u:%g %TY-%Tm-%Td %p\n' 2>/dev/null | sort -k3
```

- `-perm /6000` → **any** of these bits set: SUID or SGID or both. The slash is the whole point. `-perm -6000` demands *all* the listed bits, so it matches only files carrying SUID **and** SGID together — a handful on a normal host — and returns almost nothing while looking like a clean result. `-perm 6000` with no prefix at all matches an exact mode and returns nothing.
- `-printf` → owner, group and date on the same line as the path, so you can judge a hit without a second command. GNU-only; a busybox `find` rejects it.
- `sort -k3` → sorts by date, which puts anything installed after the base image at one end. On a host whose stock binaries are all dated 2020, a 2026 date is the finding before you have read the path.
- `2>/dev/null` → an unprivileged walk of `/` prints hundreds of `Permission denied` lines. Drop this and the one interesting line scrolls out of the buffer.

**What you will see**

- **Found** — an `s` in the owner execute slot (SUID) or the group slot (SGID), on a path under `/opt`, `/usr/local`, or a home directory; or on an interpreter, an editor, a pager or a compression tool anywhere. A capital `S` means the set-bit is on but the execute bit is not — you cannot run it, so it is a misconfiguration rather than a path.
- **Empty** — suspicious rather than clean. Every Linux host ships a dozen SUID binaries, so a completely empty result almost always means the `-perm` argument was wrong, not that the host is hardened. Re-run it as `find / -type f -perm -4000 2>/dev/null` and compare before you believe it.
- **Error** — `find: unknown predicate '-printf'` is busybox; drop the `-printf` and `sort` and read the paths alone. `Permission denied` lines appearing anyway means the `2>/dev/null` was attached to the pipeline rather than to `find`.
- **Noise** — `passwd`, `su`, `sudo`, `mount`, `umount`, `ping`, `chsh`, `chfn`, `newgrp`, `gpasswd`, `pkexec` are stock on nearly every host and are not findings. On the SGID side, `wall`, `write`, `ssh-agent`, `expiry` and `crontab` are equally standard.

**Then** — a non-stock hit goes to [[Linux-SUID-Abuse]], which is also where the rule that decides what the binary is *worth* lives. A hit owned by a service account rather than root is still worth taking; it is a lateral move, not a dead end. Empty, or stock-only, goes to the capability check below — not to the next category, because these two sweeps are structurally blind to each other.

## The same privilege, stored where `find -perm` cannot look

**Why now** — the mode-bit sweep came back stock. That closes binaries whose privilege lives in the permission bits and nothing more. A capability is a slice of root attached to a binary through an extended attribute, so a capped interpreter shows an entirely ordinary `-rwxr-xr-x` and appears in no `-perm` sweep ever run. This is the second half of one question, not a separate category.

```bash
getcap -r / 2>/dev/null
```

- `-r` → recurse. Without it `getcap` wants an explicit list of files and silently checks nothing useful.
- `2>/dev/null` → mandatory in practice: as an unprivileged user this walks the whole filesystem and every unreadable directory emits a line.

**What you will see**

- **Found** — a line in the form `/path/to/binary = cap_setuid+ep`. The suffix decides its value: `+ep` is permitted **and** effective at exec, which is the usable case. Anything on an interpreter, an editor, or a path under `/home` or `/usr/local` is the finding.
- **Empty** — genuinely common and a real negative, but only if `getcap` exists. Silence from a tool that is not installed is not a clean host.
- **Error** — `getcap: command not found` is the trap. It is a missing tool, not a missing finding, and it leaves you blind to this entire class. Try `/sbin/getcap` first, then read the attribute directly with `getfattr -n security.capability <file>`.
- **Noise** — `ping`, `mtr-packet`, `traceroute6` (`cap_net_raw`), `gnome-keyring-daemon` (`cap_ipc_lock`) and `gst-ptp-helper` are the stock set. They are the reason the mechanism exists; do not spend time on them.

**Then** — any capability that grants a [[Security-Terms#^uid|UID]] change, a file read or a file write goes to [[Linux-Capabilities]], which lists which of the forty are actually a path. Empty here, with the SUID sweep also stock, means no *file* on this host carries privilege — so the privilege is attached to a process instead, and [[PSPY]] is where the next answer lives.

## Whether a bare command name can be hijacked

**Why now** — you found a privileged binary or a privileged job but cannot write the file it executes. This check asks a different question: does anything privileged resolve a helper *by name*, and is a directory on that search path writable by you. It is only worth running once you hold a trigger; on its own a writable directory is not a finding.

```bash
echo "$PATH" | tr ':' '\n' | while read -r d; do [ -w "${d:-.}" ] && echo "writable: ${d:-.}"; done
```

- `tr ':' '\n'` → splits the variable into one directory per line, which is the only way to see an **empty element**. A leading `:`, a trailing `:` or a `::` in the middle means the current working directory is searched, and that is a finding needing no writable directory at all.
- `${d:-.}` → substitutes `.` for an empty element, so the test above actually evaluates the case you are hunting for instead of silently skipping it.
- `[ -w ]` → asks the kernel, not the mode bits. It accounts for your group memberships and for ACLs, which is the reason to test rather than to read `ls -ld` and reason about it.

**What you will see**

- **Found** — a writable directory that is already on the path, printed above the system directories. Best case of all: no `export` is needed and nothing about your environment looks tampered with. `writable: .` is the strongest version of this finding.
- **Empty** — the ordinary result on a healthy host, and a real negative on the *unmodified* path only. It does not close the vector: you can still prepend a directory yourself for anything that runs in **your** shell. It does close it for anything running in root's environment, which you cannot edit.
- **Error** — no error path worth naming; the loop prints nothing when nothing matches, which is why the Empty case above needs reading carefully.
- **Noise** — `/usr/local/bin` and `/usr/local/sbin` are writable on some development images by design. Confirm the owner before treating it as a misconfiguration, and remember it still needs a privileged caller to be worth anything.

**Then** — a writable path element plus a privileged trigger goes to [[Linux-PATH-Abuse]], which covers finding the bare-name call inside the binary and the reason the privilege often evaporates in the child process. If the trigger you hold is a sudo entry and the `Defaults` line carried `secure_path=`, this vector is closed for that entry regardless of what the loop printed.

## What is listening that a port scan could not reach

**Why now** — the file-based categories are exhausted. A service bound only to the loopback interface was invisible to every scan you ran from outside, and it is often the softest thing on the host precisely because its author assumed nobody could reach it.

```bash
ss -tlnp | grep -E '127\.0\.0\.1|\[::1\]'
```

- The `grep` is the question. A listener on `0.0.0.0` was already in your nmap output and adds nothing; a listener on `127.0.0.1` or `[::1]` is the one that was unreachable from outside, which is the entire reason for running this. Filtering here is not tidiness — the unfiltered list mostly repeats a scan you already have.
- Drop the `grep` once, deliberately, if you want the full picture. Never read the unfiltered list first.
- `-t` → TCP; add `-u` when you also want UDP.
- `-l` → listening sockets only. Without it you get every established connection as well and the listeners are lost in the noise.
- `-n` → numeric. Without it `ss` tries to resolve every address through DNS, and on a host with no route out that hangs for a minute before printing anything.
- `-p` → the owning process. You will only see it for processes you own, which is a permission limit rather than an empty column.

**What you will see**

- **Found** — a socket on `127.0.0.1` or `::1` bound to a port you did not see from outside: a database, an admin interface, a language runtime. That is a service reachable only from inside the host, which is exactly what you now are.
- **Empty** — showing only the ports you already scanned from outside is a real answer and closes the internal-service route cleanly.
- **Error** — `ss: command not found` on older systems. `netstat -tulnp` is the fallback and prints the same information in a different layout.
- **Noise** — `127.0.0.53:53` is systemd-resolved on every modern Debian-family host. `631` is CUPS. Neither is a finding. A blank process column is a permission limit, not an empty result: the port is real and something is listening on it.

**Then** — a loopback service goes to [[Pivoting-and-Tunneling]] to be forwarded back to your own machine, where your normal tooling can reach it. It also goes back to the credential hunt: a database on `127.0.0.1` and a password in a config file are two halves of one finding.

## What this pass deliberately does not cover

Five checks, five categories, and three large ones left out. Naming them is the point — an enumeration note that pretends to be complete is how a host gets called clean.

- **Other users, and their files.** Who else lives here, whose home you can enter, whose keys are readable. That is steps 2 and 6 of [[Linux-Run-Sheet]].
- **Anything on a schedule.** Nothing above looks at cron, at timers, or at what runs while you are not watching. [[Cron-Jobs]] for the readable half, [[PSPY]] for the half you cannot read.
- **Credentials in files.** The single most common path on a chained host, and not a permission question at all. [[Config-File-Looting]] for what each format hides.

## Reading the output

**Five empties is a result, not a wasted pass.** Each check above closes exactly one category, and the value of running them is that the remaining categories get your whole attention instead of a share of it. Write the empties down; the position "sudo closed, no SUID, no caps, path clean, no internal services" is a specific and useful place to be, and it points hard at processes and credentials.

**None of this sees a process.** Every command above photographs disk state or socket state at one instant. A root job that runs for forty milliseconds every minute is invisible to all five and to every automated script, which is why an empty local sweep sends you to [[PSPY]] rather than to a conclusion.

**Two of the checks are structurally blind to each other.** The mode-bit sweep and the capability sweep both answer "which binary carries privilege", and neither can see the other's findings. Running one and skipping the other is the most expensive omission on this page.

## Next

- [[Linux-Sudo-Abuse]] — cash in a `sudo -l` entry, and read the Defaults line before you try
- [[Linux-SUID-Abuse]] — cash in a non-stock mode-bit hit, and learn what it is actually worth
- [[Linux-Automated-Enumeration]] — the same ground swept by script, once the noise is affordable

## Gaps

- **No `nosuid` check.** A mount option silently disables every SUID and capability finding on that filesystem, and nothing above reads `mount` to say so.
- **No group-membership check.** `docker`, `lxd`, `disk`, `adm` and `shadow` hand out root or near-root with no file involved; `id` is in [[Linux-Run-Sheet]] and has no note of its own.
- Nothing on how loud each of these is. The claim that this pass is quieter than a script is argued, not measured.
