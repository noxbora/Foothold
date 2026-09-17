---
type: technique
platform: windows
status: working
fluency: guided
source: thm
updated: 2026-09-17
---

# Active Directory — Authenticating With What You Hold

You are holding something that is not a shell — a password, a string of hex, a captured response, a ticket file — and you want it to become access to a domain service. What that thing *is* decides which of the domain's two authentication protocols it can travel over, and choosing the wrong one produces an error that reads exactly like a bad password.

## What exactly am I holding

**Why now** — you have recovered a credential-shaped string from a dump, a config file, a capture or a crack, and before you type anything you need to know whether it authenticates at all. Three of the five strings below do not, and every hour lost here is lost to passing something that was never passable.

| what you are holding | what it is | travels over | how you pass it |
| --- | --- | --- | --- |
| `Password123!` | a plaintext password | NTLM or Kerberos | `domain/user:'password'@target` |
| 32 hex characters | the NT hash | NTLM directly, Kerberos after `getTGT.py` | `-hashes :<nt hash>` |
| `user::DOMAIN:1122…:8f4c…:0101…` | a NetNTLMv2 response | nothing | crack it into a password first |
| `$krb5tgs$23$*svc…` | a service ticket | nothing | crack it into a password first |
| `$krb5asrep$23$user@…` | an AS-REP | nothing | crack it into a password first |
| `user.ccache` | a real Kerberos ticket | Kerberos only | `-k -no-pass` |

Five different things get called "the NTLM hash" in the same afternoon and only one of them is the NT hash. The stored value — 32 hex characters, sitting in the SAM or the directory — is a credential in its own right. The value seen on the wire is a NetNTLMv2 response: a signature made *with* that hash over a random challenge the server invented, so it is different on every login and there is nothing in it to replay.

> [!important] A response is not a hash you can pass
> Feeding a `user::DOMAIN:…` string to `-hashes` fails, and feeding it to `hashcat -m 1000` fails with `Token length exception` — which reads like a formatting mistake rather than the category error it is. Count the characters: 32 and nothing else is an NT hash — an MD5 digest is also 32 hex characters, so the count narrows the field and where the string came from settles it. Anything longer, anything with colons in the middle, has to be cracked before it authenticates.

Which protocol a service will even attempt is not entirely your choice. Kerberos needs a *name*: the client asks the domain controller for a ticket issued to `cifs/server1.domain.local`, and no such name exists for `192.168.1.51`. So an IP address in the command means NTLM, always; a hostname means you may pick.

**What you will see** — this section produces no output; it is the read you do before the first command. **Found** is a string that matches one row exactly. **Empty** is a string that matches none of them, which usually means it is a hash from something that is not Windows at all — take it to [[Hash-Cracking]] and identify it there. **Error** is a 32-character string that fails as an NT hash, and the usual cause is that it is an MD5 from a web application. **Noise** is the `aad3b435b51404eeaad3b435b51404ee` you will see printed beside almost every NT hash: it is the LM hash of an empty string, not a secret, and not the value you pass.

**Then** — a password goes to the next section, an NT hash to the one after it, a `.ccache` to the Kerberos section. The three crackable strings go to [[Hash-Cracking]] and come back here as passwords or not at all.

## Authenticating with a password

**Why now** — you hold a username and a plaintext password and nothing else, and you want to know what that account actually reaches before spending it on anything cleverer. An SMB session is the cheapest possible test: it answers in one round trip and tells you whether the credential is wrong, right, or right and unprivileged.

```bash
smbclient.py 'domain.local/user:Password123!'@192.168.1.51
```

- `domain.local/` → the domain the account lives in, not the target's hostname. Leave it off and the account is offered as a *local* account on the target, which a domain account is not; the answer is `STATUS_LOGON_FAILURE` and you spend the next twenty minutes doubting a password that was correct.
- single quotes around the whole `domain/user:password` string → for the shell, not for impacket. An unquoted `!` triggers history expansion in an interactive bash and an unquoted `$` expands to nothing, so the tool receives a password you never typed.
- an IP address as the target → forces NTLM, which is what you want for this test: no name resolution, no clock, nothing else that can fail.

**What you will see**

- **Found** — `Type help for list of commands` and a `#` prompt. `shares` lists what this account can see and `use <share>` enters one.
- **Empty** — the prompt appears and `shares` returns only `IPC$`, `ADMIN$` and `C$`, none of which you can enter. The credential is valid and this host holds nothing for it. That is a fact about the host, not about the credential: the same account may own a share on the next machine.
- **Error** — `STATUS_LOGON_FAILURE` is a wrong username, password or domain. `STATUS_ACCESS_DENIED` is a valid credential without the right being asked for. `STATUS_PASSWORD_MUST_CHANGE` and `STATUS_ACCOUNT_DISABLED` both mean the password you recovered is correct and the account cannot currently use it — which still makes it worth spraying elsewhere.
- **Noise** — `IPC$` appears in every authenticated session and is access to nothing you can read: it is the interprocess channel the remote-execution tools ride on, not a file share. A share that appears in `shares` and then errors on `use` is a listing right without a read right, and it is the most common thing mistaken for a foothold.

**Then** — a prompt sends you to [[Kerberoasting]] first, because any working domain credential is worth a roast before it is worth anything else, and then to [[Active-Directory-Lateral-Movement]] to find where the account is administrator. `STATUS_ACCESS_DENIED` is the same road: the credential is real. `STATUS_LOGON_FAILURE` sends you back to [[Config-File-Looting]] or [[Hash-Cracking]] for a better one.

## Authenticating with an NT hash

**Why now** — you have 32 hex characters out of a hive, a dump or a `secretsdump` run, and no plaintext. Cracking it is optional and often unnecessary: NTLM puts the hash itself into the challenge-response, so for NTLM purposes the hash *is* the credential.

```bash
smbclient.py 'domain.local/user'@192.168.1.51 -hashes :<nt hash>
```

- `-hashes <lm>:<nt>` → two halves separated by a colon, LM first. The LM half is absent on anything modern, and leaving it empty with a leading colon is the correct way to say so.
- the leading colon → the flag that is easy to drop, and dropping it puts your NT hash in the LM position and sends an empty NT hash. The result is `STATUS_LOGON_FAILURE`, indistinguishable from a wrong hash, so check the colon before you doubt the hash.
- no password anywhere in the command → correct, and the check that the flag parsed. If the tool prompts you for a password, `-hashes` did not reach it.

**What you will see**

- **Found** — the same banner and `#` prompt as a password login. Nothing in the session announces that a hash was used, which is the whole point. The session looks ordinary; the authentication itself is still logged like any other.
- **Empty** — as before, a prompt with no readable share is a valid credential on a host that holds nothing for it.
- **Error** — `STATUS_LOGON_FAILURE` covers a wrong hash *and* a malformed `-hashes` argument. An SMB session that fails during setup rather than at login is a different animal: it is a host with NTLM turned off, where the hash is still good but only through Kerberos. That route needs the domain to accept RC4 (Rivest Cipher 4) — where RC4 is disabled the hash cannot buy a ticket and you need the password or an AES (Advanced Encryption Standard) key.
- **Noise** — a password recovered by cracking a `$krb5tgs$` or `user::DOMAIN:` string is a *password*. It belongs in the previous section's command; putting it after `-hashes` produces a login failure that looks like the crack was wrong.

**Then** — a shell goes to [[Active-Directory-Lateral-Movement]] to find every host where this account is a local administrator. A host refusing NTLM goes to the next section: `getTGT.py` accepts `-hashes` too, which turns the NT hash into a Kerberos ticket without ever knowing the password.

## Authenticating with a Kerberos ticket

**Why now** — the target refuses NTLM, or you want the path that looks like normal domain traffic, or all you hold is a `.ccache` file lifted off a compromised Linux host. Kerberos needs three things NTLM never asks for: a name that resolves, the address of the domain controller, and a clock within five minutes of the domain's.

```bash
echo '192.168.1.51 server1.domain.local server1' | sudo tee -a /etc/hosts
```

```bash
getTGT.py 'domain.local/user:password' -dc-ip <dc ip>
```

```bash
export KRB5CCNAME="$PWD/user.ccache"
```

```bash
smbclient.py 'domain.local/user'@server1.domain.local -k -no-pass -dc-ip <dc ip>
```

- the target must be the hostname, never the IP → the client asks for a ticket named after whatever you typed, and no service principal name exists for an address. An IP here returns `KDC_ERR_S_PRINCIPAL_UNKNOWN`, which names the *server*, not your credential. A line in `/etc/hosts` fixes the name lookup only; it cannot create a service principal name the directory does not hold.
- `-dc-ip` → where the ticket-granting service lives. It looks redundant beside a fully qualified hostname, which is exactly why it gets dropped; without it the tool resolves the domain name through your own resolver, and on a lab network with no DNS that is a long hang followed by a connection error that reads like the domain controller being down.
- `-k` → use Kerberos, taking the ticket from `KRB5CCNAME`. `-no-pass` → do not prompt for a password. Without the `export`, `-k` finds no cache and the failure is reported in Kerberos terms, so it reads as a ticket problem rather than a missing environment variable.
- `export` with a full path rather than a bare filename → the variable is read later, from whatever directory you happen to be standing in by then.

```bash
sudo ntpdate -u <dc ip>
```

- run this the moment you see a skew error. Kerberos rejects any request whose timestamp is more than five minutes from the domain controller's, because that timestamp is what proves the request is not a replayed recording. Lab networks drift and a machine resumed from suspend drifts hard. On current Kali the binary comes from the `ntpsec-ntpdate` package.

**What you will see**

- **Found** — `[*] Saving ticket in user.ccache`, then the `#` prompt from the second tool. `klist` prints the ticket's principal, the service it is for, and its expiry.
- **Empty** — there is no empty result: `getTGT.py` either writes a file or errors. The empty-shaped failure is the one to watch for — the ticket saves, `KRB5CCNAME` was never exported, and the next tool quietly asks for a password. Being prompted for a password after passing `-no-pass` means the cache was not found.
- **Error** — `KRB_AP_ERR_SKEW(Clock skew too great)` is the clock and nothing else. `KDC_ERR_PREAUTH_FAILED` is a wrong password or hash. `KDC_ERR_C_PRINCIPAL_UNKNOWN` is a wrong username or a misspelled domain. `KDC_ERR_S_PRINCIPAL_UNKNOWN` is the target you named, not you.
- **Noise** — a `.ccache` left in the working directory from an earlier session. `KRB5CCNAME` still points at it, the tool authenticates as somebody else entirely, and whatever access that produces looks like a finding until you run `klist` and read whose ticket it is.

**Then** — a working ticket goes to [[Kerberoasting]], which needs no privilege beyond being somebody in the domain. A skew error is fixed by the command above and then `getTGT.py` is re-run: the rejected request produced no ticket, so there is nothing to retry with. `KDC_ERR_S_PRINCIPAL_UNKNOWN` is fixed in `/etc/hosts` and by using the name rather than the address.

## Reading the output

Every failure in this note is one of three kinds, and they are easy to confuse because two of them print in the same red. The credential is wrong. The credential is right and not authorised for what you asked. Or the protocol was never successfully attempted, because of a name, a clock or an environment variable. Only the first sends you back to cracking; the second is a finding about the host; the third costs a minute to fix and nothing to learn from.

Choosing the protocol is also choosing what a failure will tell you. NTLM answers with SMB status codes, which describe the session and the account. Kerberos answers with KDC error codes, which describe names and time. When a target accepts both, run the NTLM form first against the IP: it gives you a clean verdict on the credential with the fewest moving parts, and the Kerberos form afterwards tells you whether your naming is right.

## Rarely — worth one command, not worth a step

- A `.ccache` stolen from a compromised Linux host. Tickets live at `/tmp/krb5cc_<uid>`, readable by their owner and by root; copy one out, point `KRB5CCNAME` at it, and you are that user until it expires — ten hours from when it was issued, not from when you took it, unless domain policy says otherwise. `klist` prints the real expiry and the principal it belongs to.
- `-aesKey` in place of `-hashes`, for a domain where RC4 has been disabled. The key comes out of the same dump the NT hash does.
- An empty username with `-no-pass` and no `-k` is a null session; on an older or misconfigured host it still lists shares, and it costs one command to find out.

## Next

- [[Kerberoasting]] — the first thing any working domain credential is worth, and it needs no privilege
- [[Active-Directory-Lateral-Movement]] — where the credential is a local administrator, and what to do about it
- [[Hash-Cracking]] — for the three strings in the table above that must become passwords before they authenticate
- [[Authentication-Coercion]] — where a captured response came from, and the other road that produces a plaintext password

## Gaps

- Null sessions and name-resolution poisoning are still not covered; the rest of what is upstream of this note now lives in [[AD-Username-Enumeration]], [[Password-Spraying]] and [[Authentication-Coercion]].
- Forging rather than presenting: a domain-wide forged ticket from the KRBTGT hash, and a service-scoped one from a service account hash, both bypass everything here. Unwritten.
- NTLM relaying — taking an authentication attempt aimed at you and spending it somewhere else — needs no cracking at all and is the reason a captured response is still worth having.
- AS-REP roasting is named in the table and nowhere explained.
- Nothing on machine accounts as identities, or on what a SYSTEM shell on a domain-joined host is worth as a domain credential.
