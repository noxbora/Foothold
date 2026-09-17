---
type: technique
platform: any
status: working
fluency: guided
source: thm
updated: 2026-09-17
---

# Hash Cracking

Turning a hash into a password. Nine notes in this vault end by handing you a hash they cannot spend — this is where that thread continues.

The commands are the easy half and they live in your shell history. The half that costs the time is **identifying what you are holding** and **reading a failure correctly**, because "it did not crack" has five different meanings and only one of them means try harder.

Two rules first. Cracking happens **on your machine, never the target**: it is CPU-bound, loud, and the target has neither the wordlist nor the tool. And it is **offline** — not a login attempt, so no lockout policy and no failed-auth log entry can catch you. Which is also the cue to ask, before you start, whether you need the plaintext at all: an [[Security-Terms#^ntlm|NTLM]] hash is already a credential ([[5985-WinRM]], SMB), and pass-the-hash skips this whole note.

## 1 — Identify before you crack

**Why now** — you have a string that looks like a hash and nothing else. Choosing the mode is the one decision that cannot be recovered from by trying harder: the wrong `-m` does not error, it exhausts the wordlist and reports failure, which is indistinguishable from a strong password. Most wasted hours in this note start with a skipped identification.

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

The `$x$` prefix is a **format identifier**, not part of the hash: `$6$salt$digest` says "SHA-512crypt, this salt, this digest". That is why prefixed hashes never need guessing — the hash announces itself. Bare hex strings are the ambiguous ones.

```bash
hashid '$6$rounds=5000$abc'      # or: haiti '<hash>'
```

- treat the output as a **ranked list of candidates**, not an answer → `hashid` matches on shape alone and will list five modes for a 32-hex string. It narrows the guess; it does not end it.

**What you will see**

- **Found** — a row in the table matches exactly: a `$6$` prefix, a `user::DOMAIN:` shape, a clean 32-hex string. You now have a specific `-m` to carry into step 3.
- **Empty** — not a category; a string is always *some* shape. If nothing matches the table, the thing is probably not a raw hash — it may be base64, hex-encoded text, or a [[Security-Terms#^jwt|JWT]]. Decode it (`echo <s> | base64 -d`, `xxd -r -p`) before assuming it is uncrackable.
- **Error** — `hashid` returning a dozen candidates for a bare hex string is expected, not a failure: hex is genuinely ambiguous and the tool is honest about it. Try the common two or three ([[Security-Terms#^md5|MD5]], NTLM, [[Security-Terms#^sha|SHA-1]]) rather than all twelve.
- **Noise** — the `aad3b435...` half of a dumped pair is the loudest false lead here; see the callout below. A 32-hex "hash" that is actually an MD5 of the *username* is another.

> [!important] `aad3b435b51404eeaad3b435b51404ee` is not a hash to crack
> That exact string is the **empty LM half** of a dumped NT:LM pair. Seeing it means LM storage is disabled — good hygiene on the target, nothing to attack. Crack the NT half to the right of the colon.

**Then** — a confident identification goes to step 2 to prepare the file, then step 3 (hashcat) or step 4 (john). An ambiguous hex string goes to step 4, because john will try to identify it for you. A string that is not a hash at all goes back to where you found it — you are decoding, not cracking.

## 2 — Prepare the hash file

**Why now** — you have identified the hash and are about to feed it to a tool that is far pickier about its input than it looks. Get the file wrong and the tool reports a format error, which reads exactly like a cracking failure and sends you tuning the attack when the problem is a stray byte.

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

**What you will see**

- **Found** — not really an output-producing step; success here is silent and only shows up as step 3/4 *loading* the hash instead of rejecting it.
- **Empty** — a zero-byte `hash.txt` means the paste or redirection failed; `cat hash.txt` to confirm the hash is actually in there and on one line.
- **Error** — this is the whole point of the step. `No hashes loaded` almost always means a trailing newline, a `\r`, or a `username:` prefix the tool did not expect. `Token length exception` means the hash length does not fit the declared mode — wrong `-m`, or a truncated paste. Both are **input** errors, not password errors.
- **Noise** — a warning that hashcat is "Removing" a hash from the session usually means a duplicate or an already-cracked entry, not a malformed file. Read which hash it names.

**Then** — a file that loads cleanly goes to step 3 or 4. A persistent `No hashes loaded` after you have checked the newline and line endings means the **mode** is wrong — back to step 1.

## 3 — hashcat

**Why now** — you have a clean file and a confident mode, and you want raw speed on the [[Security-Terms#^gpu|GPU]]. hashcat is the right tool when you know what you are holding; its numeric modes are unforgiving but its throughput and rule engine are why it is the default for a known hash.

```bash
hashcat -m 1800 -a 0 hash.txt /usr/share/wordlists/rockyou.txt
```

- `-m` → hash mode from step 1's table. The one flag you cannot get wrong.
- `-a 0` → attack mode 0, straight dictionary. The default, and it covers most lab work.
- `-a 3 hash.txt '?u?l?l?l?l?d?d'` → brute force by **mask**: one upper, four lower, two digits. `?l` lower `?u` upper `?d` digit `?s` symbol `?a` all. Use when a password's *shape* is known but it is not in any list.
- `-r /usr/share/hashcat/rules/best64.rule` → mutate every wordlist word (`password` → `Password1`, `p@ssw0rd`, `PASSWORD!`). The single highest-value upgrade when a plain dictionary run exhausts, and the step most people skip on the way to brute force.
- `--username` → **required** if the file has a `user:hash` column; without it hashcat treats the username as part of the hash and rejects the line.
- `--show` → reprint what is already cracked, straight from the potfile.
- `--force` → ignore the "no [[Security-Terms#^opencl|OpenCL]] device" warning in a VM; common on a Kali guest.

While a run is going, single keys steer it: `s` status, `p` pause, `r` resume, `q` quit-and-save.

**What you will see**

- **Found** — the hash line reprinted with `:plaintext` appended, and `Status: Cracked` in the summary. That plaintext after the last colon is the password.
- **Empty** — a run that finishes with **`Status: Exhausted`**. This does **not** mean uncrackable — it means *this list* did not contain it. Escalate in order: confirm the mode → bigger list → rules (`-r best64.rule`) → mask. Jumping to brute force before checking the mode is the classic waste.
- **Error** — the highest-value bullet in this note. **`Token length exception`** or **`No hashes loaded`** is a *format* error from step 2, not a cracking result — the mode is wrong or the file is dirty; the password is not the problem. **An instant "cracked" that prints nothing new** is a **potfile** hit: hashcat solved this hash in an earlier run and is answering from `~/.local/share/hashcat/hashcat.potfile`; recover it with `--show`, it is not lost. **`Separator unmatched`** with `--username` means the file has no `:` column after all.
- **Noise** — `bcrypt` or `$6$` grinding at a handful of hashes per second is **working as designed**, not stuck: these are deliberately slow, and `$2b$12$` means 2¹² iterations per guess. On a lab timeframe with a laptop, a bcrypt hash not in the first few thousand rockyou lines is usually not the intended path — treat the slowness as a signal about the box.

**Then** — a crack goes to the "Reading the output" section to be spent as a reuse lead. `Exhausted` goes up the escalation ladder above, and if rules and masks also exhaust, to [[Custom-Wordlist-Attack-Chain]] for a target-built list. A format error goes back to step 2. A potfile hit means you already had it — `--show` and move on.

## 4 — john

**Why now** — you *cannot* confidently identify the hash, or you want john's word-based format names and its habit of guessing the format for you. Reach for john when step 1 was ambiguous, and for the `*2john` extractors in step 6.

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

**What you will see**

- **Found** — the password printed beside the username, and a `1 password hash cracked` summary. `john --show hash.txt` reprints it later.
- **Empty** — `0 password hashes cracked, 1 left` after the session ends is john's `Exhausted`: this list did not hold it. Same ladder as hashcat — mode, list, rules, brute force.
- **Error** — `No password hashes loaded` is the step-2 format error again (newline, `\r`, wrong format). `No password hashes left to crack (see FAQ)` is the opposite and good news: everything in the file is **already cracked** and cached in the potfile — run `john --show hash.txt` to see it. Reading that message as a failure and re-running is a common loop.
- **Noise** — the `Using default input encoding: UTF-8` and `Proceeding with ...` lines are progress, not problems. The line that matters is the format john chose — watch that one.

**Then** — a crack goes to "Reading the output". `0 cracked` climbs the escalation ladder. `No hashes left` means run `--show` — you already won. A wrong auto-detected format sends you back to step 1 to name it explicitly with `--format=`.

## 5 — Linux `/etc/shadow`

**Why now** — you read `/etc/shadow` (an SUID abuse, a backup, a misconfigured file) and you are holding `$6$` hashes with the usernames sitting in a *separate* file. john wants them glued back together, and doing it by hand is where people produce an unloadable file.

```bash
unshadow /etc/passwd /etc/shadow > combined.txt
```

```bash
john --wordlist=/usr/share/wordlists/rockyou.txt combined.txt
```

- both files are needed even though only `shadow` holds the hash → `passwd` supplies the username and account metadata `unshadow` merges in. Feeding `shadow` alone still works but loses the usernames that make a crack a login.
- cut it down first → delete every account whose hash field is `*` or `!` before running. Those are **locked** accounts with no hash; cracking seventeen of them is time spent on nothing.

**What you will see**

- **Found** — `combined.txt` holds `user:$6$...:...` lines, one per real account, and john loads and cracks them as in step 4.
- **Empty** — a `combined.txt` where every hash field is `*` or `!` means the accounts you captured are all locked — a real answer that says these particular users have no crackable password, not that the file is broken.
- **Error** — `unshadow: command not found` means the `john` package's helpers are not on PATH; they ship in `/usr/sbin` or under the john install. `No password hashes loaded` after unshadow usually means you fed it the files in the wrong order — it is `unshadow PASSWD SHADOW`.
- **Noise** — system accounts (`daemon`, `bin`, `sys`) that carry `*` will appear in the output and load as "no hash"; they are not targets, they are filler. Cut them.

**Then** — a cracked human account goes to "Reading the output" and then to `su` ([[Config-File-Looting]] step 5). All-locked output closes the shadow route and sends you back to the [[Linux-Run-Sheet]] for a process- or schedule-based path.

## 6 — Everything that is not already a hash

**Why now** — the secret is locked inside a file — an SSH key, a zip, an Office document, a [[Security-Terms#^keepass|KeePass]] database — not sitting in a `shadow` line. The `*2john` family extracts a *crackable hash* out of that file, and the rule that trips people is that you feed the tool's **output** to john, never the original file.

```bash
ssh2john id_rsa > kh.txt        # zip2john / office2john / keepass2john follow the same shape
```

```bash
john --wordlist=/usr/share/wordlists/rockyou.txt kh.txt
```

- redirect to a file → `*2john` prints the extracted hash to stdout; without the `>` it scrolls past and you have nothing to crack.
- `locate *2john` → shows which extractors your install actually ships (`rar2john`, `pdf2john`, `bitlocker2john`, dozens more). The one you want is usually already there.

**What you will see**

- **Found** — `kh.txt` holds one line beginning `id_rsa:$sshng$...` (or `$zip2$`, `$office$`), and john cracks it to the passphrase.
- **Empty** — a zero-byte `kh.txt` means the extractor rejected the file — often because the file is not actually encrypted (an unprotected zip, a passphrase-less key), in which case there is nothing to crack and you can already use it.
- **Error** — `ssh2john: No such file` on a modern key can mean an OpenSSH-format key some builds of `ssh2john` mishandle; update john or use `ssh2john.py` from the source tree. A key that extracts but john reports `No hashes loaded` for is usually the format-detection issue — name it with `--format=SSH`.
- **Noise** — `office2john` on a document that was never password-protected prints nothing; that is not a tooling failure, the document simply has no secret.

**Then** — a cracked passphrase unlocks the key or archive; a key then goes to [[22-SSH]]. An extractor that produced nothing because the file was never encrypted means you can open it directly — no cracking needed.

## Wordlists

**Why now** — you have identified the hash and chosen the tool, so the list is the last variable left, and it is the one that decides whether the crack finishes in ten seconds or never finishes at all. It is also the variable nobody revisits: a failed run gets handed a bigger list when what it almost always needs is a different one.

```bash
gunzip -k /usr/share/wordlists/rockyou.txt.gz
```

- `-k` → keep the compressed original. rockyou ships gzipped on a fresh Kali; ~14M entries and the right first attempt for essentially every lab hash.
- `/usr/share/seclists/Passwords/` holds larger and more targeted lists for when rockyou exhausts.
- a list built from the target's own vocabulary beats a bigger generic one → [[Custom-Wordlist-Attack-Chain]].

**What you will see**

- **Found** — `rockyou.txt` sitting beside the `.gz`, around 14 million lines. That is the file every `--wordlist=` in this note points at, and the one to try before anything else.
- **Empty** — `/usr/share/wordlists/` missing or nearly empty is a minimal install rather than a broken one; `apt install wordlists seclists` restores it. Nothing about the hash has changed and no attempt has failed yet.
- **Error** — `gzip: ... No such file or directory` usually means it was already decompressed on a previous box, so `ls` the directory before concluding the install is wrong. `rockyou.txt already exists` is the same situation stated the other way round.
- **Noise** — a run that exhausts rockyou and reports nothing is **not** evidence the password is strong. It is evidence the password is not in rockyou, which is a far smaller claim, and it is the place in this note where "it did not crack" is most often misread as "it cannot be cracked".

**Then** — an exhausted rockyou goes to `/usr/share/seclists/Passwords/` for a larger generic list, or better to [[Custom-Wordlist-Attack-Chain]] to build one out of the target's own vocabulary: its site copy, its usernames, its product names. A missing wordlists package is a one-command install, not a dead end. And before you spend a second list on it, check the first paragraph of `Reading the output` below — an NTLM hash may be spendable as it stands.

## Rarely — worth one command, not worth a step

**Why now** — the straight wordlist run finished and cracked nothing. These are the two cheap escalations before you conclude the password is not guessable, plus the one command that stops you cracking the same hash twice.

```bash
hashcat -m 1800 -a 0 hash.txt /usr/share/wordlists/rockyou.txt -r /usr/share/hashcat/rules/best64.rule
```

- A rule file mutates every candidate as it is tried: capitalisation, appended digits, character substitutions. `best64` multiplies the run time by roughly sixty-four and catches the enormous class of passwords that are a dictionary word with a birthday on the end.
- Run it only after the plain wordlist has failed. Run first, it just makes the plain pass slower.

```bash
hashcat -m 1800 --show hash.txt
```

- Prints what has already been cracked from the local results file without running anything. After an interrupted session this is the difference between reading an answer and recomputing it for an hour.
- `john --show hash.txt` does the same for the other tool.

**What you will see**

- **Found** — a `hash:password` line, from the rule run or from results already on disk.
- **Empty** — the normal answer. A rule run that fails is a real result: it says the password is not a mutated dictionary word, and the next step is a targeted wordlist rather than a longer run.
- **Error** — `No such file or directory` on the rule path is common; the rules directory moves between distributions and versions.
- **Noise** — `--show` prints nothing at all when the results file is empty, which looks identical to a failed command. It is not one.

**Then** — a cracked password goes to the service it belongs to and to [[Authentication-Attacks]]. Nothing cracked goes to [[Custom-Wordlist-Attack-Chain]], where the list is built from the target rather than downloaded.

## Reading the output

Two things that decide the whole exercise and belong to no single command.

**Check whether you need the plaintext at all.** An NTLM hash is a credential in its own right — [[5985-WinRM]] takes `-H <hash>`, and SMB tooling authenticates the same way. Pass-the-hash skips cracking entirely. Spending an hour on a hash you could have simply *used* is the most common unforced error in this area, and it is a question to ask before step 1, not after step 3 fails.

**A cracked password is a credential-reuse lead**, exactly like one found in a config file. Try it against every other user, service and host before assuming it belongs to the one account it came from — password reuse across accounts is the normal case on a chained box. The cash-in mechanics are in [[Config-File-Looting]].

And one fact that explains a confusing sight: **two identical passwords producing two different hashes** is the salt doing its job. A salt is random data mixed in before hashing so identical passwords do not collide, which is why you cannot precompute a table and why each salted hash must be attacked on its own.

## Next

- [[Windows-Credential-Harvesting]] — where a Windows hash comes from, and the pass-the-hash alternative to cracking it
- [[Linux-SUID-Abuse]] — the `/etc/shadow` read that produces the `$6$` hashes above
- [[Config-File-Looting]] — a recovered `id_rsa` with a passphrase starts here, and where any crack gets spent
- [[5985-WinRM]] — spending an NTLM hash without ever cracking it

## Gaps

- No rules or mask attacks worked through in practice: `-r best64.rule` and `-a 3` are named but not demonstrated end to end.
- Nothing on GPU vs CPU throughput, or on when hashcat's `-w` workload tuning matters.
- Relaying a [[Security-Terms#^netntlmv2|NetNTLMv2]] response instead of cracking it is unwritten, which leaves an exhausted run against one looking like a dead end when it is not. Collecting them is now [[Authentication-Coercion]].
- No coverage of cracking as a *finding*: what a weak-password result means in a report.
