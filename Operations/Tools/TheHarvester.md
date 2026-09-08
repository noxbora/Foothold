---
type: tool
platform: any
status: working
fluency: guided
source: lab
updated: 2026-08-30
---

# theHarvester

[[Security-Terms#^osint|OSINT]] tool for gathering emails, subdomains, hostnames and employee names from public sources — search engines, [[Security-Terms#^pgp|PGP]] key servers, certificate transparency, Shodan. **Passive by default:** it queries third parties, not the target, so it touches nothing you are scoped against and leaves no trace on the box.

## Harvest a domain

**Why now** — you have a target domain and no credentials, and you want raw material before you touch the infrastructure: real employee names to turn into usernames, email formats to confirm a naming convention, subdomains to feed the next scan. This is a first move, run before anything that sends a packet at the target.

```bash
theHarvester -d target.com -b crtsh,bing,duckduckgo,hackertarget -l 500
```

- `-d` → target domain.
- `-b` → the sources to query. `all` uses every module but is slow and includes ones that need keys; a named list (`crtsh` for certs, `bing`/`duckduckgo` for pages, `hackertarget` for DNS) is faster and more predictable.
- `-l` → cap results per source. Without it a broad run against a large domain can take a long time; the cap keeps a first pass quick.
- `-f report` → write HTML/JSON/XML. Worth it — the terminal output is easy to lose and you will want to diff a later run.

**What you will see**

- **Found** — blocks headed `[*] Emails found` and `[*] Hosts found`, listing real addresses (`j.smith@target.com`) and subdomains (`vpn.target.com`, `mail.target.com`). The email format is the prize: it tells you every other employee's likely address.
- **Empty** — no results is **not** proof of no footprint. It usually means the passive sources have nothing indexed, or the richest ones are silent for lack of a key (below). A small, obscure or freshly registered domain legitimately returns little; re-run with different `-b` sources before concluding.
- **Error** — `Read timed out` or `... returned 429` is a source rate-limiting you, not a failure of the tool — drop that source or slow down. `Missing API key` on `shodan`, `hunter`, `securitytrails` means those modules did nothing; configure the key or exclude them so their silence does not look like an empty result.
- **Noise** — [[Security-Terms#^cdn|CDN]] and hosting-provider hostnames (`*.cloudflare`, `*.akamai`) that belong to infrastructure, not the target. Parked-domain and catch-all addresses. Names harvested from unrelated people who merely mention the domain.

**Then** — harvested names and emails go to [[Custom-Wordlist-Attack-Chain]] to become username candidates for spraying. Subdomains go to [[Subdomain-Discovery]] to resolve and probe. An empty return sends you to the active half of recon — DNS and cert transparency queried directly — since the passive index simply may not have this target.

## Reading the output

Passive by design, so the results are only as fresh and complete as the third parties queried — an empty return says the public index is thin, never that the target has no footprint. The value is the **names and emails**: they are the raw material for username permutations and password spraying, which is where an OSINT list actually cashes in. The richest sources (`shodan`, `hunter`, `securitytrails`) stay silent until an API key is configured, so a "quiet" run is often just an unconfigured one.

## Next

- [[Custom-Wordlist-Attack-Chain]] — turn harvested names and emails into username candidates
- [[Subdomain-Discovery]] — the hostname half of the same OSINT step

## Gaps

- No coverage of configuring API keys (`~/.theHarvester/api-keys.yaml`) for the paid sources.
- Nothing on validating harvested emails (catch-all detection) before spraying them.
