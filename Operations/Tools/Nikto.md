---
type: tool
platform: web
status: working
fluency: guided
source: lab
updated: 2026-08-30
---

# Nikto

Scans a web server for known vulnerabilities, misconfigurations, outdated software, and dangerous default files. A breadth-first sweep: it tells you *where to look*, not what is exploitable. Loud by design.

## Scan a web service

**Why now** — a port scan found an HTTP or HTTPS service and `-sV` gave you a server banner ([[Nmap]]). You want the fast, wide pass that flags default files, dangerous methods and known-bad versions before you start reading the site by hand. Run it early, let it work while you look at the application yourself.

```bash
nikto -h http://TARGET_IP:8080 -o nikto.txt
```

- `-h` → target host or URL. Include the scheme and port; a bare IP defaults to port 80 and silently misses an app on 8080.
- `-ssl` → force [[Security-Terms#^tls|TLS]]. Against an HTTPS service without it, Nikto tries plaintext and reports the whole host as unreachable — which reads as "nothing here" when the service is fine.
- `-o nikto.txt` → save the report. The scan is long and scrolls; without a saved copy you re-run a five-minute sweep to re-read one line.
- `-Tuning` → restrict to categories (`-Tuning 9` = [[Security-Terms#^sqli|SQLi]] checks only, `-Tuning x 6` excludes the slow ones). Narrows a noisy sweep to the class you care about.

**What you will see**

- **Found** — `+ OSVDB-3233: /icons/README: Apache default file found`, `+ /admin/: This might be interesting`, `+ Server may leak inodes via ETags`, a flagged outdated version with a CVE. Each `+` line is a lead: a path to open by hand or a version to look up.
- **Empty** — very few `+` lines can mean a genuinely hardened server, or that a [[Security-Terms#^waf|WAF]] is answering. If every response looks identical (same code, same size), you are being filtered, not told the host is clean — a different answer that points at WAF evasion, not "move on".
- **Error** — `ERROR: Cannot resolve hostname` is a bad `-h`. `No web server found on host` on a port you know is open usually means the scheme is wrong — add `-ssl` for HTTPS. `+ Host header ... hijacking` and a hang can mean the server only answers to a vhost name, not the IP ([[Virtual-Host-Discovery]]).
- **Noise** — the largest category. Nikto flags on **version strings**, so a backported security patch (Debian/RHEL fixing the bug while keeping the old version number) makes it report CVEs the server is not actually vulnerable to. Every finding is a *candidate*, never a confirmation.

**Then** — an interesting path goes to [[Web-Server-Checks]] to probe by hand. A flagged version with a CVE goes to [[Public-Exploit-Workflow]] to verify before trusting it. Uniform responses (a WAF) mean the automated sweep is blinded — switch to manual, throttled requests. A clean scan does not clear the app: Nikto never touched the application logic, so continue with [[Content-Discovery]].

## Reading the output

Nikto is loud — assume every request is logged and that an [[Security-Terms#^ids|IDS]] or WAF may start answering mid-scan, which quietly turns real findings into uniform noise. Its value is as a fast index of places to look, not a vulnerability report: treat every `+` line as a lead to confirm by hand, and never paste its CVE list into a report without verifying each against the actual running version.

## Next

- [[Web-Server-Checks]] — verify Nikto's findings against the per-server checklist by hand
- [[Nmap]] — the `http-*` [[Security-Terms#^nse|NSE]] scripts overlap with Nikto's method-and-WebDAV checks
- [[Content-Discovery]] — the application-path brute force Nikto does not do

## Gaps

- No `-Plugins` detail: which individual plugins are worth running alone against a known stack.
- Nothing on tuning Nikto down for a monitored target, or running it through a proxy for scope control.
