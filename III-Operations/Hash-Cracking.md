# Hash Cracking

Turning a hash into a password. Nine notes in this vault end by handing you a hash they cannot spend — this is where that thread continues.

The commands are the easy half and they live in your shell history. The half that costs the time is **identifying what you are holding** and **reading a failure correctly**, because "it did not crack" has five different meanings and only one of them means try harder.

Two rules first. Cracking happens **on your machine, never the target**: it is CPU-bound, loud, and the target has neither the wordlist nor the tool. And it is **offline** — not a login attempt, so no lockout policy and no failed-auth log entry can catch you. Which is also the cue to ask, before you start, whether you need the plaintext at all: an [[Security-Terms#^ntlm|NTLM]] hash is already a credential ([[5985-WinRM]], SMB), and pass-the-hash skips this whole note.

## 1 — Identify before you crack

| Shape | What it is | hashcat `-m` | john `--format=` |
|---|---|---|---|
| 32 hex chars | **MD5 *or* NTLM** — ambiguous, try both | `0` / `1000` | `raw-md5` / `NT` |
| 40 hex chars | SHA-1 | `100` | `raw-sha1` |
| 64 hex chars | SHA-256 | `1400` | `raw-sha256` |
| `$1$…` | MD5crypt | `500` | `md5crypt` |
| `$5$…` | SHA-256crypt | `7400` | `sha256crypt` |
| `$6$…` | SHA-512crypt — the Linux `/etc/shadow` default | `1800` | `sha512crypt` |
| `$2a$` `$2b$` `$2y$` | bcrypt | `3200` | `bcrypt` |
| `$P$…` `$H$…` | phpass — WordPress, phpBB | `400` | `phpass` |
| `user::DOMAIN:…` | NetNTLMv2 — captured from the network | `5600` | `netntlmv2` |
| `$krb5tgs$23$…` | [[Kerberoasting]] ticket, RC4 | `13100` | `krb5tgs` |
| `$krb5tgs$17$…` `$krb5tgs$18$…` | the same ticket, AES-128 / AES-256 | `19600` / `19700` | — |
| `$krb5asrep$23$…` | AS-REP roast | `18200` | `krb5asrep` |
| `$DCC2$10240#user#…` | MsCacheV2 cached domain logon (DCC2) | `2100` | `mscash2` |

The `$x$` prefix is a **format identifier**, not part of the hash: `$6$salt$digest` says "SHA-512crypt, this salt, this digest". That is why prefixed hashes never need guessing — the hash announces itself. Bare hex strings are the ambiguous ones.

```bash
hashid '$6$rounds=5000$abc'      # or: haiti '<hash>'
```

- treat the output as a **ranked list of candidates**, not an answer → `hashid` matches on shape alone and will list five modes for a 32-hex string. It narrows the guess; it does not end it.

> [!important] `aad3b435b51404eeaad3b435b51404ee` is not a hash to crack
> That exact string is the **empty LM half** of a dumped NT:LM pair. Seeing it means LM storage is disabled — good hygiene on the target, nothing to attack. Crack the NT half to the right of the colon.

> [!important] A `$DCC2$` hash cracks but never passes
> MsCacheV2 — Domain Cached Credentials, version 2 (DCC2) — is what a Windows host caches so a domain user can still log in when the domain controller is unreachable. Unlike an [[Security-Terms#^nt-hash|NT hash]] you **cannot** pass-the-hash with it: no protocol will accept it, so cracking is the only road, and a slow one — it is a deliberately expensive key-derivation function run over 10240 rounds, hashcat mode `2100`. It comes from a host's LSA cache ([[Windows-Credential-Harvesting]]), never from the [[DCSync]] domain pull.

## 2 — Prepare the hash file

```bash
printf '%s' '$6$xyz$abc123...' > hash.txt
```

- `printf '%s'` (or `echo -n`) → **no trailing newline**. `echo` without `-n` appends one, and some formats fold it into the hash, so the correct password never matches. This is the single most common self-inflicted "uncrackable".
- one hash per line, nothing else → no surrounding quotes, no `Hash: ` label pasted from a write-up, no blank trailing line.
- copied off a Windows box? `dos2unix hash.txt` → an invisible `\r` at each line end is behind a large share of "No hashes loaded".

Decide up front whether the username stays in the file:

```bash
hashcat -m 1000 --username hash.txt rockyou.txt   # hashcat: tell it the user column is there
```

```bash
john --format=NT hash.txt                         # john: reads user:hash natively
```

## 3 — hashcat

```bash
hashcat -m 1800 -a 0 hash.txt /usr/share/wordlists/rockyou.txt
```

- `-m` → hash mode from step 1's table. The one flag you cannot get wrong.
- `-a 0` → attack mode 0, straight dictionary. The default, and it covers most lab work.
- `-a 3 hash.txt '?u?l?l?l?l?d?d'` → brute force by **mask**: one upper, four lower, two digits. `?l` lower `?u` upper `?d` digit `?s` symbol `?a` all. Use when a password's *shape* is known but it is not in any list.
- `-r /usr/share/hashcat/rules/best64.rule` → mutate every wordlist word (`password` → `Password1`, `p@ssw0rd`, `PASSWORD!`). The single highest-value upgrade when a plain dictionary run exhausts, and the step most people skip on the way to brute force. Point it at **hashcat's own** rules dir — John's `/usr/share/john/rules/best64.rule` uses a different syntax, so hashcat silently skips most of its lines (`Cannot convert rule`, `Skipping`) and runs a fraction of the set. No hashcat rules dir on the box? `wget` the one file from hashcat's GitHub `rules/` folder.
- `--username` → **required** if the file has a `user:hash` column; without it hashcat treats the username as part of the hash and rejects the line.
- `--show` → reprint what is already cracked, straight from the potfile.
- `--force` → ignore the "no [[Security-Terms#^opencl|OpenCL]] device" warning in a VM; common on a Kali guest.

While a run is going, single keys steer it: `s` status, `p` pause, `r` resume, `q` quit-and-save.

## 4 — john

```bash
john --wordlist=/usr/share/wordlists/rockyou.txt hash.txt
```

```bash
john --format=sha512crypt --wordlist=/usr/share/wordlists/rockyou.txt hash.txt
```

- no `--format` → john picks one and **prints the name it chose**. Read that line; a wrong guess makes the whole run worthless, and it is easy to miss above the progress output.
- `--rules` → john's mutation engine, the equivalent of hashcat's `-r`.
- `--incremental` → brute force; a last resort that does not terminate on its own.
- `--users=root` / `--fork=4` → limit to one account, or split across four cores.
- `--show hash.txt` → print cracked results from `~/.john/john.pot`.

## 5 — Linux `/etc/shadow`

```bash
unshadow /etc/passwd /etc/shadow > combined.txt
```

```bash
john --wordlist=/usr/share/wordlists/rockyou.txt combined.txt
```

- both files are needed even though only `shadow` holds the hash → `passwd` supplies the username and account metadata `unshadow` merges in. Feeding `shadow` alone still works but loses the usernames that make a crack a login.
- cut it down first → delete every account whose hash field is `*` or `!` before running. Those are **locked** accounts with no hash; cracking seventeen of them is time spent on nothing.

## 6 — Everything that is not already a hash

```bash
ssh2john id_rsa > kh.txt        # zip2john / office2john / keepass2john follow the same shape
```

```bash
john --wordlist=/usr/share/wordlists/rockyou.txt kh.txt
```

- redirect to a file → `*2john` prints the extracted hash to stdout; without the `>` it scrolls past and you have nothing to crack.
- `locate *2john` → shows which extractors your install actually ships (`rar2john`, `pdf2john`, `bitlocker2john`, dozens more). The one you want is usually already there.

> [!important] KeePass KDBX 4 breaks this step
> `keepass2john` cannot parse the modern [[Security-Terms#^keepass|KeePass]] format — it stops with `File version '40000' is currently not supported` and the off-host crack never starts. KDBX 4 uses Argon2, which is deliberately slow to brute-force anyway. When the host has the KeePass client, open the `.kdbx` there instead of carrying it off; a database also keyed to the Windows account only opens on that box.

## Wordlists

```bash
gunzip -k /usr/share/wordlists/rockyou.txt.gz
```

- `-k` → keep the compressed original. rockyou ships gzipped on a fresh Kali; ~14M entries and the right first attempt for essentially every lab hash.
- `/usr/share/seclists/Passwords/` holds larger and more targeted lists for when rockyou exhausts.
- a list built from the target's own vocabulary beats a bigger generic one → [[Custom-Wordlist-Attack-Chain]].
