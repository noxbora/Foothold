---
type: technique
platform: linux
status: working
fluency: guided
source: thm
updated: 2026-09-08
---

# Linux — PATH Abuse

A privileged program calls a helper by **bare name** — `whoami`, not `/usr/bin/whoami`. The name is resolved at runtime through `$PATH`, and `$PATH` is an ordinary environment variable that you own. Put a writable directory earlier in it than the real binary, drop a file with the matching name there, and the privileged program executes your file instead.

This is the same shape as [[Cron-Jobs]] and [[Wildcard-Injection]]: a privileged component consuming something you control. Here the thing you control is not a file's *contents* but the **resolution order** that decides which file gets opened.

## Preconditions — all four, or it does not work

| # | Condition | Where it comes from |
|---|---|---|
| 1 | A privileged trigger — SUID binary, root cron job, sudo-able script | [[Linux-Local-Enumeration]] |
| 2 | It invokes a command **without an absolute path** | `strings`, then `ltrace` |
| 3 | A directory you can write to can be placed earlier in that `PATH` | `find / -writable -type d` |
| 4 | The privilege survives the child process | the euid section near the end |

Condition 4 is the one that quietly kills this technique, and most write-ups do not mention it. Read it before spending time on 1 to 3 — it takes two minutes and it decides whether the other three are worth anything.

## Find the trigger

**Why now** — you have a shell and no path yet. This technique needs something privileged to *call* your file, so before anything else you need a candidate: a binary that runs as root, or a job that does. Without one, a writable `$PATH` entry is not a finding and hunting for it is wasted time.

```bash
find / -type f -perm -4000 2>/dev/null \
  | grep -vE '^/(snap|usr/lib|usr/libexec|usr/bin|usr/sbin|bin|sbin)/'
```

- `grep -vE '^/(...)/'` → drops the stock system directories in the same pass. The stock SUID set runs past the scrollback of most terminals and the one interesting line is at the top, where you can no longer reach it. Filtering at the source is cheaper than scrolling.
- the trailing `\` → continues the command onto the next line. Paste both lines together; the first line alone produces the unfiltered flood you were trying to avoid.
- `2>/dev/null` must sit on the `find`, not on the pipeline, or the permission-denied lines reach `grep` and survive the filter.

**What you will see**

- **Found** — a path under `/opt`, `/usr/local/bin`, or a home directory. A recent mtime among binaries dated years earlier says the same thing even when the directory looks ordinary.
- **Empty** — a real negative on the SUID trigger and nothing else. Cron and sudo are the other two ways a privileged program calls a helper, and both are checked differently: `cat /etc/crontab` and the periodic directories for the first, `sudo -l` for the second.
- **Error** — nothing worth naming. `find` walking a filesystem you cannot read produces the denials this command already discards.
- **Noise** — `/usr/lib/openssh/ssh-keysign`, `/usr/lib/dbus-1.0/dbus-daemon-launch-helper` and `pkexec` survive some filters and are stock. If your filter leaves a dozen entries, tighten it rather than reading them all.

**Then** — a candidate binary goes to the next section, which asks whether it calls anything by bare name. Empty here goes to [[Cron-Jobs]]: a root job whose command has no `/` in it is the same vector with a different trigger, and it is the more common of the two.

## Find the bare-name call

**Why now** — you hold a privileged binary. Precondition 2 decides whether this note applies at all, and it is answered by reading the binary rather than by running it. A single absolute path in its call closes the vector outright, which is worth knowing before you build a payload.

```bash
strings -d /opt/path/mywhoami
```

```bash
ltrace /opt/path/mywhoami
```

- `strings -d` → data sections only. Plain `strings` also dumps the symbol table and the debug info, which is where the misleading matches live; `-d` removes most of the triage below in one flag.
- `ltrace` → shows the library call **with its argument**, live. It answers in one line what `strings` answers by elimination, and it is the tool to reach for first when it is installed.
- if `ltrace` is absent, `strace -f -e trace=execve ./binary` shows the `execve` the shell performs, which names the resolved path.

```text
setuid(0)                = 0
setgid(0)                = 0
system("whoami" <unfinished ...>
```

When you are stuck with plain `strings`, triage by elimination — everything below is **not** the answer:

| Pattern | What it is |
|---|---|
| `libc.so.6`, `GLIBC_2.2.5`, `/lib64/ld-linux-...` | linker and library metadata |
| `setuid`, `setgid`, `system`, `__libc_start_main` | **imported libc function names**, not arguments |
| `mywhoami.c`, `crtstuff.c`, `Scrt1.o` | source filenames from the debug info |
| `_init`, `__bss_start`, `.text`, `.rodata` | symbol and section table |
| everything after the `GCC: (Ubuntu ...)` line | compiler metadata; stop reading there |
| `PTE1`, `u+UH`, `9*3$"` | machine-code bytes that happen to be printable |

**What you will see**

- **Found** — a short word that would run if you typed it into a shell, appearing as the *argument* of a call: `system("whoami")`. In the `ltrace` output, a `setuid(0)` line above it is the other half of the finding — see the euid section below for why it matters more than the call itself.
- **Empty** — `strings` returning almost nothing means the binary is stripped and statically linked, or it is not an [[Security-Terms#^elf|ELF]] at all. Run `file` on it: a shell script is readable directly and needs none of this.
- **Error** — `ltrace: Couldn't find symbol table` or an immediate exit means `ltrace` cannot attach, which on many hosts is because it refuses to trace a SUID binary. That is a tooling limit, not a negative: fall back to `strings -d`.
- **Noise** — the expensive misread on this whole page: `system` appears in the output because the binary *imports* `system()` from libc. It is a symbol, not a target. The string you want is the argument passed to it, and the two sit in different sections and look identical in a flat dump.

**Then** — a bare name goes to the writable-directory search. An **absolute** path in that output (`system("/usr/bin/whoami")`) closes this vector cleanly: no `PATH` lookup happens, so stop here and go back to [[Linux-SUID-Abuse]] to judge the binary on what it does itself.

## Find a writable directory

**Why now** — you have a name the privileged program will resolve at runtime. Now you need somewhere on its search path to put your file. This is precondition 3, and the best possible answer is a directory that is *already* on the path, because then nothing about your environment has to be modified at all.

```bash
find / -writable -type d 2>/dev/null | grep -vE '^/(proc|sys|run)' | sort -u
```

- `-writable` → asks the kernel rather than reading mode bits, so it accounts for your group memberships and for ACLs. Reasoning about `ls -ld` output instead is how you conclude a directory is closed when it is not.
- `grep -vE '^/(proc|sys|run)'` → those three are writable in places by design and none of it is useful here. Without the filter the real answers are buried in `/proc/<pid>` entries.
- `sort -u` → sorts and drops duplicates so the list reads in one pass. `find` does not follow directory symlinks unless you ask it to, so this is tidying rather than a correction.

**What you will see**

- **Found** — `/tmp` is almost always present and is the default choice. `/dev/shm` is the quieter one: memory-backed, so nothing lands on disk. Best of all is a writable directory that already appears in `echo "$PATH"`, because it needs no `export` and nothing looks tampered with.
- **Empty** — genuinely rare, and if it happens check that you are not in a container with a read-only root filesystem. It closes this vector, but not the variant where the trigger runs in *your* shell and you may still prepend a directory you own.
- **Error** — none worth naming; unreadable directories are silently discarded.
- **Noise** — hundreds of hits under your own home directory and under `/var/tmp`. They are writable and irrelevant unless the privileged program's `PATH` reaches them, which it will not unless you put them there.

**Then** — take the shortest usable directory to the next step. If one of them is already in the running `PATH` of a *root* process — visible in `/etc/crontab`'s `PATH=` line, for instance — that is the strongest version of this finding and it works without you exporting anything: [[Cron-Jobs]].

## Prepend, do not append

**Why now** — you have a directory and a filename. The only thing left is to make the privileged program look in your directory *before* the real one, and there is exactly one way to write that line. Getting the order wrong produces a hijack that silently never fires.

```bash
export PATH=/tmp:$PATH
```

```bash
hash -r
```

- the **position of `$PATH`** in the line is the entire technique. Resolution walks left to right and stops at the first match:

```text
export PATH=/tmp:$PATH   ->   /tmp:/usr/local/bin:/usr/bin:/bin     <- searched first
export PATH=$PATH:/tmp   ->   /usr/local/bin:/usr/bin:/bin:/tmp     <- searched last
```

- when the hijacked name is a real command — `whoami`, `ls`, `ps`, `service` — appending puts you behind `/usr/bin`, which already has it, and your file is never reached.
- `hash -r` → bash remembers where it found a command and ignores `$PATH` on the next call. This bites when *testing* the hijack in your own shell; it does not affect a C program's `system()`, which starts a fresh shell each time. Assigning to `PATH` clears that cache as well, which is why an export sometimes appears to work without this line.

**What you will see**

- **Found** — `echo "$PATH"` showing your directory first, and `which whoami` (after `hash -r`) naming your file rather than `/usr/bin/whoami`.
- **Empty** — no empty case; the variable either changed or it did not.
- **Error** — a broken shell where nothing runs any more means you assigned over `$PATH` instead of prepending to it. `export PATH=$(getconf PATH)` restores a working default.
- **Noise** — nothing guards this variable and nothing warns you about it. It belongs to your shell session, applies only to your own processes, and resets on logout, which is also why the change is invisible to anyone else.

**Then** — go to the payload. Note the limit this step implies: you can only export into an environment you control. A root cron job has its own `PATH` that you cannot touch, which is why the cron variant needs a writable directory that is *already* on that job's path.

## Plant the payload and fire it

**Why now** — everything is in place and this is the only step that changes anything on disk. Keep it small: the payload's job is to prove the resolution order was hijacked, and a shell is the cheapest proof.

```bash
cd /tmp
```

```bash
printf '#!/bin/bash\n/bin/bash\n' > whoami
```

```bash
chmod 700 whoami
```

```bash
/opt/path/mywhoami
```

```bash
id
```

- the filename must match the string from the previous step **exactly**. It is not a name you choose — the binary chose it at compile time, and the match is the entire mechanism.
- `chmod 700` → executable is the part that matters, and the owner bit is enough here: a root-triggered command runs your file whoever else can read it, so there is no reason to make it world-writable. A file that is present but not executable is skipped by `PATH` resolution as if it were not there, and produces `command not found` rather than a permission error.
- confirm with `id`, not with `whoami` → `whoami` is now your own script and will print whatever you told it to. This is the single most confusing way to misread a successful exploit.

**What you will see**

- **Found** — `uid=0(root) gid=0(root)`. Restore the environment afterwards with `export PATH=$(getconf PATH)` and remove the planted file.
- **Empty** — the privileged binary running normally and printing its usual output means your file was never reached. Three causes, in order of likelihood: you appended instead of prepending, the filename does not match byte for byte, or you forgot the execute bit.
- **Error** — `command not found` from *inside* the privileged program is the same three causes. The payload running but nothing happening is a non-interactive context: a cron job or a service has no terminal, so `/bin/bash` exits immediately and you need a reverse shell instead ([[Shells]]).
- **Noise** — the biggest one on this page: `id` returning **your own** [[Security-Terms#^uid|UID]] while everything else worked. That is not a failed hijack. Your file ran; the privilege was dropped on the way in, and the next section is why.

**Then** — root goes to [[Shells]]. Your own UID goes to the euid section below, which decides whether this binary can ever pay out or whether the finding is only worth reporting.

## Why the privilege usually evaporates — and when it does not

The euid rule from [[Linux-SUID-Abuse#The rule that decides everything|SUID Abuse]] applies in full here, because `system()` is a fork:

```text
system("whoami")   ->   execl("/bin/sh", "sh", "-c", "whoami")
```

`system()` never runs the target directly. It starts **`/bin/sh`** and hands it the string — which is precisely why `$PATH` is consulted at all, since resolving bare names is the shell's job. But `sh` compares euid against ruid at startup and, when they differ, drops euid back to ruid. A SUID binary that calls `system("whoami")` and nothing else therefore runs your payload as **you**, not as root.

> [!important]
> The vector needs `setuid(0)`, or a call path with no shell in it. The worked case succeeds only because the source reads `setuid(0); setgid(0); system("whoami");`. `setuid(0)` sets the **real** UID to 0 — allowed, since euid is already 0 — and with ruid == euid == 0 the shell has nothing left to drop. `strings` showing `setuid` alongside `system` is the signal that this holds, and it is why that otherwise-noise symbol is worth one glance before you dismiss it.

When the binary does **not** call `setuid(0)`:

- if it uses `execvp()` or `execlp()` — PATH resolution without a shell — no drop happens. Your payload must then be a **compiled binary** that calls `setuid(0)` itself, since a `#!/bin/sh` script would reintroduce the interpreter and the drop:

```c
#include <unistd.h>
int main(void){ setuid(0); setgid(0); execl("/bin/bash","bash",NULL); }
```

- if it uses `system()` — the shell is unavoidable and the vector yields only your own privilege. Note it as exploitable-if-called-by-root and move on.

The cron variant has no such problem: the job already runs as root with ruid == euid == 0, so a one-line shell script is enough. The catch there is the opposite one — you cannot `export` into root's environment, so you must find a bare-name call whose *existing* `PATH` already contains a directory you can write to. See [[Cron-Jobs]].

## Rarely — worth one command, not worth a step

**Why now** — you have the four preconditions but the trigger will not fire, or `sudo -l` showed something and you are not sure it is relevant here. Both of these are the same idea as this note applied to a different environment variable.

```bash
sudo -l | grep -E 'env_keep|env_reset|secure_path'
```

- `secure_path` is why a `sudo` command ignores your `PATH` entirely, and seeing it explains a failure that otherwise looks like the technique not working. `env_reset` does the same for the rest of the environment.
- `env_keep+=LD_PRELOAD` is the opposite: it carries a variable of yours into a root command, and that variable names a library loaded before every other. Same shape as this note, different variable, and it survives `secure_path` because it is not `PATH`.

```bash
find / -writable -type d -path '*/lib*' 2>/dev/null
```

- A writable library directory that already sits on the loader's search list is the passive version of this technique: you do not need a bare call, only a library name the program already looks for.
- Expect zero results on a maintained host. One result is worth the whole evening.

**What you will see**

- **Found** — an `env_keep` entry naming a loader variable, or a writable directory that libraries are loaded from.
- **Empty** — the normal answer for both. They are lottery tickets, not steps.
- **Error** — `sudo -l` asking for a password you do not have ends the first line of enquiry cleanly; the second is unaffected.
- **Noise** — `secure_path` is present in almost every default configuration. Its presence is stock, not a finding.

**Then** — a preserved loader variable goes to [[Linux-Privilege-Escalation]] and is worked exactly like this note with a compiled library in place of a script. Nothing found means the trigger really does drop its privilege, and the section above explains why.

## Reading the output

**An absolute path closes this vector and that is a good outcome, not a wasted hour.** `system("/usr/bin/whoami")` never consults `$PATH`. Write it down as a clean negative and judge the binary on what it does in-process instead: [[Linux-SUID-Abuse]].

**Two lines in `sudo -l` decide this vector for sudo entries specifically.** `secure_path=` replaces `$PATH` with a fixed value, so nothing you export survives into the sudo'd command. `env_keep+=PATH` reopens it only where `secure_path` is absent — set both and `secure_path` wins, so read the two together rather than treating `env_keep` as the answer → [[Linux-Sudo-Abuse]].

**An empty element in `$PATH` is a finding on its own.** A leading `:`, a trailing `:`, a `::`, or a literal `.` means the **current directory** is searched. No `export` is needed at all: write your file into whatever directory the privileged program runs from.

## Next

- [[Cron-Jobs]] — the same technique with a root-owned trigger and no writable environment
- [[Linux-Sudo-Abuse]] — `secure_path` and `env_keep` decide whether this is open under sudo
- [[Shells]] — the payload to plant when the trigger is non-interactive

## Gaps

- **No compiled-payload walkthrough.** The `execvp` case above gives the C source but not the cross-compilation problem when the target's glibc is older than the attacking box's.
- **Writable-service-file variant** — a systemd unit with a bare-name `ExecStart`. Same shape, different trigger; unwritten, and listed in [[Linux-Privilege-Escalation]].
- **`PATH` in setuid-safe contexts.** glibc sanitises some variables for SUID processes but **not** `PATH`. The full list of what *is* stripped (`LD_PRELOAD`, `LD_LIBRARY_PATH`) has no note anywhere.
- No defence-side note: absolute paths in privileged scripts, `secure_path`, and how a blue team detects a prepended `/tmp`.
