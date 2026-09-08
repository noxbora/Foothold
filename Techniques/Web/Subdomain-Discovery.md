---
type: technique
platform: web
status: working
fluency: guided
source: htb
updated: 2026-09-03
---

# Subdomain Discovery

Names that resolve in DNS and belong to the target: `dev.`, `staging.`, `mail.`, `vpn.`, `old.`. Each one is a separate application with its own patch level and its own mistakes, and the forgotten ones are the point — nobody hardens a host they no longer remember owning. Passive sources first, because they send no packets to the target at all; active brute forcing after, because it is loud and only worth spending once you know what the passive sources missed.

The Host-header counterpart, for names that resolve nowhere but still serve a site, is [[Virtual-Host-Discovery]]. On an isolated lab network that note is almost always the productive one, because there is no public DNS to query.

> [!important] Tool generation
> `sublist3r`, `dnsenum` and `dnsrecon` below are what cert labs still ship, and the concepts transfer, but they are the previous generation. Current equivalents are `subfinder` (passive aggregation), `amass` (passive, active and graph), `dnsx` (resolution and brute force), and `ffuf` against the Host header. Learn the method here; reach for those when the box is not a lab.

## Passive — certificate transparency

**Why now** — you have a domain name and have not yet touched the target. Every publicly trusted [[Security-Terms#^tls|TLS]] certificate issued for it is in a public log, and hostnames go into certificates. This is the single highest-yield question you can ask without the target learning you asked.

```bash
curl -s 'https://crt.sh/?q=%25.target.com&output=json' \
  | jq -r '.[].name_value' | tr '[:upper:]' '[:lower:]' | sed 's/^\*\.//' | sort -u
```

- `%25.target.com` → `%25` is a URL-encoded `%`, which is the SQL wildcard crt.sh matches on. Ask for the bare domain instead and you get certificates for that exact name only — a handful of rows instead of the entire history, and it looks like a thin result rather than a wrong query
- `output=json` → without it you get an HTML page, and `jq` fails with a parse error that reads like a network problem
- `.[].name_value` → the field holding the names. One certificate often carries many, newline separated inside the field
- `sed 's/^\*\.//'` → strips the leading `*.` from wildcard entries, which are not hosts
- `sort -u` → the same name recurs once per renewal; without this a dozen names look like hundreds

**What you will see**

- **Found** — hostnames you did not know existed, often including internal-sounding ones (`jenkins.`, `git.`, `vpn.`, `dev.`). Names appearing in old certificates and nowhere else are the most interesting: they are systems somebody stopped maintaining.
- **Empty** — genuine and common for a lab domain, an internal-only domain, or any `.htb` / `.thm` name. Certificate transparency only sees publicly trusted certificates, so an empty result says nothing whatsoever about the target and is not a reason to stop.
- **Error** — `jq: error ... Invalid numeric literal` means you were served HTML, so the `output=json` parameter did not survive shell quoting. `curl: (6) Could not resolve host` means your own DNS is broken, not the target's.
- **Noise** — wildcards (`*.target.com`), names belonging to a [[Security-Terms#^cdn|CDN]] or a hosting provider rather than the target, and names that no longer resolve at all. Every candidate is a guess until you resolve it.

**Then** — resolve every candidate before treating it as live (the resolution section below). Names that resolve go to [[Content-Discovery]]. Empty here sends you to the active brute force, and on a lab network directly to [[Virtual-Host-Discovery]].

## Passive — aggregating the OSINT sources

**Why now** — certificate logs are one source. Search engines, passive DNS databases and public scan datasets are others, and they overlap only partly. Aggregating them costs nothing and takes a minute.

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

**What you will see**

- **Found** — a deduplicated list of hostnames across all sources. Cross-check against the crt.sh output; a name only one source knows is worth more attention, not less.
- **Empty** — expected for anything that is not a real public domain. It closes the passive route and nothing else.
- **Error** — search-engine blocking is the usual failure and shows as zero results from that engine while others work. API-key warnings are informational; the free sources still run.
- **Noise** — parked domains, third-party services on the target's name (`shop.`, `status.`, `mail.` pointing at a SaaS provider). They resolve, they are real, and they are not the target you are allowed to test. Check where each one points before you attack it.

**Then** — everything found goes through resolution below. If passive sources produced names but none resolve, they are historical, and the interesting question becomes whether the application still accepts them as a Host header — [[Virtual-Host-Discovery]].

## Active — brute force against the target's own DNS

**Why now** — passive sources gave you nothing, or gave you names you suspect are incomplete, and you have decided the noise is acceptable. Brute forcing asks the authoritative server directly, which is the only way to find a name that was never in a certificate or a search index.

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

**What you will see**

- **Found** — from `axfr`, the complete zone: every record, in one response. This is the jackpot and it ends the enumeration. From `brt`, one line per name that resolved, with its address.
- **Empty** — from `axfr`, the normal and correct behaviour of a healthy server (`Transfer failed` / `REFUSED`); it closes that route and nothing more. From `brt`, an empty result after a large wordlist genuinely suggests there are no additional names in DNS — which is exactly when [[Virtual-Host-Discovery]] becomes the answer, because vhosts never appear in DNS.
- **Error** — `Could not resolve` on every word means you are querying the wrong nameserver; add `-n` or `--dnsserver`. A timeout on every request means UDP/53 is filtered from where you are standing.
- **Noise** — **wildcard DNS is the big one.** A zone with a `*` record resolves every name you invent, so the tool reports thousands of "subdomains", all pointing at one address. Test for it by resolving a name you made up: if `zz-no-such-host.target.com` answers, every result in this section is worthless until you filter by that address.

**Then** — a successful zone transfer goes to [[53-DNS]], which is where that finding is worked properly. A list of resolved names goes to [[Content-Discovery]], one sweep per name. Wildcard DNS means discard the brute-force output entirely and switch to [[Virtual-Host-Discovery]].

## Confirm a name actually resolves

**Why now** — you have candidates from sources that report names, not living hosts. Half of them are historical. Resolving them is one command, and it is the difference between a target list and a wish list.

```bash
for s in $(cat candidates.txt); do host "$s" | grep -q 'has address' && echo "$s"; done
```

- `host <name>` → returns the A record, or `not found: 3(NXDOMAIN)`
- `grep -q 'has address'` → keeps only names that resolved to an IPv4 address, dropping CNAMEs that dead-end and [[Security-Terms#^nxdomain|NXDOMAIN]] lines
- resolve a name you invented as a control → if that also "has address", the zone is wildcarded and this filter is passing everything

**What you will see**

- **Found** — a shortlist of names that resolve. Group them by address: several names on one IP is the ordinary case and tells you they are vhosts on one server.
- **Empty** — every candidate is historical. That is still a finding: it dates the target's infrastructure and, on a lab, it points hard at Host-header discovery instead.
- **Error** — `host: command not found` on a minimal system; `dig +short <name>` does the same job.
- **Noise** — names resolving to `127.0.0.1`, to RFC1918 addresses you cannot reach, or to a third-party provider. Resolving is not the same as being in scope or being reachable.

**Then** — names that resolve to the target's address range go to [[Content-Discovery]]. Names that resolve elsewhere need a scope check before you touch them. Names that do not resolve are the input to [[Virtual-Host-Discovery]], where DNS is irrelevant.

## Rarely — worth one command, not worth a step

**Why now** — the brute force returned hundreds of names and you do not believe them, or it returned nothing and you want to know whether the wordlist was the problem.

```bash
host thisnamedoesnotexist12345.target.com
```

- A wildcard record answers for every name under the domain, so a brute force against it returns the entire wordlist as hits. This one query tells you whether every result you just collected is real or worthless, and it costs a second.
- If it resolves, the address it returns is the wildcard's address. Filter that address out of your results and what remains is the genuine list.

```bash
curl -s "http://web.archive.org/cdx/search/cdx?url=*.target.com&output=text&fl=original&collapse=urlkey" | head -40
```

- Names that existed once and were never cleaned up. A staging or admin host retired from public listings often still resolves internally, and nothing else on this page will find it.
- Cap the output. This returns thousands of lines on a large domain and the useful part is the distinct hostnames at the top.

**What you will see**

- **Found** — a resolving nonsense name, which invalidates the brute force; or an old hostname that still answers.
- **Empty** — no wildcard is the good outcome, and it means the brute-force results above can be trusted as they are.
- **Error** — a network failure on the archive query means no outbound access from where you are working, not an empty archive.
- **Noise** — the archive returns full URLs including paths and parameters. Only the hostname matters here.

**Then** — a wildcard sends you back to the confirmation section above with the wildcard address as a filter. An old hostname goes to [[Virtual-Host-Discovery]], because a name that no longer resolves may still be served by address.

## Reading the output

Passive and active are not two ways of doing the same thing; they see different worlds. Passive sources know what was published — certificates, search indexes, scan data — so they find old names and miss internal ones. Brute force knows what the server will answer for, so it finds internal names and misses anything not in your wordlist. An empty result from one says nothing about the other, and the mistake that wastes an afternoon is treating an empty passive run as a verdict on the domain.

The other whole-note trap is wildcard DNS, because it fails in the flattering direction: it does not return nothing, it returns everything, and a page of green results feels like progress. Resolve one invented name before you trust any list this note produced.

## Next

- [[Virtual-Host-Discovery]] — names that share one IP may still be separate apps by Host header
- [[53-DNS]] — a zone transfer, when it works, returns every name at once
- [[Content-Discovery]] — once a subdomain is confirmed, enumerate its paths

## Gaps

- No coverage of `subfinder` / `amass` flags, which is what the callout above says you should actually be using outside a lab.
- Nothing on permutation generation (`altdns`, `dnsgen`) — deriving `dev2`, `dev-old`, `staging2` from names you already found, which is where brute force stops and inference starts.
- No note on scope: a resolving name owned by a third party is not automatically in scope, and this note does not say how to check.
