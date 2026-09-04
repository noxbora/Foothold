---
type: technique
platform: linux
status: solid
fluency: guided
source: thm
updated: 2026-09-03
---

# Linux — Sudo Abuse

`sudo -l` returned something. Three ways to turn that entry into root, in the order you should try them: a known escape, the application's own file-handling options, and — when the environment allows it — `LD_PRELOAD`, which works against almost any binary at once.

Administrators grant narrow sudo rights for real reasons: an analyst who needs `nmap` but not root. The vulnerability is not sudo. It is that most useful programs can read a file, write a file, or run a command, and root-owned execution turns any one of those into full compromise.

## Read both halves of the output

**Why now** — the sweep in [[Linux-Local-Enumeration]] printed a `sudo -l` entry and you are about to pick a technique. Which of the three below is even *possible* is decided by a line most people scroll past, and reading it now is the fastest way to avoid an hour spent on a vector the configuration already closed.

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

**What you will see**

- **Found** — any entry at all, including a read-only one. `(ALL) NOPASSWD: /bin/cat` is enough: `sudo cat /etc/shadow` reads the root-only file holding every account's password hash. Judge an entry by what the binary lets you *reach*, not by whether **[[Security-Terms#^gtfobins|GTFOBins]]** lists a shell for it — GTFOBins (`https://gtfobins.github.io`) being a public catalogue of ordinary Unix binaries and the exact keystrokes each one needs to read a file, write a file, or spawn a shell when it runs with borrowed privilege.
- **Empty** — `user is not allowed to run sudo on <host>` is genuine and closes this note. It says nothing about any other category, so it is a narrow negative, not a bad result.
- **Error** — `sudo: a password is required` in a shell where the prompt never appears means there is no terminal attached, not that you lack the right. `sudo` will only read a password from a **TTY** — a terminal device the kernel treats as interactive — and a raw reverse shell has none, so it gives up rather than prompting. Upgrade the shell ([[Shells]]) and run it again. `sudo: unable to resolve host <name>` is a broken `/etc/hosts` on the target and is cosmetic — the rules below it still print.
- **Noise** — `mail_badpass`, `use_pty`, `logfile=` and `lecture=` on the Defaults line are logging and cosmetic settings. Only `env_reset`, `env_keep` and `secure_path` change what you can do.

**Then** — a binary with a GTFOBins entry goes to Route 1. A binary with no entry goes to Route 2, where you read its own help for the four verbs. `env_keep+=LD_PRELOAD` on the Defaults line goes straight to Route 3 regardless of which binary was granted, because that route barely cares. Empty goes back to the category sweep in [[Linux-Run-Sheet]].

## Route 1 — the known escape

**Why now** — the granted binary is a common one, so somebody has already worked out the exact sequence that turns it into a shell. Looking it up costs a minute and skips the whole of Route 2. Do this before you start reading `--help` output. How to look it up: search the binary's name on GTFOBins, open its page, and read the block headed **Sudo** — each site heading (`Sudo`, `SUID`, `Capabilities`, `Limited SUID`) is a different way the privilege arrived, and the sequences are not interchangeable, so read the one that matches yours.

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

**What you will see**

- **Found** — a prompt where `id` returns `uid=0(root)`. Unlike the SUID case in [[Linux-SUID-Abuse]], no euid rule applies here: `sudo` sets the real [[Security-Terms#^uid|UID]] as well, so the child shell has nothing to drop and the escape simply works.
- **Empty** — no empty case; either a shell appears or an error does.
- **Error** — `sorry, user X is not allowed to execute '/bin/vi ...' as root` means the path did not match the rule byte for byte, or you passed an argument the rule's wildcard does not cover. `sudoedit` entries fail deliberately: `sudoedit` drops privileges before opening the file, which is the entire reason it exists.
- **Noise** — a shell that opens as your own user is the tell that you invoked the binary *without* sudo. Check the command you actually ran before concluding the escape is broken.

**Then** — a root shell goes to [[Shells]]. A refusal on the exact path sends you back to the `sudo -l` output to copy the path verbatim. No GTFOBins entry for this binary goes to Route 2.

## Route 2 — the application's own functions

**Why now** — GTFOBins has no entry for this binary, which means nobody has published a shell escape, not that there is nothing there. Almost every non-trivial program can read a file, write a file, load a config, or run a command, and any one of those performed as root is a complete path. This is the route that generalises to software nobody has written up.

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

**What you will see**

- **Found** — a syntax error that **quotes your target file's content**: `Syntax error on line 1 of /etc/shadow: Invalid command 'root:$6$...'`. The leaked line is the finding, and line 1 of `/etc/shadow` is the root entry.
- **Empty** — apache2 starting normally and printing nothing means it accepted your file as a valid config, which means you pointed it at the wrong thing. This is a real negative on that file, not on the technique.
- **Error** — a missing-MPM error instead of your target line means the `-C` argument or the module path is wrong. `Address already in use` means it got past parsing entirely and is trying to bind, which is a different failure and one you can ignore.
- **Noise** — warnings about `ServerName` and `AH00558` appear on every run and mean nothing here.

The generalisable pattern is worth more than this one command: **make a root-run program read a file it should not, and report the contents back through an error message.** The same shape works with any binary whose parser echoes bad input, and it is why the first thing to read on an unfamiliar granted binary is its own `--help`, hunting for options that read, write, load or execute.

**Then** — a leaked hash is input, not access: [[Hash-Cracking]]. A binary whose options include one that *executes* something is a shell rather than a read primitive, and goes back to Route 1 in spirit. If the environment also carries `env_keep+=LD_PRELOAD`, stop reading help output and go to Route 3, which does not care what the binary does.

## Route 3 — LD_PRELOAD

**Why now** — the Defaults line carried `env_keep+=LD_PRELOAD`. That single string makes the granted binary almost irrelevant: your code runs before the program's own `main()`, so any entry in the list becomes a root shell. Check for it early, because when it is present the other two routes are wasted effort.

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

**What you will see**

- **Found** — the host program never produces its normal output at all; a root shell appears instead, because the constructor runs first and `system()` blocks. `id` returns `uid=0`.
- **Empty** — `find` (or whichever binary) running completely normally and exiting is the signature of `LD_PRELOAD` being **stripped**. That is a configuration answer: re-read the Defaults line, because without `env_keep` this route is closed no matter how good the payload is.
- **Error** — `ERROR: ld.so: object '/tmp/shell.so' from LD_PRELOAD cannot be preloaded` names the real problem: usually a missing `-fPIC`, a wrong architecture, or a relative path. `undefined symbol: _init` means `-nostartfiles` was omitted.
- **Noise** — a shell that opens and immediately exits is the non-interactive case, not a privilege failure. Swap `system("/bin/bash")` for a reverse shell: [[Shells]].

> [!important]
> This does not work against a SUID binary. The loader ignores `LD_PRELOAD` whenever the real UID differs from the effective UID, which is exactly the SUID case. The vector exists here only because *sudo itself* was configured to pass the variable through. Do not carry it across to a `find -perm` hit — see [[Linux-SUID-Abuse]].

**Then** — a root shell goes to [[Shells]]. `LD_PRELOAD` stripped goes back to Route 1 and Route 2, which do not depend on the environment at all.

## Rarely — worth one command, not worth a step

**Why now** — the rule you were given names a binary with no known escape and no useful function. Before writing it off, two properties of `sudo` itself are worth one command each.

```bash
sudo -u#-1 /bin/bash
```

- A rule written as `(ALL, !root)` is meant to permit every user except root. On versions before 1.8.28 the user id `-1` fails to resolve, and the failure resolves to `0`, which is root. The rule that was written to exclude root is the rule that grants it.
- One attempt tells you. If the version is patched it simply refuses.

```bash
sudo -V | head -1
```

- The version decides whether the above is even possible, and it decides several other published issues besides. It is one line and it belongs in your notes for the box regardless of what you do with it.
- Read it before searching for an exploit, not after. A version search without the version is guessing.

**What you will see**

- **Found** — a root shell from the first command, or a version old enough to be worth a search.
- **Empty** — the normal answer on any maintained host. These are lottery tickets, not steps.
- **Error** — `unknown user: #-1` or `invalid user ID` means the version is patched, which closes that line cleanly.
- **Noise** — a very old version number is not a finding on its own; it is an input to [[Public-Exploit-Workflow]], which is where it is decided.

**Then** — a root shell ends the note. A version worth searching goes to [[Public-Exploit-Workflow]]. Neither, and the rule really is a dead end, so go back to step 8 of [[Linux-Run-Sheet]] and pair it with something else.

## Reading the output

**The Defaults line decides the order of everything on this page.** It is one line, it appears before the part everyone reads, and it is the single fastest way to stop working on a closed vector. `env_keep+=LD_PRELOAD` promotes Route 3 to first. `secure_path=` tells you not to bother exporting a `$PATH` at [[Linux-PATH-Abuse]] for this entry. `env_reset` alone leaves Routes 1 and 2 and nothing else.

**A granted binary with no shell escape has not closed.** Route 2 exists because the interesting question is never "can this spawn a shell" but "can this read, write, load or execute". Three of those four end the host just as completely as a shell does, and only the first is what GTFOBins indexes under *Shell*.

**Hashes recovered by Routes 1 and 2 are not a win yet.** They are input to offline cracking, and if the wordlist misses they are worth nothing on their own: [[Hash-Cracking]].

## Next

- [[Linux-SUID-Abuse]] — the sibling vector, and where the `LD_PRELOAD` callout above sends you
- [[Shells]] — stabilise the root shell into a full TTY (job control, a working password prompt, arrow-key history) before working in it
- [[Linux-PATH-Abuse]] — the vector `secure_path=` in the Defaults line closes, and `env_keep` reopens

## Gaps

- No `LD_LIBRARY_PATH` variant — the sibling technique when that variable is the one kept.
- No sudo CVE note: Baron Samedit (CVE-2021-3156) and the `sudoedit` argument flaw (CVE-2023-22809) escalate without needing any granted entry at all.
- **Wildcards in the granted path** are named above and not worked through. `(ALL) /opt/x/*` behaves very differently from a fixed path and deserves its own section.
