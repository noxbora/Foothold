# 53 — DNS

Domain Name System: the service that maps names to addresses, and on a misconfigured server will hand you the entire internal name map at once. Reach for this note when 53 is open. Subdomain brute forcing against a public name lives in [[Subdomain-Discovery]]; this note is about querying a nameserver you can talk to directly.

## Zone transfer — try this first

```bash
dig axfr domain.htb @target_ip
```

- `axfr` → request a full zone transfer.
- `@target_ip` → ask the **target's own** nameserver. This is the flag that matters: query a public resolver instead and the zone does not exist there at all, so you get an empty answer that looks like a refusal but is really the wrong server.
- `domain.htb` → the zone to pull; you need the domain name first, which the record queries below or the box's web vhost will give you.

## Record queries

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

## nslookup — the no-`dig` equivalent

```bash
nslookup -type=MX example.com 1.1.1.1
```

- `-type=` → the record type (`MX`, `NS`, `TXT`, `A`) — the equivalent of `dig`'s positional record argument.
- trailing `1.1.1.1` → the resolver to ask, the same job as `dig`'s `@server`. Omit it and `nslookup` uses the system resolver, which for an engagement target holds none of the internal records you are after.

> [!note]
> A public resolver (`1.1.1.1`, `8.8.8.8`) keeps a lookup out of your [[Security-Terms#^isp|ISP]]'s logs. Against an engagement target you usually want the opposite: ask the target's own nameserver with `@target_ip`, because internal records do not exist in public DNS at all. Public resolver for privacy, target resolver for enumeration — they are different jobs.
