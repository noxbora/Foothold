# Linux — Local Enumeration

The five by-hand checks that map one-to-one onto the five Linux escalation notes. Each one asks a question a specific technique can answer, and each ends with the note that cashes the answer in. This is the quiet pass: five commands, no script, nothing that looks like a scan.

The ordered walk of a whole host — users, cron, credentials, the reasoning between steps — is [[Linux-Run-Sheet]]. This note is narrower on purpose: it is what you run when you have already decided which categories are still open, or when the host is monitored and a full sweep is not affordable.

> [!important]
> Every check below can come back empty, and empty is a different answer in each one. On this platform "there is nothing here" and "you are not permitted to see it" print identically, so the **Empty** line under each command is the part to read before you move on.

## What you are already allowed to do

```bash
sudo -l
```

- no flags worth learning here, but one behaviour worth knowing: `sudo -l` asks for **your own** password, not root's. Type it if you have it. With no password it still prints any `NOPASSWD` rules, so read the output before deciding the command failed.

## Files that carry privilege in their mode bits

```bash
find / -type f -perm /6000 -printf '%M %u:%g %TY-%Tm-%Td %p\n' 2>/dev/null | sort -k3
```

- `-perm /6000` → **any** of these bits set: SUID or SGID or both. The slash is the whole point. `-perm -6000` demands *all* the listed bits, so it matches only files carrying SUID **and** SGID together — a handful on a normal host — and returns almost nothing while looking like a clean result. `-perm 6000` with no prefix at all matches an exact mode and returns nothing.
- `-printf` → owner, group and date on the same line as the path, so you can judge a hit without a second command. GNU-only; a busybox `find` rejects it.
- `sort -k3` → sorts by date, which puts anything installed after the base image at one end. On a host whose stock binaries are all dated 2020, a 2026 date is the finding before you have read the path.
- `2>/dev/null` → an unprivileged walk of `/` prints hundreds of `Permission denied` lines. Drop this and the one interesting line scrolls out of the buffer.

## The same privilege, stored where `find -perm` cannot look

```bash
getcap -r / 2>/dev/null
```

- `-r` → recurse. Without it `getcap` wants an explicit list of files and silently checks nothing useful.
- `2>/dev/null` → mandatory in practice: as an unprivileged user this walks the whole filesystem and every unreadable directory emits a line.

## Whether a bare command name can be hijacked

```bash
echo "$PATH" | tr ':' '\n' | while read -r d; do [ -w "${d:-.}" ] && echo "writable: ${d:-.}"; done
```

- `tr ':' '\n'` → splits the variable into one directory per line, which is the only way to see an **empty element**. A leading `:`, a trailing `:` or a `::` in the middle means the current working directory is searched, and that is a finding needing no writable directory at all.
- `${d:-.}` → substitutes `.` for an empty element, so the test above actually evaluates the case you are hunting for instead of silently skipping it.
- `[ -w ]` → asks the kernel, not the mode bits. It accounts for your group memberships and for ACLs, which is the reason to test rather than to read `ls -ld` and reason about it.

## What is listening that a port scan could not reach

```bash
ss -tlnp | grep -E '127\.0\.0\.1|\[::1\]'
```

- The `grep` is the question. A listener on `0.0.0.0` was already in your nmap output and adds nothing; a listener on `127.0.0.1` or `[::1]` is the one that was unreachable from outside, which is the entire reason for running this. Filtering here is not tidiness — the unfiltered list mostly repeats a scan you already have.
- Drop the `grep` once, deliberately, if you want the full picture. Never read the unfiltered list first.
- `-t` → TCP; add `-u` when you also want UDP.
- `-l` → listening sockets only. Without it you get every established connection as well and the listeners are lost in the noise.
- `-n` → numeric. Without it `ss` tries to resolve every address through DNS, and on a host with no route out that hangs for a minute before printing anything.
- `-p` → the owning process. You will only see it for processes you own, which is a permission limit rather than an empty column.

## What this pass deliberately does not cover

Five checks, five categories, and three large ones left out. Naming them is the point — an enumeration note that pretends to be complete is how a host gets called clean.

- **Other users, and their files.** Who else lives here, whose home you can enter, whose keys are readable. That is steps 2 and 6 of [[Linux-Run-Sheet]].
- **Anything on a schedule.** Nothing above looks at cron, at timers, or at what runs while you are not watching. [[Cron-Jobs]] for the readable half, [[PSPY]] for the half you cannot read.
- **Credentials in files.** The single most common path on a chained host, and not a permission question at all. [[Config-File-Looting]] for what each format hides.
