# Active Directory — Lateral Movement

Moving from one host to the next using a credential rather than an exploit: you hold a username and password (or a hash) and you want a shell on a *different* machine that account can reach. This is the domain-wide counterpart to local privilege escalation — same idea, one host over.

> [!note] What this note assumes
> That you already have a credential and know it authenticates — [[AD-Authentication]] is the note that establishes both, and [[Kerberoasting]] is what an unprivileged one is worth first. This note starts one step later: you have something that works, and the question is where else it works. [[BloodHound]] is the note that answers *where else* in one pass; [[DCSync]] is the move once a credential turns out to be Domain Admin; delegation and [[Security-Terms#^acl|ACL]] abuse are still unwritten.

## Is this credential a local admin somewhere

```bash
python3 psexec.py username:password@hostIP
```

- `username:password@hostIP` → credential and target in one string. Swap `password` for `-hashes <lm>:<nt>` to pass a hash instead of a plaintext.
- PsExec works by uploading a service binary over SMB (445) and having the [[Security-Terms#^scm|SCM]] start it, so the target must expose 445 and the account must be **local admin** on it — a valid-but-unprivileged credential authenticates and still fails here.
