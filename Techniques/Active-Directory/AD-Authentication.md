# Active Directory — Authenticating With What You Hold

You are holding something that is not a shell — a password, a string of hex, a captured response, a ticket file — and you want it to become access to a domain service. What that thing *is* decides which of the domain's two authentication protocols it can travel over, and choosing the wrong one produces an error that reads exactly like a bad password.

## What exactly am I holding

| what you are holding | what it is | travels over | how you pass it |
| --- | --- | --- | --- |
| `Password123!` | a plaintext password | NTLM or Kerberos | `domain/user:'password'@target` |
| 32 hex characters | the NT hash | NTLM directly, Kerberos after `getTGT.py` | `-hashes :<nt hash>` |
| `user::DOMAIN:1122…:8f4c…:0101…` | a NetNTLMv2 response | nothing | crack it into a password first |
| `$krb5tgs$23$*svc…` | a service ticket | nothing | crack it into a password first |
| `$krb5asrep$23$user@…` | an AS-REP ([[AS-REP-Roasting]]) | nothing | crack it into a password first |
| `user.ccache` | a real Kerberos ticket | Kerberos only | `-k -no-pass` |

Five different things get called "the NTLM hash" in the same afternoon and only one of them is the NT hash. The stored value — 32 hex characters, sitting in the SAM or the directory — is a credential in its own right. The value seen on the wire is a NetNTLMv2 response: a signature made *with* that hash over a random challenge the server invented, so it is different on every login and there is nothing in it to replay.

> [!important] A response is not a hash you can pass
> Feeding a `user::DOMAIN:…` string to `-hashes` fails, and feeding it to `hashcat -m 1000` fails with `Token length exception` — which reads like a formatting mistake rather than the category error it is. Count the characters: 32 and nothing else is an NT hash — an MD5 digest is also 32 hex characters, so the count narrows the field and where the string came from settles it. Anything longer, anything with colons in the middle, has to be cracked before it authenticates.

Which protocol a service will even attempt is not entirely your choice. Kerberos needs a *name*: the client asks the domain controller for a ticket issued to `cifs/server1.domain.local`, and no such name exists for `192.168.1.51`. So an IP address in the command means NTLM, always; a hostname means you may pick.

**What you will see** — this section produces no output; it is the read you do before the first command. **Found** is a string that matches one row exactly. **Empty** is a string that matches none of them, which usually means it is a hash from something that is not Windows at all — take it to [[Hash-Cracking]] and identify it there. **Error** is a 32-character string that fails as an NT hash, and the usual cause is that it is an MD5 from a web application. **Noise** is the `aad3b435b51404eeaad3b435b51404ee` you will see printed beside almost every NT hash: it is the LM hash of an empty string, not a secret, and not the value you pass.

## Authenticating with a password

```bash
smbclient.py 'domain.local/user:Password123!'@192.168.1.51
```

- `domain.local/` → the domain the account lives in, not the target's hostname. Leave it off and the account is offered as a *local* account on the target, which a domain account is not; the answer is `STATUS_LOGON_FAILURE` and you spend the next twenty minutes doubting a password that was correct.
- single quotes around the whole `domain/user:password` string → for the shell, not for impacket. An unquoted `!` triggers history expansion in an interactive bash and an unquoted `$` expands to nothing, so the tool receives a password you never typed.
- an IP address as the target → forces NTLM, which is what you want for this test: no name resolution, no clock, nothing else that can fail.

## Authenticating with an NT hash

```bash
smbclient.py 'domain.local/user'@192.168.1.51 -hashes :<nt hash>
```

- `-hashes <lm>:<nt>` → two halves separated by a colon, LM first. The LM half is absent on anything modern, and leaving it empty with a leading colon is the correct way to say so.
- the leading colon → the flag that is easy to drop, and dropping it puts your NT hash in the LM position and sends an empty NT hash. The result is `STATUS_LOGON_FAILURE`, indistinguishable from a wrong hash, so check the colon before you doubt the hash.
- no password anywhere in the command → correct, and the check that the flag parsed. If the tool prompts you for a password, `-hashes` did not reach it.

## Authenticating with a Kerberos ticket

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
