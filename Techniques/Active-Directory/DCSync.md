---
type: technique
platform: windows
status: working
fluency: guided
source: thm
updated: 2026-10-13
---

# Active Directory — DCSync

Every account's password hash in the domain lives in one file on the domain controller: `NTDS.dit` (NT Directory Services Directory Information Tree — the on-disk Active Directory database). You never have to read that file, and you never have to run code on the domain controller. A domain controller will *hand you* any account's hashes if you ask the way a second domain controller would when the two of them sync up. That request is DCSync, and one account holding the replication right — Domain Admins, Enterprise Admins and the built-in Administrator hold it by default — turns into every account in the domain, `krbtgt` included.

> [!note] What this note assumes
> You already hold a **Domain Admin** (or otherwise replication-privileged) credential — a password or an [[Security-Terms#^nt-hash|NT hash]]. [[Active-Directory-Lateral-Movement]] and [[AD-Authentication]] are how you arrive here; this note is the single highest-value thing that credential is worth. If all you hold is *local* admin on one workstation you are one note too early — that yields this host's [[Security-Terms#^sam|SAM]] and its cached domain logons only ([[Windows-Credential-Harvesting]]), never the domain.

## Pull the whole domain from your own box — secretsdump

**Why now** — you hold a domain admin credential and you want every hash in the domain in one request, run from Kali, with nothing uploaded and no interactive login to the domain controller.

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

**What you will see**

- **Found** — `[*] Dumping Domain Credentials` then a block of `user:RID:lmhash:nthash:::` for every account, closing with `[*] Kerberos keys grabbed`. The two lines that matter most: `Administrator` ([[Security-Terms#^rid|RID]] 500) and `krbtgt` (RID 502).
- **Empty** — not a real state here: you get the whole domain or you get an error. A dump listing only machine accounts and no users is not a quiet controller, it is an output file you are reading wrong — open the `.ntds` file `-outputfile` wrote.
- **Error** — `STATUS_LOGON_FAILURE` is a wrong credential, full stop. The important one is a *successful* connection that then fails with a `DRSUAPI` / `rpc_s_access_denied` message: the account is real, it just lacks the replication right — you are not Domain Admin yet, go back to [[Active-Directory-Lateral-Movement]]. A connection refused or a timeout is a network path to the controller, not a credential problem.
- **Noise** — the `aad3b435b51404eeaad3b435b51404ee` LM half on every single line is the empty-LM marker, not a hash to crack (see the [[Hash-Cracking]] callout). Machine accounts — `DC$`, `WRK$`, anything ending `$` — are real hashes and almost never what you spend.

**Then** — the `Administrator` NT hash goes straight to [[AD-Authentication]] (authenticate with the hash, no cracking) or [[Active-Directory-Lateral-Movement]] (`psexec.py … -hashes` for a `nt authority\system` shell on the controller). Pass-the-hash is the whole point; you do not crack a raw NT hash, you replay it. The `krbtgt` hash is the master key to the domain's Kerberos and what it forges is in Gaps below.

## The same pull from on the box — mimikatz

**Why now** — you are already sitting on a Windows host with a privileged domain token and would rather spend that token than carry a credential back to Kali. mimikatz asks the controller to replicate one account at a time, in the context of whoever you are right now.

```text
lsadump::dcsync /domain:domain.local /user:krbtgt
```

- `/user:` → one account per call; `krbtgt` and `Administrator` are the two worth the typing. There is a `/all`, and it is loud.
- runs as the **current token** → mimikatz does not authenticate separately here, so `whoami` before you run it decides whether it works. A non-privileged token gets the same replication refusal as `secretsdump` without the right.

**What you will see**

- **Found** — a block naming the user, the RID, and `Hash NTLM:` followed by 32 hex characters, plus any Kerberos keys the account has.
- **Empty** — no such state; mimikatz prints the record or an error.
- **Error** — `ERROR kuhl_m_lsadump_dcsync` with an access-denied cause is the replication right missing again. A name error is a misspelled `/domain:` or `/user:`.
- **Noise** — running it for a user who genuinely has no stored key returns a sparse record that looks broken and is not; pick an account you know is active.

**Then** — identical to the `secretsdump` route: the hash goes to [[AD-Authentication]], never to a password prompt.

## Reading the output

DCSync is a **read**, not code execution on the controller — nothing is written to its disk, which is why it is quiet next to dropping a binary. Quiet is not silent: the replication pull is logged (Event ID 4662, the directory-access audit event), the same lesson as a [[Kerberoasting]] request being logged rather than invisible.

Everything it returns is an NT hash or a Kerberos key — never a plaintext password. You spend these by pass-the-hash or by forging tickets, so a DCSync dump always flows to [[AD-Authentication]] and never to a login box expecting a typed password. The one exception that wants cracking is a cached-logon (`$DCC2$`) hash, and those come from a *host's* LSA cache ([[Windows-Credential-Harvesting]]), not from this domain pull.

## Next

- [[AD-Authentication]] — spend the Administrator NT hash without cracking it
- [[Active-Directory-Lateral-Movement]] — `psexec.py … -hashes` for a SYSTEM shell on the controller
- [[Kerberoasting]] — the unprivileged move that often gets you the first credential toward here
- [[BloodHound]] — the map that shows a non-admin path to the replication right

## Gaps

- The `krbtgt` hash is dumped here but what it unlocks has no procedure yet: a **golden ticket** — a Kerberos ticket-granting ticket you forge offline, for any user, valid until `krbtgt` is rotated twice — and a **silver ticket** forged from a single service account's hash.
- No path to the replication right when you are *not* Domain Admin: the [[Security-Terms#^acl|ACL]] route where a user is granted `DS-Replication-Get-Changes` directly, which [[BloodHound]] draws and which makes DCSync reachable without full domain admin.
- Offline parsing of a stolen `NTDS.dit` plus a `SYSTEM` hive copy (a Volume Shadow Copy or `ntdsutil` export, then `secretsdump.py -ntds … -system … LOCAL`) is the file-based road to the same hashes and is unwritten.
