---
type: technique
platform: linux
status: working
fluency: guided
source: lab
updated: 2026-09-04
---

# Wildcard Injection

The shell expands `*` into a list of filenames **before** the command runs. If a filename starts with `-`, the command receives it as an option, not as data. So write access to the directory a privileged script globs over is write access to that command's argument list.

```text
Privileged script:   tar -czf backup.tar.gz *
You control:         filenames in that directory
Therefore:           you control tar's argument list
```

Both halves are required and neither is a finding alone. A wildcard over `/root/` you cannot write to is inert. A writable directory in a command with explicit filenames is inert too.

## Find the wildcard in a privileged command

**Why now** — you have found something that runs as another user — a cron entry, a sudo-able script, a service unit — and you cannot write the script itself. This asks a different question: does that script hand a `*` to a command whose options can execute something, and does the glob land in a directory you own. It is the check that turns an unwritable script into an escalation.

```bash
grep -rnE '(tar|rsync|chown|chmod|zip|7z|scp)[^|;#]*\*' \
  /etc/cron.d /etc/cron.daily /opt /usr/local/bin /srv 2>/dev/null
```

- `-r` → recurse, because the script is rarely where you first looked. Cron entries point at `/usr/local/bin` and `/opt` far more often than they hold the command themselves.
- `-n` → line numbers, so you can go straight back to the line rather than re-reading the file.
- `[^|;#]*` → keeps the match on the *same command* as the binary name and drops comment lines. Without it, a `#` line documenting the backup and a second command after a `;` both match, and the false positives outnumber the real hits.
- listing the directories explicitly rather than searching `/` → a full-filesystem grep on a live host is slow, loud, and returns every manual page that mentions `tar`.

**What you will see**

- **Found** — a line such as `cd /opt/backups && tar -czf /root/b.tgz *`. Two things must be true and both are visible on that one line: the `*` is a bare glob rather than a quoted string, and the working directory is named. If the `cd` is missing, read the surrounding script for it — the glob expands in whatever directory the script is *in* at that moment, which is not necessarily where the script lives.
- **Empty** — a real negative on the directories you listed, and nothing more. Extend the list to the application's own directory before concluding the host has no wildcarded job; a `*` inside a systemd unit's `ExecStart=` will not be found by this at all.
- **Error** — `Permission denied` on `/opt` or `/srv` is the interesting failure: the script may be there and simply unreadable to you. That is not an empty result, and it sends you to [[PSPY]], where the command line appears whether or not you can read the file.
- **Noise** — `*` inside quotes (`tar -czf out.tgz "$DIR"/*`) still globs, but `find . -name '*.log'` does not — the quotes stop the shell and hand the pattern to `find`. Read whether the `*` is bare on the command line before spending time on it.

**Then** — a bare glob whose directory you can write goes to the payload below. A glob over a directory you cannot write is closed: check the *other* commands in the same script instead. No readable script at all goes to [[PSPY]] and then to [[Cron-Jobs]].

## The classic case — `tar`

**Why now** — you have a privileged `tar` globbing over a directory you can write. GNU tar has an option that runs a command at a checkpoint, so the argument injection converts directly into execution as whoever runs the job. This is the shortest path from finding to shell in the whole technique.

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

**What you will see**

- **Found** — nothing at all from tar; the job completes looking entirely normal. Success is **indirect** and you check for the side effect you built: `ls -l /bin/bash` showing an `s`, a new file appearing, a connection arriving. Never look for a message from the job itself.
- **Empty** — the job runs and the side effect never appears. Three causes in order: the command uses explicit filenames or an absolute path rather than a bare `*`; the script's working directory is not the one you wrote to; or the option is not one this binary acts on. Confirm the exact flag on [[Security-Terms#^gtfobins|GTFOBins]] before blaming the setup.
- **Error** — `tar: Cannot open: Permission denied` **on your planted files** is fine and is not a failure. You control the directory listing but not those files' content, and the argument injection happens at the filename layer regardless of whether tar can read them. `tar: unrecognized option` in the job's log means the binary is bsdtar or busybox tar, neither of which has `--checkpoint-action`, and the vector is closed on this host.
- **Noise** — your own `.s.sh` appearing in the archive listing, and the job's normal output about the files it archived. Both look like activity and neither is evidence.

**Then** — a SUID `/bin/bash` goes to `/bin/bash -p` and then to [[Shells]]. A closed `tar` sends you back to the same script for a *different* command with the same shape — the list below is what to look for. If the job is the thing you cannot see rather than the thing you cannot exploit, that is [[PSPY]].

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

## Reading the output

**Success here never announces itself.** Every other vector in this vault ends with a prompt or an error. This one ends with a job completing normally, so the only way to know it worked is to have decided in advance what side effect you were checking for, and to check that. Build the payload and the test together.

**The failure mode is a clean run with no effect**, which reads identically to "the job did not fire yet". Wait one full interval before changing anything, then verify the three preconditions in order: bare `*` on the command line, working directory writable by you, option supported by this build of the binary.

**The `--` on `touch` is the single most expensive omission on this page.** Forget it and you have created ordinary files, the job runs clean, nothing happens, and every symptom points at the wrong thing. `ls -la` afterwards and read the filenames back before you wait for the next tick.

## Next

- [[Cron-Jobs]] — the scheduled job that usually supplies the privileged, wildcarded command
- [[PSPY]] — when the script that holds the glob is one you cannot read
- [[Shells]] — payload choice when the job has no terminal and no egress

## Gaps

- No worked example yet. Add the real command and output the first time this lands on a box.
- **No `rsync` or `7z` walkthrough.** Both are named in the table with the right flag and neither has been run here, so the exact filename quoting is untested.
- Nothing on the defensive view: `--` in privileged scripts, explicit `./` prefixes, and why `find -exec` is the safe idiom the wildcard version replaces.
