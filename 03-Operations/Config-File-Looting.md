---
type: technique
platform: any
status: working
fluency: guided
source: lab
updated: 2026-09-08
---

# Config File Looting

Requires a shell you already hold. Configuration files are where applications keep the secrets they need at runtime — database passwords, API keys, connection strings — in plaintext, because the application has to read them back every time it starts. More notes point here than to almost anywhere else in the vault, because "did you check the config?" is the answer to a large share of stuck boxes.

The note is one loop, repeated per user: find a file somebody configured, read a value out of it, then find the account that value belongs to. A password with no username attached is half a finding, and half a finding is what keeps people typing for two hours.

> [!important]
> After `2>/dev/null`, *no match* and *permission denied* look identical — both print nothing. Every step below says which of the two its silence means, because they demand opposite next moves: one closes the route, the other says come back as a different user.

## 1 — The web root

**Why now** — you have a shell on a host that serves a web application, and enumeration already handed you the document root. That application authenticates to something — a database, an API, a mail relay — and the credential it uses has to sit on disk in cleartext for it to boot. This is the cheapest secret on the host and usually the first one.

```bash
ls -la /var/www /var/www/html /srv/www /usr/share/nginx/html 2>/dev/null
```

```bash
cat /var/www/html/config.php /var/www/html/wp-config.php 2>/dev/null
```

- `ls -la` before `cat` → configuration hides in dotfiles: `.env`, `.htpasswd`, `.git/config`, `.aws/credentials`. A bare `ls` does not print them, so leaving off `-a` walks you straight past the richest file in the tree while showing you a directory that looks fully explored.
- `2>/dev/null` → stops one missing path from burying the file that does exist. It also hides `Permission denied`, so if the whole thing comes back empty, re-run the single path you care about **without** it before you believe the answer.

**What you will see**

- **Found** — an assignment carrying a value nobody would print in a manual: `define('DB_PASSWORD', 'Str0ngishThing')` in `wp-config.php`, a `new mysqli('localhost', 'webapp', '...')` line in `config.php`, a `DB_PASSWORD=` line in `.env`. Specific and unmemorable is the tell.
- **Empty** — if `ls` listed the files but `cat` printed nothing, the web user owns them and you are not the web user; that is a permission answer, not an absence. If `ls` itself showed nothing, the app is served from somewhere else — find it from the running process (`ps aux | grep -E 'apache|nginx|php'`) or the vhost config in `/etc/nginx/sites-enabled/`.
- **Error** — `cat: ...: Permission denied` is the good error: the file exists and is worth a privilege step. `No such file or directory` on every path means wrong root, not a clean host.
- **Noise** — `.env.example`, `config.php.dist`, `wp-config-sample.php`. These ship with the framework and contain `your_password_here`, `secret`, `changeme`. A value that appears in the project's public documentation is documentation.

**Then** — a real value goes to step 5 to be spent. A `Permission denied` goes to [[Linux-Privilege-Escalation]] with a concrete target in hand, which is a much better position than a generic escalation hunt. Nothing at all sends you to step 2, which does not depend on knowing the path.

## 2 — Sweep for the shape of a secret

**Why now** — step 1 assumed you knew where to look. This one does not: instead of a filename you search for the *shape* of an assignment, which catches backup scripts, cron helpers, `.bak` copies and the application nobody mentioned. Run it when step 1 was empty, and again after every lateral move, because the filesystem you can read changes with the user.

```bash
grep -rniI --exclude-dir={node_modules,vendor,.git,proc,sys} \
  -E '(pass(word|wd)?|secret|api[_-]?key|token|connection ?string)[[:space:]]*[=:>][[:space:]]*[^[:space:]#]' \
  /var/www /opt /srv /home /usr/local /etc 2>/dev/null
```

- `-I` → skip binary files. Without it a single matching binary dumps raw bytes into your terminal, which on a raw reverse shell can leave the session unusable and cost you the shell.
- `[=:>]` followed by a **non-blank** → demands an actual assigned value. This one character class is what removes every prose sentence that merely contains the word "password", and it is the difference between forty hits and four thousand.
- `--exclude-dir` → `node_modules` and `vendor` are third-party code shipped with the app. They contain thousands of matches, all of them somebody else's test fixtures.
- path order → application directories first, `/etc` last. `/etc` is mostly documentation and will scroll the real hit off the screen if it comes first.
- no bare `/` → walking the whole filesystem drags `grep` through `/proc` and `/sys`, where it blocks on pseudo-files and appears to hang. Name your directories.

**What you will see**

- **Found** — a hit inside a file belonging to something a human configured: a `.env`, a `settings.py`, a `docker-compose.yml`, a backup script under `/opt`, a `.git-credentials`. Note the filename's **owner** with `ls -l` in the same breath — you will need it in step 5.
- **Empty** — a genuine and useful answer if you ran it as a user with broad read access: it says the escalation is a process or a schedule, not a stored secret, and points you back at [[Linux-Run-Sheet]] steps 4 and 5b. As a low-privilege web user it says almost nothing, because most of the tree was invisible to you.
- **Error** — `grep: ...: Permission denied` only when you drop `2>/dev/null`, and that listing is worth reading once on purpose: the directories that refuse you are the ones a privilege step would open. `Argument list too long` means a shell glob crept in — this command passes directories, never `*`.
- **Noise** — the largest category on this whole page. Lines starting `#` are comments, which are documentation, not configuration. `foobar`, `changeme`, `example`, `<your-key-here>`, `password123456` in a manual page. `/etc/login.defs`, `/etc/ssh/sshd_config` and everything under `/etc/fwupd/` match on a completely clean system.

**Then** — a hit with an owner goes to step 5. A hit whose owner is `root` and whose file you could only partly read is a privilege target: [[Linux-Privilege-Escalation]]. Empty goes to step 3, which searches what the *user* typed rather than what the app stores.

## 3 — The user's own trail

**Why now** — steps 1 and 2 searched what applications store. People leave a different kind of evidence: a password typed on a command line, a host they mounted, an environment variable exported into a service. This is where you find the credential nobody wrote into a config.

```bash
cat ~/.bash_history ~/.zsh_history ~/.mysql_history ~/.psql_history 2>/dev/null
```

```bash
env
```

```bash
cat /proc/<PID>/environ | tr '\0' '\n'
```

```bash
ls -la ~ /home/* /root 2>/dev/null
```

- read the **file**, do not run `history` → the `history` builtin prints the current shell's in-memory list, and a reverse shell has none. It answers with silence on a host whose `.bash_history` is full. This exact confusion ends the hunt one command too early. The reverse also bites: a live session has not written its own commands to the file yet, so the file and the builtin never quite agree.
- `cat /proc/<PID>/environ` → the environment as the kernel holds it, for the process you name. A service started with a password in its environment shows it here even when `env` in your interactive shell does not. `<PID>` (process identifier) comes from the process list in [[Linux-Run-Sheet]]; `/proc/self` is the process doing the reading, so it hands you your own environment back and tells you nothing.
- `ls -la /home/*` → per-user dotfiles you may still be able to read across accounts: `.netrc`, `.git-credentials`, `.aws/credentials`, `.docker/config.json`, `.my.cnf`.

**What you will see**

- **Found** — a command line with the password inline: `mysql -u root -pHunter2`, `sshpass -p '...' ssh ...`, `curl -u admin:...`, a `wget` to an internal host with a token in the query string. Also worth as much: the *hostnames and paths* in the history, which name internal services you have not scanned yet.
- **Empty** — usually means the shell was configured not to record: `HISTFILE` unset, `HISTSIZE=0`, or the file symlinked to `/dev/null`. Check with `ls -la ~/.bash_history` — a zero-byte file or a symlink is a deliberate choice by whoever built the box, not an absence of activity, and it tells you this route is closed rather than untried.
- **Error** — `Permission denied` on another user's `.bash_history` is expected and is itself a finding: the file exists and holds their typing, so it becomes a reason to become them.
- **Noise** — your own commands, once you have been on the box a while. And `ls`, `cd`, `vi` with no arguments. Read the history for arguments, not for command names.

**Then** — a password goes to step 5. A hostname or port you have not seen goes to [[Pivoting-and-Tunneling]], because internal services are the usual reason a history file names a host you cannot reach. Empty goes to step 4.

## 4 — Keys, and the mount table

**Why now** — a key is better than a password: it is a login on its own, it survives password changes, and it often works across hosts. The mount table is the other half — it records credentials used to attach network storage, and those are frequently the domain or [[Security-Terms#^nas|NAS]] account.

```bash
find / -name 'id_*' -o -name '*.pem' -o -name 'authorized_keys' 2>/dev/null | grep -v '/proc/'
```

```bash
cat /etc/fstab; cat /etc/exports 2>/dev/null
```

- `find -name 'id_*'` → catches `id_rsa`, `id_ed25519`, `id_ecdsa` and the `.pub` halves in one pass. Searching only for `id_rsa` misses the modern default on any host built recently.
- `authorized_keys` → the reverse direction, and the one people forget. If you can **write** it in another user's `.ssh`, you do not need their password at all; append your own public key.
- `/etc/fstab` → world-readable by design, and a [[Security-Terms#^cifs|CIFS]] mount line carries either the password inline or `credentials=/root/.smbcred`, which names a file you now know to want.

**What you will see**

- **Found** — a private key whose first line reads `-----BEGIN OPENSSH PRIVATE KEY` and closes with five more dashes, in another user's `.ssh/`, or an fstab line like `//10.0.0.5/backup /mnt/backup cifs credentials=/etc/.smb,uid=1000 0 0`.
- **Empty** — genuinely common on a lab host and closes the key route. It does not close step 2 or step 3.
- **Error** — after copying a key back to Kali, `ssh` refuses with `Permissions 0644 for 'id_rsa' are too open ... this private key will be ignored`. That is **your own** file mode on **your own** machine, not a bad key — `chmod 600 id_rsa` and it works. Reading that message as a corrupt key is a standard half-hour. `Load key: error in libcrypto` means the file was truncated in transfer or you saved an HTML error page ([[File-Transfer]]). `Enter passphrase for key` means the key is encrypted — do not discard it, it cracks offline.
- **Noise** — `/etc/ssh/ssh_host_*_key` are the *server's* host keys. They authenticate the server to clients and log you in nowhere. `id_rsa.pub` is public by definition.

**Then** — a usable key goes to [[22-SSH]]; try it against every username from `/etc/passwd`, since the file's location does not always name its owner. A passphrase-protected key goes to [[Hash-Cracking]] through `ssh2john`. An fstab credentials path you cannot read is a privilege target with a name attached. A writable `authorized_keys` is a foothold — [[Linux-Privilege-Escalation]].

## 5 — Spend it

**Why now** — you are holding a string. It is worth nothing until it is attached to an account, and the mistake that wastes the most time here is assuming a database password is only a database password. Reuse across accounts and across hosts is the normal case on lab boxes and common in the field.

```bash
su - "$USER_GUESS"                          # names come from /etc/passwd, step 2 of the run sheet
```

```bash
ssh -o PreferredAuthentications=password,keyboard-interactive "$USER_GUESS"@127.0.0.1
```

```bash
mysql -h 127.0.0.1 -u "$DB_USER" -p         # the same string, against the service it was written for
```

- try the **shell** account before the service account → a password written for MySQL that also opens `su` is worth far more than one that only opens MySQL, and it costs one command to find out.
- `-o PreferredAuthentications=password` → without it, `ssh` offers your keys first, burns through the server's `MaxAuthTries`, and returns `Permission denied (publickey,password)` before it ever tries the password you came to test. You then wrongly cross the password off.
- `su - ` with the dash → a login shell, so you get the target user's `PATH`, `HOME` and profile. Without it you keep your own environment and their `sudo` rules can behave oddly.

**What you will see**

- **Found** — a prompt that comes back as somebody else. Confirm with `id`, then restart the whole host sweep as them: [[Linux-Run-Sheet]] from step 1.
- **Empty** — not a category here; every attempt either succeeds or errors.
- **Error** — `su: Authentication failure` means wrong password *or* wrong user; vary the user before you retire the password. `su: must be run from a terminal` means your shell has no TTY, the password is untested, and the fix is the upgrade in [[Shells]] — not another password. `Permission denied, please try again` from `ssh` to `127.0.0.1` while `su` works usually means `PasswordAuthentication no` in `sshd_config`; use `su`. `ERROR 1045 (28000): Access denied for user` from MySQL is a clean negative for that user.
- **Noise** — a successful `su` to a service account with `/usr/sbin/nologin` returns you instantly to your own prompt with no error worth reading. Check `id` after every switch rather than trusting the prompt string, which the target user's `PS1` controls.

**Then** — success restarts the loop as the new user, and the loop is the point: each account sees files the last one could not. Failure against every username sends the string to [[Hash-Cracking]] if it was a hash rather than a password, or to [[Custom-Wordlist-Attack-Chain]] to mutate it — `Summer2024` and `Summer2024!` are different strings and the same secret.

## Windows

The same idea, different storage. Windows keeps its secrets in the registry, in the Credential Manager, in unattended-install XML and in PowerShell transcripts rather than in text files under a web root — the sweep is structurally different and lives in [[Windows-Credential-Harvesting]]. PowerShell's own history file is the direct analogue of step 3: [[PowerShell-History]].

## Rarely — worth one command, not worth a step

**Why now** — the five steps above cover where secrets normally live. These are the places that hold one perhaps twice a year, and each is a single command you run when the sweep came back with nothing but template boilerplate.

```bash
cat ~/.netrc ~/.git-credentials ~/.aws/credentials ~/.docker/config.json 2>/dev/null
```

- Four files that exist to store a credential in clear text so a tool does not have to ask. They are missed by a `password=` sweep because three of them do not use that word at all.
- `.git-credentials` holds the full URL including the token, which is a working credential for a code host rather than for this machine.

```bash
ls -la /var/backups /var/mail /var/spool/mail 2>/dev/null
```

- Backups of `/etc` land in the first of these on Debian-family systems, including old copies of the shadow file that are sometimes readable when the live one is not.
- Mail is where a service or a person is told their own initial password, and it is plain text. Read the spool file for any user whose name you already have.

```bash
grep -rniI 'password' /var/log --include='*.log' 2>/dev/null | head -20
```

- Applications log the failed command, and the failed command frequently contains the password that was typed one field early. The `--include` keeps this off binary rotated archives, which is what makes the difference between two seconds and two minutes.
- Cap the output on purpose. If twenty lines hold nothing, the twenty-first will not either, and a full log sweep is how an hour disappears.

**What you will see**

- **Found** — a token in a tool's own credential file, a readable backup of a file you were denied, or a password sitting in a log line beside the command that failed.
- **Empty** — the normal answer for all three. They are lottery tickets, not steps.
- **Error** — `Permission denied` on `/var/backups` or a mail spool is itself the finding you want next: it means the files exist and belong to someone worth becoming.
- **Noise** — logs are full of the literal word in prompts and error strings. A hit is a line where the word is followed by a value, not by a question mark.

**Then** — anything recovered goes to step 5 above and gets spent against a service. Nothing found means the secrets on this host are not in files, and the next place to look is the process list in the run sheet.

## Reading the output

The point is never the file, it is the **reach** of what is in it. A credential found here is rarely single-use: the same string very often opens the database, another user's `su`, an SSH login, and a second host. Treat every secret as a credential-reuse lead and try it everywhere before accepting that it unlocks only the service it was written for.

A config that names a database you cannot reach is not a dead end — it is a reason to look for a tunnel ([[Pivoting-and-Tunneling]]). Services referenced in a config are very often bound to `127.0.0.1` and were therefore invisible to your external scan.

Two findings from different steps beat one strong finding on its own. A username from step 3 and a password from step 1 are a login; either alone is a note in your file.

## Next

- [[Source-Code-Disclosure]] — when the server-side source itself is exposed, this is the file you read
- [[Windows-Credential-Harvesting]] — the same sweep on a Windows host
- [[3306-MySQL]] · [[5432-PostgreSQL]] · [[27017-MongoDB]] — the connection string you just found usually points here
- [[Pivoting-and-Tunneling]] — reaching a database the config names but the firewall hides

## Gaps

- No structured list of framework-specific config paths (Laravel, Django, Rails, Node).
- Nothing on cloud credential files (`~/.aws/credentials`, instance metadata) beyond the mention in step 3.
- No coverage of secrets inside container images or `docker inspect` output on a host running containers.
