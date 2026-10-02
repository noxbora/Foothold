---
type: technique
platform: windows
status: working
fluency: unseen
source: thm
updated: 2026-10-02
---

# AS-REP Roasting

A domain controller normally refuses to issue anything until the client has proved it knows the account's password, and that proof is a timestamp encrypted with the password. An account flagged to skip the proof gets its reply sent to whoever asks for it, and part of that reply is encrypted with the account's password anyway, so a username on its own becomes an offline cracking job with no credential behind it.

## Which accounts skip the proof, when you hold no credential

**Why now** — you have a domain name, a reachable controller and a list of candidate usernames from [[AD-Username-Enumeration]], and nothing that authenticates yet. This is the one Kerberos attack that runs before you own a single credential, which is why it belongs here rather than after [[Password-Spraying]] has found you one.

```bash
GetNPUsers.py 'domain.local/' -dc-ip <dc ip> -usersfile users.txt -format hashcat -outputfile hashes.txt -no-pass
```

- the trailing `/` after the domain name → it is what tells [[Security-Terms#^impacket|Impacket]] the string is a domain with no username in it. Drop the slash and the whole string is read as a host to connect to instead, and the tool stops complaining that the domain is missing rather than that your syntax is wrong.
- `-no-pass` → send no password at all, which is the entire point of the attack. Omit it and the tool prompts for one and waits, which inside a script reads as a hang.
- `-usersfile users.txt` → one username per line. Without a credential there is nothing to query, so this file *is* the attack surface: the run can only find accounts you have already named.
- `-format hashcat` → state it rather than trust the default, which has moved between Impacket versions. The two forms differ by the `$23$` field naming the cipher, and hashcat cannot load the john form; it says no hashes were loaded, which reads like a wrong mode number.
- `-outputfile hashes.txt` → easy to skip, because the hash prints to the terminal as well. It is several hundred characters long, it wraps, and copying it back out of a wrapped terminal puts a line break inside it; hashcat then reports `Token length exception` and sends you to check the mode instead of the file.
- the eliminating is already inside the tool: it tries each name in turn and prints a hash only for the accounts whose reply came back unprotected. Expect one or two from a list of fifty, and often none.

**What you will see**

- **Found** — a line starting `$krb5asrep$23$` for each flagged account, carrying the account name, the realm and two long blocks of hex.
- **Empty** — every line reads `doesn't have UF_DONT_REQUIRE_PREAUTH set` and the output file is zero bytes. Empty is honest here but narrow: it says nothing about accounts you never named, and since no bind happens without a credential there is no permission refusal hiding behind it.
- **Error** — `KDC_ERR_CLIENT_REVOKED` means that account is disabled or locked out, which is the normal answer for `Guest` and `krbtgt` and not a fault in your request. `KDC_ERR_C_PRINCIPAL_UNKNOWN` is a name that does not exist. `Name or service not known` carrying the domain name is `-dc-ip` missing or aimed at the wrong host.
- **Noise** — those two revoked built-ins turn up on almost every run and are never the answer. A flagged account is not a win either: the flag says the reply is free, not that the password is weak.

**Then** — a `$krb5asrep$23$` line goes straight to the cracking section below. All-empty with a list you trust sends you back to [[AD-Username-Enumeration]] for a longer one, or to [[Password-Spraying]] for a credential so you can ask the directory instead of guessing, which is the next section.

## Asking the directory instead of guessing names

**Why now** — you now hold one credential that authenticates ([[AD-Authentication]]), however unprivileged. Any authenticated account may read the directory, so the guessing stops: you can ask which accounts carry the flag and get the complete answer.

```bash
GetNPUsers.py 'domain.local/user:password' -dc-ip <dc ip>
```

- with a credential and no `-usersfile`, the tool queries the directory for exactly the accounts whose `userAccountControl` carries the "do not require pre-authentication" bit, so the eliminating is a directory filter rather than a loop over guesses, and the result is every flagged account rather than the ones you thought of.
- no `-request` on this first run → you get the table and no hashes. It carries `MemberOf` and `PasswordLastSet`, which is what decides whether the cracking time is worth spending, exactly as in [[Kerberoasting]].
- holding only a shell and no Impacket, the same question in raw directory syntax is `(&(objectCategory=person)(objectClass=user)(userAccountControl:1.2.840.113556.1.4.803:=4194304))`, where `4194304` is that one bit and the long dotted number is the matching rule that makes the comparison bitwise. [[AD-Authenticated-Enumeration]] carries the command that runs it with nothing installed.

```bash
GetNPUsers.py 'domain.local/user:password' -dc-ip <dc ip> -request -format hashcat -outputfile hashes.txt
```

- `-request` → fetch the replies for the accounts the table listed. On this route it is safe to ask for all of them, because the directory already told you the list is short.

**What you will see**

- **Found** — a table of flagged accounts on the first run, then one `$krb5asrep$23$` line per account on the second. The table is usually one or two rows long; the flag is set by hand, account by account, so a domain with dozens of them has a policy problem rather than an accident.
- **Empty** — `No entries found!` after a bind that plainly worked. This is a real empty: nobody in the domain has the flag, and there is no narrower list to try. A failed bind errors instead of printing an empty table, which is what separates this from the no-credential route.
- **Error** — `STATUS_LOGON_FAILURE` is the credential, not the attack. `KRB_AP_ERR_SKEW` is your clock more than five minutes off the controller's. A timeout is usually `-dc-ip` pointing at a file server rather than at a controller.
- **Noise** — a flagged account whose `MemberOf` is blank belongs to nothing beyond its primary group, so its password buys you the access you already have. That attribute never lists the primary group, so blank means no *extra* groups, not no groups.

**Then** — a row with a real group in `MemberOf` and an old `PasswordLastSet` goes to the cracking section. `No entries found!` closes this attack for this domain: spend the credential on [[Kerberoasting]] instead, and on [[AD-Authenticated-Enumeration]] to find out what else the account can see.

## Cracking what came back

**Why now** — you hold one or more AS-REP lines and a reason to want that particular account. From here nothing touches the domain: the guessing happens on your own disk, so there is no lockout and no retry limit.

```bash
hashcat -m 18200 -a 0 hashes.txt /usr/share/wordlists/rockyou.txt
```

- `-m 18200` → the mode for an AS-REP encrypted with [[Security-Terms#^rc4|RC4]], which is the `23` in `$krb5asrep$23$`. The number inside the hash picks the mode; habit does not.
- for this hash hashcat covers etype 23 and nothing else, so there is no mode for an AS-REP encrypted with [[Security-Terms#^aes|AES]]. Impacket asks the controller for RC4 and a default domain still grants it, which is why `23` is what you normally get. A domain with RC4 disabled outright hands you an `18`, hashcat will not load it, and that one goes to john's jumbo build, whose `krb5asrep` format does cover the AES types.
- `-a 0` → straight wordlist. [[Hash-Cracking]] owns rules, bigger lists and what an exhausted run is evidence of; this note only decides the mode.

**What you will see**

- **Found** — the hash reprinted with the password after its final colon, and `Status.........: Cracked`. That is a plaintext password, so it goes back into [[AD-Authentication]] as a password rather than as a hash.
- **Empty** — `Status.........: Exhausted` and nothing recovered. That is a statement about the wordlist, not about the password, and it is the expected outcome against an account whose password was machine-generated. The hash keeps indefinitely, so this is a pause rather than a failure.
- **Error** — `Token length exception` is the hash file: either a line break got into it, or the hash is an `18` and the mode is `18200`. `No hashes loaded` is the same problem one step earlier, and is also what a john-formatted file produces.
- **Noise** — a cracked password for an account in no interesting group is a real crack and a worthless one. That is why `MemberOf` is read before the run is started rather than after.

**Then** — a plaintext goes to [[AD-Authentication]] to find out what it opens, and to [[Active-Directory-Lateral-Movement]] if the account turns out to be a local administrator somewhere. Exhausted goes to [[Hash-Cracking]] for a targeted list before it is abandoned.

## Reading the output

Why the flag exists at all is what tells you how to read a hit. Nobody turns pre-authentication off for convenience; it is switched on for an old application or an appliance that cannot manage the modern exchange, and it is set by hand on one account at a time. So a flagged account is usually an old account, and an old account's password was usually chosen under an older policy by somebody who has since left. That is the same probability argument `PasswordLastSet` carries in [[Kerberoasting]], arriving from a different direction.

The ceiling is the password, and it is a hard one. A flagged service account with a long machine-generated password produces a hash that will never crack, and that run looks identical to a run against a weak one right up until the wordlist ends. The two columns in the table are therefore not optional reading: `MemberOf` says what the password would buy, and `PasswordLastSet` says how likely you are to get it.

The attack is quiet rather than invisible. Nothing is exploited and nothing is bypassed: the controller is doing exactly what its configuration tells it to do, and it logs the ticket request like any other, with a field recording that no pre-authentication was used. That field is precisely what a defender hunts for, so a domain that is watching will see a sweep of these requests as clearly as you see the flag.

## Rarely — worth one command, not worth a step

- `-request-user <name>` asks for one account's reply instead of all of them, for a long table where only one row has a group worth having.
- On a domain-joined Windows host, [[Security-Terms#^rubeus|Rubeus]] does the discovery and the request together with `asreproast`, needing neither a name list nor Impacket. It is the better choice when what you hold is a shell rather than a credential on your own machine.
- Setting the flag on an account you can already modify makes that account roastable on purpose. It needs write access to the account object, so it converts a directory permission into a password, the same way writing an [[Security-Terms#^spn|SPN]] does for [[Kerberoasting]]. It is a way to escalate, never a way in.

## Next

- [[Hash-Cracking]] — the mode is chosen here; everything after it lives there
- [[AD-Authentication]] — where a cracked password goes, and what it can be passed to
- [[AD-Authenticated-Enumeration]] — the directory query behind the second section, run with nothing installed

## Gaps

- No worked case of a domain with RC4 disabled: the `18` path is written from the tools' behaviour, not from a box.
- The john invocation for an AES AS-REP is pointed at and not written out.
- Nothing on how many flagged accounts a real domain carries, so "one or two in fifty" is a rule with no cases behind it.
- The write-the-flag variant in `## Rarely` has no command and does not say which permission is enough.
