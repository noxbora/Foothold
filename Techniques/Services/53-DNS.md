---
type: service
platform: any
status: working
fluency: guided
source: htb
updated: 2026-08-31
---

# 53 — DNS

Domain Name System: the service that maps names to addresses, and on a misconfigured server will hand you the entire internal name map at once. Reach for this note when 53 is open. Subdomain brute forcing against a public name lives in [[Subdomain-Discovery]]; this note is about querying a nameserver you can talk to directly.

## Zone transfer — try this first

**Why now** — 53 is open and a nameserver is meant to replicate its zone only to its own secondaries. If it will replicate to *you*, you get every record — every internal host, every subdomain — in a single reply. It is rare, high value, and the one thing most worth attempting before anything else on this port.

```bash
dig axfr domain.htb @target_ip
```

- `axfr` → request a full zone transfer.
- `@target_ip` → ask the **target's own** nameserver. This is the flag that matters: query a public resolver instead and the zone does not exist there at all, so you get an empty answer that looks like a refusal but is really the wrong server.
- `domain.htb` → the zone to pull; you need the domain name first, which the record queries below or the box's web vhost will give you.

**What you will see**

- **Found** — a long list of records dumped at once: `A`, `NS`, `MX`, `CNAME`, `TXT`, often naming internal hosts you had no other way to discover. This is the whole prize.
- **Empty** — a reply with only the `SOA` record and nothing else means the transfer was allowed in form but the zone is minimal, or you asked the wrong server. Confirm the domain and the `@server` before concluding anything.
- **Error** — `Transfer failed.` or `; Transfer failed.` is the **normal, well-configured** case: [[Security-Terms#^axfr|AXFR]] is restricted to secondaries. `connection timed out; no servers could be reached` means 53/tcp is filtered — zone transfers use TCP, not the UDP most DNS rides on.
- **Noise** — a `communications error ... connection refused` on the UDP port does not rule out AXFR; the transfer needs TCP, so retry rather than trusting a UDP refusal.

**Then** — a successful transfer's internal hostnames go to [[Virtual-Host-Discovery]] (names pointing at one IP may be separate vhosts) and each new host back into your scan queue. A failed transfer goes to *Record queries* below, then to [[Subdomain-Discovery]] to brute the names the server would not simply hand over.

## Record queries

**Why now** — the zone transfer was refused, so now you pull records one type at a time. You also need the domain name and nameservers before AXFR will work, and these queries are where they come from.

```bash
dig ns domain.htb @target_ip
```

```bash
dig CH TXT version.bind @target_ip
```

- `ns` → the authoritative nameservers for the zone; their names sometimes leak internal hostnames.
- `CH TXT version.bind` → a Chaos-class query that asks BIND to name its own version. An old version string is a lead for [[Public-Exploit-Workflow]].

> [!warning] `ANY` is usually refused now
> `dig any domain.htb @target_ip` once returned every record type at once. Since RFC 8482 most resolvers answer `ANY` with a minimal `HINFO` record instead of the full set. An empty or `HINFO`-only reply means the server declined the query — not that the zone is empty. Enumerate record types individually.

**What you will see**

- **Found** — an `ANSWER SECTION` listing the records you asked for. `NS` records naming hosts like `ns1.internal.domain.htb` are leads in their own right.
- **Empty** — a `status: NOERROR` with a zero-count `ANSWER SECTION` means the server answered and that record does not exist — a real answer. A `status: NXDOMAIN` means the *name* does not exist, which is different: you have the wrong domain.
- **Error** — `status: REFUSED` means the server will not answer you for that name at all (often a recursion or [[Security-Terms#^acl|ACL]] restriction), distinct from an empty answer. `version.bind` returning nothing just means the admin hid the version — not that the query failed.
- **Noise** — a public resolver happily answering for `domain.htb`-style names it should not know is the resolver making something up or you hitting a wildcard; verify against the target's own nameserver.

**Then** — nameserver and domain names feed straight back into the *Zone transfer* attempt above. A version string goes to [[Public-Exploit-Workflow]]. Names that resolve go to [[Virtual-Host-Discovery]].

## nslookup — the no-`dig` equivalent

**Why now** — you are on a Windows box, or a host where `dig` is not installed, and need the same lookups. `nslookup` ships nearly everywhere and does the job with different syntax.

```bash
nslookup -type=MX example.com 1.1.1.1
```

- `-type=` → the record type (`MX`, `NS`, `TXT`, `A`) — the equivalent of `dig`'s positional record argument.
- trailing `1.1.1.1` → the resolver to ask, the same job as `dig`'s `@server`. Omit it and `nslookup` uses the system resolver, which for an engagement target holds none of the internal records you are after.

> [!note]
> A public resolver (`1.1.1.1`, `8.8.8.8`) keeps a lookup out of your [[Security-Terms#^isp|ISP]]'s logs. Against an engagement target you usually want the opposite: ask the target's own nameserver with `@target_ip`, because internal records do not exist in public DNS at all. Public resolver for privacy, target resolver for enumeration — they are different jobs.

**What you will see**

- **Found** — a `Non-authoritative answer:` block (or an authoritative one from the target's own server) listing the records.
- **Empty** — `** server can't find <name>: NXDOMAIN` is the name not existing; a query that returns the server but no records is the record type not existing. Same distinction as `dig`.
- **Error** — `connection timed out; no servers could be reached` is the resolver unreachable or 53 filtered, not a missing record.
- **Noise** — the `Server:`/`Address:` header naming *which resolver answered* is not part of the answer; read the section below it.

**Then** — same destinations as the `dig` queries: [[Virtual-Host-Discovery]], [[Subdomain-Discovery]], [[Public-Exploit-Workflow]].

## Reading the output

The distinction that governs this whole port is **"refused" versus "empty"**. A refused transfer or a `REFUSED` status is the server declining to answer you — the data exists and is protected, so the move is to find another way at it (brute the names, try TCP, find the right server). An empty `NOERROR` answer is the server telling you the record genuinely does not exist — a real finding that closes that line. DNS makes those two look almost identical, and treating a refusal as an absence is how you walk away from a zone that was one TCP retry from opening.

## Next

- [[Subdomain-Discovery]] — when the zone transfer fails, brute force the names instead
- [[Virtual-Host-Discovery]] — names that resolve to the same IP may still be separate vhosts

## Gaps

- No DNS cache snooping, and nothing on DNS as an exfiltration or C2 channel.
- `fierce` / `dnsenum` (which automate transfer-plus-brute in one run) are not covered.
