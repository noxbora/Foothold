---
type: technique
platform: linux
status: working
fluency: guided
source: thm
updated: 2026-09-03
---

# Linux — SUID & SGID Abuse

The mode-bit sweep from [[Linux-Local-Enumeration]] returned something non-standard. This note is what to do with it: identify which bit is set, work out what the binary actually lets you *reach*, and turn a file read or a file write into root.

Linux permissions normally answer "what may **this user** do to this file". SUID (Set-User Identification) and [[Security-Terms#^sgid|SGID]] (Set-Group Identification) invert that: the file carries the privilege. A SUID binary executes with the **effective [[Security-Terms#^uid|UID]] of its owner**, not of the user running it, and a SGID binary with the effective [[Security-Terms#^gid|GID]] of its group. Owner `root` therefore means *anything that binary can do, you can do as root* — including reading and writing files your own account has no claim to. That is the design (`passwd` must write `/etc/shadow`); the vulnerability is the bit set on a binary that was never meant to carry it.

## Find them, and know which bit you found

**Why now** — you hold a shell and `sudo -l` is closed, so the privilege is not in a policy file. It may be in a mode bit. This is one walk of the filesystem, and it is the only command here that has to be run before anything else on the page makes sense.

<!-- raw-ok -->
```bash
find / -type f -perm -4000 -ls 2>/dev/null   # SUID
```

<!-- raw-ok -->
```bash
find / -type f -perm -2000 -ls 2>/dev/null   # SGID
```

Those two are the honest, unfiltered sweep and they return roughly twenty files, nearly all of them stock. Read them once on a host you are learning; after that, run the version that removes the distribution's own binaries and hands you the two lines that matter:

```bash
find / -type f \( -perm -4000 -o -perm -2000 \) -printf '%M %u %p\n' 2>/dev/null | grep -vwE 'passwd|su|sudo|mount|umount|ping|chsh|chfn|newgrp|gpasswd|pkexec|fusermount|fusermount3|ssh-keysign|ssh-agent|snap-confine|unix_chkpwd|pam_extrausers_chkpwd|utempter|polkit-agent-helper-1|dbus-daemon-launch-helper|at|crontab|wall|write|expiry|chage|dotlockfile|mlocate'
```

- The exclusion list **is** the "Noise" paragraph, moved into the command where it does the work instead of asking you to hold twenty filenames in your head while you scan.
- `%M %u %p` → mode string, owner, path. `-rws` in the mode is SUID, `-rwx...r-s` is SGID, and the owner tells you whose privilege you would be borrowing — which is the first thing you would have asked anyway.
- It hides one thing: a planted binary wearing a stock **name** in a non-stock directory. If this comes back empty, re-run without the `grep` and read the paths rather than the names.
- `-perm -4000` → the leading `-` means **"at least these bits"**, so the other permission bits are ignored. Written without it, `-perm 4000` matches only files whose mode is *exactly* `4000` — in practice nothing at all — and the empty result reads exactly like a clean host.
- `-type f` → regular files only. Directories carry SGID with a completely different meaning (new files inherit the group), and including them fills the output with results that escalate nothing.
- `-ls` → prints the `ls -l` line, so owner, group, size and date arrive in the same pass and you can judge a hit without a second command.
- `2>/dev/null` → discards the permission-denied noise from directories you cannot enter. Drop it and the one interesting line scrolls out of the terminal buffer.

> [!warning]
> A line repeated across write-ups claims `-perm -6000` lists "SUID or SGID". It does not. With the leading `-`, `find` requires **all** the listed bits, so `-6000` matches only files carrying SUID **and** SGID together — a handful on a normal host. The "either bit" form is `-perm /6000` with a slash. Run the two sweeps above separately and the ambiguity disappears.

**What you will see**

- **Found** — an `s` in the owner execute slot for SUID, or in the group execute slot for SGID. A path under `/opt`, `/usr/local` or a home directory; an interpreter, an editor, a pager or a compression tool anywhere; or a stock-looking path with a date years newer than its neighbours.
- **Empty** — from the SUID sweep, almost always a mistake rather than a finding. Every Linux host ships a dozen SUID binaries, so nothing at all means the `-perm` argument was wrong or the `2>/dev/null` swallowed the output. From the SGID sweep, a short list is normal. Genuinely empty on both, with the syntax verified, closes this category — and sends you to the capability sweep, not to the next category.
- **Error** — `find: paths must precede expression` means an argument landed in the wrong order. `Permission denied` lines appearing anyway means the redirect was attached to the pipeline rather than to `find` itself.
- **Noise** — `passwd`, `su`, `sudo`, `mount`, `umount`, `ping`, `chsh`, `chfn`, `newgrp`, `gpasswd`, `pkexec` are expected SUID on nearly every host. On the SGID side, `wall`, `write`, `ssh-agent`, `expiry` and `crontab` are equally standard. A capital `S` instead of `s` means the set-bit is on but the execute bit is not: you cannot run it, so it is a misconfiguration rather than a path.

**Then** — a non-stock hit goes to the mode column below, then to the rule that decides what it is worth. Cross-check the binary name on **[[Security-Terms#^gtfobins|GTFOBins]]** (`https://gtfobins.github.io`), a public catalogue of ordinary Unix binaries listing, for each one, the exact keystrokes that make it read a file, write a file, or spawn a shell when it runs with borrowed privilege.

Type the binary's name into its search box, open the page, and read the block headed **SUID** — that block is the sequence that works when the privilege comes from the mode bit specifically, and it is usually two lines you can paste. No page for your binary closes nothing; it only means nobody published a recipe, and the four-verb rule below still applies.

An empty or stock-only result goes to [[Linux-Capabilities]]: a capped interpreter carries the same privilege in an extended attribute — a named value stored alongside a file's contents, outside the permission bits — and appears in no `-perm` sweep ever run.

## Read the mode column

**Why now** — the sweep printed a path and you are about to decide whether it is worth an hour. Three columns on that line settle it before you touch the binary: which slot the `s` is in, who owns the file, and whether the execute bit is there at all.

```text
-rwsr-xr-x   1 root  root    188328 Apr 15  2010 /bin/nano
-rwxr-sr-x   1 root  shadow   62304 Jan  5  2016 /usr/bin/expiry
-rwSr--r--   1 root  root      8192 May 14  2017 /usr/local/bin/backup
```

- `s` in the **owner** execute slot → SUID; the process runs as the owner, `root` above.
- `s` in the **group** execute slot → SGID; it runs as the group. `shadow` is not root, but the `shadow` group reads `/etc/shadow` — judge the group by what it can reach, not by whether the word says root.
- capital `S` → the set-bit is on and the execute bit is off. Nobody can run it, including you.
- an owner that is a **service account** — a non-human account a daemon runs under, such as `www-data`, `mysql` or `backup`, normally with no password and no login shell — rather than root is still worth taking. It is a lateral move rather than an escalation, and on a chained host that is usually the intended path.

## The rule that decides everything

A SUID process runs with **euid=root, ruid=you**. That split is the whole story, because the privilege lives in the *process*, not in you:

```text
vim                    ruid=user  euid=root      <- the privilege is here
 |__ :!cmd  ->  bash   ruid=user  euid=user      <- and it dies here
```

`bash` and `dash` compare euid against ruid at startup and, when they differ, **drop euid back to ruid**. That is a deliberate defence against exactly this technique, and it is why the obvious move so often produces nothing.

> [!important]
> A SUID binary is worth exactly what it does *itself*. Read, write, search, browse, parse — in-process, still root. Shell out, `cat`, `system()`, `sh -c` — a child process, back to your own user. The moment the binary hands work to another program, the privilege evaporates at the fork.
> This is why GTFOBins having no *shell* entry closes nothing: a binary that reads any file or writes any file is already a complete escalation path. Judge it by which of the four verbs it gives you — read, write, execute, load.

## Worked case — SUID `vim`

An editor is the cleanest illustration of the rule above, because it offers both kinds of operation and only one of them keeps the privilege.

### The moves that fail

**Why now** — you have a SUID editor and the instinct is to ask it for a shell. Running these first is worth the thirty seconds, because seeing them fail is how the euid rule stops being something you read and starts being something you can predict.

```vim
:!/bin/bash
:shell
```

- `:!` → "run this as a *system* command, not as a Vim command". Without the `!`, `:/bin/bash` is a **search**: Vim's `/` looks for the text `bin/bash` in the [[Security-Terms#^buffer|buffer]] and reports it missing. An easy ten minutes.
- `:shell` → the same fork, reached through `$SHELL`.
- `-p` does not rescue it. `:!/bin/bash -p` runs as `$SHELL -c "/bin/bash -p"`, so the **outer** shell drops euid before the inner one starts and the flag arrives one process too late.

**What you will see**

- **Found** — nothing here counts as found. If `id` in that shell does show `uid=0`, the binary called `setuid(0)` internally before forking, which is unusual and means you are done.
- **Empty** — the expected outcome: a working shell prompt where `id` returns your own UID. That is confirmation of the fork-and-drop, not a failed exploit and not a false lead.
- **Error** — `E492: Not an editor command` means the leading colon or the `!` was mistyped. `Shell returned 1` after `:!` usually means the command itself failed, which tells you the fork happened and is still not privileged.
- **Noise** — the shell *looks* successful in every way: a prompt, a working `ls`, a readable home directory. Nothing about it announces that the privilege is gone. `id` is the only test.

**Then** — stop hunting for a shell at this point. The binary is still a full escalation and the route is below: use it for what it does in-process.

### The moves that work

**Why now** — the fork is closed, so use the operations the editor performs itself. Every one of these keeps the root euid because no second process is ever created.

```vim
:e /root/
:r /etc/shadow
:w /etc/passwd
```

- `:e /root/` → opens netrw, Vim's own file browser. It is a plugin, not a program: it never forks, so it lists a directory your shell cannot enter.
- `:r <file>` → reads a file into the current buffer, as root.
- `:w <file>` → writes the buffer out, as root. This is the write half of the primitive and it is what Route B below uses.

**What you will see**

- **Found** — a directory listing for `/root/`, or the contents of `/etc/shadow` appearing in the buffer. While you are in `/root/` the flag file is rarely the valuable thing — `.bash_history` and `.ssh/` are.
- **Empty** — a directory that really is empty. Rare on `/root`, and worth a second look at the path before believing it.
- **Error** — `E484: Can't open file` does **not** distinguish *missing* from *unreadable*. Browse the directory with `:e` and read the real filename before concluding you hit a permission wall; a file named for the box is not named `flag.txt`. `E212: Can't open file for writing` on `:w` means the SUID bit is not doing what you assumed — check that the `s` was in the owner slot and that the filesystem is not mounted `nosuid`, a mount option (visible by running `mount` with no arguments) that tells the kernel to ignore the SUID bit on every file under that mountpoint, so the binary runs as you no matter what the mode column claims.
- **Noise** — netrw renders an unreadable directory and an empty one almost identically. The header line at the top of the netrw buffer carries the real path; read it.

**Then** — a successful read of `/etc/shadow` goes to Route A below. A successful write goes to Route B, which is faster and does not depend on a wordlist.

### The one reliable shell escape

**Why now** — you would still rather have a shell than a file primitive, and there is exactly one way to get it: run code *inside* the process instead of beside it.

```vim
:py3 import os; os.setuid(0); os.system("/bin/bash")
```

- `:py3` → hands the rest of the line to the Python interpreter compiled into Vim. Check `:version` for `+python3` (or `+lua`, `+perl`) first — in that feature list a leading `+` means the feature is compiled in and a leading `-` means it is not, so `-python3` closes this route on this binary; a stripped `vim.tiny` has none of them.
- `os.setuid(0)` → sets the **real** UID to 0, which is permitted precisely because euid is already 0. After it, ruid == euid == 0 and the shell that spawns has nothing left to drop. This is the step that converts a fragile euid into a real one, and omitting it puts you back in the failing case above.

**What you will see**

- **Found** — a shell where `id` returns `uid=0(root) gid=0(root)`.
- **Empty** — no such outcome; either a shell appears or an error does.
- **Error** — `E319: Sorry, the command is not available in this version` means the interpreter was not compiled in, and this route is closed on this binary. A Python `OSError: [Errno 1] Operation not permitted` from `setuid` means the process is not actually running as root — re-check the mode bits and the mount options.
- **Noise** — a shell that opens and immediately closes is a non-interactive context rather than a permission problem. Use a reverse shell there instead: [[Shells]].

**Then** — a root shell goes to [[Shells]] to be stabilised into a full **TTY** — a terminal device the kernel treats as interactive, which is what gives you job control (`Ctrl+C` and `Ctrl+Z` reaching the program instead of killing your session), a working password prompt, arrow-key history and a window that resizes. No interpreter means falling back to the file primitive and Route B.

## Worked case — turning a read or write into root

**Why now** — the binary opens arbitrary files as root and gives you no shell. That is not a lesser finding; it is a complete escalation with two routes out, and the choice between them is about noise and time rather than about power. This is the general pattern for any read or write [[Security-Terms#^primitive|primitive]], editor or not.

### Route A — take the hashes and crack them elsewhere

**Why now** — the binary opens any file as root and you have decided to take something away rather than change anything on the host. `/etc/shadow` — the root-only file holding one line per account, each carrying that account's password hash — is the highest-value file that read reaches: it turns a file-read primitive into every account's password, spent later and on your own machine rather than on the target.

```bash
nano /etc/shadow
```

```bash
nano /etc/passwd
```

- both files, not just `shadow` → the hashes live in one and the usernames and UIDs in the other. `/etc/passwd` is world-readable and lists every account as `name:x:UID:GID:comment:home:shell`; the `x` in field 2 is a pointer meaning "the hash is in `/etc/shadow`", which is the split this pair of files exists to create. Every cracking tool wants them joined again. Copying out only `/etc/shadow` means going back for the second file later, usually after the shell has died.
- this route writes nothing to the target: no file changed, no account created, nothing for a defender to trip over.

**What you will see**

- **Found** — lines of the form `root:$6$...:19000:0:99999:7:::`. A `$6$` prefix is [[Security-Terms#^sha|SHA-512]] crypt, `$1$` is [[Security-Terms#^md5|MD5]] crypt, `$y$` is yescrypt. That prefix decides the cracking mode.
- **Empty** — a `shadow` file whose password fields are all `*` or `!` means every account is locked or authenticates elsewhere. That is a genuine dead end for this route and sends you to Route B.
- **Error** — `Permission denied` opening `/etc/shadow` through the SUID binary means the bit is not in effect: either the `s` was in the group slot with a group that cannot read it, or the filesystem is mounted `nosuid`.
- **Noise** — service accounts with `!` or `*` fill most of the file. Only lines with a real `$` hash are worth carrying away.

**Then** — the hashes are **input**, not access. Formats, modes and wordlist choice are [[Hash-Cracking]]. A long root password will not fall to a wordlist, so start Route B in parallel rather than waiting on the crack.

### Route B — write your own root account

**Why now** — the same primitive used the other way. Route A leaves you waiting on a crack that a long root password will never give up; this route needs no wordlist at all, because you choose the password before you write it. Faster, and it never fails on password strength — paid for by a change to a critical system file, which is what the warning at the end of this route is about.

```bash
openssl passwd -6 -salt sec 'Passw0rd!'
```
```text
$6$sec$HF9bViGHNNZuM57aDC.eGxWKnnHHqD57pDy1AMB.BepyS7a8vxh9bDv79Ou800CnAw3w9JYtBLMj3F3h3rjVt1
```

- `-6` → SHA-512 crypt, which every current Linux accepts. `-1` produces MD5 crypt, which is weaker but still honoured on older hosts if `-6` is rejected.
- `-salt` → a fixed salt so the output is reproducible while you are testing. Any value works; it is not a secret and it is stored in the hash in clear.
- single quotes around the password → stop your local shell expanding `!`, `$` and backticks before `openssl` ever sees the string. An unquoted `!` in an interactive bash is a history expansion and produces a hash for a password you did not choose.

Append one line to `/etc/passwd` using the SUID editor, since only root may write it:

```text
hacker:$6$sec$HF9bV...rjVt1:0:0:root:/root:/bin/bash
```

- **field 2** — normally `x`, meaning "the hash lives in `/etc/shadow`". A hash placed here directly is still honoured, and that is the entire trick.
- **fields 3 and 4** — UID and GID. `0:0` *is* root; the username is cosmetic.
- **field 7** — the login shell. `/bin/bash`, not `/bin/false`, or the account exists and cannot be used.

**What you will see**

- **Found** — `su hacker` accepts the password and `id` returns `uid=0(root)`. `su` is a fresh process authenticating normally, so nothing about the euid rule applies here — this route sidesteps the fork problem rather than fighting it.
- **Empty** — no empty case; the account either authenticates or it does not.
- **Error** — `su: Authentication failure` almost always means the hash was truncated on the way into the file, or the password was mangled by shell expansion when you generated it. Generate it again with single quotes and compare the string byte for byte. `This account is currently not available` means field 7 is a `nologin` shell.
- **Noise** — a successful `su` that lands you in `/root` with a `#` prompt but `id` showing a non-zero UID means fields 3 and 4 were not both `0`.

**Then** — [[Shells]] to stabilise, and then remove the line. Either route generalises: any root-owned SUID binary that opens a file of your choosing reaches `/etc/shadow`, `/etc/passwd`, `/etc/sudoers`, `/root/.ssh/id_rsa` and every credential file on the host.

> [!warning]
> Route B is a change to a critical system file. It creates a persistent UID 0 account, it is trivially visible in `/etc/passwd`, and a botched line can lock accounts out of the host. Record the exact line, remove it when you are done, and check that the rules of engagement permit it. Route A is the quieter option when time allows both.

## What does not work here

> [!important]
> `LD_PRELOAD` is dead against SUID. The dynamic linker — the part of the system that loads a program's shared libraries into memory before its `main()` runs — ignores `LD_PRELOAD` and `LD_LIBRARY_PATH` whenever the real UID differs from the effective UID, precisely the SUID case. That technique exists in [[Linux-Sudo-Abuse]] only because *sudo itself* was configured to pass the variable through. Do not carry it across.

**SUID on a shell script does nothing.** The kernel drops the set-bits when it hands the file to an interpreter, so a `-rwsr-xr-x` `.sh` is not a path. A SUID *interpreter* — `perl`, `python`, `bash` itself — is, and it is a much better finding.

**`s` on a directory is not this technique.** SGID on a directory makes new files inherit the group. Worth noting for a writable shared directory; it escalates nothing on its own.

**A `nosuid` mount discards the bit at execution time** regardless of what the inode says — the inode being the on-disk record holding a file's owner, mode bits and block pointers, which is where the `s` you saw actually lives. `mount | grep <path>` before concluding the binary is broken.

## Rarely — worth one command, not worth a step

**Why now** — the sweep returned a binary that is not on any public list, or it returned nothing at all and you want to know whether the mechanism is even in play on this host.

```bash
strings /usr/local/bin/SUSPECT | grep -E '^[a-z][a-z0-9_-]{2,}$'
```

- A custom binary written in-house is not in any lookup table, so you read it instead. Bare command names in its strings are the finding: a name with no leading slash means the program calls it through `PATH`, and `PATH` is yours.
- The filter keeps lowercase word-shaped strings and drops the format strings, paths and library symbols that make up most of the output. Expect a handful of lines from a small binary.

```bash
ltrace /usr/local/bin/SUSPECT 2>&1 | grep -E 'system|exec|popen|fopen'
```

- This shows what the binary actually calls rather than what it contains. A `system("gzip …")` line is the same finding as above, confirmed instead of guessed.
- `ltrace` is missing on many hardened hosts and refuses to trace a `setuid` binary as a normal user on others. A refusal here is a property of the tracer, not of the target.

```bash
mount | grep -E 'nosuid|noexec'
```

- A filesystem mounted `nosuid` ignores the bit entirely, so a perfect `-rwsr-xr-x` binary sitting on it grants nothing. Worth one command before spending an hour on a candidate that was never going to fire.

**What you will see**

- **Found** — a bare command name in a custom binary, a confirmed `system()` call, or a mount option that explains why a promising binary does nothing.
- **Empty** — the normal answer. These are lottery tickets, not steps.
- **Error** — `command not found` for `ltrace` is the common case and simply removes that line of enquiry.
- **Noise** — `strings` returns library and symbol names on every binary. A name you recognise as a real command on this host is the signal; `printf` and `stderr` are not.

**Then** — a bare command name goes to [[Linux-PATH-Abuse]]. A confirmed call to another program goes there too. A `nosuid` mount means cross the candidate off and go back to the run sheet.

## Reading the output

**A shell that is still your own user is the expected result of the wrong move, not evidence of a wrong finding.** The single most common way to abandon a real SUID path is to run `:!/bin/bash` or `sudo -l`-style shell hunting, see `uid=1000`, and file the binary as a false positive. Read the euid rule once and the entire class stops costing time.

**Three findings together form a shape worth recognising.** `sudo -l` empty, every shell escape dropping to your own user, and an in-process file read succeeding: that is euid-only privilege on a binary whose forks are all closed. The win there is file access, not a shell, and Route B is how you convert it.

**This note cannot see half of its own category.** Mode bits are one of two places privilege attaches to a file. Before calling a host clean, run the capability sweep — the two are blind to each other and running only one is how a capped `/usr/bin/perl` survives an entire engagement: [[Linux-Capabilities]].

## Next

- [[Linux-Capabilities]] — the same privilege in an xattr; run that sweep before calling the host clean
- [[Linux-PATH-Abuse]] — when the binary calls a helper by bare name and you pick which program forks
- [[NFS-No-Root-Squash]] — the same mode bit reached from the other direction: planted from your own machine rather than found on this one
- [[Shells]] — stabilise the root shell into a full TTY before working in it

## Gaps

- **Route A's cracking step is now [[Hash-Cracking]].** What remains uncovered here: which wordlist and which rules to reach for against a `$6$` hash from a lab host.
- **Shared-object injection** — a SUID binary that `open()`s a `.so` from a path you can write, visible with `strace -f -e trace=openat,stat`. The classic `suid-so` case; not covered.
- **Bash function abuse / `env_keep` in older bash** — exported shell functions inherited by a SUID binary's `system()` call, on bash before 4.2-048.
- No defence-side note: `nosuid` mount options, and how a blue team baselines the SUID set.
