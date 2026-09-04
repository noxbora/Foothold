---
type: technique
platform: windows
status: working
fluency: guided
source: lab
updated: 2026-09-02
---

# Active Directory — Lateral Movement

Moving from one host to the next using a credential rather than an exploit: you hold a username and password (or a hash) and you want a shell on a *different* machine that account can reach. This is the domain-wide counterpart to local privilege escalation — same idea, one host over.

> [!note] What this note assumes
> That you already have a credential and know it authenticates — [[AD-Authentication]] is the note that establishes both, and [[Kerberoasting]] is what an unprivileged one is worth first. This note starts one step later: you have something that works, and the question is where else it works. [[Security-Terms#^bloodhound|BloodHound]], delegation, [[Security-Terms#^dcsync|DCSync]] and [[Security-Terms#^acl|ACL]] abuse are still unwritten.

## Is this credential a local admin somewhere

**Why now** — you have recovered a domain or local credential (from [[Windows-Credential-Harvesting]], a config file, or a hash you cracked) and one shell. The question that decides whether it is worth anything beyond this box is: **does it have local administrator rights on another host?** PsExec answers that and, if yes, hands you a SYSTEM shell there in the same step.

```bash
python3 psexec.py username:password@hostIP
```

- `username:password@hostIP` → credential and target in one string. Swap `password` for `-hashes <lm>:<nt>` to pass a hash instead of a plaintext.
- PsExec works by uploading a service binary over SMB (445) and having the [[Security-Terms#^scm|SCM]] start it, so the target must expose 445 and the account must be **local admin** on it — a valid-but-unprivileged credential authenticates and still fails here.

**What you will see**

- **Found** — a banner, then an interactive prompt landing at `nt authority\system` (PsExec starts its service as SYSTEM, so success is a SYSTEM shell, not just a login). `whoami` confirms it.
- **Empty** — no blank state: PsExec drops a shell or returns one of the errors below. A long hang usually means 445 is filtered on the target, not that it succeeded silently.
- **Error** — `STATUS_ACCESS_DENIED` means the credential is **valid but not local-admin** on this target — authentication worked, authorization did not. `STATUS_LOGON_FAILURE` means the **credential itself is wrong**. The two send you in opposite directions, so read which one you got.
- **Noise** — a `STATUS_ACCESS_DENIED` is easy to misread as "wrong password" and give up on a good credential; it is the opposite — the password is right, the target is just not one this account administers.

**Then** — `STATUS_ACCESS_DENIED` means spray the same working credential across other hosts ([[445-SMB]] to find which expose 445), or escalate locally on the current box first ([[Windows-Privilege-Escalation]]) to obtain a stronger credential. `STATUS_LOGON_FAILURE` means go find a better credential — [[Config-File-Looting]] and [[Windows-Credential-Harvesting]]. A SYSTEM shell means loot the new host and repeat the whole process from it.

## Next

- [[AD-Authentication]] — before this note is worth opening: what you hold, and whether it authenticates at all
- [[445-SMB]] — the SMB channel PsExec rides on; check share and admin access first
- [[Windows-Privilege-Escalation]] — if the credential is a user, not an admin, escalate locally first
- [[Config-File-Looting]] — where the reusable credential usually comes from

## Gaps

- One technique only. [[Security-Terms#^as-rep|AS-REP]] roasting, [[Security-Terms#^pass-the-ticket|pass-the-ticket]], DCSync, delegation abuse and BloodHound-driven ACL paths are the rest of AD lateral movement and are all unwritten.
- No coverage of the other execution methods in the same family — `wmiexec.py`, `smbexec.py`, `atexec.py` — which are quieter than PsExec (no service binary dropped) and succeed in some places PsExec is blocked.
- Nothing on *finding* which hosts a credential can reach (`crackmapexec`/`nxc` sweeps); this note assumes you already have a target IP.
