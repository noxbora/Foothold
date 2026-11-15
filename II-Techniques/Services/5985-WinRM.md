# 5985 — WinRM

Windows Remote Management: PowerShell over HTTP, the sanctioned way administrators drive a Windows host without a desktop. When it is open and you hold a credential, it beats every other option — you get a real PowerShell session instead of a shell that needs upgrading.

Two ports: **5985** plain HTTP, **5986** HTTPS. The traffic is [[Security-Terms#^soap|SOAP]] over HTTP, but the payload is encrypted at the message layer even on 5985, so plain does not mean cleartext.

## Check it is open

```bash
nmap -p5985,5986 <ip>
```

- scanning **both** ports → a host hardened to HTTPS-only shows 5986 open and 5985 closed. Scan 5985 alone and you would wrongly conclude WinRM is off.

## Connect

```bash
evil-winrm -i <ip> -u <user> -p '<password>'
```

- `-i` → target IP.
- `-u` / `-p` → the credential. **Quote the password**: `!`, `$` and `&` are shell metacharacters, and an unquoted password containing one is mangled by bash before evil-winrm ever sees it, producing an auth failure that has nothing to do with the password being wrong.
- `-H <nthash>` → authenticate with an NTLM hash instead of a password (pass-the-hash); no cracking required. Use this the moment you have a hash and no plaintext.
- `-S` → use HTTPS, for 5986.

Inside the session, `upload <local> <remote>` and `download <remote> <local>` are built in — no separate transfer channel to set up.
