# 873 — rsync

rsync in daemon mode: a fast file-sync service that, when it exposes a `module` without a secret, lets anyone list and pull — sometimes push — its files. Reach for this note when 873 is open; the first question is whether any module answers with no credential.

## List the modules

```bash
rsync -a --list-only {target_IP}::public
```

- `--list-only` → list without downloading, so you see what is there before pulling anything.
- `-a` → archive mode; preserves permissions, ownership and timestamps, so the listing shows the real mode bits — which is how you spot a world-writable path.
- `::public` → the **double colon** selects the rsync daemon protocol and names the `public` module. A single colon means SSH transport instead and asks for an SSH login you may not have, which fails in a way that looks like the module being closed. First list the modules themselves with a bare `rsync -a --list-only {target_IP}::` (nothing after the colons).

## Pull and test

```bash
rsync {target_IP}::public/flag.txt ./loot_flag.txt
```

- source first, destination second → the remote path (`::public/flag.txt`) is the source, the local name is the destination — the same order as `cp`. Reverse them and you attempt to *upload* your local file over the remote, which is the write test below, not a download.

To test write access, push a throwaway file the other way:

```bash
rsync ./probe.txt {target_IP}::public/probe.txt
```
