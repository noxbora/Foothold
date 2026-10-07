---
type: service
platform: any
status: working
fluency: guided
source: htb
updated: 2026-10-08
---

# 3306 — MySQL

MySQL (and its fork [[Security-Terms#^mariadb|MariaDB]]): the database behind most PHP web apps. Reach for this note when 3306 is open and you hold — or can guess — a database credential. The two prizes are the data itself and, with the right privilege, reading and writing files on the host through the database.

## Connecting

**Why now** — 3306 is open and you either found a DB credential in a web config or want to test the classic misconfiguration: a `root` account with no password. That test is one command and occasionally hands you the whole database.

```bash
mysql -h <ip> -P 3306 -u root
```

- `-h` → the target host. Without it the client tries a local Unix socket and fails with a socket error that has nothing to do with the remote server.
- `-u root` → the account. **No** `-p` here is deliberate: it attempts a passwordless login. Add `-p` (no value) to be prompted, or `-p'<pass>'` inline once you hold a password.
- `--skip-ssl-verify-server-cert` → add this if the connection is refused over a self-signed certificate; the handshake, not the credential, is what failed.

**What you will see**

- **Found** — a `mysql>` prompt. A passwordless `root` login succeeding is a misconfiguration, not luck — record it as a finding before you touch the data.
- **Empty** — not applicable; you get a prompt or an error.
- **Error** — `Access denied for user 'root'@'<you>' (using password: NO)` means passwordless is off — try credentials pulled from config looting before brute forcing. `using password: YES` with a password you trust means that pair is simply wrong. `Host '<you>' is not allowed to connect` is a host-based restriction, not a credential problem — the account may work from the box itself but not from your IP.
- **Noise** — a MariaDB banner where you expected MySQL is not a different situation; the client, the SQL and the privilege model are the same for everything in this note.

**Then** — a prompt goes to *What the account can do*. `Access denied` goes to [[Config-File-Looting]] (a `wp-config.php`, `.env` or `config.php` holds the DB credentials) and to [[Source-Code-Disclosure]] where server-side source names the user and password directly.

## What the account can do

**Why now** — you are at a `mysql>` prompt. Before reading tables, find out whether this account can only *read data* or can *touch the filesystem*, because the second is a foothold and the first is only loot.

```text
SELECT version();
SELECT current_user();
SELECT * FROM information_schema.user_privileges WHERE grantee LIKE CONCAT("'", SUBSTRING_INDEX(CURRENT_USER(),'@',1), "'@%");
```

- `information_schema.user_privileges` → lists the global grants your account holds. This is the query that tells you whether `FILE` is present, which is the whole point of running it.

**What you will see**

- **Found** — a `FILE` privilege in the grant list. That turns database access into host file read (`LOAD_FILE('/etc/passwd')`) and write (`SELECT ... INTO OUTFILE '/var/www/html/x.php'`), which is a webshell if you know a served path.
- **Empty** — no `FILE` privilege is the common, well-configured case. It closes the file-write route and leaves you with data only — still worth sweeping for credentials.
- **Error** — `SELECT command denied to user ... for table 'user_privileges'` is rare but means the account is scoped so tightly it cannot even read its own grants; try `SHOW GRANTS;` instead.
- **Noise** — `USAGE` in the grants means "no privileges" — it is the placeholder grant every account has, not a capability.

Then read the data itself:

```text
SHOW DATABASES;
USE <database>;
SHOW TABLES;
SELECT * FROM users;
```

- these run on the database you `USE`; skip `information_schema`, `performance_schema`, `mysql` and `sys` — they are the engine's own, and the application database is the one with a real name.

**Then** — a `FILE` privilege plus a known web root goes to [[SQL-Injection]] for the `INTO OUTFILE` webshell and `--os-shell` escalation. Password hashes in a `users` table go to [[Hash-Cracking]]. Plaintext credentials go to every other service, since reuse across the database and shell accounts is common enough to try every time.

## Reading the output

The decision this port turns on is *read* versus *write*. A database you can only query is loot: sweep it for credentials and move on. A database whose account holds `FILE` is a foothold: it reads any file the MySQL service user can, and writes a webshell into any directory that user can write. Run the privilege query before you get absorbed in the tables, because it decides which of those two situations you are actually in.

## Next

- [[Config-File-Looting]] — `wp-config.php`, `.env`, `config.php` hold the DB credentials
- [[SQL-Injection]] — `INTO OUTFILE` webshell and `--os-shell` escalation
- [[Source-Code-Disclosure]] — server-side source names the DB user and password
- [[Hash-Cracking]] — password hashes pulled from a table get cracked here

## Gaps

- Nothing on [[Security-Terms#^udf|UDF]] (user-defined function) privilege escalation when the DB runs as root.
- No `mysqldump` for pulling a whole schema out for offline review.
