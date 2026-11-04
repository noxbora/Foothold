# Linux — SUID & SGID Abuse

The mode-bit sweep from [[Linux-Local-Enumeration]] returned something non-standard. This note is what to do with it: identify which bit is set, work out what the binary actually lets you *reach*, and turn a file read or a file write into root.

Linux permissions normally answer "what may **this user** do to this file". SUID (Set-User Identification) and [[Security-Terms#^sgid|SGID]] (Set-Group Identification) invert that: the file carries the privilege. A SUID binary executes with the **effective [[Security-Terms#^uid|UID]] of its owner**, not of the user running it, and a SGID binary with the effective [[Security-Terms#^gid|GID]] of its group. Owner `root` therefore means *anything that binary can do, you can do as root* — including reading and writing files your own account has no claim to. That is the design (`passwd` must write `/etc/shadow`); the vulnerability is the bit set on a binary that was never meant to carry it.

## Find them, and know which bit you found

```bash
find / -type f -perm -4000 -ls 2>/dev/null   # SUID
```

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

Type the binary's name into its search box, open the page, and read the block headed **SUID** — that block is the sequence that works when the privilege comes from the mode bit specifically, and it is usually two lines you can paste. No page for your binary closes nothing; it only means nobody published a recipe, and the four-verb rule below still applies.

An empty or stock-only result goes to [[Linux-Capabilities]]: a capped interpreter carries the same privilege in an extended attribute — a named value stored alongside a file's contents, outside the permission bits — and appears in no `-perm` sweep ever run.

## Read the mode column

```text
-rwsr-xr-x   1 root  root    188328 Apr 15  2010 /bin/nano
-rwxr-sr-x   1 root  shadow   62304 Jan  5  2016 /usr/bin/expiry
-rwSr--r--   1 root  root      8192 May 14  2017 /usr/local/bin/backup
```

- `s` in the **owner** execute slot → SUID; the process runs as the owner, `root` above.
- `s` in the **group** execute slot → SGID; it runs as the group. `shadow` is not root, but the `shadow` group reads `/etc/shadow` — judge the group by what it can reach, not by whether the word says root.
- capital `S` → the set-bit is on and *that slot's* execute bit is off. It is not a blanket block: `-rwSr--r--` has no execute bit anywhere and nobody runs it, while `-rwSr-xr-x` still runs for group and other, and still runs as the owner.
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

```vim
:!/bin/bash
:shell
```

- `:!` → "run this as a *system* command, not as a Vim command". Without the `!`, `:/bin/bash` is a **search**: Vim's `/` looks for the text `bin/bash` in the [[Security-Terms#^buffer|buffer]] and reports it missing. An easy ten minutes.
- `:shell` → the same fork, reached through `$SHELL`.
- `-p` does not rescue it. `:!/bin/bash -p` runs as `$SHELL -c "/bin/bash -p"`, so the **outer** shell drops euid before the inner one starts and the flag arrives one process too late.

### The moves that work

```vim
:e /root/
:r /etc/shadow
:w /etc/passwd
```

- `:e /root/` → opens netrw, Vim's own file browser. It is a plugin, not a program: it never forks, so it lists a directory your shell cannot enter.
- `:r <file>` → reads a file into the current buffer, as root.
- `:w <file>` → writes the buffer out, as root. This is the write half of the primitive and it is what Route B below uses.

### The one reliable shell escape

```vim
:py3 import os; os.setuid(0); os.system("/bin/bash")
```

- `:py3` → hands the rest of the line to the Python interpreter compiled into Vim. Check `:version` for `+python3` (or `+lua`, `+perl`) first — in that feature list a leading `+` means the feature is compiled in and a leading `-` means it is not, so `-python3` closes this route on this binary; a stripped `vim.tiny` has none of them.
- `os.setuid(0)` → sets the **real** UID to 0, which is permitted precisely because euid is already 0. After it, ruid == euid == 0 and the shell that spawns has nothing left to drop. This is the step that converts a fragile euid into a real one, and omitting it puts you back in the failing case above.

## Worked case — turning a read or write into root

### Route A — take the hashes and crack them elsewhere

```bash
nano /etc/shadow
```

```bash
nano /etc/passwd
```

- both files, not just `shadow` → the hashes live in one and the usernames and UIDs in the other. `/etc/passwd` is world-readable and lists every account as `name:x:UID:GID:comment:home:shell`; the `x` in field 2 is a pointer meaning "the hash is in `/etc/shadow`", which is the split this pair of files exists to create. Every cracking tool wants them joined again. Copying out only `/etc/shadow` means going back for the second file later, usually after the shell has died.
- this route writes nothing to the target: no file changed, no account created, nothing for a defender to trip over.

### Route B — write your own root account

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

> [!warning]
> Route B is a change to a critical system file. It creates a persistent UID 0 account, it is trivially visible in `/etc/passwd`, and a botched line can lock accounts out of the host. Record the exact line, remove it when you are done, and check that the rules of engagement permit it. Route A is the quieter option when time allows both.

## Worked case — a SUID interpreter (`python`)

An interpreter runs whatever code you hand it, so with the bit set it is root running whatever you write. No escape trick needed — only a shell that keeps the privilege.

```bash
/usr/bin/python2.7 -c 'import os; os.execl("/bin/sh", "sh", "-p")'
```

- the path → call the exact file the sweep printed. A bare `python` may resolve to a different interpreter without the bit, and you get a shell as yourself with no error to tell you why.
- `os.execl` → replaces the Python process with `sh` instead of starting a child, so euid=root carries straight over.
- `-p` → tells `sh` not to drop euid back to ruid ([[#The rule that decides everything|the rule above]]). Leave it out and `id` shows your own user.
- success → `id` prints `euid=0(root)` beside your own `uid=`. The split is expected; euid is what the kernel checks.

If this `sh` rejects `-p`: `import os; os.setuid(0); os.system("/bin/sh")`. `setuid(0)` is allowed because euid is already 0, and it sets the real UID too, so there is no split left for the shell to correct.

## What does not work here

> [!important]
> `LD_PRELOAD` is dead against SUID. The dynamic linker — the part of the system that loads a program's shared libraries into memory before its `main()` runs — ignores `LD_PRELOAD` and `LD_LIBRARY_PATH` whenever the real UID differs from the effective UID, precisely the SUID case. That technique exists in [[Linux-Sudo-Abuse]] only because *sudo itself* was configured to pass the variable through. Do not carry it across.

**SUID on a shell script does nothing.** The kernel drops the set-bits when it hands the file to an interpreter, so a `-rwsr-xr-x` `.sh` is not a path. A SUID *interpreter* — `perl`, `python`, `bash` itself — is, and it is a much better finding.

**`s` on a directory is not this technique.** SGID on a directory makes new files inherit the group. Worth noting for a writable shared directory; it escalates nothing on its own.

**A `nosuid` mount discards the bit at execution time** regardless of what the inode says — the inode being the on-disk record holding a file's owner, mode bits and block pointers, which is where the `s` you saw actually lives. `mount | grep <path>` before concluding the binary is broken.
