# Active Directory — Lateral Movement

Moving from one host to the next using a credential rather than an exploit: you hold a username and password (or a hash) and you want a shell on a *different* machine that account can reach. This is the domain-wide counterpart to local privilege escalation — same idea, one host over.

> [!note] What this note assumes
> That you already have a credential and know it authenticates — [[AD-Authentication]] is the note that establishes both, including which hash can be passed and which has to be cracked first. [[Kerberoasting]] is what an unprivileged credential is worth first. This note starts one step later: you have something that works, and the question is where else it works. [[BloodHound]] answers *where else* in one pass; [[DCSync]] is the move once a credential turns out to be Domain Admin; [[Pivoting-and-Tunneling]] is how you reach a host your own box cannot route to; delegation and [[Security-Terms#^acl|ACL]] abuse are still unwritten.

## Check for admin before you fire anything

```bash
nxc smb TARGET_IP -u user -p 'password'
```

- read the tag at the end of the line: `[+]` on its own means the credential is valid but **not** local admin; `(Pwn3d!)` means valid **and** local admin. Only `(Pwn3d!)` means an execution method will actually land — throwing psexec at a `[+]`-only host just buys you a timeout.
- swap `-p 'password'` for `-H <nt hash>` to run the same check with a hash.

## Get a shell where you are admin

```bash
psexec.py domain/user:'password'@TARGET_IP
```

- `domain/user:'password'@TARGET_IP` → credential and target in one string. Swap `:'password'` for `-hashes :<nt>` to pass a hash instead of a plaintext — mind the leading colon ([[AD-Authentication]] covers why dropping it fails silently).
- PsExec uploads a service binary over SMB (445) and has the [[Security-Terms#^scm|SCM]] start it, so you land as **NT AUTHORITY\SYSTEM**, not as the user — which is why a SYSTEM shell can read files the user himself cannot.
- the account must be **local admin** on the target (writable `ADMIN$`). A valid-but-unprivileged credential authenticates and still fails here.
- it is the loud one: a file on disk, a new service, and **Event ID 7045** carrying a random 4-character service name. Reach for a quieter method below when that matters.

## When PsExec will not fit

Same credential, a different Windows subsystem underneath. Switch methods when 445 is filtered, when antivirus eats the uploaded binary, or when you need to be quieter. Every tool below takes the same auth flags (`-hashes`, `-k`).

| the constraint | tool | why it gets past it |
| --- | --- | --- |
| only Remote Management Users, not admin | `evil-winrm` ([[5985-WinRM]]) | runs as the **user** over 5985 — no service, nothing written to disk |
| PsExec blocked or flagged | `wmiexec.py` | executes over WMI (Windows Management Instrumentation) — no service install |
| SCM locked down | `dcomexec.py` | rides legitimate DCOM (Distributed Component Object Model) automation objects |
| antivirus catches the upload | `smbexec.py` | a service running `cmd.exe /c`, no binary on disk (still Event ID 7045) |
| SCM *and* DCOM both locked | `atexec.py` | schedules a one-shot task — Event ID 4698 instead of 7045 |

- `evil-winrm` is the one that is **not** merely a quieter PsExec: it needs only **Remote Management Users** membership, so it lands on a host where you are not local admin at all. The other four still require admin.

## Spray a local hash across the subnet

A local Administrator hash lifted off one box is routinely reused on the others when LAPS is absent. Test the whole list in one shot before choosing where to land:

```bash
nxc smb TARGET1 TARGET2 -u Administrator -H <nt hash> --local-auth
```

- `--local-auth` → authenticate against each host's **local SAM** (Security Account Manager, the on-disk account database), not the domain. A local Administrator is not a domain account; leave this flag off and nxc asks the domain controller instead, the hash matches nothing there, and every host comes back failed — a result that reads exactly like a wrong hash.
- every host answering `(Pwn3d!)` takes the same `-hashes :<nt>` you would hand psexec, or `-H <nt>` for evil-winrm.
