---
type: service
platform: linux
status: working
fluency: guided
source: reading
updated: 2026-09-03
---

# 21 — FTP

File Transfer Protocol: a plaintext file-sharing service from 1971 that is still everywhere. Reach for this note the moment port 21 shows up in a scan — before any web enumeration, because an anonymous FTP share can hand you credentials, source code, or a backup in under a minute.

## Anonymous access

**Why now** — nmap says 21 is open and you hold no credential for anything on this host. FTP is the one common service that may hand you files with no credential at all, so this is the cheapest first move on the whole box: thirty seconds for a chance at source code, a backup, or a config with a password in it. Every other section here assumes you tried this first.

```bash
ftp <ip>
```

At the prompt, `anonymous` as the user and anything (or nothing) as the password. Some servers want an email address out of habit — `anonymous@` satisfies them. When you want the answer without sitting in a session:

```bash
ftp -n <ip> <<< $'user anonymous anonymous\nls\nquit'
```

- `-n` → suppress the client's own automatic login. Leave it off and the client prompts for a user itself, eats your `user` line as a stray command, and the here-string collapses in a way that reads exactly like the server refusing you.

**What you will see**

- **Found** — `230 Login successful.` and then a prompt. Anonymous read access to a share is a finding in its own right; write it down before you look at what is inside.
- **Empty** — a `230` followed by a listing with nothing in it is *not* an empty share. Three things produce that exact screen and only one of them is a real answer: see the next section before you believe it.
- **Error** — `530 Login incorrect` means anonymous is disabled, which is how a well-configured server is supposed to look. `530` with a credential you know is *valid* means the account exists and is refused — `/etc/ftpusers` blocks `root` and the system accounts by default. `421 Service not available` is a connection cap or a host that answered the SYN and nothing more.
- **Noise** — the `220` banner naming a vendor and a version arrives before any authentication. That is free version intel, not access, and it is easy to read a friendly banner as progress.

**Then** — a `230` goes to *Inside the session*, then straight to *Testing write access*, which is the question that decides whether this share is loot or a foothold. A `530` is not a dead end: you still collected the banner, so go to *When anonymous fails*.

## Inside the session

**Why now** — you are logged in and looking at a prompt that is not a shell. Every verb below acts on the **remote** side unless it says otherwise, and mixing the two up is the single most common way to waste ten minutes here.

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

**What you will see**

- **Found** — filenames that belong to somebody's real work: `backup.zip`, `.env`, `web.config`, a `users` or `dev` directory, anything with a date in the name.
- **Empty** — the important case. A blank listing means one of three things and they lead different ways: you ran plain `ls` and the content is dotfiles; you are in active mode and the data channel never opened, so the listing was never delivered; or you are chrooted into an empty upload directory with the real content one level up. Try `ls -la`, then `passive`, then `cd ..` — in that order — before you accept the share is genuinely empty.
- **Error** — `550 Failed to open file` or `550 Permission denied` on a `cd` is the server telling you that directory exists but is not yours to enter. That is different from `550 No such file or directory`, which means you guessed the name.
- **Noise** — a `pub` or `incoming` directory containing nothing. It is the default layout of every anonymous FTP server ever shipped, and its presence says nothing about this host.

**Then** — real filenames go to [[Config-File-Looting]] for what to grep them for. Genuinely empty, after all three checks, sends you to *Testing write access* — an empty share you can write to is worth more than a full one you cannot.

## Moving files in and out

**Why now** — you found something worth having, or you want to leave something behind. Both transfer verbs take **two** arguments and the second one is the one you will forget.

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

**What you will see**

- **Found** — `226 Transfer complete.` with a byte count and a rate. Check the byte count: a `226` on 0 bytes is a completed transfer of nothing.
- **Empty** — a transfer that reports success but produces a file of the wrong size is the ASCII mode problem above, not a broken server.
- **Error** — `553 Could not create file.` is the filename trap far more often than a permission problem. `550 Permission denied` on a `get` means the file is there and not readable by anonymous. `425 Can't open data connection` or a `get` that hangs after `150 Opening data connection` is the data channel, not the file — see *Passive vs active*.
- **Noise** — `200 Switching to Binary mode.` and `227 Entering Passive Mode (...)` are the client doing its job. They scroll past looking like results.

**Then** — files you pulled go to [[Config-File-Looting]]. A `553` goes back to the two-argument rule above before you conclude anything about permissions; only after that does it become the real answer described in *Testing write access*.

## Passive vs active — and why a transfer hangs

FTP uses **two** connections: a control channel on port 21 that carries your commands, and a separate data channel that carries the actual file bytes. Who opens that second connection is the whole difference:

- **Active mode** — the *server* connects back to *you*. Your firewall or a [[Security-Terms#^nat|NAT]] box sees an unsolicited inbound connection and drops it. Listing hangs forever with no error.
- **Passive mode** — the *server* opens a listening port and tells you where; *you* connect out to it. Outbound connections are almost always allowed, so this is the one that works.

If `ls` connects, authenticates, then freezes on the listing, you are in active mode. Type `passive` at the prompt to flip it. (NAT — Network Address Translation — is the router trick where many private machines share one public address; it has no way to route an inbound connection nobody asked for, which is why active mode dies behind it.)

## Testing write access

**Why now** — you have read access and you have swept the files. The remaining question is the one that decides whether this port is loot or a foothold, and it has exactly one honest answer: try it. Guessing from the directory listing is how people conclude "read-only" about a share that would have taken their payload.

```text
lcd /tmp
put probe.txt probe.txt
```

- the second `probe.txt` → mandatory here, or the test is invalid. A `553` caused by the missing argument is indistinguishable from a `553` caused by policy, and you will believe the wrong one.
- run `ls -la` on the directory first → `drwxrwxrwx` on the target directory means the filesystem permits the write, so a `553` against a `rwx` directory is your filename, not the server's policy.

**What you will see**

- **Found** — `226 Transfer complete.` and `probe.txt` appearing in the next `ls`. Anonymous write is a serious misconfiguration; record it immediately.
- **Empty** — the upload reports success and the file is **not** in the next listing. That is not a failure, it is a pipeline: something consumed the file. A directory that eats uploads is more interesting than one that keeps them.
- **Error** — `553 Could not create file.` against a directory that really is `r-x`, on every directory in the share, is a genuine answer rather than a failure: anonymous write is off, which is how a sane server is configured.
- **Noise** — a `README` naming a required format. A directory that advertises what it wants drops anything else **silently**: no error, no file, no feedback. Recover a sample of the expected format from a sibling or archive directory before uploading a single byte.

**Then** — a successful `put` is still only half an answer. A writable share matters when you can work out *where those bytes land* and *who reads them*. Into a directory the web server serves, that is code execution — [[Shells]] for the payload. Into a path a scheduled job consumes, that is somebody else's privileges — [[Cron-Jobs]]. Into a directory nothing ever touches, it is nothing at all. Read-only across the whole share closes this route and sends you back to the loot: [[Config-File-Looting]].

## Pulling everything at once

**Why now** — the share has more than a handful of files and clicking through it in the client is slow and lossy. Mirror the whole tree once, then grep it locally at your own speed with tools the FTP prompt does not have.

```bash
wget -m --no-passive ftp://anonymous:anonymous@<ip>
```

- `-m` → mirror: recursive, keeps timestamps, no depth limit. This is the flag that fixes `mget`'s non-recursive behaviour.
- `--no-passive` → forces active mode. Drop it the moment the transfer stalls, because active is usually the mode that does *not* work from behind NAT.

**What you will see**

- **Found** — a directory tree under `<ip>/` on your own disk. Sweep it with a single `grep -rniI` rather than opening files by hand.
- **Empty** — a tree containing only empty directories means the mirror walked the structure but every file transfer failed. That is the data channel again, not the content.
- **Error** — `Not connecting to <ip>:port insecurely` or a login refusal repeats whatever the interactive client already told you. `No such directory` after a successful login means anonymous is chrooted somewhere `wget` cannot climb out of.
- **Noise** — `index.html` files generated by `wget` itself from directory listings. They are not files from the server.

**Then** — the local tree goes to [[Config-File-Looting]], and any source code in it to [[Source-Code-Disclosure]].

## Nmap

**Why now** — you want the anonymous check, the server type and the bounce test in one pass, without opening a session at all. This is also the version of the check you can run against a whole subnet.

```bash
nmap -p21 -sV --script ftp-anon,ftp-syst,ftp-bounce <ip>
```

- `ftp-anon` → tries the anonymous login and prints the root listing if it lands. This is the same answer as the first section, delivered without a session.
- `ftp-syst` → server type and system info from `SYST`/`STAT`, which sometimes names the OS more precisely than `-sV` does.
- `ftp-bounce` → tests whether the server will proxy connections for you via the `PORT` command. Ancient, but a hit means this FTP server can port-scan the internal network on your behalf.
- `-sV` → the flag people drop to save time. Without it you get "21/tcp open ftp" and no version string, and the version string is the entire payoff when anonymous is disabled.

**What you will see**

- **Found** — an `ftp-anon: Anonymous FTP login allowed` line followed by a directory listing. For `ftp-syst`, a `SYST` reply naming the platform.
- **Empty** — no script output at all under an open port usually means the scripts never ran: check you did not typo the script names, since nmap does not error on an unmatched name.
- **Error** — `ftp-anon: ERROR: Script execution failed` is usually a connection cap on the server, not a defended one. Retry alone with `--script ftp-anon`.
- **Noise** — a version banner is what the daemon *claims*. Distributions backport security patches without changing the version string, so an old-looking version is a lead, never a vulnerability.

**Then** — the version string goes straight to [[Public-Exploit-Workflow]]. An `ftp-anon` hit goes back to *Inside the session* to work the share by hand.

## When anonymous fails

**Why now** — anonymous was refused, so the share is not free. You now have two remaining routes and they are worth exactly opposite amounts of your time: the banner is free, and password guessing is expensive and loud.

The banner first — it arrives before authentication, so a refused login has already given it to you (see [[23-Telnet#The client as a bare TCP probe|23-Telnet]]). Some FTP daemons carry famous backdoors and auth bypasses, and that is a one-command win rather than an hour of guessing. Feed the exact string to [[Public-Exploit-Workflow]].

Password attacks are the fallback, not the opening move:

```bash
hydra -L users.txt -P passwords.txt -f -t 4 ftp://<ip>
```

- `-f` → stop at the first valid pair. Without it hydra keeps running through the whole list after it already has your answer.
- `-t 4` → four parallel tasks. FTP daemons throttle and drop connections above this, so a higher number produces **false negatives**, not speed — you will be told a valid password is invalid.
- `-L` versus `-l` → capital is a user *list*, lowercase is a single user. Spraying one password across many users with `-l` is a common slip and tests the wrong thing.

**What you will see**

- **Found** — a `[21][ftp] host: <ip>   login: <user>   password: <pass>` line. Take the pair to every other service on the box before you spend it here; reuse is the norm.
- **Empty** — `0 valid passwords found` against a wordlist you chose blindly is not evidence the account is strong. It is evidence your wordlist was wrong, and the fix is a targeted list ([[Custom-Wordlist-Attack-Chain]]), not a bigger one.
- **Error** — `[ERROR] all children were disabled, dying` means the server dropped every connection: lower `-t`. Repeated `[ERROR] could not connect` is the throttle, not the wordlist.
- **Noise** — a server that answers `230` to *every* password. Some misconfigured daemons accept anything, so hydra reports the whole list as valid. Verify one pair by hand before you trust it.

**Then** — a valid pair goes back to *Inside the session* as that user, and then to [[Config-File-Looting]] for what it can now read. No pair, and no exploitable banner, closes port 21 as a route — record it and move to the next port rather than growing the wordlist.

## Rarely — worth one command, not worth a step

**Why now** — anonymous access failed, or it worked and the directory was empty. Two things are left and both are one command.

```bash
curl -k --ssl-reqd -u 'anonymous:anonymous' ftp://TARGET/
```

- Some servers refuse a plaintext login and accept the identical one once the session is encrypted. The refusal message is the same in both cases, so a plain client makes an encrypted-only server look like a closed one.
- Port `990` is the other spelling of the same idea, with the encryption negotiated before the greeting rather than after it.

```bash
curl -s http://TARGET/uploads/probe.txt
```

- The combination worth remembering: an anonymous upload directory that some web server also publishes. Neither half is a finding on its own, and together they are a shell.
- Upload a marker first, as in the write test above, and request it over every web port the host has open before concluding the two services are unrelated.

**What you will see**

- **Found** — a directory listing over the encrypted session, or your uploaded marker coming back from a web request.
- **Empty** — the normal answer for both. They are lottery tickets, not steps.
- **Error** — a certificate complaint is not a failure; `-k` exists precisely because a self-signed certificate on an internal service is normal.
- **Noise** — a web server returning its own custom 404 page with a `200` status makes a missing file look present. Read the body, not the code.

**Then** — an upload directory that the web server serves goes to [[File-Upload-Bypass]] and then to [[Shells]]. An encrypted-only server that answers goes back to the sections above, which all work unchanged inside the session.

## Reading the output

Two things this note as a whole cannot tell you.

The first is that **every FTP failure has two candidate causes**, because the protocol has two connections. Anything that hangs after a successful login is the data channel, not your credentials or your permissions. Anything that fails instantly with a numbered reply is the control channel and means what it says. Sorting a symptom into one of those two buckets before you start theorising saves most of the time this service costs.

The second is that FTP sends the username and password in **cleartext**. On a segment you can sniff, that makes any FTP client on the network a credential source — and it also means every credential you use here is exposed to anyone else in the same position.

## Next

- [[File-Transfer]] — FTP as a deliberate transfer channel once you have a shell
- [[Config-File-Looting]] — what to grep for in whatever the share hands you
- [[Public-Exploit-Workflow]] — when the banner is the only thing anonymous access gives you

## Gaps

- FTPS (implicit 990 / explicit `AUTH TLS`) and [[Security-Terms#^sftp|SFTP]] — a different protocol over SSH entirely — are both absent; only cleartext FTP is covered here.
- Credential capture off the wire: FTP sends the password in plaintext, so it is a prize on a sniffable segment, but that is not documented here or in [[TShark]].
- Nothing on FTP servers as a *pivot* target beyond the `ftp-bounce` mention.
