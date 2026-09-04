---
type: service
platform: any
status: working
fluency: guided
source: lab
updated: 2026-08-30
---

# 27017 — MongoDB

MongoDB: a [[Security-Terms#^nosql|NoSQL]] document database that, in its classic default, ships with **no authentication at all**. Reach for this note when 27017 is open — the first question is simply whether it lets you in, because an unauthenticated Mongo instance is a data breach you reach with one command.

## Connecting

**Why now** — nmap shows 27017 and MongoDB's historic default is to bind with authentication off. This is the cheapest possible check: if it connects with no prompt, you already have every document on the server.

```bash
./mongosh mongodb://{target_IP}:27017
```

- `./mongosh` → the shell run from the current directory; use the system `mongosh` if it is on your `PATH`. The older `mongo` binary connects the same way if `mongosh` is unavailable.
- `mongodb://` → the connection URI scheme. Add `<user>:<pass>@` before the host once you hold a credential: `mongodb://user:pass@{target_IP}:27017`.

**What you will see**

- **Found** — a `test>` (or `>`) prompt with no password asked. That silent entry **is** the finding: an unauthenticated database. Do not move on — walk it in the next section.
- **Empty** — not applicable; you either land at a prompt or are refused.
- **Error** — `MongoServerError: command requires authentication` means auth is enabled and you need a credential. `MongoNetworkError: connect ECONNREFUSED` means nothing is on 27017 despite the scan, or it is bound to loopback and reachable only through a tunnel.
- **Noise** — a connection warning about an unencrypted transport or an access-control notice is Mongo's own advisory, not a failure; you are still connected.

**Then** — a prompt goes to *Walking the data*. `requires authentication` sends you to [[Config-File-Looting]] — application configs carry the Mongo connection string with its credentials embedded. `ECONNREFUSED` on an open-per-nmap port goes to [[Pivoting-and-Tunneling]].

## Walking the data

**Why now** — you are at an unauthenticated prompt. Now find where the interesting documents live, because Mongo hides nothing behind further permissions once you are in.

```text
show dbs
use <database>
show collections
db.<collection>.find().pretty()
```

- `show dbs` → lists databases with their sizes. Skip the stock `admin`, `config` and `local`; the one somebody named after their application is where the data is.
- `.find().pretty()` → dumps a collection formatted for reading. On a large collection add a limit — `db.users.find().limit(5).pretty()` — or the screen fills before you see the schema.

**What you will see**

- **Found** — a database with an application name, a `users` or `accounts` collection, documents containing usernames, password hashes, tokens or session data.
- **Empty** — only `admin`, `config`, `local` present means the instance is running but unused; a real answer that closes the loot route without closing the *access* finding.
- **Error** — `MongoServerError: not authorized on <db> to execute command` appears when auth is on and your account is scoped to one database — you are in, but not everywhere.
- **Noise** — the three system databases are on every instance and hold Mongo's own metadata, not target data.

**Then** — password hashes go to [[Hash-Cracking]]. Plaintext credentials or tokens go to whatever service they unlock, and to [[Config-File-Looting]] to confirm reuse. A scoped `not authorized` sends you back to hunt a higher-privileged credential.

## Reading the output

Two judgements govern this port, and the first one is the reason not to move on too quickly.

**Access here is binary, and the access itself is the finding.** MongoDB has no permission layer waiting behind the prompt: once a connection is accepted without a credential, every database on the server is readable, and there is no second gate to test. So the result is decided at the connect, not at the data — an instance holding nothing but the three stock databases is exactly as misconfigured as one holding a `users` collection, and it is reported the same way. Walking the data tells you what the exposure is worth; it does not tell you whether there is one.

**A reachable 27017 is itself evidence, not just an opportunity.** Modern MongoDB binds to loopback by default, so a port answering from another machine means somebody deliberately changed the bind address. That edit is made in the same configuration file, in the same sitting, as the authentication setting — which is why a Mongo you can reach at all is far more often a Mongo you can enter than the base rate would suggest. Treat `requires authentication` as the surprise, and go looking for the credential in [[Config-File-Looting]] rather than assuming the route is closed.

## Next

- [[Config-File-Looting]] — app configs carry the Mongo connection string and its credentials
- [[Pivoting-and-Tunneling]] — 27017 is often bound to localhost and only reachable through a tunnel
- [[Hash-Cracking]] — password hashes pulled from a collection get cracked here

## Gaps

- No NoSQL injection (authentication bypass via `$ne`/`$gt` operators in a web app front-end).
- Nothing on `mongodump` for pulling a whole database out at once for offline analysis.
