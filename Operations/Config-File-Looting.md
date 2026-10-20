# Config File Looting

Requires a shell you already hold. Configuration files are where applications keep the secrets they need at runtime — database passwords, API keys, connection strings — in plaintext, because the application has to read them back every time it starts. More notes point here than to almost anywhere else in the vault, because "did you check the config?" is the answer to a large share of stuck boxes.

The note is one loop, repeated per user: find a file somebody configured, read a value out of it, then find the account that value belongs to. A password with no username attached is half a finding, and half a finding is what keeps people typing for two hours.

> [!important]
> After `2>/dev/null`, *no match* and *permission denied* look identical — both print nothing. Every step below says which of the two its silence means, because they demand opposite next moves: one closes the route, the other says come back as a different user.

## 1 — The web root

```bash
ls -la /var/www /var/www/html /srv/www /usr/share/nginx/html 2>/dev/null
```

```bash
cat /var/www/html/config.php /var/www/html/wp-config.php 2>/dev/null
```

- `ls -la` before `cat` → configuration hides in dotfiles: `.env`, `.htpasswd`, `.git/config`, `.aws/credentials`. A bare `ls` does not print them, so leaving off `-a` walks you straight past the richest file in the tree while showing you a directory that looks fully explored.
- `2>/dev/null` → stops one missing path from burying the file that does exist. It also hides `Permission denied`, so if the whole thing comes back empty, re-run the single path you care about **without** it before you believe the answer.

## 2 — Sweep for the shape of a secret

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

## 3 — The user's own trail

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

## 4 — Keys, and the mount table

```bash
find / -name 'id_*' -o -name '*.pem' -o -name 'authorized_keys' 2>/dev/null | grep -v '/proc/'
```

```bash
cat /etc/fstab; cat /etc/exports 2>/dev/null
```

- `find -name 'id_*'` → catches `id_rsa`, `id_ed25519`, `id_ecdsa` and the `.pub` halves in one pass. Searching only for `id_rsa` misses the modern default on any host built recently.
- `authorized_keys` → the reverse direction, and the one people forget. If you can **write** it in another user's `.ssh`, you do not need their password at all; append your own public key.
- `/etc/fstab` → world-readable by design, and a [[Security-Terms#^cifs|CIFS]] mount line carries either the password inline or `credentials=/root/.smbcred`, which names a file you now know to want.

## 5 — Spend it

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

## Windows

The same idea, different storage. Windows keeps its secrets in the registry, in the Credential Manager, in unattended-install XML and in PowerShell transcripts rather than in text files under a web root — the sweep is structurally different and lives in [[Windows-Credential-Harvesting]]. PowerShell's own history file is the direct analogue of step 3: [[PowerShell-History]].
