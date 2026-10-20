# Subdomain Discovery

Names that resolve in DNS and belong to the target: `dev.`, `staging.`, `mail.`, `vpn.`, `old.`. Each one is a separate application with its own patch level and its own mistakes, and the forgotten ones are the point — nobody hardens a host they no longer remember owning. Passive sources first, because they send no packets to the target at all; active brute forcing after, because it is loud and only worth spending once you know what the passive sources missed.

The Host-header counterpart, for names that resolve nowhere but still serve a site, is [[Virtual-Host-Discovery]]. On an isolated lab network that note is almost always the productive one, because there is no public DNS to query.

> [!important] Tool generation
> `sublist3r`, `dnsenum` and `dnsrecon` below are what cert labs still ship, and the concepts transfer, but they are the previous generation. Current equivalents are `subfinder` (passive aggregation), `amass` (passive, active and graph), `dnsx` (resolution and brute force), and `ffuf` against the Host header. Learn the method here; reach for those when the box is not a lab.

## Passive — certificate transparency

```bash
curl -s 'https://crt.sh/?q=%25.target.com&output=json' \
  | jq -r '.[].name_value' | tr '[:upper:]' '[:lower:]' | sed 's/^\*\.//' | sort -u
```

- `%25.target.com` → `%25` is a URL-encoded `%`, which is the SQL wildcard crt.sh matches on. Ask for the bare domain instead and you get certificates for that exact name only — a handful of rows instead of the entire history, and it looks like a thin result rather than a wrong query
- `output=json` → without it you get an HTML page, and `jq` fails with a parse error that reads like a network problem
- `.[].name_value` → the field holding the names. One certificate often carries many, newline separated inside the field
- `sed 's/^\*\.//'` → strips the leading `*.` from wildcard entries, which are not hosts
- `sort -u` → the same name recurs once per renewal; without this a dozen names look like hundreds

## Passive — aggregating the OSINT sources

Search engines and certificate logs together, written to a file. Nothing here touches the target:

```bash
sublist3r -d target.com -o subdomains.txt
```

Restrict to named engines when one of them is rate-limiting you and poisoning the whole run:

```bash
sublist3r -d target.com -e google,bing,yahoo
```

Adding `-b` changes what this command *is* — the run stops being passive and starts brute forcing DNS directly:

```bash
sublist3r -d target.com -b -t 50
```

Port-scanning what it found is loud, and belongs in its own deliberate step rather than bolted onto enumeration:

```bash
sublist3r -d target.com -p 80,443
```

- `-d` → the target domain, and the only required flag
- `-o` → write to a file. These lists are inputs to later stages and you will not want to rerun
- `-b` → **the flag that changes what this command is.** Without it, nothing reaches the target and the run is invisible. With it, direct DNS brute force starts and the noise level jumps to match `dnsrecon`'s brute mode. Adding `-b` reflexively turns a stealth step into a loud one
- `-e` → limit to specific engines. Useful when one is rate-limiting you and poisoning the run
- `-t` → threads, and only meaningful together with `-b`

## Active — brute force against the target's own DNS

The zone transfer first, always — one query, and a hit makes everything below it unnecessary:

```bash
dnsrecon -d domain.htb -t axfr
```

The standard record set: A, MX, NS, SOA, TXT:

```bash
dnsrecon -d domain.htb -t std
```

The brute force, which is the loud one:

```bash
dnsrecon -d domain.htb -t brt -D /usr/share/seclists/Discovery/DNS/subdomains-top1million-5000.txt
```

Reverse lookups across a range, on an internal network:

```bash
dnsrecon -r 10.10.10.0/24
```

- `-t axfr` → **run this before any brute force.** A misconfigured secondary hands over the entire zone in one request, which makes the wordlist irrelevant. It costs one query
- `-t brt` → the brute-force module, and the loud one
- `-D` → the wordlist, required by `-t brt`. Omit it and dnsrecon exits complaining about a missing dictionary, which is easy to misread as the scan finding nothing
- `-r` → reverse lookups across a range. On an internal network this often names hosts nothing else revealed, because [[Security-Terms#^ptr-record|PTR]] records are maintained by the people who built the network
- `-n` → query a specific nameserver. Point it at the target's own DNS server rather than your resolver, or you are asking a cache what the target thinks

For the same job with a different tool, and when you want the zone transfer attempted against every nameserver automatically:

```bash
dnsenum --dnsserver target_ip --enum -f /usr/share/seclists/Discovery/DNS/namelist.txt domain.htb
```

- `--dnsserver` → ask the target's nameserver directly. Without it you query your own resolver, which knows nothing about an internal-only zone and returns a clean, entirely misleading empty
- `--enum` → shorthand that turns on zone transfer, brute force and reverse lookup together
- `-f` → the wordlist for brute forcing

## Confirm a name actually resolves

```bash
for s in $(cat candidates.txt); do host "$s" | grep -q 'has address' && echo "$s"; done
```

- `host <name>` → returns the A record, or `not found: 3(NXDOMAIN)`
- `grep -q 'has address'` → keeps only names that resolved to an IPv4 address, dropping CNAMEs that dead-end and [[Security-Terms#^nxdomain|NXDOMAIN]] lines
- resolve a name you invented as a control → if that also "has address", the zone is wildcarded and this filter is passing everything
