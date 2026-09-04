---
type: technique
platform: windows
status: working
fluency: guided
source: lab
updated: 2026-08-30
---

# PowerShell History (PSReadLine)

[[Security-Terms#^psreadline|PSReadLine]] writes every command typed at a PowerShell prompt into a plain text file, one file per user, and nothing rotates or truncates it. That makes it the cheapest credential source on a Windows host: no exploit, no privilege, one `type`. It belongs at the front of the sweep on every shell you land in, and again after every account you switch to.

## What did this account type

**Why now** — you have a shell and no password. Before touching services, tokens or CVEs you check whether whoever used this account already typed a credential at the prompt, because that costs one command and skips the entire escalation. You are hoping for a password passed on a command line, which PowerShell users do constantly because the alternative is a prompt.

```cmd
type %userprofile%\AppData\Roaming\Microsoft\Windows\PowerShell\PSReadline\ConsoleHost_history.txt
```

- `type` → cmd.exe's `cat`: print the file to the screen.
- `%userprofile%` → expands to the **current** user's folder, so this one-liner only ever reads your own history. **cmd.exe only.** PowerShell does not expand `%VAR%`; there the path is taken literally, and the failure looks like a missing history file rather than the wrong shell. In PowerShell write `$Env:userprofile` instead, or run the line through `cmd /c`.
- `PSReadline` in the path → spelled with a lowercase `l`, and it is a directory, not the module name. Getting the case wrong is harmless on [[Security-Terms#^ntfs|NTFS]]; getting the *level* wrong (dropping `\PowerShell\`) produces the same path-not-found as a genuinely empty profile.

**What you will see**

- **Found** — a line with a password sitting in the open: `-AsPlainText -Force 'Passw0rd!'`, `net use \\host\share /user:svc_backup <password>`, a connection string with `Password=`, or `$p = 'something'` two lines above a `New-Object System.Net.NetworkCredential`. Any hostname, share or service name in the file is a second finding even without a password attached.
- **Empty** — the file exists and holds a few boring lines: real, and it closes this account only. It says nothing about the other profiles on the host, which is what the next section is for.
- **Error** — `The system cannot find the file specified.` means history logging was off, the PSReadLine module was never loaded, or the profile is fresh — **not** that the user typed nothing. `Access is denied.` on your own profile means you are running as a service account with no interactive profile of its own; that is a wrong-account signal, not a clean host.
- **Noise** — most of the file is ordinary work: `cd`, `dir`, `Get-ChildItem`, `ipconfig`, failed tab-completions. `Get-Credential` on a line carries **no** password — it prompts interactively, so the secret never reaches the history. Likewise a `ConvertTo-SecureString` reading from a file or a stored key gives you a pointer, not a secret; only the `-AsPlainText` form has the password inline.

**Then** — a password goes straight to the accounts you know about: try it with `runas`, over [[5985-WinRM]], or against [[3389-RDP]]. A hostname or share name with no password goes to [[Windows-Credential-Harvesting]] to find the matching secret elsewhere on disk. Empty or an error sends you to the next section — the account you landed as is rarely the interesting one.

## Which other users' history can I read

**Why now** — your own history came back thin, and the account you compromised first is almost never the account that types passwords. This asks the filesystem which history files exist at all, and lets the ACLs tell you which ones you are allowed to open.

```cmd
dir /s /b C:\Users\*ConsoleHost_history.txt
```

- `/b` → bare format: full paths only, no header or byte counts, so the output is a list you can work down.
- `/s` → recurse. Without it you search only `C:\Users\` itself, which contains no files at all, and the empty result reads as "no history anywhere on the host".
- `C:\Users\` → not `%userprofile%`. The point of this command is to leave your own profile.

**What you will see**

- **Found** — one path per profile that has ever run PowerShell. Every path naming an account that is not you is a target; the admin or service account in that list is the one to open first.
- **Empty** — genuine on a host where PowerShell has only ever been used by one account, and it closes this technique. It does not close credential hunting: the files in [[Windows-Credential-Harvesting]] live outside `C:\Users\`.
- **Error** — `Access is denied.` on individual subdirectories while other lines still print is the normal case: `dir` continues past what it cannot read. The denials are themselves a map of which profiles are locked to you.
- **Noise** — `Default`, `Public`, and `DefaultAppPool` are stock profiles. `Administrator` with a zero-byte history is a profile that exists but was never used interactively.

**Then** — take each path you can read into the next section. A path you cannot read is not a dead end; it is a named target that becomes readable the moment you escalate, so write it down and come back after [[Windows-Privilege-Escalation]].

## Reading another account's history

**Why now** — the listing named a profile belonging to somebody more privileged than you, and you want to know whether they typed their own password at a prompt. This is the same file, with the variable removed because the variable would send you back to yourself.

```cmd
type C:\Users\<username>\AppData\Roaming\Microsoft\Windows\PowerShell\PSReadline\ConsoleHost_history.txt
```

- `<username>` → substitute the account name from the listing above. Nothing here expands; the literal path is the whole point.
- The path is per-user by design, so there is no single command that reads all of them at once as an unprivileged account. Repeat it per profile.

**What you will see**

- **Found** — the same shapes as your own history, and worth more, because this account is one you cannot already run commands as. A password here converts directly into a session.
- **Empty** — a readable file with nothing useful in it. Real, and it closes that account.
- **Error** — `Access is denied.` is the interesting failure: the file **exists** and NTFS is refusing you. That is a permission answer, not a content answer, and it means this file becomes loot the moment your privileges change. `The system cannot find the file specified.` on a profile that exists means that user never ran PowerShell.
- **Noise** — a history full of the same commands you already ran is your own profile; check you actually substituted the username rather than leaving `%userprofile%` in the line.

**Then** — a recovered password is spent in [[Windows-Privilege-Escalation]] if the account is privileged, or carried sideways to another host if it is not. `Access is denied.` on a profile you care about is a reason to finish the escalation first and come back — the same file will open with a better token. Nothing anywhere means the credential is in a config file instead: [[Windows-Credential-Harvesting]] and [[Config-File-Looting]].

## Reading the output

Two things this note cannot tell you on its own.

A password with no username attached is half a finding. The history file records what was typed, not who it belonged to, so match every secret against the account list from `net user` and against the file's own owner before deciding whose it is. Password reuse across accounts on the same host is common enough that trying it everywhere is cheaper than reasoning about it.

Nothing here proves a negative. A silent history means logging was off or the work happened in `cmd.exe`, which keeps no equivalent file. The absence of history is a gap in your visibility, not evidence about the host.

## Next

- [[Windows-Credential-Harvesting]] — the other four places a Windows password sits on disk
- [[Config-File-Looting]] — the file-based counterpart to shell-history credentials
- [[Windows-Privilege-Escalation]] — where a recovered credential gets spent

## Gaps

- `cmd.exe` keeps no persistent history at all, and this note has no substitute for it — `doskey /history` shows only the current session.
- Nothing on the PowerShell **transcript** and **script block** logs (`Microsoft-Windows-PowerShell/Operational`, event ID 4104), which record far more than PSReadLine when an administrator has enabled them.
- No coverage of clearing or tampering with the file to stay quiet; this note only reads.
