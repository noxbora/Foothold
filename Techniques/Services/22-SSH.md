# 22 — SSH

Secure Shell: the standard remote login for Linux, and usually the port you *arrive through* once you hold a credential rather than one you break open. This note covers connecting. Tunnelling and port forwarding (`-L`, `-R`, `-D`) are a movement technique, not a service lookup, and live in [[Pivoting-and-Tunneling]].

## Connecting

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
