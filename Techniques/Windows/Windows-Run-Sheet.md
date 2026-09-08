---
type: technique
platform: windows
status: working
fluency: guided
source: reading
updated: 2026-09-08
---

# Windows Run Sheet

What to run on a Windows host you just landed on, in order, one command per block. Keep this open beside the shell and run nothing else until step 8. The Linux twin is [[Linux-Run-Sheet]].

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

**Why now** — you have a shell and nothing else. On Windows an account's power is not its group list alone: it is the list of **privileges** attached to its token, and one of them can end the box with no exploit and no writable file. Checking costs one command.

```cmd
whoami /all
```

- `whoami` alone prints the username and stops. `/all` is three commands in one — [[Security-Terms#^sid|SID]], group memberships **and the privileges table**. The privileges table is at the bottom, past a screen of group SIDs, which is exactly why it gets scrolled past.
- If the output is too long to page in your shell, `whoami /priv` prints only the table you came for.

```cmd
systeminfo
```

- The Windows equivalent of `uname -a`: build number, architecture, domain membership, and the hotfix list — the input to any missing-patch search ([[Windows-Automated-Enumeration]]).

**What you will see**

- **Found** — in the privileges table, any of `SeImpersonatePrivilege`, `SeAssignPrimaryTokenPrivilege`, `SeBackupPrivilege`, `SeRestorePrivilege`, `SeTakeOwnershipPrivilege`, `SeDebugPrivilege`, `SeLoadDriverPrivilege`. In the group list, `BUILTIN\Administrators` (you are already admin, you just need to get past [[Security-Terms#^uac|UAC]]), `Backup Operators`, or `DnsAdmins`.
- **Empty** — a token with only the four stock privileges (`SeChangeNotifyPrivilege`, `SeIncreaseWorkingSetPrivilege`, `SeShutdownPrivilege`, `SeUndockPrivilege`) is genuine and common. It closes the token route and nothing else.
- **Error** — `whoami` missing entirely means a stripped or very old host; `echo %USERNAME%` and `net user %USERNAME%` get you most of the way back.
- **Noise** — the `State: Disabled` column beside a privilege is **not** a negative answer. A disabled privilege is still held and can be enabled from your own process; see [[Windows-Privilege-Abuse]]. Ignore the dozens of `Mandatory Label` and group SIDs.

**Then** — a listed abusable privilege goes straight to [[Windows-Privilege-Abuse]] and usually ends the box there. Nothing listed means continue to step 2.

## 2 — Who else lives here

**Why now** — the target is rarely `SYSTEM` directly; it is the next account along. You need their names now, so that a password you trip over in step 6 has somebody to belong to.

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

**What you will see**

- **Found** — a handful of real names. Write them down; from here every filename, share and password gets matched against this list.
- **Empty** — `net user` returning only the stock accounts (`Administrator`, `Guest`, `DefaultAccount`, `WDAGUtilityAccount`) means local accounts are not the story — the interesting identities are domain ones, so add `net user /domain` and `net group "Domain Admins" /domain`.
- **Error** — `System error 5 has occurred. Access is denied.` from `net localgroup` happens in a restricted shell or with a filtered token. `Get-LocalGroupMember Administrators` in PowerShell often answers where `net` will not.
- **Noise** — the four stock accounts above are on every Windows host. `dir C:\Users` also lists `Public` and `Default`; neither is a person.

**Then** — carry the list into steps 5, 6 and 8. A name with no password is half a pair; step 6 looks for the other half.

## 3 — What runs with more privilege than me

**Why now** — this is where Windows and Linux diverge, and getting the order wrong is what makes a Windows box feel unsolvable. Linux gives you a file-first sweep (`find -perm -4000`); Windows has no equivalent, because Windows has no SUID bit. Here you enumerate the **privileged thing first**, then test in step 4 whether you can touch it. Sweeping the disk for writable files before you know what runs is how you spend an hour reading permissions on files nobody executes.

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

**What you will see**

- **Found** — anything that survived the filter. A service under `C:\Program Files`, `C:\Program Files (x86)`, or somewhere odd like `C:\Apps` or `C:\Temp`, with `StartName` reading `LocalSystem`. Or a loopback port that was not in your nmap results.
- **Empty** — a filtered service list genuinely can be empty: a stock host with no third-party software installed. Confirm the filter is not lying by running the same command without the `Where-Object` once and checking the count is around 200 rather than zero. An empty loopback list in `netstat` is a real answer and closes the internal-service route ([[Pivoting-and-Tunneling]]).
- **Error** — `Access is denied.` from `wmic` means your token cannot query the service database remotely-shaped; fall back to `sc query state= all` and `reg query HKLM\SYSTEM\CurrentControlSet\Services`.
- **Noise** — none, and that is the point: the `C:\Windows\` exclusion is exactly the noise, removed before you read. What remains that is still not interesting: vendor updaters (Google Update, Adobe ARM) and antivirus, which are third-party and legitimately privileged. Recognise them by name and move on.

**Then** — take every non-stock `pathname` you found and run step 4 on it. A loopback port goes to [[Pivoting-and-Tunneling]]. This step alone escalates nothing.

## 4 — Can I write to what it runs

**Why now** — step 3 handed you a list of privileged executables. This step asks the only question that turns one of them into a shell: can this account replace it, or replace something it loads on the way. This pairing — a privileged process plus a path you control — is the whole of Windows service escalation.

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

**What you will see**

- **Found** — `(F)` or `(M)` for `Users`, `Everyone`, `Authenticated Users` or your account, on a binary or a folder that a `LocalSystem` service uses. Or an unquoted path with a space and a writable directory in the chain.
- **Empty** — `icacls` listing only `Administrators`, `SYSTEM` and `Users:(RX)` is the normal, secure answer. `RX` is read and execute, **not** write. Take that service off the list and go back to step 3's list for the next one.
- **Error** — `The system cannot find the path specified.` almost always means quoting: a path with spaces needs the whole path in double quotes. `Access is denied.` from `icacls` on a folder means you cannot even read its permissions, which is itself an answer about how locked down the host is.
- **Noise** — an unquoted path with **no** space in it is immune, and so is a quoted executable followed by unquoted arguments (`"C:\...\svc.exe" -k netsvcs`) — only a space inside the executable path itself counts. `(RX)`, `(R)` and `(GR)` for `Users` are read rights and appear everywhere. Inheritance markers `(I)`, `(OI)`, `(CI)` describe how the entry propagates, not what you may do; read the letter after them.

**Then** — a writable binary or folder goes to [[Windows-Service-Abuse]], which covers the three vectors and the reason a plain reverse-shell binary does not survive as a service. Nothing writable here means the path is a schedule or a credential, so continue to step 5.

## 5 — What runs automatically

**Why now** — steps 3 and 4 looked at what is running now. This one looks at what will run later without anyone typing anything: a scheduled task or a startup entry firing as another account is the same vulnerability with a delay on it.

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

**What you will see**

- **Found** — a task whose `Task To Run` points at a `.bat`, `.ps1`, `.vbs` or `.exe` outside `C:\Windows`, with a `Run As User` that is not you. The moment you have that path, run step 4's `icacls` on both the file and its folder — that is the pairing.
- **Empty** — the important case. `schtasks` shows you the tasks your token may read; tasks registered by another user in their own folder are simply absent, with **no denial printed**. Empty here means "not visible to this account", not "no task exists". If steps 3-5 are all empty, the answer is a credential, so weight step 6 heavily.
- **Error** — `ERROR: Access is denied.` on a single task is a per-task permission answer and tells you that task exists and is interesting. `The system cannot find the file specified` from `reg query` means that key does not exist on this host, which is normal for the `Wow6432Node` variants.
- **Noise** — removed by the filter. A few Microsoft-authored updater tasks are registered outside `\Microsoft\` because they install per-user, so they survive the filter; they are stock, and you skip them by name.

**Then** — a writable task target goes to [[Windows-Privilege-Escalation]] (scheduled tasks section). An empty sweep goes to step 6.

## 6 — Credentials lying around

**Why now** — steps 1-5 came back thin, or you have a username with no password. Becoming another account with their real credential is quieter and more reliable than any exploit, and on a chained host it is usually the intended path.

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

**What you will see**

- **Found** — an assignment with a specific value nobody would ship in a manual, in a file belonging to software somebody configured. A stored credential in `cmdkey`. A command line in the history file containing a password as an argument.
- **Empty** — `cmdkey` reporting no stored credentials is genuine and common. An empty history file usually means this account has only ever used `cmd.exe`, not that nothing was typed.
- **Error** — a registry sweep such as `reg query HKLM /f password /t REG_SZ /s` walks keys your token cannot open and, unlike a single-key query, **prints no denial for the ones it skipped**. Its empty result therefore means "not visible to this account". Query specific keys, as above, when you want an answer you can trust.
- **Noise** — much smaller once you demand `password=` rather than `password`, but not zero: shipped config templates still contain `password=` with an empty or placeholder value. A line assigning a value somebody clearly chose is the finding; `password=`, `password=changeme` and `password=%PASSWORD%` are not.

**Then** — a password alone is half an answer; step 2 gave you the names it might belong to. Spend it: `runas /user:<user> cmd.exe`, or against [[5985-WinRM]] and [[3389-RDP]] from Kali, which gets you a real terminal instead of this one. Password reuse between a service account and a human account is common enough to always be worth one attempt.

## 7 — Automated, as a second opinion

**Why now** — the manual pass is done and you have either a path or a list of empties. Run the scanner now to check your work, not to replace it: run first and you learn nothing and bury the answer in two thousand lines.

```cmd
winPEASx64.exe log
```

- Neither this nor Windows ships WinPEAS — fetch it onto Kali once from `https://github.com/peass-ng/PEASS-ng/releases/latest/download/winPEASx64.exe`, then carry it across ([[File-Transfer]]). The download URLs for all four scanners, the obfuscated AV-evasion build, and the run-from-memory trick are in [[Windows-Automated-Enumeration]].
- The `log` argument writes the output to a file beside the binary as well as to the screen, which you want, because the output is far longer than the console buffer.

```powershell
Import-Module .\PrivescCheck.ps1; Invoke-PrivescCheck -Extended
```

- PowerShell-native, so nothing needs to be written to disk as an executable if you can pipe it in. Comparison of all four scanners, and why an attacker-side one sees different things: [[Windows-Automated-Enumeration]].

**What you will see**

- **Found** — red and yellow highlighted lines are what the tool rates as probable. Everything else is context it printed because it could.
- **Empty** — these tools are never empty. If nothing printed, it did not run.
- **Error** — the binary being deleted the moment it lands is antivirus, not a broken transfer; that is what the PowerShell-native option is for. `Import-Module` refused with an execution-policy message is bypassed per-process, not globally — see [[Windows-Automated-Enumeration]].
- **Noise** — most of the output. The tool cannot see intent, so it flags every non-default configuration as if it were a vector.

**Then** — for every highlight, say out loud what privileged component it involves and what you control about it. If you cannot finish that sentence, it is not a finding.

## 8 — Stop and connect

**Why now** — you have a page of notes and no shell. Nothing above escalates on its own. Every Windows escalation is a **pair**: something privileged, and something about it you control.

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

**What you will see**

- **Found** — two findings that name the same path or the same account. That is the box.
- **Empty** — no pair after a full sweep means one of your empties was a permission, not an absence. The likeliest liars are step 5 and the registry half of step 6, in that order. Re-run those specifically, then [[Stuck-Checklist]].
- **Error** — the pair closes but the payload fails. That is not an enumeration problem; it is [[Windows-Service-Abuse]]'s `exe-service` point or a wrong architecture, and the sheet has done its job.
- **Noise** — an interesting-looking finding that pairs with nothing is worth less than a boring one that does. Four empties and one writable folder is a better position than twelve highlights.

**Then** — once you are the new account, come back to step 1 and run the whole sheet again as them. Their token, their registry view, their task list.

## Rarely — worth one command, not worth a step

**Why now** — the eight steps above cover what is on most hosts. These are cheap enough to run when the sheet came back empty, and each is one command.

```cmd
reg query HKLM\SOFTWARE\Policies\Microsoft\Windows\Installer /v AlwaysInstallElevated
```

```cmd
reg query HKCU\SOFTWARE\Policies\Microsoft\Windows\Installer /v AlwaysInstallElevated
```

- Both must return `0x1`. One alone does nothing, which is why checking only the machine key produces a false negative. Full vector: [[Windows-Privilege-Escalation]].

```cmd
wmic product get name,version,vendor | findstr /i /v /c:"Microsoft"
```

- Third-party software and its version, fed to a public exploit search ([[Public-Exploit-Workflow]]). The `findstr` drops Microsoft's own redistributables, which are most of the list and none of the answer.
- It lists only MSI-installed software, so it is blind to anything unzipped into a folder. The PowerShell form, and the three other places software hides, are in [[Vulnerable-Software]].

```cmd
net share
```

```powershell
Get-ChildItem C:\Users,C:\ProgramData -Include *.kdbx,*.ppk,*.pfx,*.rdp -Recurse -File -ErrorAction SilentlyContinue
```

- Key and session files: [[Security-Terms#^keepass|KeePass]] databases, PuTTY keys, certificates, saved RDP connections. Scoped to `C:\Users` and `C:\ProgramData` on purpose — that is where a person's files are, and searching `C:\` instead takes minutes and returns Windows' own certificate store.
- `-Include` only works alongside `-Recurse` (or a path ending in `\*`). Written without it the command returns **nothing at all**, silently, which reads exactly like a clean host.
- `-File` drops directories that happen to match. `-ErrorAction SilentlyContinue` is the `2>/dev/null` of PowerShell, and it hides denials exactly as thoroughly.

**What you will see**

- **Found** — `0x1` from both `AlwaysInstallElevated` keys; a share nobody should have exported; a `.kdbx` or `.ppk` in a user profile.
- **Empty** — the normal answer for all of these. They are lottery tickets, not steps, and an empty result here says nothing about the host.
- **Error** — `The system was unable to find the specified registry key or value` means the policy was never set, which is the same as not enabled.
- **Noise** — `net share` always lists the administrative shares `ADMIN$`, `C$` and `IPC$`. They are stock and you cannot reach them as this account anyway.

**Then** — a hit here goes to the note named beside it. No hit means go back to step 8 and re-examine which of your empties was really a denial.

## Reading the output

Two things this sheet as a whole cannot tell you.

The first is **who else can see what you cannot**. Almost every step here is filtered by your token, silently. That is why the sheet says to run it again after every lateral move, and why "I already checked scheduled tasks" is only true for the account that checked them.

The second is **timing**. Every command photographs one instant. A task that runs at 03:00, a service that starts on demand and exits, an installer that only touches disk while it runs — none of them appear. If the sheet is empty twice and the host still feels like it has an answer, the missing dimension is usually time.

## Next

- [[Windows-Privilege-Abuse]] — when step 1 hands you a privilege
- [[Windows-Service-Abuse]] — when steps 3 and 4 pair up
- [[Windows-Credential-Harvesting]] — when the answer is a password rather than a permission
- [[Linux-Run-Sheet]] — the same eight questions on the other platform

## Gaps

- Domain enumeration is not here. Once the host is domain-joined, `net user /domain` is the door into a different sheet entirely — that belongs with [[Active-Directory-Lateral-Movement]] and is not yet written.
- Nothing on staying quiet. Every command here is loud in an event log and the note does not say which are loudest.
- No coverage of `SeDebugPrivilege` or `SeLoadDriverPrivilege`, both named in step 1 but neither cashed in anywhere in the vault.
