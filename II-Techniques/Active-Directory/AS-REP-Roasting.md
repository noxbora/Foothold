# AS-REP Roasting

A domain controller normally refuses to issue anything until the client has proved it knows the account's password, and that proof is a timestamp encrypted with the password. An account flagged to skip the proof gets its reply sent to whoever asks for it, and part of that reply is encrypted with the account's password anyway, so a username on its own becomes an offline cracking job with no credential behind it.

## Which accounts skip the proof, when you hold no credential

```bash
GetNPUsers.py 'domain.local/' -dc-ip <dc ip> -usersfile users.txt -format hashcat -outputfile hashes.txt -no-pass
```

- the trailing `/` after the domain name → it is what tells [[Security-Terms#^impacket|Impacket]] the string is a domain with no username in it. Drop the slash and the whole string is read as a host to connect to instead, and the tool stops complaining that the domain is missing rather than that your syntax is wrong.
- `-no-pass` → send no password at all, which is the entire point of the attack. On this exact line it changes nothing: the target names no user, and Impacket only asks for a password when a username is present. It becomes load-bearing the moment a name goes into the target (`'domain.local/<name>'`, the one-account form under *Rarely*) — leave it off there and a `Password:` prompt appears and waits, which inside a script reads as a hang. Keep it in so the line survives that edit.
- `-usersfile users.txt` → one username per line. Without a credential there is nothing to query, so this file *is* the attack surface: the run can only find accounts you have already named.
- `-format hashcat` → already the default in current Impacket; it is written out so the line says what lands in the file. The hashcat form carries `$23$`, the cipher number that picks the mode in *Cracking what came back*. hashcat reads the `john` form as well, so this flag is not what breaks a crack — a hash broken across two lines is, and the next flag is the guard against it.
- `-outputfile hashes.txt` → easy to skip, because the hash prints to the terminal as well. It is several hundred characters long, it wraps, and copying it back out of a wrapped terminal puts a line break inside it; hashcat then reports `Token length exception` and sends you to check the mode instead of the file.
- the eliminating is already inside the tool: it tries each name in turn and prints a hash only for the accounts whose reply came back unprotected. Expect one or two from a list of fifty, and often none.

## Asking the directory instead of guessing names

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

## Cracking what came back

```bash
hashcat -m 18200 -a 0 hashes.txt /usr/share/wordlists/rockyou.txt
```

- `-m 18200` → the mode for an AS-REP encrypted with [[Security-Terms#^rc4|RC4]], which is the `23` in `$krb5asrep$23$`. The number inside the hash picks the mode; habit does not.
- for this hash hashcat covers etype 23 and nothing else, so there is no mode for an AS-REP encrypted with [[Security-Terms#^aes|AES]]. Impacket asks the controller for RC4 and a default domain still grants it, which is why `23` is what you normally get. A domain with RC4 disabled outright hands you an `18`, hashcat will not load it, and that one goes to john's jumbo build, whose `krb5asrep` format does cover the AES types.
- `-a 0` → straight wordlist. [[Hash-Cracking]] owns rules, bigger lists and what an exhausted run is evidence of; this note only decides the mode.
