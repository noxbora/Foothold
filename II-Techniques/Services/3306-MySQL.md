# 3306 — MySQL

MySQL (and its fork [[Security-Terms#^mariadb|MariaDB]]): the database behind most PHP web apps. Reach for this note when 3306 is open and you hold — or can guess — a database credential. The two prizes are the data itself and, with the right privilege, reading and writing files on the host through the database.

## Connecting

```bash
mysql -h <ip> -P 3306 -u root
```

- `-h` → the target host. Without it the client tries a local Unix socket and fails with a socket error that has nothing to do with the remote server.
- `-u root` → the account. **No** `-p` here is deliberate: it attempts a passwordless login. Add `-p` (no value) to be prompted, or `-p'<pass>'` inline once you hold a password.
- `--skip-ssl-verify-server-cert` → add this if the connection is refused over a self-signed certificate; the handshake, not the credential, is what failed.

## What the account can do

```text
SELECT version();
SELECT current_user();
SELECT * FROM information_schema.user_privileges WHERE grantee LIKE CONCAT("'", SUBSTRING_INDEX(CURRENT_USER(),'@',1), "'@%");
```

- `information_schema.user_privileges` → lists the global grants your account holds. This is the query that tells you whether `FILE` is present, which is the whole point of running it.

Then read the data itself:

```text
SHOW DATABASES;
USE <database>;
SHOW TABLES;
SELECT * FROM users;
```

- these run on the database you `USE`; skip `information_schema`, `performance_schema`, `mysql` and `sys` — they are the engine's own, and the application database is the one with a real name.
