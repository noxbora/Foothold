# Linux Run Sheet

What to run on a Linux host you just landed on, in order, one command per block. Keep this open beside the shell and run nothing else until step 8. The Windows twin is [[▸ Windows-Run-Sheet]]; the domain-wide counterpart is [[▸ AD-Run-Sheet]].

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

## 2 — Who else lives here

```bash
grep -v nologin /etc/passwd
```

```bash
ls -la /home
```

- `grep -v nologin` → drops the service accounts. What remains is accounts a human logs into, which are the accounts you can become.

## 3 — Files with more privilege than they should have

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

## 4 — What runs with more privilege than me

```bash
ps -eo user,pid,cmd --ww --no-headers | grep -vE '\[' | grep -vE ' /(usr/)?s?bin/[^ ]+$| /usr/lib(exec)?/[^ ]+$'
```

- Same discriminator as the SUID sweep and the same reason: the distribution's own binaries live in `/bin`, `/sbin`, `/usr/bin`, `/usr/sbin`, `/usr/lib`. What is left runs from `/opt`, `/srv`, `/home`, `/usr/local` or is a script — and that is the only part of a 200-line process list you were ever going to act on.
- **The `$` at the end of the exclusion is load-bearing.** A stock interpreter running somebody's script — `monitor 812 /bin/bash /usr/local/bin/healthcheck` — contains `/bin/bash`, so an unanchored exclusion deletes the exact line you came for. Anchored, a line only dies when the stock path is the **last** thing on it, which means nothing was handed to it.
- What it still hides: a planted binary sitting in `/usr/bin` under a stock name. What it lets through: a stock daemon carrying flags, `/usr/sbin/sshd -D`, because the line does not end at the path. Two or three of those are normal. Two hundred lines back means the quoting broke and the filter never ran at all.
- `grep -vE '\['` → drops kernel threads, which show as `[kworker/0:1]`. There are dozens and none of them are yours to influence.
- `-eo user,pid,cmd` rather than `aux` → the same information with the columns you need and none of the CPU/memory noise that pushes the command line off the right edge of a narrow shell. `--ww` → never truncate at the terminal width, or the script path you are hunting is cut off the right edge anyway.
- A surviving line running as a **non-standard user from a non-standard path** — `monitor 812 /bin/bash /usr/local/bin/healthcheck` — is the signal to go read that script and the unit or cron entry that launches it. The exploitable detail (a `PATH` override, a bare command name) is in the file, never in the process list.

```bash
ss -tulpn | grep -E '127\.0\.0\.1|\[::1\]'
```

- `-t` TCP, `-u` UDP, `-l` listening only, `-p` owning process, `-n` numbers not names. Without `-n` it hangs trying to resolve DNS on a host with no route out.
- The `grep` keeps only **loopback** bindings, which is the whole reason to run this: a port on `0.0.0.0` was already in your nmap results and tells you nothing new. A port on `127.0.0.1` was invisible from outside and is reachable only from this shell.
- Run it once without the `grep` if you need the full picture, but read the filtered version first.

## 5 — What runs automatically

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

## 5b — When you cannot see the schedule

```bash
./pspy64
```

```bash
find / -writable -type f -not -user $(whoami) -not -path '/proc/*' -not -path '/sys/*' 2>/dev/null
```

- `pspy` → prints every process the moment it starts, no privileges required. Leave it running longer than the longest plausible interval; five minutes covers most lab jobs. A job you have not waited for looks exactly like a job that does not exist.
- `find -writable -not -user $(whoami)` → the sharper of the two: files you can **write** that you do not **own**. That combination is the entire vulnerability in one command, and it does not care whether the thing running the file is cron, a timer, a daemon or another user.

## 6 — Credentials lying around

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

```bash
./linpeas.sh | tee ~/linpeas.log
```

- `tee` → keeps a copy on disk while it scrolls past. The output is far too long to read live.

## 8 — Stop and connect

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
