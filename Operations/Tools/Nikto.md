# Nikto

Scans a web server for known vulnerabilities, misconfigurations, outdated software, and dangerous default files. A breadth-first sweep: it tells you *where to look*, not what is exploitable. Loud by design.

## Scan a web service

```bash
nikto -h http://TARGET_IP:8080 -o nikto.txt
```

- `-h` → target host or URL. Include the scheme and port; a bare IP defaults to port 80 and silently misses an app on 8080.
- `-ssl` → force [[Security-Terms#^tls|TLS]]. Against an HTTPS service without it, Nikto tries plaintext and reports the whole host as unreachable — which reads as "nothing here" when the service is fine.
- `-o nikto.txt` → save the report. The scan is long and scrolls; without a saved copy you re-run a five-minute sweep to re-read one line.
- `-Tuning` → restrict to categories (`-Tuning 9` = [[Security-Terms#^sqli|SQLi]] checks only, `-Tuning x 6` excludes the slow ones). Narrows a noisy sweep to the class you care about.
