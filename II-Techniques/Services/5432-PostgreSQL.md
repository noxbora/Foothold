# 5432 — PostgreSQL

PostgreSQL: an enterprise relational database usually bound to localhost, which means you often meet it *after* a foothold, reached through a tunnel rather than across the network. Reach for this note when 5432 shows up locally on a compromised host or at the end of an SSH forward.

## Connecting

```bash
psql -h localhost -U christine -p 1234
```

- `-h localhost` → connect to the locally forwarded port on your own machine, not the target directly. Postgres frequently listens only on `127.0.0.1`, so this is the whole reason a tunnel exists.
- `-p 1234` → the **local** port your forward maps to the remote 5432; it is not 5432 unless you chose that. Point it at the wrong local port and the refusal looks like a credential problem.
- `-U christine` → the database user. `psql` prompts for the password; supply it non-interactively with a `PGPASSWORD=<pass>` prefix when scripting.

## Walking the databases

```text
\l
\c secrets
\dt
SELECT * FROM flag;
```

- `\l` → list every database. The one with an application name, not `postgres`/`template0`/ `template1`, is where the data is.
- `\c <db>` → connect to that database; the meta-commands that follow act on it.
- `\dt` → list the tables in the current database. Forget the `\c` first and `\dt` answers "Did not find any relations." because you are still standing in the empty default database, which reads as an empty server when it is not.
- `\dt` also shows only what the schema search path covers, so a database whose tables live in another schema answers exactly the same way with the tables sitting right there. `\dn` lists the schemas and `\dt *.*` lists across all of them.
