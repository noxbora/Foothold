# theHarvester

[[Security-Terms#^osint|OSINT]] tool for gathering emails, subdomains, hostnames and employee names from public sources — search engines, [[Security-Terms#^pgp|PGP]] key servers, certificate transparency, Shodan. **Passive by default:** it queries third parties, not the target, so it touches nothing you are scoped against and leaves no trace on the box.

## Harvest a domain

```bash
theHarvester -d target.com -b crtsh,bing,duckduckgo,hackertarget -l 500
```

- `-d` → target domain.
- `-b` → the sources to query. `all` uses every module but is slow and includes ones that need keys; a named list (`crtsh` for certs, `bing`/`duckduckgo` for pages, `hackertarget` for DNS) is faster and more predictable.
- `-l` → cap results per source. Without it a broad run against a large domain can take a long time; the cap keeps a first pass quick.
- `-f report` → write HTML/JSON/XML. Worth it — the terminal output is easy to lose and you will want to diff a later run.
