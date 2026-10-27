# Windows Run Sheet

What to run on a Windows host you just landed on, in order, one command per block. Keep this open beside the shell and run nothing else until step 8. The Linux twin is [[▸ Linux-Run-Sheet]]; the domain-wide counterpart is [[▸ AD-Run-Sheet]].

Run the whole sheet again after every lateral move: a Windows account's view of the registry, the service list and the filesystem is decided by its token, so what one account cannot see, the next one often can.

> [!important]
> **An empty result is a finding, not a failure** — and on Windows the trap is sharper than on Linux. `Access is denied.` is printed on standard **output**, not standard error, so `2>nul` never hides it and you will see it if it happens. That cuts both ways: a command that prints *nothing at all* really did find nothing, but a command that walks many keys or many services prints the denial only for the ones it tried and skips the rest silently. Registry sweeps and `icacls` on a tree are the two that lie this way.

## The order, and where each step cashes in

| # | The question | Where the hit is cashed in |
|---|---|---|
| 1 | What is this token allowed to do? | [[Windows-Privilege-Abuse]] |
| 2 | Who else lives here? | step 6, then [[Windows-Credential-Harvesting]] |
| 3 | What runs with more privilege than me? | [[Windows-Service-Abuse]] |
| 4 | Can I write to what it runs? | [[Windows-Service-Abuse]] |
| 5 | What runs automatically? | [[Windows-Privilege-Escalation]] |
| 6 | What credentials are lying around? | [[Windows-Credential-Harvesting]], [[PowerShell-History]] |
| 7 | What does a scanner see that I missed? | [[Windows-Automated-Enumeration]] |
| 8 | Which two findings touch the same path? | this note, step 8 |

Steps 1-2 are recon on yourself. Steps 3-5 are the escalation hunt. Steps 6-7 are the second sweep. Step 8 is the only step that produces a shell.

## 1 — What is this token allowed to do

```cmd
whoami /all
```

- `whoami` alone prints the username and stops. `/all` is three commands in one — [[Security-Terms#^sid|SID]], group memberships **and the privileges table**. The privileges table is at the bottom, past a screen of group SIDs, which is exactly why it gets scrolled past.
- If the output is too long to page in your shell, `whoami /priv` prints only the table you came for.

```cmd
systeminfo
```

- The Windows equivalent of `uname -a`: build number, architecture, domain membership, and the hotfix list — the input to any missing-patch search ([[Windows-Automated-Enumeration]]).

## 2 — Who else lives here

```cmd
net user
```

```cmd
net localgroup administrators
```

- The second one is the list you are actually trying to join. Any name here that is not `Administrator` is a human account somebody logs in with, and becoming it is a win.

```cmd
dir C:\Users
```

- Folders here are accounts that have **logged in at least once**, which `net user` does not tell you. A profile folder you can enter is loot; one you cannot is a target.

## 3 — What runs with more privilege than me

The discriminator for all three commands below is the same, and it is **not** "runs as SYSTEM" — almost everything on a Windows host runs as SYSTEM. It is the **path**. Microsoft's own components live under `C:\Windows\`; anything somebody installed afterwards does not. So every command here filters that path out before you read a single line.

```powershell
Get-CimInstance Win32_Service | Where-Object { $_.PathName -notlike "*\Windows\*" } | Select-Object Name,StartName,PathName
```

- The leading `*` is mandatory. `-notlike "\Windows\*"` matches nothing at all, because `PathName` starts with `C:` — so nothing is excluded, the full list comes back, and you believe you filtered. A filter that silently does nothing is worse than no filter.
- `StartName` is the account it runs as; `LocalSystem` is what you want beside a non-Microsoft path.
- Expect 5-15 rows out of roughly 200. That is the list you read line by line.

```cmd
wmic service get name,pathname,startname | findstr /i /v /c:"C:\Windows"
```

- The `cmd` fallback for the same question. `/v` inverts the match, `/i` ignores case, `/c:` keeps the string literal — without `/c:` findstr splits on the spaces and treats each fragment as a separate search term.
- On Windows 11 and Server 2025 `wmic` is gone entirely (`'wmic' is not recognized`). That is a missing tool, not a permission answer — use the PowerShell line above.

```powershell
Get-CimInstance Win32_Process | Where-Object { $_.ExecutablePath -notlike "*\Windows\*" -and $_.ExecutablePath } | Select-Object ProcessId,Name,ExecutablePath
```

- The same discriminator applied to what is running **now** rather than what is registered. `-and $_.ExecutablePath` drops the kernel and system processes that have no readable path — without it they all pass the filter, because `$null -notlike "*\Windows\*"` is true.
- `tasklist /v` is the `cmd` equivalent, but it has no path column, so it cannot be filtered this way. Use it only to attach a username to a process id you already care about.

```cmd
netstat -ano | findstr /c:"LISTENING" | findstr /c:"127.0.0.1"
```

- Two literal filters in a row, and both are needed. The first drops every established connection; the second keeps only what is bound to **loopback** — the services your external scan could never see, which is why they are usually the soft ones.
- `-a` all sockets, `-n` numeric (no DNS lookups to hang on), `-o` the owning process id. Take that id back to `tasklist /svc /fi "PID eq <pid>"` to learn what it is.

## 4 — Can I write to what it runs

```cmd
icacls "C:\Program Files\Vendor App\service.exe"
```

- Read the rights in brackets: `(F)` full control, `(M)` modify, `(W)` write. Read them against the identity in front: `BUILTIN\Users`, `Everyone`, `NT AUTHORITY\Authenticated Users` or your own username means **you**.
- Check the **folder** as well as the file. Write access to the folder lets you rename the binary out of the way and drop yours in, which is as good as writing the file.

```cmd
icacls "C:\Program Files\Vendor App"
```

```cmd
sc qc <servicename>
```

- Prints `BINARY_PATH_NAME` and `SERVICE_START_NAME` for one service. Read the binary path for a space in an **unquoted** path (`C:\Program Files\Vendor App\service.exe` with no quotes) — Windows will try `C:\Program.exe`, then `C:\Program Files\Vendor.exe`, and a writable directory anywhere along that chain is the vector.
- One service at a time is the wrong shape once you have a shell: the sweep that returns **every** unquoted service on the host in one command, and the `StartMode` column that says whether the hit pays out before a reboot, opens [[Windows-Service-Abuse]] vector 2.
- `sc` in PowerShell is an alias for `Set-Content`. In a PowerShell shell you must write `sc.exe`.

```cmd
accesschk64.exe -quvcw "Authenticated Users" *
```

- The shortcut when you can transfer a tool ([[File-Transfer]]): asks the service database directly which services this identity may reconfigure. `SERVICE_CHANGE_CONFIG` in the answer means you can point the service at your own binary without touching a file at all.

## 5 — What runs automatically

Same principle as step 3, different discriminator: Windows ships several hundred of its own tasks and they all live under the task path `\Microsoft\Windows\`. A planted task sits at the root of the tree with a plain name.

```powershell
Get-ScheduledTask | Where-Object { $_.TaskPath -notlike "\Microsoft\*" } | Select-Object TaskName,TaskPath,@{n='RunAs';e={$_.Principal.UserId}},@{n='Runs';e={$_.Actions.Execute}}
```

- Here the leading `*` must **not** be there. `TaskPath` really does start with a backslash, so `-notlike "\Microsoft\*"` is correct and `-notlike "*\Microsoft\*"` would also exclude legitimate nested paths. The rule is not "always add a star" — it is *look at what the field actually contains first*, which is why the two filters in this sheet are shaped differently.
- The two `@{n=...;e={...}}` blocks are calculated columns: `Principal.UserId` and `Actions.Execute` are nested inside the object, so `Select-Object` cannot reach them by name alone. Those two are the whole point — **who it runs as**, and **what it runs**.
- Expect a handful of rows. Every one of them is worth reading.

```cmd
schtasks /query /fo csv /v | findstr /i /v /c:"\Microsoft\Windows\"
```

- The `cmd` fallback, and the format matters: `/fo csv` puts each task on **one line**, so removing the line removes the task. With `/fo list` each task is a paragraph and filtering deletes only its name line, leaving the body behind — that is the version that looks filtered and is not.

```cmd
reg query HKLM\Software\Microsoft\Windows\CurrentVersion\Run
```

- Machine-wide startup entries. `HKLM\...\Run` fires at **logon**, not at boot, and the entry runs as the account that signs in — so a writable target here pays out only when somebody with more privilege than you logs on. That is a wait with no guarantee attached; weigh it against a service you can restart yourself.

```cmd
dir "C:\ProgramData\Microsoft\Windows\Start Menu\Programs\StartUp"
```

## 6 — Credentials lying around

```cmd
cmdkey /list
```

- Stored credentials for other accounts or other hosts. A hit here is used with `runas /savecred /user:<user> "<command>"` — you never see the password, you just spend it.

```powershell
type $env:APPDATA\Microsoft\Windows\PowerShell\PSReadLine\ConsoleHost_history.txt
```

- Everything this account typed into PowerShell, kept in a plain text file by default. Full treatment, including reading **other** users' history files: [[PowerShell-History]].

```cmd
reg query "HKLM\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Winlogon" | findstr /i "AutoAdminLogon Default AutoLogonSID"
```

- Autologon stores the password in the registry as literal text, in a key any user can read. `DefaultPassword` is the prize; `DefaultUserName` and `DefaultDomainName` say whose it is and where to spend it.
- The quotes around the key path are load-bearing — `Windows NT` contains a space, so unquoted `reg` reads it as two arguments and answers `ERROR: Invalid syntax.`, a complaint about your typing that reads exactly like "no such key".
- `findstr /i "a b c"` treats the space-separated strings as alternatives, not as one phrase, so a line matching any of them survives. About thirty stock values live in this key (`Shell`, `Userinit`, `ShutdownFlags`, the whole `SiHost*` family) and this takes three to five lines out of them, because `Default` as a substring catches all three `Default*` values at once and nothing stock contains it.
- Do **not** narrow it with `/v DefaultPassword` instead. When that value is absent `reg` answers `ERROR: The system was unable to find the specified registry key or value.` — the identical sentence you get when the key does not exist and when your token cannot read it, three situations collapsed into one string. Reading the key and filtering keeps them apart.
- Silent-filter trap: `findstr` matching nothing prints nothing and exits quietly, which looks exactly like a key you were denied. No output at all means run the `reg query` once without the pipe before concluding anything.
- What a hit means, and why an `AutoAdminLogon` of `0` is not a reason to skip the key: [[Windows-Credential-Harvesting]].

```cmd
dir /s /b C:\unattend.xml C:\Windows\Panther\Unattend.xml C:\Windows\Panther\Unattend\Unattend.xml C:\Windows\system32\sysprep\sysprep.xml
```

- Deployment answer files. They hold the local administrator password used to build the host, sometimes base64-encoded rather than encrypted. Details: [[Windows-Credential-Harvesting]].

```cmd
findstr /sip /c:"password=" /c:"pwd=" /c:"connectionString" *.xml *.ini *.txt *.config
```

- Searching for the **word** `password` returns documentation, schema files and form labels. Searching for `password=` demands an actual assignment, which is the same discriminator the Linux sheet uses at step 6 and it removes almost all of the noise.
- `/s` recurse, `/i` ignore case, `/p` skip files with unprintable characters — the Windows equivalent of `grep -I`, and without it a matching binary floods the console.
- Run it from a directory that means something — an application folder, a web root, a user profile — not from `C:\`, where it runs for twenty minutes and returns Windows' own templates.

## 7 — Automated, as a second opinion

```cmd
winPEASx64.exe log
```

- Neither this nor Windows ships WinPEAS — fetch it onto Kali once from `https://github.com/peass-ng/PEASS-ng/releases/latest/download/winPEASx64.exe`, then carry it across ([[File-Transfer]]). The download URLs for all four scanners, the obfuscated AV-evasion build, and the run-from-memory trick are in [[Windows-Automated-Enumeration]].
- The `log` argument writes the output to a file beside the binary as well as to the screen, which you want, because the output is far longer than the console buffer.

```powershell
Import-Module .\PrivescCheck.ps1; Invoke-PrivescCheck -Extended
```

- PowerShell-native, so nothing needs to be written to disk as an executable if you can pipe it in. Comparison of all four scanners, and why an attacker-side one sees different things: [[Windows-Automated-Enumeration]].

## 8 — Stop and connect

```text
I am <account>
    ↓ I can write / hold / reconfigure <the thing you control>
    ↓ which <the privileged component> runs, reads or trusts
    ↓ so my code executes as <SYSTEM or the other account>
```

- If that sentence does not close, you do not have a path — you have a list, and the fix is another sweep, not another exploit.
- The pairs that actually occur here: a `LocalSystem` service (3) plus a writable binary or folder (4). A scheduled task (5) plus a writable script (4). A privilege (1) plus a tool that spends it — `SeImpersonatePrivilege` plus a [[Security-Terms#^potato|potato]]. A password (6) plus a username (2). A loopback service (3) plus a credential (6).
- **Prioritise by reversibility, not by excitement.** Reconfiguring a service or overwriting a binary changes the host and can break the thing you need; a credential you can simply spend costs nothing and leaves the host as you found it. Try the credential first, then the writable path, then anything that requires a restart.
- **Validate before you fire.** For a writable-path vector, confirm you can actually restart the trigger (`sc query <name>` for `START_TYPE`, the task's schedule) — a payload that only runs at boot on a host you cannot reboot is not a path.
