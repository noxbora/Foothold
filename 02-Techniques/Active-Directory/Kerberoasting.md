---
type: technique
platform: windows
status: working
fluency: guided
source: thm
updated: 2026-09-08
---

# Kerberoasting

Any account in the domain may ask for a ticket to any service, and that ticket comes back encrypted with the service account's own password. So one ordinary credential — no administrator, no shell on anything — turns into an offline cracking job against every service account in the domain. It is the first thing a working domain credential is worth.

## Which accounts are even roastable

**Why now** — you have one credential that authenticates ([[AD-Authentication]]) and no privilege at all. This asks the domain a question it will answer for anybody: which user accounts have a service name registered against them, and are therefore roastable. You are looking for a name to spend the cracking time on, not for the ticket yet.

```bash
GetUserSPNs.py 'domain.local/user:password' -dc-ip <dc ip>
```

- no `-request` on this first run → you get the table only. Requesting every ticket in the domain before you have read the table is louder, and hands you a pile of hashes most of which are not worth a wordlist.
- `-dc-ip` → the domain controller to query. Omit it and the tool resolves the domain name through your own resolver, which on a lab network is a hang and then a connection error that reads as the domain being unreachable.
- the filter you would otherwise have to write is already inside this tool: it asks the directory only for accounts that have a service name *and* are user accounts. Machine accounts also carry service names, and their passwords are 120 random characters rotated automatically — enumerate service names by hand over the directory protocol and you will collect those too, and spend a night on something that has never once been cracked. Managed service accounts are the same class of waste, for the same reason.

**What you will see**

- **Found** — a table with six columns: the service name, the account, `MemberOf`, `PasswordLastSet`, `LastLogon` and `Delegation`. Read the third and fourth before anything else; they decide whether the crack is worth starting.
- **Empty** — `No entries found!` with the bind having plainly succeeded. This is the rare place where empty means empty: nobody has registered a service name on a user account. It is not a permission problem, because a failed bind errors instead of returning a table. A small domain genuinely produces this.
- **Error** — `STATUS_LOGON_FAILURE` is the credential, not the attack. `KRB_AP_ERR_SKEW` is your clock. A timeout is usually `-dc-ip` pointing at the wrong host, or at the file server rather than the domain controller.
- **Noise** — an account whose `MemberOf` is blank belongs to nothing beyond its primary group, so cracking its password buys you exactly the access you already have. That attribute never lists the primary group, which is `Domain Users` on an ordinary account, so blank means *no extra groups*, not *no groups*. `krbtgt` sometimes appears in the table and is never the answer.

**Then** — a name with a real group in `MemberOf` goes to the next section. An empty `MemberOf` on every row means this domain has nothing here for you: go back to [[AD-Authentication]] and spend the credential on finding a host where it is administrator ([[Active-Directory-Lateral-Movement]]). An empty table means the same thing, sooner.

## Requesting the ticket and cracking it

**Why now** — the table gave you one account worth the electricity: it belongs to a group that matters, and its `PasswordLastSet` is old. An old date is the strongest signal in the output — a service password set years ago predates whatever policy the domain enforces now, and nobody has touched it since, because rotating it means restarting the service that depends on it.

```bash
GetUserSPNs.py 'domain.local/user:password' -dc-ip <dc ip> -request-user <account from the table> -outputfile tgs.txt
```

- `-request-user <name>` → asks for that one ticket. `-request` on its own asks for all of them, which is a louder event on the domain controller and gives you hashes you have already decided not to crack.
- `-outputfile` → easy to skip, because the hash also prints to the terminal. It is long, it wraps, and copying it out of a wrapped terminal introduces a line break in the middle; hashcat then reports `Token length exception`, which reads like the wrong mode and sends you to check the mode number instead of the file.

```bash
hashcat -m 13100 -a 0 tgs.txt /usr/share/wordlists/rockyou.txt
```

- the mode is decided by the number after `$krb5tgs$` in the hash, not by habit. `$krb5tgs$23$` is RC4 and mode `13100`; `$krb5tgs$17$` is AES-128 and mode `19600`; `$krb5tgs$18$` is AES-256 and mode `19700`. Almost every write-up shows `13100` because almost every lab is RC4, and a hardened domain issues you an `18` that mode `13100` refuses.
- `-a 0` → straight wordlist. Wordlist strategy, rules and what to do when rockyou is exhausted all live in [[Hash-Cracking]]; this note only decides the mode.

**What you will see**

- **Found** — the hash reprinted with the password appended after the final colon, and `Status.........: Cracked`. That password is the service account's, and it is a plaintext, so it goes back into [[AD-Authentication]] as a password rather than as a hash.
- **Empty** — `Status.........: Exhausted` and nothing recovered. That is a statement about the wordlist, not about the password: a service password absent from rockyou may still be four dictionary words. It is also the expected outcome for a managed service account, which is what a random-looking name with a recent `PasswordLastSet` usually is.
- **Error** — `Token length exception` is the hash: either the mode does not match the number after `$krb5tgs$`, or a line break got into the file. `No hashes loaded` is the same problem one step earlier.
- **Noise** — a cracked password whose account is in no interesting group is a real crack and a worthless one. This is why the table is read before the crack is started, not after.

**Then** — a cracked service account goes back to [[AD-Authentication]] to find out what it actually opens, and to [[Active-Directory-Lateral-Movement]] if it turns out to be a local administrator somewhere. An exhausted run goes to [[Hash-Cracking]] for a bigger or a targeted list before it is abandoned, since the hash keeps indefinitely and can be cracked on your own time.

## Reading the output

Two columns decide the whole attack and both are printed by the first command, before any ticket is requested. `MemberOf` is the payout: it is what the password buys, and blank means it buys nothing you do not already have. `PasswordLastSet` is the probability: a date several years old means a password chosen under an older policy by a person who has since left, while a recent date on an unmemorable account name usually means the domain is managing that password automatically and it will not crack.

The reason this works at all is worth keeping straight, because it explains the one thing that surprises people: nothing is exploited, and nothing is bypassed. The domain controller is doing exactly what it is designed to do — issuing a ticket for a service to a user who asked. The flaw is that the ticket is encrypted with a human-chosen password and the domain will hand it to anyone, so the attack lives entirely on your own machine after the request. There is no lockout and no retry limit, because the guessing happens on your disk. The ticket request itself is an ordinary logged event, so the attack is quiet, not invisible.

## Rarely — worth one command, not worth a step

- `-usersfile` takes a list of account names instead of querying, for the case where you have names from somewhere else and no credential that can read the directory.
- Writing a service name onto an account you already control makes that account roastable on purpose. It needs write access to the account object, which means it is a way of turning one directory permission into a password, not a way in.
- The same tool run with `-no-preauth` targets accounts with pre-authentication switched off, which is AS-REP roasting rather than Kerberoasting and needs no credential at all.

## Next

- [[Hash-Cracking]] — wordlists, rules, and what an exhausted run is actually evidence of
- [[AD-Authentication]] — where a cracked service password goes next, and what it can and cannot be passed to
- [[Active-Directory-Lateral-Movement]] — if the service account turns out to be a local administrator somewhere

## Gaps

- No coverage of how noisy the request is, or what it looks like from the defender's side, which decides whether `-request` for the whole domain is ever acceptable.
- AS-REP roasting is named in the last section and not written; it is the closer relative of this attack than anything else in the folder, because it needs no credential.
- Nothing on delegation, which the `Delegation` column in the output announces and this note ignores entirely.
- No worked example of what a service account's group membership typically opens, so the `MemberOf` judgement is currently a rule with no cases behind it.
