---
type: tool
platform: web
status: working
fluency: guided
source: lab
updated: 2026-08-31
---

# Curl and Wget

Two HTTP clients for two jobs. **curl** probes and interacts — it prints the response to stdout, so you read status codes, headers and bodies and send crafted requests. **wget** fetches and mirrors — it writes to a file by default. The split (curl to stdout, wget to disk) is the thing to keep straight; most "why did nothing print / why is there no file" confusion is reaching for the wrong one.

## Probe: is it there, and what does it answer?

**Why now** — a port is open on HTTP and you want to know what the server is and how it responds before loading anything in a browser: the status code, the server header, whether a path exists. This is the cheapest possible look at a web service.

```bash
curl -I http://TARGET_IP/
```

```bash
curl -s -o /dev/null -w "%{http_code}\n" http://TARGET_IP/admin
```

- `-I` → HEAD request: headers only. Fast identification of the server, framework and redirects without pulling the body.
- `-s` → silent: drop the progress meter so it does not pollute scripted output.
- `-o /dev/null -w "%{http_code}\n"` → throw away the body, print **only** the status code. This is the backbone of any bulk check — it is how you tell `200` from `301` from `403` across a wordlist without reading a single body.
- `-k` → accept a self-signed or expired certificate. **Required** against the certs common in labs; without it an HTTPS probe dies with `SSL certificate problem` and you wrongly read the service as down.
- `-L` → follow redirects. Without it a `301`/`302` shows you the redirect's tiny body, not the destination — so you see a blank page and conclude the path is empty when it moved.

**What you will see**

- **Found** — `-I` prints a status line and headers (`Server: Apache/2.4.41`, `X-Powered-By: PHP/7.4`, a `Set-Cookie`, a `Location:`). The `http_code` probe prints a bare `200` or `301` for a path that exists.
- **Empty** — a `000` from the `http_code` probe means curl never got a response at all — wrong port, host down, or a [[Security-Terms#^tls|TLS]] failure swallowed by `-s` (re-run without `-s -o` to see it). A `403` is not empty: the path exists and you are being denied, which is a different answer than `404`.
- **Error** — `curl: (7) Failed to connect` is nothing listening on that port. `curl: (60) SSL certificate problem` is the missing `-k`. `curl: (6) Could not resolve host` is a name that needs a `/etc/hosts` entry — common when the app only answers to a vhost ([[Virtual-Host-Discovery]]).
- **Noise** — a friendly `200` page that is actually a catch-all error page or a [[Security-Terms#^waf|WAF]] block page. Check the `size_download`: a wall of identical `200`s at the same byte size is a wildcard responder, not a directory full of hits.

**Then** — an identified server goes to [[Web-Server-Checks]] for the per-server probes. The `http_code` one-liner scales straight into [[Content-Discovery]] for path brute forcing. A vhost resolution error goes to [[Virtual-Host-Discovery]].

## Interact: send data, carry a session

**Why now** — you have found an endpoint and need to send it something specific: login credentials to test, a cookie to reuse a session you captured, a file to test an upload, a header to spoof. Curl lets you shape the exact request a browser would make, and repeat it.

```bash
curl -X POST -d "user=admin&pass=test" -b "PHPSESSID=abc123" http://TARGET_IP/login
```

```bash
curl -F "file=@shell.php" http://TARGET_IP/upload
```

- `-X POST -d "..."` → send form data as a POST. `-d` implies POST, but naming `-X` keeps it explicit when you are reading back a command later.
- `-b "name=value"` → send a cookie — this is how you replay a session token pulled from a capture ([[TShark]]) or from another response.
- `-F "file=@localfile"` → multipart upload, the `@` reading the file from disk. The tool for testing an upload vulnerability from the command line.
- `-A "<string>"` → set the User-Agent, for a filter that keys on it.
- `-v` → verbose: shows the full request and response including headers, so you can see exactly what you sent when a request behaves unexpectedly. The first thing to add when a POST "does nothing".

**What you will see**

- **Found** — a response body or a `Set-Cookie`/`Location` that shows the action took: a redirect to a dashboard after a good login, an "upload successful" message, a reflected value.
- **Empty** — a `200` that returns the **login page again** is a failed login, not an empty response — the app re-served the form. Read the body, not just the code; a form-reflected error lives there.
- **Error** — a `405 Method Not Allowed` means the endpoint does not take POST (or you guessed the wrong verb — try the one the form actually uses). `411 Length Required` or `415` on an upload means a missing or wrong `Content-Type`; let `-F` set it rather than forcing `-H`. A `419`/`403` on a POST often means a missing [[Security-Terms#^csrf|CSRF]] token the form expected.
- **Noise** — a reflected parameter that looks like it "worked" but is just your input echoed back with no state change. Confirm the effect (a session cookie, a redirect, a created file), not the echo.

**Then** — a working login or session goes to [[Authentication-Attacks]] to script across a credential list. A successful `-F` upload goes to [[Command-Injection]] or a web shell ([[Shells#Web Shells|Web Shells]]) if the file executes. A CSRF wall means the request needs a freshly scraped token per attempt — [[Burp-Suite]].

## Download and mirror

**Why now** — you found a file or an exposed directory and want a copy on disk to read offline, or you want to clone an exposed source tree before it changes. This is wget's job precisely because it writes to disk without you asking.

```bash
wget http://TARGET_IP/backup.zip -O /tmp/backup.zip
```

```bash
wget -r -np -k http://TARGET_IP/exposed/ -P /tmp/loot
```

- `-O <file>` → name the output. Without it wget derives a name from the URL, which for a path ending in `/` becomes a confusing `index.html`.
- `-r -np` → recursive mirror, `--no-parent` so it does not climb above the directory you pointed at and start pulling the whole site.
- `-k` → convert links for offline viewing after the mirror.
- `--header="Cookie: PHPSESSID=abc"` → mirror behind a session, when the exposed directory needs auth you already hold.
- `-q` → quiet, for scripts.

**What you will see**

- **Found** — `saved [12345/12345]` with matching byte counts, and the file on disk. For a mirror, a tree of files under `-P`.
- **Empty** — a saved file that is actually an **HTML error page** under your chosen name: the server returned `404`/`403` with a body and wget saved it. `file /tmp/backup.zip` and `head` it — an `<html>` header where a zip signature should be means the download "succeeded" and delivered nothing.
- **Error** — `ERROR 403: Forbidden` / `404: Not Found` is a wrong path or a directory that refuses listing. `Unable to establish SSL connection` needs `--no-check-certificate` (wget's `-k` equivalent for TLS — note `-k` means something different in wget than in curl).
- **Noise** — a recursive mirror that starts pulling external [[Security-Terms#^cdn|CDN]] assets or loops on generated links. `--no-parent` and a tight `-P` target keep it bounded; watch what it is actually fetching.

**Then** — a downloaded archive or source tree goes to [[Source-Code-Disclosure]] and [[Config-File-Looting]] to read for secrets. A `403` on a directory you expected to list goes back to [[Content-Discovery]] to enumerate paths individually.

## Reading the output

Keep the split straight: **curl prints to stdout, wget writes to a file** — reach for curl to *see* a response and wget to *keep* one. Two flags cause most wasted time. Without `-L`, curl shows you a redirect's stub body instead of following it, so a moved page reads as empty. And `-k` (curl) / `--no-check-certificate` (wget) is mandatory against the self-signed certs labs ship — omit it and a live HTTPS service looks dead. When a request behaves in a way you cannot explain, add `curl -v` and read the exact bytes you sent before blaming the server.

## Next

- [[Content-Discovery]] — the status-code checks scale up into path brute forcing
- [[Web-Server-Checks]] — the manual `curl` probes (OPTIONS, web.config, trace.axd) live there
- [[Authentication-Attacks]] — scripting the `-d`/`-b` login request across a credential list

## Gaps

- No `--data-binary` vs `-d` distinction for sending raw JSON/XML bodies to an API.
- Nothing on `-x`/`--proxy` to route curl through Burp for inspection.
