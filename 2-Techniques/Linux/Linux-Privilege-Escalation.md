# Linux — Privilege Escalation

The ordered sweep that produces the findings, and step 8 that decides which of them matter together, is [[Linux-Run-Sheet]]. This note is the Linux side of that — what there is to look at, the single observation that makes each one worth your time, and the order that reaches a real lead for the least effort. Read it when you have a shell and no plan.

## The order to look

The vectors below are not equally expensive to test, and the cheap ones pay out more often than their reputation suggests. So the order is not *most powerful first*, it is *cheapest observation first*, and it survives on almost every host.

**One command, immediate answer.** `sudo -l` is first because it needs no search and no waiting, and it answers outright: either the account is allowed to run something as another user or it is not. A single entry here is frequently the whole box, and it costs one line to find out.

**One sweep of the filesystem.** The mode-bit and capability sweeps come next. They read the whole disk, which takes seconds and produces a list you compare against what a stock system carries — the finding is never "there are SUID binaries" but "there is a SUID binary that does not belong on a default install". Two sweeps, because they are stored differently and one does not reveal the other: the mode bits, and the extended attributes that carry capabilities.

**Something that has to be caught in the act.** Scheduled jobs are next and they cost real time, because the readable half of the picture (crontab files) is only the half a normal user is allowed to see. Watching the process table catches the rest, and watching means waiting — usually a couple of minutes, sometimes longer than the job's interval.

**Something outside the host.** Exports and shares you can mount from your own machine come after that. They are cheap to test but you have to think of them, because nothing in a local sweep points at them: the misconfiguration lives on the server's side of a network file system, not in any file you can read from the shell.

**Last, and reluctantly.** Kernel exploits. They crash hosts, the crash is the finding nobody wanted, and a patched-but-old version string wastes an hour. Prefer any configuration path that reaches the same privilege.

The order breaks in exactly one situation, and it is worth watching for: **a finding you already hold outranks the sweep you have not run yet.** A password recovered from a config, a writable file owned by root, a service listening only on loopback — each of those points at one specific vector and makes the rest of the list irrelevant until it is spent.

## What makes each vector live

Read this the other way round from a checklist. The left column is something you can already see; the right is the note that turns it into privilege.

```text
what you already hold                          the vector it opens        note
─────────────────────────────────────────────────────────────────────────────────────
any sudo entry at all, even a narrow one       sudo abuse                 Linux-Sudo-Abuse
a mode bit on a binary a stock system lacks    SUID / SGID abuse          Linux-SUID-Abuse
a capability on an interpreter                 capability abuse           Linux-Capabilities
a root job that runs a file you can write      scheduled job abuse        Cron-Jobs
root activity no readable file explains        live process watching      pspy
a root job whose command ends in a glob        argument injection         Wildcard-Injection
a root-run binary calling a bare-name helper   search-order hijack        Linux-PATH-Abuse
an export you can mount from your own box      planted SUID binary        NFS-No-Root-Squash
a shell but no observations at all             the sweeps themselves      Linux-Local-Enumeration
```

## Already written

Each line names the precondition, not the technique — that is the thing you check for before opening the note.

- [[Linux-Local-Enumeration]] — the manual first pass: `sudo -l`, the mode-bit sweep, listening sockets. Start here when you hold nothing.
- [[Linux-Automated-Enumeration]] — linPEAS, [[Security-Terms#^linenum|LinEnum]], [[Security-Terms#^les|LES]], lse: the same ground swept by script, once the noise is affordable, and what a snapshot cannot see.
- [[Linux-Sudo-Abuse]] — live when `sudo -l` returns any entry. [[Security-Terms#^gtfobins|GTFOBins]] escapes, app-function abuse, LD_PRELOAD.
- [[Linux-SUID-Abuse]] — live when the sweep returns a binary a default install does not carry. Why shell escapes drop privilege, `/etc/shadow` and `/etc/passwd`.
- [[Linux-Capabilities]] — live when `getcap` returns anything on an interpreter. Why the mode-bit sweep misses it entirely.
- [[Cron-Jobs]] — live when a root-owned schedule runs a file you can write.
- [[PSPY]] — live when root activity is visible but no readable file explains it.
- [[Wildcard-Injection]] — live when a privileged command's arguments end in a glob rather than named paths.
- [[Linux-PATH-Abuse]] — live when a privileged binary calls a helper by bare name instead of an absolute path.
- [[NFS-No-Root-Squash]] — live when the host exports a share you can also mount as root from your own machine.

## Not written yet

**Writable service files** — systemd units under `/etc/systemd/system/` that the current user can edit, where the service runs as root and can be restarted (or fires at boot). Same shape as the cron case: a privileged component reading a file you control.

**Kernel exploits** — `uname -r`, match against known CVEs. Last resort on a live engagement: they crash hosts and the crash is the finding nobody wanted. Prefer any configuration path that reaches the same privilege. Individual exploits are deliberately not written up here — a kernel exploit is one CVE against one host, and what transfers between boxes is the vetting method in [[Public-Exploit-Workflow]], not the exploit.

**Container escapes** — only relevant once you know you are in one: `/.dockerenv`, `cat /proc/1/cgroup`, a mounted docker socket.
