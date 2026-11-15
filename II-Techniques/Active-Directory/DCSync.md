# Active Directory — DCSync

Every account's password hash in the domain lives in one file on the domain controller: `NTDS.dit` (NT Directory Services Directory Information Tree — the on-disk Active Directory database). You never have to read that file, and you never have to run code on the domain controller. A domain controller will *hand you* any account's hashes if you ask the way a second domain controller would when the two of them sync up. That request is DCSync, and one account holding the replication right — Domain Admins, Enterprise Admins and the built-in Administrator hold it by default — turns into every account in the domain, `krbtgt` included.

> [!note] What this note assumes
> You already hold a **Domain Admin** (or otherwise replication-privileged) credential — a password or an [[Security-Terms#^nt-hash|NT hash]]. [[Active-Directory-Lateral-Movement]] and [[AD-Authentication]] are how you arrive here; this note is the single highest-value thing that credential is worth. If all you hold is *local* admin on one workstation you are one note too early — that yields this host's [[Security-Terms#^sam|SAM]] and its cached domain logons only ([[Windows-Credential-Harvesting]]), never the domain.

## Pull the whole domain from your own box — secretsdump

```bash
secretsdump.py 'DOMAIN/da_user:password@dc-ip' -just-dc -outputfile domain
```

- `-just-dc` → the flag that *is* the attack. Drop it and `secretsdump` also tries to read the target's local SAM and LSA over the remote registry — louder, slower, and against a domain controller it answers a different question. `-just-dc` means "skip the local hives, do the replication pull only".
- `DOMAIN/da_user` must be a **replication-privileged** account → an ordinary domain user authenticates fine and *then* the controller refuses the replication call. The failure lands after a successful login, so it reads like a tool bug and is really "right credential, wrong privilege".
- `-outputfile` → writes the dump to files you can `grep` later. Leave it off and the hashes scroll off the terminal; against a real domain that is hundreds of lines.

A hash instead of a password, same attack:

```bash
secretsdump.py 'DOMAIN/da_user@dc-ip' -hashes :nt_hash -just-dc
```

- the leading colon before the hash → same trap as [[AD-Authentication]]. `-hashes lm:nt` is two halves colon-separated, LM (LAN Manager, the dead pre-2000 scheme) first; modern hosts have no LM half, so the bare leading colon says "empty LM, this is the NT half". Drop the colon and you send the NT hash *as* the LM half and an empty NT hash — a login failure that looks like a wrong hash.

## The same pull from on the box — mimikatz

```text
lsadump::dcsync /domain:domain.local /user:krbtgt
```

- `/user:` → one account per call; `krbtgt` and `Administrator` are the two worth the typing. There is a `/all`, and it is loud.
- runs as the **current token** → mimikatz does not authenticate separately here, so `whoami` before you run it decides whether it works. A non-privileged token gets the same replication refusal as `secretsdump` without the right.
