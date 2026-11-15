# 27017 — MongoDB

MongoDB: a [[Security-Terms#^nosql|NoSQL]] document database that, in its classic default, ships with **no authentication at all**. Reach for this note when 27017 is open — the first question is simply whether it lets you in, because an unauthenticated Mongo instance is a data breach you reach with one command.

## Connecting

```bash
./mongosh mongodb://{target_IP}:27017
```

- `./mongosh` → the shell run from the current directory; use the system `mongosh` if it is on your `PATH`. The older `mongo` binary connects the same way if `mongosh` is unavailable.
- `mongodb://` → the connection URI scheme. Add `<user>:<pass>@` before the host once you hold a credential: `mongodb://user:pass@{target_IP}:27017`.

## Walking the data

```text
show dbs
use <database>
show collections
db.<collection>.find().pretty()
```

- `show dbs` → lists databases with their sizes. Skip the stock `admin`, `config` and `local`; the one somebody named after their application is where the data is.
- `.find().pretty()` → dumps a collection formatted for reading. On a large collection add a limit — `db.users.find().limit(5).pretty()` — or the screen fills before you see the schema.
