# Kerberoasting

Any account in the domain may ask for a ticket to any service, and that ticket comes back encrypted with the service account's own password. So one ordinary credential — no administrator, no shell on anything — turns into an offline cracking job against every service account in the domain. It is the first thing a working domain credential is worth.

## Which accounts are even roastable

```bash
GetUserSPNs.py 'domain.local/user:password' -dc-ip <dc ip>
```

- no `-request` on this first run → you get the table only. Requesting every ticket in the domain before you have read the table is louder, and hands you a pile of hashes most of which are not worth a wordlist.
- `-dc-ip` → the domain controller to query. Omit it and the tool resolves the domain name through your own resolver, which on a lab network is a hang and then a connection error that reads as the domain being unreachable.
- the filter you would otherwise have to write is already inside this tool: it asks the directory only for accounts that have a service name *and* are user accounts. Machine accounts also carry service names, and their passwords are 120 random characters rotated automatically — enumerate service names by hand over the directory protocol and you will collect those too, and spend a night on something that has never once been cracked. Managed service accounts are the same class of waste, for the same reason.

## Requesting the ticket and cracking it

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
