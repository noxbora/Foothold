---
type: technique
platform: linux
status: working
fluency: guided
source: reading
updated: 2026-09-04
---

# Linux Run Sheet

What to run on a Linux host you just landed on, in order, one command per block. Keep this open beside the shell and run nothing else until step 8. The Windows twin is [[Windows-Run-Sheet]].

Run the whole sheet again after every lateral move. Each user sees a different filesystem — what one account cannot read, the next one often can.

> [!important]
> One rule governs the entire sheet: **an empty result is a finding, not a failure.** Every step below tells you what nothing means, because on a Linux host "nothing found" and "you are not permitted to see it" look absolutely identical, and they demand opposite next moves.

## The order, and where each step cashes in

| # | The question | Where the hit is cashed in |
|---|---|---|
| 1 | What am I already allowed to do? | [[Linux-Sudo-Abuse]] |
| 2 | Who else lives here? | step 6, then [[Config-File-Looting]] |
| 3 | What files hold privilege they should not? | [[Linux-SUID-Abuse]], [[Linux-Capabilities]] |
| 4 | What runs with more privilege than me? | [[Pivoting-and-Tunneling]] |
| 5 | What runs automatically? | [[Cron-Jobs]] |
| 5b | ...and what if I cannot see the schedule? | [[PSPY]], [[Wildcard-Injection]] |
| 6 | What credentials are lying around? | [[Config-File-Looting]] |
| 7 | What does a scanner see that I missed? | [[Linux-Automated-Enumeration]] |
| 8 | Which two findings touch the same path? | this note, step 8 |

Steps 1-2 are recon on yourself. Steps 3-5b are the escalation hunt. Steps 6-7 are the second sweep. Step 8 is the only step that produces a shell.

## 1 — Who am I

**Why now** — you have a shell and nothing else. Before hunting for a weakness you need to know what you are already allowed to do, because a group membership can hand you root with no exploit at all, and finding that out costs one second.

```bash
id
```

```bash
sudo -l
```

```bash
hostname; cat /etc/os-release; uname -a
```

- `id` → user, primary group, **and every secondary group**. This is the line that matters, not `whoami`.
- `sudo -l` → what this account may run as another user. It asks for **your** password; type it if you have it. With no password it still prints `NOPASSWD` rules, so read the output before deciding it failed.
- `uname -a` → kernel version and architecture, the input to any kernel exploit search.

**What you will see**

- **Found** — in `id`, membership in `docker`, `lxd`, `disk`, `adm`, `shadow`, `sudo` or `wheel`. In `sudo -l`, a line naming a program you may run as root, especially with `NOPASSWD:`.
- **Empty** — `sudo -l` saying the user may run no commands is genuine and common. It closes one route and nothing more.
- **Error** — `sudo: a password is required` means you are typing into a shell with no terminal attached. Upgrade the shell first ([[Shells]]) and come back; the answer is still there.
- **Noise** — being in your own username-group (`bora : bora`) is normal, not a finding.

**Then** — a `sudo -l` entry sends you to [[Linux-Sudo-Abuse]] and usually ends the box there. A special group sends you to [[Linux-Privilege-Escalation]]. Empty or ordinary output means continue to step 2; nothing here is a dead end yet.

## 2 — Who else lives here

**Why now** — the target is rarely root directly. It is usually the next user along, and you need their names before you can recognise their password, their key, or their cron job when you trip over it two steps from now.

```bash
grep -v nologin /etc/passwd
```

```bash
ls -la /home
```

- `grep -v nologin` → drops the service accounts. What remains is accounts a human logs into, which are the accounts you can become.

**What you will see**

- **Found** — a handful of real usernames with real shells, and home directories. Write them down; from here on, every filename and every password you find gets matched against this list.
- **Empty** — impossible; `/etc/passwd` is world-readable by design. An empty result means the command is wrong, not the host.
- **Error** — a permission error reading `/etc/passwd` does not happen on a working Linux host. If you get one you are in a restricted shell or a stripped container, and that is a larger finding than the user list you came for.
- **Noise** — `root`, `sync`, and a couple of stock accounts always have shells. The interesting names are the ones that mean something to whoever built the box.

**Then** — carry the list into every later step. A home directory you can enter (step 6) is loot; one you cannot is a target.

## 3 — Files with more privilege than they should have

**Why now** — you are looking for the classic mismatch: a file that runs as somebody else, or a file you can change that somebody else runs. This step finds the first kind.

A bare SUID sweep returns about twenty files on a stock host and every one of them shipped with the distribution. That set is fixed and known, so it belongs **inside the command**, not in a paragraph telling you to skip twenty lines by eye.

```bash
find / -type f \( -perm -4000 -o -perm -2000 \) -printf '%M %p\n' 2>/dev/null | grep -vwE 'passwd|su|sudo|mount|umount|ping|chsh|chfn|newgrp|gpasswd|pkexec|fusermount|fusermount3|ssh-keysign|ssh-agent|snap-confine|unix_chkpwd|pam_extrausers_chkpwd|utempter|polkit-agent-helper-1|dbus-daemon-launch-helper|at|crontab|wall|write|expiry|chage|dotlockfile|mlocate'
```

- Typical result: 21 files in, 0-2 out. Those one or two are the entire finding.
- `-perm -4000` → SUID: the file runs as its **owner**, whoever runs it. The leading `-` means "these bits are set, ignore the others". Write `4000` without it and you match only files whose permissions are *exactly* `4000` — almost none — so the command returns nothing and you wrongly conclude the host is clean.
- `-perm -2000` → [[Security-Terms#^sgid|SGID]], the same idea with the file's **group**. Both bits are swept at once and `-printf '%M %p'` prints the mode string, so `-rwsr-xr-x` (SUID) and `-rwxr-sr-x` (SGID) are told apart at a glance without running two commands.
- `grep -vwE` → `-w` demands a whole word, so `su` in the list does not also delete `/usr/bin/sudoedit`.
- **The one thing this filter can hide:** a planted binary given a stock *name* in a non-stock directory — `/tmp/passwd`, `/opt/app/mount`. If the filtered result is empty, run it once more with the `grep` removed and read the paths rather than the names.

```bash
getcap -r / 2>/dev/null
```

- `getcap -r /` → capabilities: a slice of root's power attached to one binary. Stored in an extended attribute, so the two `find` commands above are structurally blind to it.
- `2>/dev/null` → an unprivileged `find` walking the whole filesystem prints hundreds of `Permission denied` lines. Without this, the one hit you want scrolls off the screen.

**What you will see**

- **Found** — a binary that has no business being SUID: an interpreter (`python`, `perl`), an editor (`vim`, `nano`), a pager (`less`, `more`), a compression tool, or anything under `/home`, `/opt`, `/usr/local`. From `getcap`, anything carrying `cap_setuid` or `cap_dac_read_search`.
- **Empty** — from `find`, plausible but rare; hosts normally have a dozen stock SUID binaries, so a completely empty result usually means you mistyped the `-perm` argument. From `getcap`, genuinely empty is common and normal.
- **Error** — `getcap: command not found` happens on minimal systems. That is a missing tool, not a missing finding, and it leaves you blind to this whole class.
- **Noise** — for the SUID sweep, none left: the stock names are in the `grep -vwE` list, which is where that knowledge belongs. `getcap` is not filtered because its output is three or four lines; `ping`, `mtr-packet` and `traceroute6` are the stock capability holders and are the ones to skip there.

**Then** — a non-stock hit goes to [[Security-Terms#^gtfobins|GTFOBins]] and to [[Linux-SUID-Abuse]]; a capability hit to [[Linux-Capabilities]]. Empty here is not a dead end: it means the escalation is behind a *process* rather than a file, so go to step 4 and step 5.

## 4 — What runs with more privilege than me

**Why now** — steps 1-3 looked at files sitting still. This one looks at what is actually running, because a process owned by root that you can talk to, feed, or restart is as good as a SUID binary and shows up nowhere in a permissions sweep.

```bash
ps -eo user,pid,cmd --no-headers | grep -vE '\[' | grep -vE '(^| )/(usr/)?s?bin/|/usr/lib/|/usr/libexec/'
```

- Same discriminator as the SUID sweep and the same reason: the distribution's own binaries live in `/bin`, `/sbin`, `/usr/bin`, `/usr/sbin`, `/usr/lib`. What is left runs from `/opt`, `/srv`, `/home`, `/usr/local` or is a script — and that is the only part of a 200-line process list you were ever going to act on.
- `grep -vE '\['` → drops kernel threads, which show as `[kworker/0:1]`. There are dozens and none of them are yours to influence.
- `-eo user,pid,cmd` rather than `aux` → the same information with the columns you need and none of the CPU/memory noise that pushes the command line off the right edge of a narrow shell.
- A surviving line running as a **non-standard user from a non-standard path** — `monitor 812 /bin/bash /usr/local/bin/healthcheck` — is the signal to go read that script and the unit or cron entry that launches it. The exploitable detail (a `PATH` override, a bare command name) is in the file, never in the process list.

```bash
ss -tulpn | grep -E '127\.0\.0\.1|\[::1\]'
```

- `-t` TCP, `-u` UDP, `-l` listening only, `-p` owning process, `-n` numbers not names. Without `-n` it hangs trying to resolve DNS on a host with no route out.
- The `grep` keeps only **loopback** bindings, which is the whole reason to run this: a port on `0.0.0.0` was already in your nmap results and tells you nothing new. A port on `127.0.0.1` was invisible from outside and is reachable only from this shell.
- Run it once without the `grep` if you need the full picture, but read the filtered version first.

**What you will see**

- **Found** — anything that survived either filter. A process running from `/opt`, `/usr/local` or a home directory, especially as a user that is not you; or a loopback port that was not in your nmap results.
- **Empty** — no loopback ports is a real answer and closes the internal-service route. An empty **process** list after filtering is not: it means nothing runs outside the distribution paths, so re-read the unfiltered list once for anything odd rather than trusting the blank.
- **Error** — `ss: command not found` on old systems; `netstat -tulpn` is the fallback.
- **Noise** — `ss` shows a blank process column for processes you do not own. That is a permission limit, not an empty result: the port is still real and something is still listening. In the process list, what survives the filter and is still uninteresting is your own shell and the `grep` you just ran.

**Then** — a loopback service goes to [[Pivoting-and-Tunneling]] to reach it from Kali. A root-owned custom process means read its files, its config and its working directory. Empty here plus empty at step 3 makes step 5 the whole game.

## 5 — What runs automatically

**Why now** — this is the pipeline question, and the most common escalation on a lab box: some job runs on a timer as a more privileged user, and it touches a file you can write.

```bash
cat /etc/crontab
```

```bash
ls -la /etc/cron.d/ /etc/cron.daily/ /etc/cron.hourly/ /etc/cron.weekly/
```

```bash
crontab -l
```

```bash
find /etc/systemd/system -maxdepth 1 -type f \( -name '*.service' -o -name '*.timer' \) 2>/dev/null
```

- `crontab -l` → **your** jobs only. Another user's jobs are in `/var/spool/cron/crontabs/<user>`, mode `600` and owned by them. Reading `crontab -l`, seeing nothing and moving on is the single most common way to walk past the answer.
- That `find` is the sharpest command in this step. Units shipped by packages live in `/lib/systemd/system` and `/usr/lib/systemd/system`; `/etc/systemd/system` is where a **person** puts one. `-type f` is what makes it work: that directory is mostly full of symlinks pointing back at the package units, which is how a service gets enabled, and without `-type f` they drown the two or three real files.
- `systemctl list-timers --all` still has a use — it says **when** each timer next fires — but it names the timer, not what the timer runs, and it lists every stock one. Read `systemctl cat <unit>` for the `ExecStart=` line once the `find` has told you which unit to care about.

**What you will see**

- **Found** — a job naming a script path. Immediately run `ls -l` on **both** the script and the directory holding it, then read the script.
- **Empty** — the important case, and usually *not* an answer. Root's crontab is unreadable to you by design; a `/etc/cron.d/` file can be `640 root:root`; `2>/dev/null` hides the denial that would have told you so. Empty here means **switch method**, not "no job exists".
- **Error** — `crontab: must be privileged to use -u` means you asked for another user's jobs directly; that is the expected answer, and the route is step 5b rather than a different flag. `systemctl: command not found` means the host is not systemd-managed, so timers are not a category here at all and cron is the only schedule to chase.
- **Noise** — stock timers (`anacron`, `logrotate`, `man-db`, `apt-daily`, `fstrim`) only appear if you fall back to `systemctl list-timers`; the `find` never shows them, because none of them are installed into `/etc/systemd/system` as files.

**Then** — a readable job goes to [[Cron-Jobs]], and if the script uses a `*` or a bare command name, to [[Wildcard-Injection]] or [[Linux-PATH-Abuse]]. An empty result goes to step 5b, which is where the answer actually lives on most boxes.

## 5b — When you cannot see the schedule

**Why now** — step 5 came back empty and you know that proves nothing. There are two ways to find a job you are not allowed to read, and neither needs root.

```bash
./pspy64
```

```bash
find / -writable -type f -not -user $(whoami) -not -path '/proc/*' -not -path '/sys/*' 2>/dev/null
```

- `pspy` → prints every process the moment it starts, no privileges required. Leave it running longer than the longest plausible interval; five minutes covers most lab jobs. A job you have not waited for looks exactly like a job that does not exist.
- `find -writable -not -user $(whoami)` → the sharper of the two: files you can **write** that you do not **own**. That combination is the entire vulnerability in one command, and it does not care whether the thing running the file is cron, a timer, a daemon or another user.

**What you will see**

- **Found** — from `pspy`, a command line appearing on a rhythm, with a [[Security-Terms#^uid|UID]] that is not yours. From `find`, a `.sh` under `/opt`, `/srv`, `/usr/local` or an application directory, owned by root or another user. A script like that is not there by accident; something runs it.
- **Empty** — `pspy` silent for ten minutes is a real answer: no scheduled job is firing. Then the escalation is credential-based, so step 6 is where it lives.
- **Error** — `pspy` must be transferred to the target and made executable ([[File-Transfer]]). Check it with `file` before running it — a downloaded GitHub *page* instead of the raw binary is the standard trap and produces a syntax error that looks like a broken tool.
- **Noise** — `pspy` shows your own commands and the shell's own children. Filter by UID.

**Then** — append your payload to the writable file with `>>`, never `>`. Appending keeps the script doing its real job so nothing breaks and nobody notices. Then wait for the interval and catch the result — a listener from [[Shells]].

## 6 — Credentials lying around

**Why now** — becoming another user with their own password is quieter and more reliable than any exploit, and on a chained box it is usually the intended path. Step 2 gave you the names; this step looks for the passwords that go with them.

```bash
history; cat ~/.bash_history ~/.zsh_history 2>/dev/null
```

```bash
env
```

```bash
ls -la ~/.ssh /home/*/.ssh 2>/dev/null
```

```bash
grep -rniI -E '(password|passwd|secret|api[_-]?key)[[:space:]]*[=:][[:space:]]*[^[:space:]#]' \
  /var/www /opt /srv /home /etc 2>/dev/null | grep -vE ':[0-9]+:[[:space:]]*#'
```

- `-I` → skip binary files. Without it one matching binary floods the terminal with unreadable bytes and can leave it in a broken state.
- `[=:]` followed by a non-blank → demands an actual assigned **value**, which drops every prose sentence that merely contains the word "password".
- the second `grep -v` → drops comment lines, which is where nearly all the false positives live.
- search order → application directories first, `/etc` last, because `/etc` is documentation.

**What you will see**

- **Found** — an assignment with a specific value nobody would print in a manual, in a file belonging to an application someone configured: a `config.php`, a `.env`, a database connection string, a backup script, `.git-credentials`. A readable private key in another user's `.ssh` is the same thing in stronger form.
- **Empty** — a genuine answer, and it points back at steps 4 and 5b: the path is a process, not a secret.
- **Error** — the terminal filling with unreadable bytes or hanging means the search reached a binary and you dropped `-I`. Visible `Permission denied` lines mean you dropped `2>/dev/null` — keep them for exactly one run, because a directory you are not allowed to read is itself a target, and the redirect hides that from you on every later run.
- **Noise** — the large one. Every line beginning `#` is a comment: documentation, not configuration. `foobar`, `somepassword`, `changeme`, `example`, `<your-password>` are words a manual uses, not words an admin picks. `/etc/login.defs`, `/etc/overlayroot.conf`, `/etc/ssh/sshd_config` and everything under `/etc/fwupd/` ship with these on a clean system.

**Then** — a password alone is half an answer. You need the **user** it belongs to: check the file's owner with `ls -l`, the service it configures, and any username in the same block. Then try it — `su <user>`, `ssh <user>@localhost`, or against the service itself. Password reuse across accounts is common enough that a database password is worth trying as a shell password. Full sweep of what each config format hides: [[Config-File-Looting]].

> [!important]
> A broad `grep` for `password`/`secret`/`api-key` across system directories
> (`/etc`, `/var/www`, `/opt`) mostly returns **false positives** — config-template
> boilerplate, not real secrets. Known offenders to recognize and skip:
> - `/etc/ssl/openssl.cnf` — OpenSSL's own doc examples (`secret = pass:insta`),
>   not a real password
> - `/etc/cloud/cloud.cfg` — cloud-init's default-user template
>   (`lock_passwd: True`), not a live account
> - `/etc/nsswitch.conf`, `/etc/security/namespace.init` — reference the
>   `passwd` *service name*, not a credential
>
> Real secrets are more likely in app-specific config: `.env`, `wp-config.php`,
> anything under a web app's own config folder — not generic `/etc` system files.

## 7 — Automated, as a second opinion

**Why now** — the manual pass is done and you have either a path or a list of empties. Now run the script, to check your work rather than to replace it. Running it first teaches you nothing and buries the answer in a thousand lines.

```bash
./linpeas.sh | tee ~/linpeas.log
```

- `tee` → keeps a copy on disk while it scrolls past. The output is far too long to read live.

**What you will see**

- **Found** — red-and-yellow highlighted lines are what the tool considers a probable escalation. Everything else is context.
- **Empty** — linpeas is never empty; if it produced nothing, it did not run.
- **Error** — `syntax error near unexpected token` with HTML in the message means you downloaded a GitHub *page* rather than the raw file. Check with `file linpeas.sh` before every run.
- **Noise** — most of the output. The tool cannot see intent and flags things that are normal.

**Then** — for every highlight ask what privileged component it involves and what you control about it. Nothing found by a tool becomes a path until you can say that sentence. Context: [[Linux-Automated-Enumeration]].

## 8 — Stop and connect

**Why now** — you have a page of findings and no shell. Nothing on this sheet is an escalation on its own; the escalation is always a **pair** of findings that touch the same file, port or account.

Write the chain in one sentence:

```text
I am <user>
    ↓ I can <the thing you control>
    ↓ which <the privileged thing> reads or runs
    ↓ so my commands execute as <user>
```

- If the sentence does not close, you do not have a path yet — you have a list, and the fix is another sweep rather than another exploit.
- The two halves usually come from different steps. A writable file (5b) plus a job you cannot see (5). A password (6) plus a username (2). A loopback service (4) plus a credential (6). A SUID binary (3) plus the [[Security-Terms#^gtfobins|GTFOBins]] entry that tells you what it will do for you.
- **Write down the empties too.** In the first pair above, the empty *is* half the answer: you cannot see the schedule, and you can write a file — neither half means anything alone. A list that records only hits cannot form that pair.
- **Do not discard a finding for not being an escalation.** None of them are. That is the point of the step.

**Prioritise by directness, not by how interesting it looks.** Roughly: a credential you can simply spend, then a permission you can act on immediately, then anything needing a wait, then anything needing a restart or a compile. A root password beats a writable hourly cron script even though the cron script is the more satisfying find.

A pair that needs **waiting** is not a bad pair, it is a slow one — so start it first and work the others while it runs. Append your payload, leave the listener up, keep enumerating. The interval passes whether you watch it or not.

**What you will see**

- **Found** — two findings that name the same path or the same account. That is the box.
- **Empty** — no pair after a full sweep means one of your empties was a permission rather than an absence, and the likeliest liar is step 5. Re-run 5b, wait longer on `pspy`, then [[Stuck-Checklist]].
- **Error** — the pair closes but the payload does nothing. That is no longer enumeration: it is the interval, the shell ([[Shells]]), or a `>` where you needed `>>`.
- **Noise** — an interesting finding that pairs with nothing is worth less than a boring one that does. Four empties and one writable file is a better position than twelve highlights.

**Then** — once you are the new user, come back to step 1 and run the whole sheet again as them. Different account, different filesystem.

## Rarely — worth one command, not worth a step

**Why now** — the eight steps above cover what is on almost every host. These four are for the evening the sheet came back empty everywhere: each is one command, each pays rarely, and none of them deserves a place in the order.

```bash
cat /etc/fstab
```

- Mount options carry credentials in clear text. A `cifs` line with `username=` and `password=` on it, or a `credentials=` path you can read, is a working password for another machine sitting in a world-readable file.
- The same file names every share this host expects to reach, which maps a piece of the internal network for free.

```bash
ls -la /opt /usr/local/bin /usr/local/sbin 2>/dev/null
```

- The distribution's own binaries live in `/bin`, `/sbin`, `/usr/bin` and `/usr/lib`. Anything a person installed by hand lands here instead, so these three directories are the third-party software list without a package manager and without a thousand lines. Versions go to [[Public-Exploit-Workflow]].
- Read the owner and the mode, not only the name. A binary here that your group may write is a different finding from one that is merely present.

```bash
find /home /opt /srv -type f \( -name 'id_*' -o -name '*.kdbx' -o -name '*.pem' -o -name '*.ovpn' \) 2>/dev/null
```

- Keys, password databases, certificates and connection profiles. Scoped to three directories on purpose: rooted at `/` this returns the system certificate store, takes minutes, and buries the two files you wanted.
- `-name 'id_*'` catches `id_rsa` and `id_ed25519` together with their `.pub` partners, and the public half tells you which account the private half belongs to.

```bash
ls -l /var/run/docker.sock /var/snap/lxd/common/lxd/unix.socket 2>/dev/null
```

- A container socket you may write to is a daemon that will mount the host filesystem for you on request. Step 1 already catches this through group membership; this catches the case where the socket permissions are loose and the group is not.

**What you will see**

- **Found** — a password in a mount line, a hand-installed binary with a searchable version, a private key under a home directory, or a container socket that is writable by you.
- **Empty** — the normal answer for all four. They are lottery tickets, not steps, and an empty result here says nothing about the host.
- **Error** — `No such file or directory` from the socket check simply means no container runtime is installed, which is a clean answer rather than a failure.
- **Noise** — `/etc/fstab` always lists the root filesystem and swap, and `/opt` is frequently empty on a stock server. Both are stock and neither is a finding.

**Then** — a credential goes to [[Config-File-Looting]] and to the service it belongs to. A private key goes to [[22-SSH]]. A writable container socket goes to [[Linux-Privilege-Escalation]]. Nothing found means go back to step 8 and re-examine which of your empty results was actually a denial.

## Reading the output

Two things this sheet as a whole cannot tell you.

The first is timing. Every command here photographs one instant. A job that starts and exits between two of your commands appears nowhere, which is why step 5b exists and why an empty run sheet is not proof of a clean host.

The second is that findings are only worth what they combine into. Four separate empties and one writable file is a better position than twelve interesting-looking hits with nothing that pairs. Resist acting on the first hit; finish the sheet, then pair.

## Next

- [[Windows-Run-Sheet]] — the same eight questions on the other platform
- [[Linux-Local-Enumeration]] — the Linux half in more depth, with the cash-in link for each hit
- [[Shells]] — you will need a listener before most of these pay out
- [[PSPY]] — when steps 4 and 5 both come back empty

## Gaps

- Container and VM escape checks (`/.dockerenv`, `/proc/1/cgroup`, the `docker` group beyond the one-line mention in step 1) are not here.
- No macOS column.
- Nothing on staying quiet: every command here is loud on a monitored host, and the note does not say which are loudest.
