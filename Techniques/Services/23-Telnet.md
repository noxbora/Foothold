# 23 — Telnet

Telnet is remote login from before SSH existed: a raw TCP session carrying your keystrokes and the host's replies with no encryption and no integrity checking of any kind. Two separate things wear the name, and keeping them apart is what this note is for. On **port 23** it is a *service* — a shell you can log into, in cleartext, still shipped on printers, switches, routers and embedded boards. Everywhere else it is a *client* — the shortest way to open a bare TCP socket and read whatever a service says on connect, which is how a version string gets into your hands when a scan was vague.

## Log in on port 23

```bash
telnet {target_IP} 23
```

- no flags worth learning here — the client connects and hands you the raw session. `Ctrl-]` then `quit` is the escape sequence when the session hangs and `Ctrl-C` goes to the *remote* end instead of yours.
- try the obvious pairs first: `root` with no password, `admin`/`admin`, and the vendor default named in the banner. A device that names its own model in the greeting has told you which default list to search.
- a credential recovered anywhere else on the host belongs here too — reuse is the standing assumption, and telnet does not lock out the way a web login does.

> [!warning]
> Telnet authenticates in the clear, so anyone able to capture the traffic reads the password ([[TShark]]). Treat every credential you use over it as burned, and never send a credential you actually care about through it.

## The client as a bare TCP probe

```bash
telnet <target> <port>
```

- `telnet` here is a bare TCP client, not the telnet *protocol* — it opens the socket and shows you whatever bytes come back. `nc <target> <port>` does the identical job if telnet is absent.
- some services stay silent until prompted → for HTTP (80) type `HEAD / HTTP/1.1` then a blank line; the server answers with its `Server:` header. Skip the blank line and the request never completes and the connection just hangs.

## TLS-wrapped services

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
