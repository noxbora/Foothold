---
type: service
platform: windows
status: working
fluency: guided
source: thm
updated: 2026-08-30
---

# 5985 — WinRM

Windows Remote Management: PowerShell over HTTP, the sanctioned way administrators drive a Windows host without a desktop. When it is open and you hold a credential, it beats every other option — you get a real PowerShell session instead of a shell that needs upgrading.

Two ports: **5985** plain HTTP, **5986** HTTPS. The traffic is [[Security-Terms#^soap|SOAP]] over HTTP, but the payload is encrypted at the message layer even on 5985, so plain does not mean cleartext.

## Check it is open

**Why now** — [[Security-Terms#^winrm|WinRM]] is off by default on workstations, so before this note applies at all you need to know the service is actually listening. One line decides whether the rest is relevant.

```bash
nmap -p5985,5986 <ip>
```

- scanning **both** ports → a host hardened to HTTPS-only shows 5986 open and 5985 closed. Scan 5985 alone and you would wrongly conclude WinRM is off.

**What you will see**

- **Found** — `5985/tcp open` (or `5986/tcp open`). That is the green light for the rest of this note.
- **Empty** — both ports closed or filtered means WinRM is not enabled here. Nothing to fix — use another route onto the host.
- **Error** — a `filtered` state (rather than `closed`) means a firewall is dropping the probe; the service may still be reachable from a foothold on the same segment.
- **Noise** — a host answering on 47001 (the WinRM listener's alternate) without 5985/5986 is rare and not the standard endpoint; target 5985/5986.

**Then** — an open port goes to *Connect*. Both closed sends you to [[Shells]] or another service entirely.

## Connect

**Why now** — the port is open and you hold a Windows credential — a password, or just an [[Security-Terms#^ntlm|NTLM]] hash. This turns that credential into a full PowerShell session, the best shell available on a Windows target.

```bash
evil-winrm -i <ip> -u <user> -p '<password>'
```

- `-i` → target IP.
- `-u` / `-p` → the credential. **Quote the password**: `!`, `$` and `&` are shell metacharacters, and an unquoted password containing one is mangled by bash before evil-winrm ever sees it, producing an auth failure that has nothing to do with the password being wrong.
- `-H <nthash>` → authenticate with an NTLM hash instead of a password (pass-the-hash); no cracking required. Use this the moment you have a hash and no plaintext.
- `-S` → use HTTPS, for 5986.

Inside the session, `upload <local> <remote>` and `download <remote> <local>` are built in — no separate transfer channel to set up.

**What you will see**

- **Found** — an `*Evil-WinRM* PS C:\Users\<user>\Documents>` prompt. It is a real PowerShell runspace: `$PSVersionTable`, tab completion and pipelines all behave normally.
- **Empty** — not applicable; you get a prompt or an error.
- **Error** — a **401** with a credential you *know* is valid is the interesting case: authentication succeeded, authorisation did not. WinRM requires membership in **Remote Management Users** or local administrator. This is a finding, not a dead end — it names exactly the group you need to reach. `Connection refused` on 5985 while 5986 is open means the host was hardened to HTTPS-only; add `-S`.
- **Noise** — an [[Security-Terms#^tls|SSL]]/certificate warning on `-S` against a self-signed cert is expected and does not stop the login.

**Then** — a session goes to [[Windows-Credential-Harvesting]] as the first sweep, then [[Windows-Privilege-Escalation]]. A 401 for group membership means this credential is valid but under-privileged here — try it over [[445-SMB]] (which does not require Remote Management Users), and hunt a better account. None of the shell-upgrade caveats in [[Shells#Windows — ConPtyShell|the shell-upgrade section]] apply, because this is already a full runspace.

## Reading the output

The one distinction to hold on this port is **refused connection versus refused authorisation**. A closed port means WinRM is off and there is nothing here. A **401 on a valid credential** means WinRM is on and working and the account simply is not in the right group — which is a precise, actionable finding, and the reason a credential that opens [[445-SMB]] can still be turned away here. Never read that 401 as a wrong password.

## Next

- [[Windows-Credential-Harvesting]] — the first sweep to run once the session opens
- [[Windows-Privilege-Escalation]] — where the session goes next
- [[Shells]] — the fallback when WinRM is closed or the account is not in the right group

## Gaps

- No `netexec winrm` for spraying a credential across a subnet.
- No Kerberos authentication (`--spn`), only NTLM and pass-the-hash.
- Nothing on enabling WinRM from an existing foothold as a persistence move.
