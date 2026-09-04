---
type: service
platform: linux
status: working
fluency: guided
source: lab
updated: 2026-08-31
---

# 22 — SSH

Secure Shell: the standard remote login for Linux, and usually the port you *arrive through* once you hold a credential rather than one you break open. This note covers connecting. Tunnelling and port forwarding (`-L`, `-R`, `-D`) are a movement technique, not a service lookup, and live in [[Pivoting-and-Tunneling]].

## Connecting

**Why now** — you found a username, a password, or a private key — in a config, a share, a history file — and 22 is open. This is where that credential turns into a shell. SSH rarely yields to guessing, so the trigger for this note is *holding a credential*, not "port 22 is up".

```bash
# Password or default port
ssh mark@10.112.165.56
```

```bash
# Non-standard port
ssh -p 2222 mark@10.112.165.56
```

```bash
# A private key you recovered
ssh -i ./id_mark mark@10.112.165.56
```

```bash
# Jump through a bastion to reach an internal host
ssh -J bastion.example.com mark@internal-server
```

```bash
# Run one command without an interactive shell
ssh mark@10.112.165.56 "id; sudo -l"
```

- `-i <keyfile>` → authenticate with a private key. The key must be mode `600`; SSH refuses a world-readable key with "UNPROTECTED PRIVATE KEY FILE" and falls back to asking for a password you may not have. `chmod 600` a key the moment you recover it, or this looks like the key not working.
- `-p <port>` → the port. Omit it against a service moved off 22 and you get `Connection refused` on the default port and wrongly conclude SSH is closed.
- `-J <host>` → chain through a jump host in one command; the credential prompts apply to the final host, not the bastion, unless the bastion needs its own.
- a trailing `"command"` → runs non-interactively and exits. Good for a fast `id; sudo -l` before committing to a full session.

**What you will see**

- **Found** — a shell prompt as the target user, or, for the one-shot form, the command's output followed by the connection closing. Run `id` first thing to confirm who you landed as.
- **Empty** — a key that connects but drops you at a locked or `nologin` shell means the account exists and is deliberately shell-less; the credential is valid but this user is not a login route. That is a finding about *which* user to target, not a failure.
- **Error** — `Permission denied (publickey)` means password auth is **off** — you need a key, and a better password will never work. `Permission denied (publickey,password)` means passwords are still accepted, so credential attacks are in play. `Connection refused` is nothing listening on that port; `Connection timed out` is filtered — reach it through a tunnel. `REMOTE HOST IDENTIFICATION HAS CHANGED` in a lab is almost always the box being rebuilt, not a [[Security-Terms#^mitm|MITM]] — clear the offending `known_hosts` line and reconnect.
- **Noise** — the fingerprint-acceptance prompt on first connect (`Are you sure you want to continue connecting`) is routine, not a security event; type `yes`.

**Then** — a shell goes straight to [[Linux-Local-Enumeration]] and the [[Linux-Run-Sheet]] as this user. `Permission denied (publickey)` sends you to hunt a key in [[Config-File-Looting]] (reusable keys and passphrases hide in configs and shell history). `(publickey,password)` with no password in hand goes to a targeted guess built from [[Custom-Wordlist-Attack-Chain]], not a blind rockyou run.

## Reading the output

The authentication error on SSH is not noise — it is a configuration readout. The parenthesised list after `Permission denied` names exactly which methods the server accepts, so it tells you whether to spend the next hour looking for a key or looking for a password. Read that list before you choose a route; it is the difference between an hour well spent and an hour wasted on a method the server will never accept.

## Next

- [[Pivoting-and-Tunneling]] — `-L`, `-R`, `-D` once you have a session
- [[Linux-Local-Enumeration]] — first moves after landing
- [[Config-File-Looting]] — reusable keys and passphrases live in configs and history

## Gaps

- No password/key brute forcing (`hydra ssh`, `patator`) — this note is connect-only by design.
- Nothing on cracking an encrypted private key's passphrase (`ssh2john`); that lives in [[Hash-Cracking]].
- No coverage of `authorized_keys` write access as a persistence or lateral-movement move.
