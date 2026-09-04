---
type: service
platform: any
status: working
fluency: guided
source: lab
updated: 2026-08-31
---

# 23 — Telnet

Telnet is remote login from before SSH existed: a raw TCP session carrying your keystrokes and the host's replies with no encryption and no integrity checking of any kind. Two separate things wear the name, and keeping them apart is what this note is for. On **port 23** it is a *service* — a shell you can log into, in cleartext, still shipped on printers, switches, routers and embedded boards. Everywhere else it is a *client* — the shortest way to open a bare TCP socket and read whatever a service says on connect, which is how a version string gets into your hands when a scan was vague.

Reach for this note when 23 is open, or when a port anywhere is open and `-sV` gave a thin or missing version.

## Log in on port 23

**Why now** — a scan shows 23 open, so a login prompt is probably waiting and everything crossing it will be readable. The first question is not *which password* but *whether one is needed at all*: embedded devices routinely ship an open or default-credential telnet, and that is a shell in one command rather than an hour of work.

```bash
telnet {target_IP} 23
```

- no flags worth learning here — the client connects and hands you the raw session. `Ctrl-]` then `quit` is the escape sequence when the session hangs and `Ctrl-C` goes to the *remote* end instead of yours.
- try the obvious pairs first: `root` with no password, `admin`/`admin`, and the vendor default named in the banner. A device that names its own model in the greeting has told you which default list to search.
- a credential recovered anywhere else on the host belongs here too — reuse is the standing assumption, and telnet does not lock out the way a web login does.

**What you will see**

- **Found** — a banner naming the vendor and model, then `login:`. A shell prompt with no password at all is the finding itself, and so is a working default pair. Note the exact banner text either way.
- **Empty** — a connection that opens and prints nothing is not a dead port. Press Enter once: some daemons send the prompt only after the first byte. Silence after that means it is not telnet on 23, and the next section treats it as an unknown service instead.
- **Error** — `Connection refused` means nothing is listening despite the scan, usually a stale result or a firewall answering for the host. `Connection closed by foreign host` immediately after connect is an access control list on the target refusing your source address — the service is fine, you are not on its list.
- **Noise** — a login prompt that accepts anything and then closes is a honeypot pattern, and vendor banners are freely edited, so the model string is a lead rather than a fact.

**Then** — a shell goes to [[Linux-Local-Enumeration]] or, on an appliance, straight to [[Config-File-Looting]] for the stored credentials that usually unlock the rest of the network. The banner goes to [[Public-Exploit-Workflow]]. A login you cannot guess goes to [[Authentication-Attacks]], and any password read off this wire goes everywhere else you have a service — cleartext is the whole point of the finding.

> [!warning]
> Telnet authenticates in the clear, so anyone able to capture the traffic reads the password ([[TShark]]). Treat every credential you use over it as burned, and never send a credential you actually care about through it.

## The client as a bare TCP probe

**Why now** — a port is open and you do not yet know what version is behind it. Most cleartext services announce themselves the instant you connect, so a raw TCP connection is the fastest way to read the exact software and version string. This has nothing to do with the telnet *protocol*; the client is simply the socket opener that is on every machine.

```bash
telnet <target> <port>
```

- `telnet` here is a bare TCP client, not the telnet *protocol* — it opens the socket and shows you whatever bytes come back. `nc <target> <port>` does the identical job if telnet is absent.
- some services stay silent until prompted → for HTTP (80) type `HEAD / HTTP/1.1` then a blank line; the server answers with its `Server:` header. Skip the blank line and the request never completes and the connection just hangs.

**What you will see**

- **Found** — a line naming the software and version: FTP (21) and SMTP (25) greet you with a `220 ...` banner on connect, [[Security-Terms#^pop3|POP3]] (110) with `+OK`, SSH with `SSH-2.0-OpenSSH_...`. That exact string is the goal.
- **Empty** — no banner does **not** mean no service. Many daemons stay silent until they receive a valid protocol request, so silence means "send it something," not "nothing is here." For HTTP that something is the `HEAD` request above.
- **Error** — the connection hanging or closing immediately under plain `telnet` against a port you know is open is the signature of a **TLS-wrapped** service: it is waiting for a handshake telnet cannot perform. That failure is itself the finding — switch to the [[Security-Terms#^tls|TLS]] tools below.
- **Noise** — a version banner is what the daemon *claims*. Distributions backport security fixes without bumping the version string, so an old-looking version is a lead for a search, never a confirmed vulnerability.

**Then** — the version string goes straight to [[Public-Exploit-Workflow]]. A banner naming Apache, IIS or nginx goes to [[Web-Server-Checks]]. A hang that signals TLS goes to the next section.

## TLS-wrapped services

**Why now** — plain `telnet` hung or errored, or the port is a known TLS port (443, 465, 993). Telnet cannot complete a TLS handshake, so you need a client that speaks TLS but then hands you the same raw connection to read banners and issue protocol commands.

```bash
openssl s_client -connect <target>:443
```

```bash
curl --head https://<target>
```

```bash
ncat --ssl <target> <port>
```

- `openssl s_client -connect` → completes the handshake, prints the certificate, then leaves the connection open for you to type protocol commands — the TLS-capable equivalent of telnet. The certificate's Common Name and SAN fields often leak internal hostnames worth adding to your scope.
- `curl --head` → for HTTPS specifically, pulls just the response headers (the `Server:` line) without the body.
- `ncat --ssl` → nmap's netcat with TLS; the fallback when `openssl` is not to hand.

**What you will see**

- **Found** — the certificate details plus, after the handshake, the same `220`/`+OK`/`Server:` banners the plaintext tools would have shown. HTTPS is 443, SMTPS is 465 (implicit TLS).
- **Empty** — a completed handshake with no application banner is normal for services that wait to be prompted; issue the protocol command (`HEAD`, `EHLO`, etc.) as you would in cleartext.
- **Error** — a certificate-verification error (`self signed certificate`, `unable to verify`) does **not** stop banner grabbing — `s_client` still connects and shows the banner; the warning is about trust, not reachability. A handshake that fails outright means the port is not actually TLS after all — go back to plain `telnet`.
- **Noise** — the wall of certificate chain and cipher output from `s_client` is not the banner; scroll past it to the application response below.

**Then** — same destinations as plaintext: [[Public-Exploit-Workflow]] for the version, [[Web-Server-Checks]] for a web server. Internal hostnames from the certificate go into your scan and vhost list.

## Reading the output

Two judgements live here, one for each half of the note.

On **port 23**, the finding is rarely a clever exploit — it is that the protocol is in use at all. Cleartext login on a modern network means either a device nobody has touched in a decade or a segment where nobody expected to be watched, and both of those are worth more than the shell itself. Take the credentials and try them everywhere; that is where a telnet foothold actually pays.

As a **probe**, the one judgement is that **silence is a prompt, not an answer**. A port that returns no banner is far more often a service waiting for a valid protocol request — or a TLS service waiting for a handshake — than a dead port. The move on silence is always to send the thing it expects (a `HEAD`, an `EHLO`, or a TLS handshake), not to conclude nothing is there. `-sV` in [[Nmap]] automates all of this across many ports at once; hand-grabbing is for when its guess is thin or you need to see the raw exchange yourself.

## Next

- [[Public-Exploit-Workflow]] — the version string you just read is the input to this
- [[Nmap]] — `-sV` automates version detection across many ports at once
- [[Authentication-Attacks]] — when the login prompt on 23 does not yield to defaults
- [[Web-Server-Checks]] — once a banner says Apache / IIS / nginx, this is what to test next

## Gaps

- Nothing on UDP-service banners (SNMP, DNS version.bind) — every example here is TCP.
- No coverage of protocol-specific probe strings beyond HTTP's `HEAD` and a bare TLS handshake.
- Nothing on capturing a telnet login off the wire, which is the other half of why cleartext matters.
