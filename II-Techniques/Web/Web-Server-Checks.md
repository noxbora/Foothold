# Web Server Checks

Before attacking the application, attack the thing serving it. A web server ships with defaults, diagnostic endpoints and administrative features that are safe in a lab and dangerous in production, and an administrator who was fighting a permission error at 2am often left one of them on. These checks are cheap, they run in minutes, and they occasionally end the box outright by handing you a configuration file with live credentials in it.

The discipline that makes this note useful rather than noisy: **read every result against the server's correct state, not against its mere presence.** A `405` on `TRACE` is the right answer, not a finding. An absent `customErrors` line is a default, not a vulnerability. Reporting configuration you do not understand is how a report loses its credibility.

> [!important] Example paths, not guaranteed defaults
> Endpoint and filename examples below came from practical notes and labs. Treat them as patterns to test, not as paths every server exposes.

## Identify what is actually serving

```bash
curl -sIL http://target.thm/ | grep -iE 'server|x-powered-by|x-aspnet|set-cookie|location'
```

- `-I` → headers only; you want the banner, not the page
- `-L` → follow redirects. Servers frequently redirect HTTP to HTTPS and only the final response carries the real banner. **Without it you fingerprint the redirector, not the application**
- `Server:` → the product and often the version. `Microsoft-IIS/10.0`, `Apache/2.4.41 (Ubuntu)`, `nginx/1.18.0`, `Werkzeug/2.0.1 Python/3.8`
- `X-Powered-By:` and `X-AspNet-Version:` → the application stack behind the server, which decides which file extensions are worth requesting in [[Content-Discovery]]
- `Set-Cookie:` → the framework's fingerprint even when the banners are stripped. `PHPSESSID` is PHP, `JSESSIONID` is Java, `ASP.NET_SessionId` is .NET, `connect.sid` is Express
- a stripped `Server:` header is itself information: somebody hardened this deliberately, which usually means the rest is hardened too

## General Misconfiguration Matrix

What to look for on each server type, and where it usually lives. Use it as a checklist of questions, not a list of URLs that exist.

| Misconfiguration                 | Apache                             | Python HTTP                       | Node.js                         | Nginx                                   |
| -------------------------------- | ---------------------------------- | --------------------------------- | ------------------------------- | --------------------------------------- |
| Version disclosure in headers    | Yes                                | Yes                               | Partial                         | Yes                                     |
| Directory listing                | `/files/`                          | Root path                         | N/A                             | `/files/`                               |
| Exposed status or debug endpoint | `/server-status`                   | N/A                               | `/api/debug/env`, `/api/routes` | `/nginx_status`                         |
| Sensitive files accessible       | `backup.bak`, `internal-notes.txt` | `.env`, `notes.txt`, `backup.zip` | `config.js`                     | `server-config.txt`, `deploy-notes.txt` |
| Missing security headers         | All                                | All                               | All                             | All                                     |

Two rows deserve emphasis. `/server-status` on Apache with `ExtendedStatus` on lists **the URLs other people are requesting right now**, including ones no wordlist would find and occasionally session tokens in query strings. A Python `http.server` in the process list means somebody is serving a directory that was never meant to be a webroot, and the root path lists all of it.

## IIS

> [!note] One canonical IIS checklist
> Enumeration, exploitation, and application-pool identity checks stay together here so IIS-specific behavior has one home. [[Pentest-Workflow]] links to the relevant context.

### Is directory browsing on, and what does it expose

```bash
curl -s http://target.thm/uploads/ | head -40
```

- request the directory **with** the trailing slash → without it IIS answers a redirect and you see nothing
- try the directories the content sweep already found, and the standard ones: `/uploads/`, `/files/`, `/images/`, `/backup/`, `/temp/`, `/_vti_bin/`
- read the listing for extensions that should never be public: `.bak`, `.config`, `.log`, `.zip`, `.sql`, `.pfx`, `.ps1`

### Which HTTP methods are allowed

```bash
curl -s -X OPTIONS -i http://target.thm/uploads/ | grep -iE '^(allow|public|dav|ms-author-via):'
```

- `-X OPTIONS` → asks the server which methods it permits for this path. **Methods are configured per path**, so a `GET`-only root can sit above a directory that accepts `PUT`; running this once against `/` and concluding is the standard mistake
- `Allow:` → the answer. `PUT`, `DELETE`, `MOVE`, `COPY`, `PROPFIND`, `MKCOL` are the interesting ones
- `DAV:` and `MS-Author-Via:` → WebDAV is enabled. WebDAV is not confined to `/webdav/`; administrators enable it site-wide, which makes every directory potentially writable
- confirm rather than trust the header: PUT a small file (`curl -i -X PUT --data 'zz7f31' http://target.thm/uploads/zz.txt`) and then request it back. A `201 Created` or `204 No Content` followed by a successful `GET` is the proof

### Configuration and diagnostic files that should never be served

```bash
curl -s -o /dev/null -w '%{http_code} %{size_download}  web.config\n'   http://target.thm/web.config
```

```bash
curl -s -o /dev/null -w '%{http_code} %{size_download}  trace.axd\n'    http://target.thm/trace.axd
```

```bash
curl -s -o /dev/null -w '%{http_code} %{size_download}  elmah.axd\n'    http://target.thm/elmah.axd
```

- `web.config` → connection strings, API keys, SMTP credentials, machine keys. A `200` here is high severity on its own
- `trace.axd` → ASP.NET's request log: headers, form values, cookies, session state for the most recent requests (the trace `requestLimit`, **10 by default**). That window closes fast on a busy server, so re-request it a few minutes apart rather than once
- `elmah.axd` → the error-logging module, the same class of exposure and frequently forgotten
- status **and size** together → IIS often answers a custom 404 page with a 200, and size is what separates a real config file from an error page
- also try `/web.config.bak`, `/web.config.old`, `/App_Data/`, `/bin/` — the filtering rule usually matches the exact extension and not its variants

### Verbose errors and the TRACE method

```bash
curl -s http://target.thm/zz-no-such-page-7f31.aspx | grep -iE 'stack trace|\\\\inetpub|version=|line [0-9]+'
```

```bash
curl -s -X TRACE -i -H 'X-Probe: zz7f31' http://target.thm/ | head -20
```

- forcing an error → request a page that cannot exist with the application's own extension, so the framework handles it rather than the server
- what a verbose error leaks → the physical path (`C:\inetpub\wwwroot\...`), the framework version, the failing query, and sometimes internal IP addresses. The physical path is the valuable part; it is what a file-write primitive needs
- `customErrors` defaults to **`RemoteOnly`**, which already protects remote clients. Only `Off` sends traces to you. **Do not flag a server merely because `customErrors` is absent from the config** — absent means the safe default is in force
- `-X TRACE` with a custom header → TRACE echoes the request back. If your `X-Probe` header comes back in the body, TRACE is live
- TRACE is distinct from `trace.axd` despite the name; one is an HTTP verb, the other an ASP.NET handler

### Application pool identity, once you have execution

```bash
curl -s 'http://target.thm/uploads/zz7f31.aspx?cmd=whoami+/all' | sed -n '1,40p'
```

- `whoami /all` → user, groups **and privileges** in one call. The privileges block is what matters and is the part most people scroll past
- `SeImpersonatePrivilege` shown as `Enabled` on a service account is the potato family of escalations, and it is the single most common IIS privilege escalation
- URL-encode the space as `+` or `%20`, and remember `&` in a command ends the query parameter — an unencoded `&&` in your `cmd` value silently truncates the command

### The same checks as NSE scripts

| Script | What it does |
| --- | --- |
| `http-methods` | Sends an OPTIONS request and parses the `Allow:` header to list permitted methods |
| `http-webdav-scan` | Probes for WebDAV support and retrieves the server's DAV headers |
| `http-iis-webdav-vuln` | Tests for IIS WebDAV authentication bypass (CVE-2009-1535, affects IIS 5 and 6) |
| `http-ntlm-info` | Sends an NTLM authentication request and extracts host and domain names from the challenge |
| `http-enum` | Requests a list of known interesting paths, the nmap-native version of a small content sweep |

`http-ntlm-info` deserves calling out separately: against an IIS endpoint using Windows authentication it returns the **hostname, domain and forest name** without any credentials. On a domain-joined target that is the first piece of domain context you get, and it comes from a web port.
