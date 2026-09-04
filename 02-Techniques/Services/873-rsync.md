---
type: service
platform: linux
status: working
fluency: guided
source: lab
updated: 2026-08-30
---

# 873 — rsync

rsync in daemon mode: a fast file-sync service that, when it exposes a `module` without a secret, lets anyone list and pull — sometimes push — its files. Reach for this note when 873 is open; the first question is whether any module answers with no credential.

## List the modules

**Why now** — 873 is open and rsync daemons publish named `modules` (its word for a share). The cheapest move is to ask for the file list of a module: if it answers without a secret, that is a disclosure you reach in one command, and a writable module is more than a disclosure.

```bash
rsync -a --list-only {target_IP}::public
```

- `--list-only` → list without downloading, so you see what is there before pulling anything.
- `-a` → archive mode; preserves permissions, ownership and timestamps, so the listing shows the real mode bits — which is how you spot a world-writable path.
- `::public` → the **double colon** selects the rsync daemon protocol and names the `public` module. A single colon means SSH transport instead and asks for an SSH login you may not have, which fails in a way that looks like the module being closed. First list the modules themselves with a bare `rsync -a --list-only {target_IP}::` (nothing after the colons).

**What you will see**

- **Found** — a file listing with permissions, sizes and dates. Returned with no credential, that listing **is** the misconfiguration — record it.
- **Empty** — a module that lists no files is genuinely empty, or you are seeing only its top level; `--list-only` on a subpath (`::public/subdir`) confirms which.
- **Error** — `@ERROR: access denied` or `auth failed` means the module requires a secret. `@ERROR: Unknown module '<name>'` means the name is wrong — list the modules first. `connection refused` / `unexpectedly closed` means nothing spoke rsync on 873.
- **Noise** — a bare-colon module list showing only a default or example module name is common; the presence of a module says nothing until you try to list *inside* it.

**Then** — a readable module goes to *Pull and test* below. `auth failed` sends you to [[Config-File-Looting]] for the module secret (often in an `rsyncd.conf` or `rsyncd.secrets` on another foothold).

## Pull and test

**Why now** — the module lists, so now you take what is there and settle what decides its worth: can you write back? A readable module is loot; a writable module tied to a path a privileged process reads is a foothold.

```bash
rsync {target_IP}::public/flag.txt ./loot_flag.txt
```

- source first, destination second → the remote path (`::public/flag.txt`) is the source, the local name is the destination — the same order as `cp`. Reverse them and you attempt to *upload* your local file over the remote, which is the write test below, not a download.

To test write access, push a throwaway file the other way:

```bash
rsync ./probe.txt {target_IP}::public/probe.txt
```

**What you will see**

- **Found** — on a pull, the file appears locally with its size. On a push, `probe.txt` shows up in the next `--list-only` — anonymous write, a serious finding.
- **Empty** — a pull of a zero-byte file is a real (empty) file, not a failure; check the size in the listing first.
- **Error** — `ERROR: ... Read-only file system` or `access denied` on the push means the module is read-only, the well-configured case. `Permission denied` on a specific file during a pull means that file is not world-readable even though the module lists it.
- **Noise** — rsync's progress and `sent/received bytes` summary is transfer accounting, not a result; read the file, not the summary.

**Then** — pulled files go to [[Config-File-Looting]]. A writable module goes to [[File-Transfer]] as a delivery channel, and — if you can place a file where a privileged process reads or runs it — to [[Cron-Jobs]] for the pipeline that turns the write into execution. Read-only closes the foothold route and leaves you the loot.

## Reading the output

Two things govern this port. The first is the **`::` versus `:` distinction**: a double colon is the rsync daemon (no login), a single colon is rsync-over-SSH (needs an SSH account). Mixing them up produces auth errors that look like the module is protected when you simply asked the wrong transport. The second is the same read-versus-write line as every file service here: the listing tells you what is there, but only a push test tells you whether this is disclosure or a foothold.

## Next

- [[File-Transfer]] — rsync as a bulk pull/push channel
- [[Config-File-Looting]] — a writable module often lands you next to readable configs
- [[Cron-Jobs]] — a writable module a scheduled job consumes turns a push into execution

## Gaps

- Nothing on rsync run over SSH (`rsync -e ssh`) as a deliberate transfer channel post-foothold.
- No coverage of `uid`/`gid` daemon settings that decide what a written file lands as.
