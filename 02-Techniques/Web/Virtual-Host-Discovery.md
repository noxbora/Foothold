---
type: technique
platform: web
status: working
fluency: guided
source: htb
updated: 2026-08-31
---

# Virtual Host Discovery

One IP address, one open port, and possibly several completely different web applications. A web server picks which site to serve by reading the `Host:` header of the request, so a name that resolves nowhere in DNS can still be a live application — you just have to ask for it by name. This note is how you find those names. Its DNS-based counterpart is [[Subdomain-Discovery]]; same goal, different mechanism, and on a lab box this one is far more often the answer.

> [!important]
> A vhost is a Host-header trick, not a DNS record. Everything you find here is invisible to `nslookup`, `host` and `dig`, and stays unreachable in a browser until you add the name to `/etc/hosts` yourself — one line, `<target IP>  <name>`, on the attacking machine.

## Establish the default response

**Why now** — the server answers **every** Host header you send it; unknown names simply fall through to the default site. That means every word in your list will "succeed", and without knowing the default response you cannot tell a real vhost from the fallback. This one request is what makes the whole technique work.

```bash
curl -s -H 'Host: zz-not-a-real-vhost.htb' http://target.htb/ | wc -c
```

```bash
curl -sI -H 'Host: zz-not-a-real-vhost.htb' http://target.htb/
```

- `-H 'Host: ...'` → the whole technique in one flag. You connect to the IP, but ask for a different site by name
- a name that cannot exist → same rule as any baseline: if you probe with `dev` or `admin` and it happens to be real, you have calibrated your filter against a hit and will filter out the finding
- `| wc -c` → the byte count that `-fs` / `--exclude-length` will take. Record it now
- `-sI` → headers only, on the second call. A `Server:` or `Location:` that changes per vhost is a second discriminator when sizes are too close to separate

**What you will see**

- **Found** — the default site's page, with a stable byte count. That number is the tool for the rest of this note, not a result in itself.
- **Empty** — a zero-length body with a 200 is unusual and worth noting: it often means the default vhost is a stub and every *real* site lives behind a name, which makes this note the main event rather than a side check.
- **Error** — `curl: (7)` means the port is closed. A `400 Bad Request` in response to a hostname with an underscore or an odd character is the server rejecting the header format, not rejecting the site.
- **Noise** — a body that embeds the requested hostname, a timestamp or a [[Security-Terms#^csrf|CSRF]] token changes length on every request. Then byte count is worthless as a filter and you must use word count.

**Then** — carry the byte count into the sweep. If the body varies between two identical requests, skip straight to the `ffuf` section and filter on words rather than size.

## Brute force the Host header

**Why now** — you have the default response and a domain name (from a [[Security-Terms#^tls|TLS]] certificate, a redirect, a page's own links, or simply the box's name). Now you ask the server which other names it knows.

```bash
gobuster vhost -u http://target.htb --domain target.htb --append-domain \
  -w /usr/share/seclists/Discovery/DNS/subdomains-top1million-20000.txt \
  --exclude-length 11952 -t 30
```

- `vhost` → Host-header mode. It does not touch DNS and does not request paths; if you wanted paths you are in the wrong mode and should be in [[Content-Discovery]]
- `--append-domain` → sends `dev.target.htb` rather than the bare word `dev`. **The flag that is easy to omit**, and omitting it makes every request ask for a single-label host that no vhost config matches, so you get a clean run of zero results and conclude wrongly that there are no vhosts. Older gobuster versions appended by default, which is exactly why this trips people
- `--domain` → the base name appended. Get this from the certificate's CN or a redirect, not from a guess; a wrong base domain produces the same silent zero as the flag above
- `--exclude-length 11952` → drop responses of the default page's size. Takes a range too (`--exclude-length 250-320`) when the default varies slightly
- `-t 30` → threads; the same tradeoff as any brute force, and vhost sweeps are noisy by nature

**What you will see**

- **Found** — `Found: dev.target.htb Status: 200 [Size: 8452]` — a size that is **not** the default. A redirect to a login page, or a completely different title, is the same signal.
- **Empty** — the server may genuinely host one site, which closes this route honestly. But check the two silent failures first: no `--append-domain`, or a base domain the server does not recognise. An entirely empty vhost run with a 20k wordlist is more often a flag mistake than a clean host.
- **Error** — every single word reported as found means your exclusion is wrong, not that you struck gold. `the server returns a status code that matches the provided options` is gobuster's way of saying the same thing, and it wants a filter rather than a retry.
- **Noise** — the default page answering under every name is the whole noise problem here. Wildcard vhost configuration produces it deliberately. Size-based filtering is the answer, and when sizes collide, compare page titles instead.

**Then** — a discovered name goes into `/etc/hosts` on your own machine and then into [[Content-Discovery]], because a new vhost is a new application with its own paths, its own login and its own bugs. Empty here sends you to [[Subdomain-Discovery]] for the DNS side, and to re-reading the TLS certificate: `subjectAltName` frequently lists names no wordlist contains.

## The same sweep with ffuf, when sizes collide

**Why now** — gobuster's exclusion works on byte length only. If the default page embeds the hostname you asked for, every response is a different length and size filtering collapses. `ffuf` filters on word and line counts too, which are stable across that variation.

<!-- dup-ok -->
```bash
ffuf -w /usr/share/seclists/Discovery/DNS/subdomains-top1million-5000.txt \
  -u http://target.htb -H 'Host: FUZZ.target.htb' -fw 1274 -mc all
```

- `-H 'Host: FUZZ.target.htb'` → `FUZZ` goes in the **header**, not the URL. This is the distinction between this note and [[Content-Discovery]]: same tool, same wordlist format, one keyword moved. Put `FUZZ` in the URL by mistake and you will spend the run fuzzing paths and wondering why the results look like a directory listing
- `-fw 1274` → filter by word count, the number to use when the body length varies per request
- `-mc all` → show every status. Vhosts frequently answer 301 or 401 rather than 200, and the default `-mc` set will hide them
- `-fs`, `-fl` → the size and line equivalents, when word count is the one that collides

**What you will see**

- **Found** — a row whose word count differs from the crowd. Confirm it by hand with a single `curl -H 'Host: ...'` before adding it to `/etc/hosts`; one confirmation costs a second and saves you from mapping a phantom.
- **Empty** — with a correct filter this is a real answer for this wordlist. Try a larger list once, then stop; vhost names are usually short and ordinary (`dev`, `staging`, `admin`, `internal`, `portal`, the company's own product names).
- **Error** — `FUZZ keyword not found in the request` means it is missing from both the URL and the headers. Two filters at once (`-fs` and `-fw`) combine and will hide everything.
- **Noise** — some servers answer any unknown Host with a redirect to the canonical name. That redirect is identical for every word, so it filters out cleanly once you notice it.

**Then** — same destination as above: `/etc/hosts`, then [[Content-Discovery]] against the new name. If the new vhost presents a login form, [[Authentication-Attacks]] is the next surface.

## Reading the output

The whole note rests on one comparison: this response versus the default response. That means a vhost sweep can only ever be as good as the baseline you took, and re-taking the baseline is the correct first move whenever the results look absurd in either direction — everything found, or nothing found.

Two findings that combine into more than their sum: a name in the TLS certificate's `subjectAltName` that your wordlist never contained, plus a vhost sweep that came back empty, means the naming here is custom and a generic list will never reach it. That is the moment to stop brute forcing and start reading the application's own words — links, comments, JavaScript bundles, email addresses — which is [[Custom-Wordlist-Attack-Chain]].

## Next

- [[Content-Discovery]] — enumerate the new vhost's paths once it resolves
- [[Subdomain-Discovery]] — the DNS-based counterpart to this Host-header technique

## Gaps

- Nothing on HTTPS vhosts and [[Security-Terms#^sni|SNI]]: the certificate served can differ per name, and `curl --resolve` is the cleaner tool there than `/etc/hosts`.
- No coverage of vhosts that only differ by port, or by protocol on the same name.
- Nothing on reading `subjectAltName` out of a certificate as a source of candidate names, which is often faster than any wordlist.
