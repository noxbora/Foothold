# 21 — FTP

File Transfer Protocol: a plaintext file-sharing service from 1971 that is still everywhere. Reach for this note the moment port 21 shows up in a scan — before any web enumeration, because an anonymous FTP share can hand you credentials, source code, or a backup in under a minute.

## Anonymous access

```bash
ftp <ip>
```

At the prompt, `anonymous` as the user and anything (or nothing) as the password. Some servers want an email address out of habit — `anonymous@` satisfies them. When you want the answer without sitting in a session:

```bash
ftp -n <ip> <<< $'user anonymous anonymous\nls\nquit'
```

- `-n` → suppress the client's own automatic login. Leave it off and the client prompts for a user itself, eats your `user` line as a stray command, and the here-string collapses in a way that reads exactly like the server refusing you.

## Inside the session

```text
ls          list the current remote directory
ls -la      list hidden files — the interesting ones are almost always dotfiles
cd <dir>    move around; `cd ..` is worth trying immediately, anonymous is often
            chrooted into an empty subdirectory while the content sits one level up
pwd         where you are on the remote side — check this before every transfer
lcd <dir>   change the LOCAL directory: where `get` saves to and `put` reads from
!ls         run a command on your OWN machine without leaving the session
binary      switch to binary mode
passive     toggle passive mode
bye         quit
```

- `ls -la` → the one that is easy to skip. Plain `ls` hides dotfiles, and `.ssh`, `.bash_history` and `.git` are exactly what you came for. An "empty" share that was never listed with `-la` is not an empty share.
- `lcd` → sets the local side once so you can then use bare filenames. It is the fix for the `put` trap in the next section, and it also stops `get` from dropping loot into whatever directory you happened to launch `ftp` from.

## Moving files in and out

```text
get <remote-name> <local-name>
put <local-name> <remote-name>
```

- second argument on `put` → without it the client sends your **full local path** as the remote filename. `put /home/user/Documents/shell.sh` does not upload into the directory you are standing in; it asks the server to create `/home/user/Documents/shell.sh` on **its** filesystem. That path does not exist there, so the server answers `553 Could not create file.` — a permission-shaped error caused by a filename mistake. You can lose an hour here believing the share is read-only when it is world-writable.
- `binary` → set it before transferring anything that is not plain text. The default [[Security-Terms#^ascii|ASCII]] mode rewrites line endings in transit, which silently corrupts archives, images, databases and compiled binaries. The transfer reports success and the file is broken. `md5sum` both sides when it matters.

The client prints the truth on every attempt. Read the second half of the echo line:

```text
local: /home/user/Documents/shell.sh remote: /home/user/Documents/shell.sh
```

If `remote:` shows a path instead of a bare filename, that is the bug. Two ways to make it impossible — pick one and make it a habit:

```text
put /home/user/Documents/shell.sh shell.sh
```

or set the local directory once and work with bare names from then on:

```text
lcd /home/user/Documents
put shell.sh
```

Many files at once:

```text
prompt        turn OFF the per-file y/n confirmation (it is a toggle)
mget *        download everything matching
mput *        upload everything matching
```

- `prompt` → without it `mget *` stops on every single file waiting for a `y`, which on a share of two hundred files looks like the client has hung.
- `mget` / `mput` are **non-recursive**. They take the files in the current directory and nothing below it, so a tree comes back looking half-empty. For a whole tree, leave the session and mirror it — see *Pulling everything at once*.

## Passive vs active — and why a transfer hangs

FTP uses **two** connections: a control channel on port 21 that carries your commands, and a separate data channel that carries the actual file bytes. Who opens that second connection is the whole difference:

- **Active mode** — the *server* connects back to *you*. Your firewall or a [[Security-Terms#^nat|NAT]] box sees an unsolicited inbound connection and drops it. Listing hangs forever with no error.
- **Passive mode** — the *server* opens a listening port and tells you where; *you* connect out to it. Outbound connections are almost always allowed, so this is the one that works.

If `ls` connects, authenticates, then freezes on the listing, you are in active mode. Type `passive` at the prompt to flip it. (NAT — Network Address Translation — is the router trick where many private machines share one public address; it has no way to route an inbound connection nobody asked for, which is why active mode dies behind it.)

## Testing write access

```text
lcd /tmp
put probe.txt probe.txt
```

- the second `probe.txt` → mandatory here, or the test is invalid. A `553` caused by the missing argument is indistinguishable from a `553` caused by policy, and you will believe the wrong one.
- run `ls -la` on the directory first → `drwxrwxrwx` on the target directory means the filesystem permits the write, so a `553` against a `rwx` directory is your filename, not the server's policy.

## Pulling everything at once

```bash
wget -m ftp://anonymous:anonymous@<ip>
```

- `-m` → mirror: recursive, keeps timestamps, no depth limit. This is the flag that fixes `mget`'s non-recursive behaviour.
- Passive is `wget`'s default, and it is the mode that works from behind NAT because **your** side opens the data connection. Reach for `--no-passive` only when a passive transfer stalls and you want to know whether the server's advertised passive port is reachable at all.

## Nmap

```bash
nmap -p21 -sV --script ftp-anon,ftp-syst,ftp-bounce <ip>
```

- `ftp-anon` → tries the anonymous login and prints the root listing if it lands. This is the same answer as the first section, delivered without a session.
- `ftp-syst` → server type and system info from `SYST`/`STAT`, which sometimes names the OS more precisely than `-sV` does.
- `ftp-bounce` → tests whether the server will proxy connections for you via the `PORT` command. Ancient, but a hit means this FTP server can port-scan the internal network on your behalf.
- `-sV` → the flag people drop to save time. Without it you get "21/tcp open ftp" and no version string, and the version string is the entire payoff when anonymous is disabled.

## When anonymous fails

The banner first — it arrives before authentication, so a refused login has already given it to you (see [[23-Telnet#The client as a bare TCP probe|23-Telnet]]). Some FTP daemons carry famous backdoors and auth bypasses, and that is a one-command win rather than an hour of guessing. Feed the exact string to [[Public-Exploit-Workflow]].

Password attacks are the fallback, not the opening move:

```bash
hydra -L users.txt -P passwords.txt -f -t 4 ftp://<ip>
```

- `-f` → stop at the first valid pair. Without it hydra keeps running through the whole list after it already has your answer.
- `-t 4` → four parallel tasks. FTP daemons throttle and drop connections above this, so a higher number produces **false negatives**, not speed — you will be told a valid password is invalid.
- `-L` versus `-l` → capital is a user *list*, lowercase is a single user. Spraying one password across many users with `-l` is a common slip and tests the wrong thing.
