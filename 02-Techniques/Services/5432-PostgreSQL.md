---
type: service
platform: any
status: working
fluency: guided
source: thm
updated: 2026-08-30
---

# 5432 — PostgreSQL

PostgreSQL: an enterprise relational database usually bound to localhost, which means you often meet it *after* a foothold, reached through a tunnel rather than across the network. Reach for this note when 5432 shows up locally on a compromised host or at the end of an SSH forward.

## Connecting

**Why now** — you have a database credential (from a config, a connection string, an `.env`) and 5432 is reachable — commonly through a forward you have already stood up. This is where you spend that credential. A successful connection is also proof your tunnel works, which is the second reason to run it early.

```bash
psql -h localhost -U christine -p 1234
```

- `-h localhost` → connect to the locally forwarded port on your own machine, not the target directly. Postgres frequently listens only on `127.0.0.1`, so this is the whole reason a tunnel exists.
- `-p 1234` → the **local** port your forward maps to the remote 5432; it is not 5432 unless you chose that. Point it at the wrong local port and the refusal looks like a credential problem.
- `-U christine` → the database user. `psql` prompts for the password; supply it non-interactively with a `PGPASSWORD=<pass>` prefix when scripting.

**What you will see**

- **Found** — a `christine=>` prompt (the database name then `=>`, or `=#` for a superuser). The `#` versus `>` is worth reading: `#` means you are a superuser, which widens what the next section can do.
- **Empty** — not applicable; a prompt or an error.
- **Error** — `peer authentication failed for user` means Postgres wants to match your **OS** user, not a password — it only happens on a local socket, so connect over TCP with `-h` instead. `no pg_hba.conf entry for host` means your source IP is not permitted — an access-control signal, not a wrong password. `Connection refused` on the local port means the forward is not up or points elsewhere.
- **Noise** — an [[Security-Terms#^tls|SSL]] negotiation notice in the connection banner is routine; you are still connected.

**Then** — a prompt goes to *Walking the databases*. `peer authentication failed` sends you to retry over TCP; `pg_hba.conf` denials and `Connection refused` send you back to [[Pivoting-and-Tunneling]] to fix the forward, and to [[Config-File-Looting]] for the right credential.

## Walking the databases

**Why now** — you are at a `psql` prompt. Postgres uses backslash meta-commands rather than SQL to navigate, and knowing the four that matter turns a prompt into a data sweep in seconds.

```text
\l
\c secrets
\dt
SELECT * FROM flag;
```

- `\l` → list every database. The one with an application name, not `postgres`/`template0`/ `template1`, is where the data is.
- `\c <db>` → connect to that database; the meta-commands that follow act on it.
- `\dt` → list tables in the current database. Forget the `\c` first and `\dt` reports "no relations found" because you are still in the empty default database — which reads as an empty server when it is not.

**What you will see**

- **Found** — a table listing, then rows containing credentials, hashes, tokens or flags.
- **Empty** — `\dt` showing "Did not find any relations." *after* a correct `\c` is a genuinely empty database; the same message before the `\c` is just the wrong database.
- **Error** — `permission denied for table <name>` means the account sees the table exists but cannot read it — a scoped user, so hunt a higher-privileged credential.
- **Noise** — `postgres`, `template0` and `template1` are on every instance; they are the engine's own databases, not target data.

**Then** — hashes go to [[Hash-Cracking]]; plaintext credentials go to every other service and back to [[Config-File-Looting]] to confirm reuse. A superuser prompt (`=#`) additionally opens command execution via `COPY ... FROM PROGRAM`, which belongs on the escalation path once you have confirmed the privilege.

## Reading the output

The recurring trap here is misreading *where* you are connected. A refusal is far more often the tunnel — wrong local port, forward not up — than a bad credential, and an "empty" server is usually the default `postgres` database you never `\c`'d out of. Confirm the forward and the database before you doubt the password; on this port the connection topology causes more lost time than the authentication ever does.

## Next

- [[Pivoting-and-Tunneling]] — the SSH forward that makes 5432 reachable
- [[Config-File-Looting]] — the connection string that carried these credentials
- [[Hash-Cracking]] — hashes pulled from a table get cracked here

## Gaps

- No `COPY ... FROM PROGRAM` command-execution walk-through for a superuser account.
- Nothing on reading server-side files with `pg_read_file()` short of superuser.
