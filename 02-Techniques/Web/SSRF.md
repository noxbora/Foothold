---
type: technique
platform: web
status: working
fluency: guided
source: reading
updated: 2026-09-03
---

# Server-Side Request Forgery

A parameter that makes the server fetch a URL for you. The prize is not the fetch itself, it is the position: the server sits inside the network and you do not, so its requests reach hosts, ports and metadata services that your own packets never will.

Reach for this note when a parameter holds a URL, a hostname, a filename that could be a URL, or anything the application later renders, imports, previews or checks.

## 1 — Does this parameter fetch, and does the server do the fetching

**Why now** — you have a candidate parameter and no proof. Before spending an hour on internal targets you need one fact: does a request actually leave the server, or is your browser making it. Those look identical in the response and are opposite findings.

```bash
python3 -m http.server 8000
```

```bash
curl -s "http://TARGET/preview?url=http://YOUR_IP:8000/probe-a"
```

- Run the listener on your own machine first and leave it in a second terminal. The whole test is whether a line appears in it.
- Use a distinct path per test (`/probe-a`, `/probe-b`). When three tests are in flight, the path is the only thing that tells you which one landed.
- If nothing arrives, repeat the test from your browser. A hit from the browser and no hit from `curl` means the fetch is client-side and there is no [[Security-Terms#^ssrf|SSRF]] here.

**What you will see**

- **Found** — a request in the listener whose source address is the target, not you. Read the `User-Agent`: a library string (`python-requests`, `Go-http-client`, `curl/`) is the server; a browser string is your own page.
- **Empty** — nothing arrives. Three different causes, and they are not interchangeable: the parameter is never fetched, the fetch happens in the browser, or the server has no outbound route to you. Section 2 separates the last one from the first two.
- **Error** — the response says the scheme, host or port is not allowed. This is the best outcome on this page: it is proof a fetch exists and proof someone wrote a filter around it. Filters are bypassable; absence is not.
- **Noise** — scanners, the target's own health checks and your earlier tests all land in the same listener. The per-test path is what keeps them apart.

**Then** — a request from the target goes to section 2. A filter message also goes to section 2, but start with `127.0.0.1` rather than your own address. Nothing at all, and no filter message, means test the same parameter for [[File-Inclusion]] instead, because a path that is read rather than fetched behaves this way.

## 2 — What can the server reach that you cannot

**Why now** — you have proof the server fetches. Now the only question that matters is what sits in front of it, and the two answers worth having first are the loopback interface and the cloud metadata service.

```bash
curl -s "http://TARGET/preview?url=http://127.0.0.1:8080/" -o - | head -40
```

```bash
curl -s "http://TARGET/preview?url=http://169.254.169.254/latest/meta-data/" -o - | head -40
```

- `127.0.0.1` is the point of the technique. Services bound to loopback were never in your `nmap` output, and admin panels, debug endpoints and databases live there precisely because their owner believed they were unreachable.
- `169.254.169.254` is the [[Security-Terms#^imds|IMDS]] address on every major cloud. A plain fetch works only against version 1. Version 2 needs a `PUT` first to get a token, so a `403` here is a version answer, not a dead end.
- Sweeping ports through the parameter works, but read the **length** of the response rather than the body: a closed port usually returns the app's own error page at a constant size, and an open one returns something else.

**What you will see**

- **Found** — a body that is not the application's error page: a title, a JSON document, a directory listing, a metadata key list. Anything at all that differs in size from the failure case is the finding.
- **Empty** — an identical error page for every port. That is a real answer about that host: either nothing listens there, or the fetch never leaves the application layer.
- **Error** — a timeout that grows with the port number means the request is being attempted and dropped, which itself maps the firewall. An instant refusal means nothing is listening. Time is the signal here, not text.
- **Noise** — many applications return `200` with an error inside the body. Never grade this by status code alone; grade it by response length.

**Then** — credentials from the metadata service go to [[AWS-Cognito-Identity-Pool-to-DynamoDB]] and the wider cloud path. A reachable internal web service goes to [[Content-Discovery]] run through the same parameter. A reachable database port goes to its own service note.

## Rarely — worth one command, not worth a step

**Why now** — the two sections above cover almost every real target. These are for a filter you have already proven exists and cannot get past with an address alone.

```bash
curl -s "http://TARGET/preview?url=file:///etc/passwd"
```

```bash
curl -s "http://TARGET/preview?url=http://127.1/"
```

```bash
curl -s "http://TARGET/preview?url=http://YOUR_IP:8000@127.0.0.1/"
```

- `file://` turns the fetch into a local file read. Worth one attempt because the payoff is immediate and the fix is usually a scheme allowlist that nobody wrote.
- `127.1` is a valid, shorter spelling of loopback. So are `0`, `[::1]` and decimal notation. A blocklist written as a literal string match misses all of them.
- The `@` form exploits parsers that read the host as everything before the first `/` while the fetch library reads it as everything after the `@`. Two parsers, one string, different answers.

**What you will see**

- **Found** — file contents, or a loopback response that the plain address was refused.
- **Empty** — the normal answer. These are lottery tickets, not steps, and an empty result says nothing about the target.
- **Error** — a different error message than before is progress: it means you reached a later stage of the same filter.
- **Noise** — some frameworks return the string `file` in an error and it looks like a leak. Read the whole body before believing it.

**Then** — a bypass that works goes straight back to section 2 with the internal targets. Nothing works, and the parameter is still worth a line under `## Gaps` in the engagement rather than a second hour.

## Reading the output

The hardest part of this technique is that the interesting response and the boring one are often the same length and the same status. The application is standing between you and the internal service, and it usually rewrites both outcomes into its own template.

So do not read for content, read for **difference**. One known-bad target and one candidate, run back to back, and any divergence in size, timing or wording is the signal. Without a baseline you are guessing.

Blind is not dead. If the body never changes, the request still either happened or did not, and your own listener answers that question with certainty when the internal one cannot.

## Next

- [[Content-Discovery]] — once an internal service answers, the parameter becomes your browser into it
- [[File-Inclusion]] — the sibling bug when the parameter reads a path instead of fetching a URL
- [[Web-Server-Checks]] — where the candidate parameters are found in the first place

## Gaps

- Nothing on `gopher://` and the raw-socket payloads it enables, which is how SSRF reaches non-HTTP services like Redis.
- No worked example of the metadata token request for version 2 of the service.
- DNS rebinding is not covered, and it is the standard answer to a filter that resolves the name once and fetches it again later.
