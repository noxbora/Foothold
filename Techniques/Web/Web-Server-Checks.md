---
type: technique
platform: web
status: solid
fluency: guided
source: lab
updated: 2026-09-03
---

# Web Server Checks

Before attacking the application, attack the thing serving it. A web server ships with defaults, diagnostic endpoints and administrative features that are safe in a lab and dangerous in production, and an administrator who was fighting a permission error at 2am often left one of them on. These checks are cheap, they run in minutes, and they occasionally end the box outright by handing you a configuration file with live credentials in it.

The discipline that makes this note useful rather than noisy: **read every result against the server's correct state, not against its mere presence.** A `405` on `TRACE` is the right answer, not a finding. An absent `customErrors` line is a default, not a vulnerability. Reporting configuration you do not understand is how a report loses its credibility.

> [!important] Example paths, not guaranteed defaults
> Endpoint and filename examples below came from practical notes and labs. Treat them as patterns to test, not as paths every server exposes.

## Identify what is actually serving

**Why now** — you have an HTTP port and nothing else. Every check below is server-specific, so this one request decides which half of the note applies and saves you running IIS probes against nginx.

```bash
curl -sIL http://target.thm/ | grep -iE 'server|x-powered-by|x-aspnet|set-cookie|location'
```

- `-I` → headers only; you want the banner, not the page
- `-L` → follow redirects. Servers frequently redirect HTTP to HTTPS and only the final response carries the real banner. **Without it you fingerprint the redirector, not the application**
- `Server:` → the product and often the version. `Microsoft-IIS/10.0`, `Apache/2.4.41 (Ubuntu)`, `nginx/1.18.0`, `Werkzeug/2.0.1 Python/3.8`
- `X-Powered-By:` and `X-AspNet-Version:` → the application stack behind the server, which decides which file extensions are worth requesting in [[Content-Discovery]]
- `Set-Cookie:` → the framework's fingerprint even when the banners are stripped. `PHPSESSID` is PHP, `JSESSIONID` is Java, `ASP.NET_SessionId` is .NET, `connect.sid` is Express
- a stripped `Server:` header is itself information: somebody hardened this deliberately, which usually means the rest is hardened too

**What you will see**

- **Found** — a product and version. Feed the version straight into [[Public-Exploit-Workflow]] before doing anything else in this note; a known CVE beats every manual check below.
- **Empty** — no `Server` header at all means it was removed, or a reverse proxy is answering. That is a hardening signal, not an absence of a server, and the cookie name usually still betrays the stack.
- **Error** — `curl: (60)` on HTTPS wants `-k`. A `400 Bad Request` to a plain HEAD is unusual and suggests something in front of the server that is not a web server at all.
- **Noise** — a [[Security-Terms#^cdn|CDN]] or load balancer banner (`cloudflare`, `AkamaiGHost`) describes the edge, not the origin. A version in a banner can be false; administrators edit them.

**Then** — IIS or `X-AspNet-Version` sends you to the IIS section, which is the bulk of this note. Apache or nginx sends you to the matrix below and then to [[Nikto]] for the automated sweep. Anything with a version goes to [[Public-Exploit-Workflow]] in parallel.

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

**Why now** — the fingerprint said IIS. When no default document exists and Directory Browsing is enabled, IIS lists the folder instead of returning 403 — which hands you filenames that no wordlist contains, including backups and configuration.

```bash
curl -s http://target.thm/uploads/ | head -40
```

- request the directory **with** the trailing slash → without it IIS answers a redirect and you see nothing
- try the directories the content sweep already found, and the standard ones: `/uploads/`, `/files/`, `/images/`, `/backup/`, `/temp/`, `/_vti_bin/`
- read the listing for extensions that should never be public: `.bak`, `.config`, `.log`, `.zip`, `.sql`, `.pfx`, `.ps1`

**What you will see**

- **Found** — an HTML listing with `<pre>` formatted rows of filenames, sizes and dates. Every filename is a target; the dates tell you which are recent and therefore live.
- **Empty** — a `403 Forbidden` or the site's default page means browsing is off. That is the correct configuration and closes only this check — files inside the directory may still be served perfectly well if you can guess their names, which is [[Content-Discovery]].
- **Error** — `404` means the directory does not exist. A `500` on a directory request is unusual and worth noting; it means something ran.
- **Noise** — an application's own file-manager page that happens to list files it is supposed to list. That is a feature, not a misconfiguration, unless it lists files outside its own area.

**Then** — a listed `.config`, `.bak` or `.zip` goes to [[Source-Code-Disclosure]]. A listing of an upload directory is worth pairing with the methods check below: writable plus executable is remote code execution.

### Which HTTP methods are allowed

**Why now** — you have a directory, perhaps a writable-looking one. `GET` is not the only verb a server accepts, and an unauthenticated `PUT` is a file upload with no application logic in front of it.

```bash
curl -s -X OPTIONS -i http://target.thm/uploads/ | grep -iE '^(allow|public|dav|ms-author-via):'
```

- `-X OPTIONS` → asks the server which methods it permits for this path. **Methods are configured per path**, so a `GET`-only root can sit above a directory that accepts `PUT`; running this once against `/` and concluding is the standard mistake
- `Allow:` → the answer. `PUT`, `DELETE`, `MOVE`, `COPY`, `PROPFIND`, `MKCOL` are the interesting ones
- `DAV:` and `MS-Author-Via:` → WebDAV is enabled. WebDAV is not confined to `/webdav/`; administrators enable it site-wide, which makes every directory potentially writable
- confirm rather than trust the header: PUT a small file (`curl -i -X PUT --data 'zz7f31' http://target.thm/uploads/zz.txt`) and then request it back. A `201 Created` or `204 No Content` followed by a successful `GET` is the proof

**What you will see**

- **Found** — `Allow: OPTIONS, TRACE, GET, HEAD, POST, PUT, DELETE` on a directory, and a `201` from an actual PUT. That is unauthenticated file upload.
- **Empty** — no `Allow` header at all is common; some servers answer OPTIONS with a bare 200. That is not "no methods", it is no answer — test `PUT` directly rather than concluding.
- **Error** — `405 Method Not Allowed` on your test PUT is the correct, secure response. `401` means WebDAV is there but authenticated, which turns this into a credentials problem and points at [[Authentication-Attacks]]. `403` after a `201` means you wrote the file but cannot read it back, which still matters.
- **Noise** — an `Allow` header listing `PUT` while every actual PUT returns 403. The header describes what the module handles, not what authorisation permits. Always test.

**Then** — a working PUT into a directory that executes code (`.aspx` on IIS, `.php` on Apache) is a web shell and goes to [[Shells]]. A working PUT into a directory that does not execute is still worth having — it is a foothold for stored [[XSS]] or for planting a file another process reads.

### Configuration and diagnostic files that should never be served

**Why now** — IIS normally refuses to serve `.config` files and diagnostic handlers should be off in production. Both are single requests, and both return credentials or session data when the rule protecting them has been removed.

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
- `trace.axd` → ASP.NET's request log: headers, form values, cookies, session state for the **50 most recent requests**. That window closes fast on a busy server, so re-request it a few minutes apart rather than once
- `elmah.axd` → the error-logging module, the same class of exposure and frequently forgotten
- status **and size** together → IIS often answers a custom 404 page with a 200, and size is what separates a real config file from an error page
- also try `/web.config.bak`, `/web.config.old`, `/App_Data/`, `/bin/` — the filtering rule usually matches the exact extension and not its variants

**What you will see**

- **Found** — a `200` with XML beginning `<configuration>`. Read `<connectionStrings>` first; a live database password is the usual prize. From `trace.axd`, a table of recent requests with cookie values in it.
- **Empty** — `404` on all three is the normal, correct state and closes this check. A `200` with size zero is not a hit.
- **Error** — `403` is IIS's request-filtering rule doing its job, and it is the expected answer for `.config`. `500` on `trace.axd` sometimes still leaks a stack trace; read the body before dismissing it.
- **Noise** — a custom error page returned with a `200` status, which is why the size column is in the command. Fetch anything that looks promising and actually read it.

**Then** — a connection string goes to [[Config-File-Looting]] to interpret and then to the database service itself. A session cookie from `trace.axd` can be replayed directly, which is session hijacking rather than information disclosure and belongs in the report as such.

### Verbose errors and the TRACE method

**Why now** — two checks that are frequently over-reported, and knowing their correct default is what stops you writing up a non-finding. Both are one request.

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

**What you will see**

- **Found** — a .NET stack trace naming `C:\inetpub\wwwroot\...` and a line number. Or a `200` from TRACE with your request echoed in the body.
- **Empty** — a friendly custom error page, and a `405` from TRACE. Both are the correct states. Record them as checked and move on.
- **Error** — `501 Not Implemented` on TRACE is also correct. A `403` from a [[Security-Terms#^waf|WAF]] on the TRACE request tells you about the WAF, not the server.
- **Noise** — a generic error page that contains the word "error" and nothing else is not information disclosure. And modern browsers block TRACE in `XMLHttpRequest`, so cross-site tracing is largely a hygiene finding now rather than a live attack path — worth reporting, not worth chasing.

**Then** — a leaked physical path is an input, not a conclusion: it is what makes an upload or a file-write exploitable, so carry it to [[File-Inclusion]] and to the methods check above. Correct states on both send you on to the next check.

### Application pool identity, once you have execution

**Why now** — you already have a web shell or command execution on IIS. Before hunting for a privilege escalation, check whether you need one. The default application pool identity is low privilege, but administrators reassign it to a high-privilege account to make a permission error go away.

```bash
curl -s 'http://target.thm/uploads/zz7f31.aspx?cmd=whoami+/all' | sed -n '1,40p'
```

- `whoami /all` → user, groups **and privileges** in one call. The privileges block is what matters and is the part most people scroll past
- `SeImpersonatePrivilege` shown as `Enabled` on a service account is the potato family of escalations, and it is the single most common IIS privilege escalation
- URL-encode the space as `+` or `%20`, and remember `&` in a command ends the query parameter — an unencoded `&&` in your `cmd` value silently truncates the command

**What you will see**

- **Found** — `nt authority\system`, `nt authority\network service`, or a domain account name. A domain account means the web server is a foothold into the domain, which changes the whole engagement.
- **Empty** — no output at all means the shell is not executing, not that the identity is restricted. Test with something trivial first.
- **Error** — an access-denied message from the shell itself still tells you the identity is constrained, which is a genuine result.
- **Noise** — `iis apppool\defaultapppool` is the secure default and expected. It is not a finding and it is not a dead end either: check the privileges list underneath it.

**Then** — `SYSTEM` needs no escalation; move to post-exploitation. A service account with `SeImpersonatePrivilege` goes to [[Windows-Privilege-Abuse]]. Anything else goes to [[Windows-Privilege-Escalation]] for the general sweep.

### The same checks as NSE scripts

**Why now** — you have done the manual pass and want a second opinion, or you have several web hosts and no time to hand-check each. These map one-to-one onto the sections above.

| Script | What it does |
| --- | --- |
| `http-methods` | Sends an OPTIONS request and parses the `Allow:` header to list permitted methods |
| `http-webdav-scan` | Probes for WebDAV support and retrieves the server's DAV headers |
| `http-iis-webdav-vuln` | Tests for IIS WebDAV authentication bypass (CVE-2009-1535, affects IIS 5 and 6) |
| `http-ntlm-info` | Sends an NTLM authentication request and extracts host and domain names from the challenge |
| `http-enum` | Requests a list of known interesting paths, the nmap-native version of a small content sweep |

`http-ntlm-info` deserves calling out separately: against an IIS endpoint using Windows authentication it returns the **hostname, domain and forest name** without any credentials. On a domain-joined target that is the first piece of domain context you get, and it comes from a web port.

**What you will see**

- **Found** — script output beneath the port line in nmap's results, naming methods, DAV support, or [[Security-Terms#^ntlm|NTLM]] host information.
- **Empty** — no script output means the script found nothing applicable, which for `http-iis-webdav-vuln` on a modern IIS is the expected result. It is not the same as the script failing to run.
- **Error** — a script erroring out is reported by nmap in the output; read it rather than assuming a clean result.
- **Noise** — `http-enum` reports many low-value paths (`/icons/`, `/robots.txt`). Treat it as an index, not a finding list.

**Then** — anything found here goes back into the matching section above for confirmation by hand, because a report needs the request and response, not a script name. Flag details in [[Nmap]].

## Rarely — worth one command, not worth a step

**Why now** — the checks above found a normally configured server. These two are leaks that survive on hosts nobody has reviewed, and each is one request.

```bash
curl -s -o /dev/null -w '%{http_code} %{size_download}\n' http://target.thm/server-status
```

- Apache's status page lists every request being served right now, including full URLs with their parameters. On a busy host that is other people's session tokens and other people's admin paths, handed over without authentication.
- It is normally restricted to loopback, which is what makes it worth exactly one request rather than a step.

```bash
curl -s -H 'X-Forwarded-For: 127.0.0.1' -o /dev/null -w '%{http_code}\n' http://target.thm/admin
```

- A path that returns `403` to you sometimes returns `200` when the request claims to come from the machine itself. The restriction is written against an address the application reads from a header you control.
- Compare the code against the same request without the header. A change is the finding; an identical code means the restriction is enforced somewhere that does not trust the header.

**What you will see**

- **Found** — a status page with real request lines in it, or a different status code once the header is added.
- **Empty** — a `404` on the status page is the normal answer and means the module is not enabled.
- **Error** — a `403` on the status page means it exists and is restricted, which is worth one attempt with the header trick from the second command.
- **Noise** — many frameworks return `200` with an access-denied page in the body. Read the size, not only the code.

**Then** — a readable status page goes to [[Content-Discovery]], because it hands you paths no wordlist contains. A header that changes the answer goes to [[Authentication-Attacks]], since the same trust usually extends to the login.

## Reading the output

The thread running through this whole note is calibration: almost every check has a **correct** state as well as a vulnerable one, and half of them are more likely to return the correct state than the vulnerable one. `405` on TRACE, `403` on `web.config`, `404` on `trace.axd`, and `ApplicationPoolIdentity` on the pool are all right answers. Recording them as "checked, correct" is doing the work; recording them as findings is not.

The second point is that these checks combine into more than they are separately. A directory listing on its own is information disclosure. A directory listing plus an accepted `PUT` plus an extension that executes is remote code execution — three individually unremarkable results that together end the box. So finish the sweep before you write anything up, then look for the pairs: writable plus executable, a leaked physical path plus any file-write, a service account plus a privilege in its token.

## Next

- [[Nikto]] — automates the known-vuln and dangerous-file sweep this note does by hand
- [[Nmap]] — `http-methods`, `http-webdav-scan`, `http-iis-webdav-vuln` [[Security-Terms#^nse|NSE]] scripts
- [[Source-Code-Disclosure]] — an exposed `web.config` or `.git` turns a check into credentials
- [[SSRF]] — when a parameter holds a URL the server fetches for you
- [[File-Upload-Bypass]] — when the surface includes anything that accepts a file

## Gaps

- Nothing on security headers beyond the matrix row: `Strict-Transport-Security`, `Content-Security-Policy` and `X-Frame-Options` are named nowhere and each changes what other attacks in this folder can do.
- No Tomcat or [[Security-Terms#^jboss|JBoss]] section, where `/manager/html` with default credentials is a direct route to a deployed web shell.
- Nothing on HTTP request smuggling or proxy misconfiguration, which is where the interesting server-level bugs are on modern targets.
- No guidance on what a reverse proxy hides: the origin server's real product, version and paths.
