# Linux — Sudo Abuse

`sudo -l` returned something. Three ways to turn that entry into root, in the order you should try them: a known escape, the application's own file-handling options, and — when the environment allows it — `LD_PRELOAD`, which works against almost any binary at once.

Administrators grant narrow sudo rights for real reasons: an analyst who needs `nmap` but not root. The vulnerability is not sudo. It is that most useful programs can read a file, write a file, or run a command, and root-owned execution turns any one of those into full compromise.

## Read both halves of the output

```bash
sudo -l
```

```text
Matching Defaults entries for labuser on target:
    env_reset, mail_badpass, secure_path=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin

User labuser may run the following commands on target:
    (ALL) NOPASSWD: /bin/cat
```

- the **Defaults** line → which techniques are open. `env_reset` strips your environment, so Route 3 is closed. `env_keep+=LD_PRELOAD` means it is open. `secure_path=` replaces `$PATH` for the sudo'd command, which closes PATH abuse for that entry specifically.
- the **command list** → `(run-as) TAG: binary`. `(ALL)` means you may choose the target user with `-u`; `(root)` fixes it. `NOPASSWD` means no prompt — without it you need your own password, which you may not have.
- the **binary path is exact.** `(ALL) NOPASSWD: /bin/cat` does not authorise `/usr/bin/cat`, and a wildcard in the path (`/opt/scripts/*`) is a much larger grant than it looks: it lets you pass `../` sequences through it.

## Route 1 — the known escape

```bash
sudo -u root /bin/vi /var/tmp/anything
```
```vim
:set shell=/bin/bash
:shell
```

- `-u root` → explicit rather than implied. When the entry reads `(ALL)` you may also target a *different* user, and the interesting one is not always root: a **service account** — a non-human account a daemon runs under, such as `www-data`, `mysql` or `tomcat` — that owns the application directory is often the shorter path.
- `:set shell=` before `:shell` → Vi honours `$SHELL`, and on a locked-down account `$SHELL` may be `/bin/false`. Setting it explicitly removes a failure that looks exactly like the escape not working.
- the file argument must be one you may open. A path you cannot write makes Vi complain and exit before you reach the escape.

## Route 2 — the application's own functions

```bash
apache2 -h
```

```bash
sudo apache2 -C "LoadModule mpm_event_module /usr/lib/apache2/modules/mod_mpm_event.so" \
  -f /etc/shadow
```

- `apache2 -h` → prints the binary's own option list. Run it first on **any** unfamiliar granted binary: it is where you find the options that read, write, load or execute, which is the whole of Route 2 in one command.
- `-f /etc/shadow` → "parse this as the config file". Apache fails on line 1 and quotes the offending line back at you in the error, which on `/etc/shadow` — the root-only file holding every account's password hash — is the root hash.
- `-C "LoadModule ..."` → processed **before** the config file. An [[Security-Terms#^mpm|MPM]] (multi-processing module) is the pluggable component that decides how Apache handles concurrent requests, and the server refuses to start without exactly one loaded; on Debian and Ubuntu the packaged `apache2` has none compiled in, so without this it dies on a missing-MPM error before it ever reaches your file. This argument is the difference between the trick working and the trick looking impossible.
- the module path is distro-specific. `ls /usr/lib/apache2/modules/` first; a wrong path produces the same missing-MPM failure and is easy to misread as the whole technique failing.

The generalisable pattern is worth more than this one command: **make a root-run program read a file it should not, and report the contents back through an error message.** The same shape works with any binary whose parser echoes bad input, and it is why the first thing to read on an unfamiliar granted binary is its own `--help`, hunting for options that read, write, load or execute.

## Route 3 — LD_PRELOAD

`LD_PRELOAD` is an environment variable naming a **shared object** — a `.so` file, the Linux equivalent of a Windows DLL: compiled code loaded into a program's memory at startup rather than built into it. The dynamic linker loads whatever `LD_PRELOAD` names before every other library, and a **constructor** inside that object (a function marked to run automatically at load time, before the program's own `main()`) therefore executes first. If sudo preserves the variable, that constructor runs as root.

```c
#include <stdio.h>
#include <sys/types.h>
#include <stdlib.h>
#include <unistd.h>

void _init() {
    unsetenv("LD_PRELOAD");
    setgid(0);
    setuid(0);
    system("/bin/bash");
}
```
```bash
gcc -fPIC -shared -o /tmp/shell.so /tmp/shell.c -nostartfiles
```

```bash
sudo LD_PRELOAD=/tmp/shell.so find
```

- `_init()` → the constructor, by its historical name. [[Security-Terms#^elf|ELF]] is the executable and shared-object format Linux uses, and `_init` is the function the loader calls in an ELF object as soon as it is mapped into memory — before the host program starts, which is why the host program does not matter.
- `unsetenv("LD_PRELOAD")` → **required**. `system()` spawns a new process that would otherwise inherit the variable, load the same object again, and recurse until the host runs out of processes.
- `setgid(0)` then `setuid(0)` → in that order. Dropping the UID first would remove the privilege needed to change the group.
- `-shared` → build a shared object (`.so`) rather than an executable. Without it `gcc` produces a normal program and the linker refuses to preload it.
- `-fPIC` → position-independent code: machine code that works wherever in memory it is loaded, which a shared object must be because it has no fixed address of its own.
- `-nostartfiles` → skips the standard startup files, since you are supplying `_init` yourself. Without it the compiler's own `_init` collides with yours and the constructor never runs.
- the path to the `.so` must be **absolute**. A relative path is resolved against the sudo'd program's working directory, not yours, and fails silently.

> [!important]
> This does not work against a SUID binary. The loader ignores `LD_PRELOAD` whenever the real UID differs from the effective UID, which is exactly the SUID case. The vector exists here only because *sudo itself* was configured to pass the variable through. Do not carry it across to a `find -perm` hit — see [[Linux-SUID-Abuse]].
