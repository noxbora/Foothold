---
type: technique
platform: windows
status: working
fluency: unseen
source: thm
updated: 2026-10-02
---

# AD Authenticated Enumeration — the domain seen from a member host

Once you are on a domain-joined machine as a domain account, the directory answers questions simply because you are authenticated; almost nothing here needs a privilege. [[Windows-Run-Sheet]] asks what this box can do for you. This note asks what the domain looks like from inside it, using what is already installed before anything is downloaded.

## Am I in a domain, and which controller authenticated me

**Why now** — you have a shell and you do not yet know whether this host is domain-joined, nor whether the account you are holding is a domain account or a local one. Every other command in this note is a waste of a keystroke until that is settled, and the answer is already sitting in the environment.

```cmd
set | findstr /i "USERDOMAIN USERDNSDOMAIN LOGONSERVER"
```

- the filter is the whole point: `set` prints forty-odd variables and three of them answer the domain question.
- `/i` → match without regard to case. The names print in capitals, `findstr` is case-sensitive by default, and a pattern typed in lower case matches nothing at all, which looks exactly like a host with no domain.
- the quotes around the three names → space-separated patterns inside quotes mean "any of these". Without the quotes `findstr` reads the first word as the pattern and every word after it as a filename, and you get `FINDSTR: Cannot open USERDNSDOMAIN`.
- `USERDOMAIN` holds the computer name rather than a domain name whenever the logged-on account is local, so reading it alone makes a domain-joined machine look standalone. `USERDNSDOMAIN` is absent on exactly that logon and present on a domain one, which is why both are in the pattern.
- `LOGONSERVER` names the controller that authenticated this session, which saves you a discovery sweep, and it arrives with its two leading backslashes already attached.

**What you will see**

- **Found** — three lines: the domain in short form, the same domain in dotted form, and a controller name. That is a domain logon on a joined host, and the rest of this note applies.
- **Empty** — nothing printed means the filter missed rather than the domain being absent, so run `set` once on its own to prove the variables are there. Only `USERDOMAIN` printing, with the computer name as its value, means a local account; the machine itself may still be joined, and `net config workstation` answers that with no privilege at all.
- **Error** — `FINDSTR: Cannot open ...` is the missing quotes. `set` reported as not recognised means you are in PowerShell rather than the command prompt, where the same question is `dir env: | findstr /i "USERDOMAIN"`.
- **Noise** — the short and the dotted form of a domain are often different enough to read as two domains. A name ending `.local` or `.loc` is a private internal name and tells you nothing about what is routable.

**Then** — a domain name plus a controller goes to the account list below, and to [[Domain-Controller-Discovery]] if you still need its address rather than its name. A local-only account means this note is the wrong one for now: back to [[Windows-Run-Sheet]] and [[Windows-Credential-Harvesting]] to find a domain credential on the disk first.

## The account list, with nothing installed

**Why now** — the host is joined and you are a domain account, so the controller will list the domain's users for you. You are looking for names shaped like functions rather than people, because those are the accounts whose passwords are old and whose privileges are real.

```cmd
net user /domain | findstr /i "adm svc sql backup"
```

- `/domain` → ask the controller instead of this machine. Drop it and you get the local accounts, which on a member host are the four built-ins, and their dullness reads as a dull domain.
- the four stems are the discriminator, and knowing which stems is the valuable part rather than knowing the flag: an account that matters is usually named for its job, and these cover administrators, services, databases and backup operators.
- what the filter hides: `net user /domain` prints names three to a line in fixed-width columns, so matching happens per line and every hit drags its two neighbours along with it. A stem you did not list is invisible, so read the list unfiltered once on a small domain to learn its naming convention before you trust the filter on a large one.
- the silent failure: a stem that matches nothing prints nothing, which is indistinguishable from the command never having run. A 200-account domain prints about seventy lines bare; the filter should leave two to six.

```cmd
net user <name from the list> /domain
```

- the detail view for one account: full name, whether it is active, the password dates, the logon dates and the group memberships. `Global Group memberships` is the line to read, and `Password last set` is the line that decides whether the account is worth cracking later.

**What you will see**

- **Found** — a column line carrying a function-shaped name, which you then put through the second command. A name with `svc` or `sql` in it and a password set years ago is the strongest single finding in this note.
- **Empty** — the header line about the request being processed at a controller, and no names under it, means the filter matched nothing rather than the domain being empty; run it without the pipe to prove it. A genuine refusal looks different, and that is the next bullet.
- **Error** — `System error 5 has occurred` is access denied: an answer about your permissions, not about the domain, and unusual here because any authenticated account can normally read this. `The specified domain either does not exist or could not be contacted` is name resolution or a host that is not really joined.
- **Noise** — personal names are the bulk of any domain and nearly all of them are worthless on their own. A username is not a finding until a group is standing next to it.

**Then** — function-shaped names go to the group section below to find out what they are worth, and to [[AD-Username-Enumeration]] if what you actually need is a list to spray. A refusal sends you to the directory section, which asks the same question down a different road.

## Groups, and which ones are worth anything

**Why now** — you have names. A name without a group is a phone-book entry, so this is where the list turns into targets, and it is also where you find out whether this domain has handed privilege to a group nobody is watching.

```cmd
net group /domain | findstr /i "admin oper"
```

- `/domain` is load-bearing in a second way here: `net group` without it answers only on a controller, and on a member host it refuses with `This command can be used only on a Windows Domain Controller`, which reads like a privilege problem and is not one.
- `admin oper` → the two stems that cover the built-in privileged groups. Write-ups filter on `admin` and stop, which silently drops Server Operators, Backup Operators, Print Operators and Account Operators: all four hold enough to end the engagement, and none of them contain the word admin.
- group names print with a leading `*`, which is the quickest way to tell a group list from a user list in output you have pasted somewhere and lost the context of.

```cmd
net group "Domain Admins" /domain
```

- the quotes around a group name containing a space → without them `net` reads the second word as a parameter and prints its syntax help, which looks like you got the command wrong rather than the quoting.
- `net group "Domain Computers" /domain` lists the machine accounts instead, and every name in it ends with `$`. That `$` is how you separate a machine from a person in any Windows list, and machine passwords are 120 random characters rotated automatically, so they are never a cracking target.

**What you will see**

- **Found** — a short list of privileged groups, then the members of the one you expanded. An ordinary personal account inside `Domain Admins` is the highest-value line in this note; a group you do not recognise sitting in there is the second.
- **Empty** — a group that exists and prints no members under `Members` is real and happens: privilege is often granted through nesting instead, and the next section explains why that hides from you.
- **Error** — the controller-only refusal above is the missing `/domain`. `There is no such global user or group` on an expansion is usually the quoting, not a missing group.
- **Noise** — the built-in groups are present in every domain whether they are used or not, so their existence is not a finding. `Domain Users` contains everybody and means nothing.

**Then** — a privileged group with a reachable member goes to [[Active-Directory-Lateral-Movement]]. A service account in a group that matters goes to [[Kerberoasting]]. Anything you cannot explain goes to the directory, below, where you can ask a precise question instead of a shaped one.

## The directory itself, when the admin tools are not installed

**Why now** — `net` hands you names and nothing to filter on. The directory can be queried properly from any PowerShell on a joined host with nothing installed and nothing downloaded, because the search interface is part of Windows itself.

```powershell
$s = [adsisearcher]'(&(objectCategory=person)(objectClass=user))'; $s.PageSize = 1000; ($s.FindAll()).Count
```

- `[adsisearcher]` → the shorthand for the directory search object Windows ships with ([[Security-Terms#^adsi|ADSI]]). It binds to the current domain by itself, so there is no server to name, no credential to supply and no module to import.
- `objectCategory=person` is the load-bearing half of that filter: a machine account's `objectClass` includes `user`, because the computer class is built on top of the user class, so filtering on `objectClass=user` alone counts every machine in the domain alongside the people. `objectCategory` is single-valued and it separates them.
- `$s.PageSize = 1000` → the one that is easy to omit, and the failure is silent. With paging off the search stops at the server's own result limit of 1000 and returns what it has without a word, so a count of exactly 1000 is a page limit rather than a domain size.
- `($s.FindAll()).Count` → counting is a property of the result set, not an option on the search; there is no count flag anywhere in this interface, which is why the parentheses are doing real work.
- swap the filter for `(objectCategory=computer)` to count machines instead, and add `(!(userAccountControl:1.2.840.113556.1.4.803:=2))` to drop every disabled account from either count.

**What you will see**

- **Found** — a number, and a number you can trust as long as it is not 1000. Run it again with a narrower filter and the two counts together tell you the shape of the domain.
- **Empty** — `0` with no error means the filter is wrong, not that the domain is empty: a misspelled attribute name is still a valid filter, and it matches nothing. Prove the binding separately with `([adsisearcher]'(objectClass=*)').FindOne()` before you believe a zero.
- **Error** — `The server is not operational` means no controller was reachable, or the host is not joined, or you are running as a local account with nothing to bind with. A complaint that the search filter is invalid is an unbalanced parenthesis, which this syntax makes very easy.
- **Noise** — the count includes `krbtgt`, `Guest` and every disabled leaver still sitting in the directory, so a user count is always higher than the number of people who work there.

**Then** — a trustworthy count and a filter that works is the base for every other question: swap the filter rather than the tool. If the proper cmdlets happen to be present, the next section is more readable for the same job, and once you want the join between accounts and hosts, that is [[BloodHound]].

## With the admin tools present

**Why now** — you are on a controller, or somebody installed the remote administration tools on this workstation. The module gives you readable filtering and named attributes, which is worth checking for before you drop a script on the host.

```powershell
Get-ADUser -Filter "Name -like '*adm*'" -Properties MemberOf,LastLogonDate,Description | Select-Object Name,LastLogonDate,Description
```

- the module is called `ActiveDirectory` and it ships on a controller, not on a workstation, where it arrives with the remote administration tools ([[Security-Terms#^rsat|RSAT]]). `Import-Module ActiveDirectory` failing with a module-not-found error is that and not a permission problem; `Get-Module -ListAvailable ActiveDirectory` is the one-line check.
- `-Filter` is the module's own small language rather than PowerShell's, because the string is translated into a directory query before it is sent. So `-like` wants `*` wildcards, and the quoting is outer double quotes with inner single quotes around the value; get that backwards and PowerShell expands nothing and the filter silently matches nothing.
- `-Filter *` with nothing narrowing it returns every account in the domain. The count form is `(Get-ADUser -Filter *).Count`, since counting belongs to the pipeline and no cmdlet here carries a count flag. For machines the cmdlet changes rather than the flag: `Get-ADComputer -Filter *`, because a machine is a different object class.
- `-Properties` → the default output carries ten fields and not one of them says what the account is for. `MemberOf`, `LastLogonDate` and `Description` are the three that decide whether a name is worth anything, and `Description` on a service account is where a password occasionally sits in plain text.

```powershell
Get-ADGroupMember -Identity "Domain Admins" | Select-Object name,objectClass
```

- the other half of the same question: the group that matters, expanded. `objectClass` in the output tells you whether a member is a user, a machine or another group, and the third case is the one that matters for the next section.

**What you will see**

- **Found** — a short table of accounts with a last-logon date and a description. An account whose description explains its job, and whose last logon is years ago, is both a target and a sign that nobody is tidying this domain.
- **Empty** — no rows and no error is the filter or the quoting, not the domain. `-Filter *` returning rows proves the module and the binding are fine, which narrows it to your filter string in one step.
- **Error** — a module-not-found error is the missing administration tools. `Unable to contact the server` is name resolution or a controller that is not answering. An invalid-filter error names the filter, which is the quoting almost every time.
- **Noise** — the module returns disabled accounts like any other, and `Enabled` is not in the default output. A list of promising names where every one of them is disabled is a common waste of an hour.

**Then** — the names and groups you now hold go to [[Kerberoasting]] if any of them are service accounts, and to [[AS-REP-Roasting]] if you want the flagged ones. If the tools are absent and you can write a file to the host, the next section is the richer option.

## PowerView, when you can drop a script on the host

**Why now** — the administration tools are absent and you can write to disk. [[Security-Terms#^powerview|PowerView]] gives one consistent set of verbs over the same directory and adds the queries nobody wants to write by hand, such as which accounts carry a service name and which the directory has marked as privileged.

```bash
wget https://raw.githubusercontent.com/PowerShellMafia/PowerSploit/master/Recon/PowerView.ps1
```

- the fetch runs on your own Kali, not on the target; moving the file across is [[File-Transfer]]'s job, and that note owns the serve-and-pull half of this.
- the raw host is deliberate. A `github.com` address gives you an HTML page that looks like a successful download until PowerShell refuses to parse it.

```powershell
Import-Module .\PowerView.ps1
```

- the `.\` is required → PowerShell will not run a script from the current directory without a path, and the error it gives names the file, which reads as the file being missing rather than the path being implied.
- a complaint about the execution policy is not a permission boundary: `powershell -ep bypass -c "..."` loads the same script, because the policy exists to stop accidents rather than attackers.
- the script is part of [[Security-Terms#^powersploit|PowerSploit]], which [[Security-Terms#^av|AV]] has recognised by name for years, and it is plain text that gets scanned the moment it lands on disk. [[Windows-Automated-Enumeration]] carries the same tradeoff for the scanners.

```powershell
Get-DomainUser -AdminCount | Select-Object samaccountname,memberof,pwdlastset
```

- `-AdminCount` → the accounts the directory itself has stamped as privileged at some point in their life. That is a far shorter and far better list than any guess at names, and it survives an account being removed from the group, which is why it sometimes names an account the group list does not.
- `-SPN` in place of it lists the accounts carrying a service name, which is the input to [[Kerberoasting]]. `Get-DomainComputer` and `Get-DomainGroup` take the same filtering.

**What you will see**

- **Found** — one block per account, with the attribute names in lower case as the directory stores them. `pwdlastset` in that block is the same judgement as before: an old date on a privileged account is the finding.
- **Empty** — no output from `-AdminCount` means no account carries that stamp, which is normal in a small domain and does not mean there are no administrators. Fall back to the group expansion, which asks a different question.
- **Error** — a missing-cmdlet error means the import did not take, usually the `.\` or the execution policy. A long red block mentioning reflection is the script being blocked after loading, which is the scanner rather than the syntax.
- **Noise** — PowerView prints every attribute an object has, which is forty lines per account. Piping into `Select-Object` is not cosmetic here; without it the output buries its own findings.

**Then** — service accounts go to [[Kerberoasting]], flagged accounts to [[AS-REP-Roasting]], a local-administrator finding to [[Active-Directory-Lateral-Movement]], and the whole directory at once to [[BloodHound]].

## Reading the output

Everything in this note asks about one object at a time, and that is its ceiling. The question that actually ends an engagement is a join: which of the accounts I can reach has privilege over something that has privilege over what I want. No command here performs that join, which is why the honest end of this note is a hand-off rather than a conclusion, and why [[BloodHound]] exists at all.

Group nesting is the blind spot to know by name. `net group` and `Get-ADGroupMember` list direct members, and a group inside a group prints as a single line naming that group. So an account can hold Domain Admin through two levels of nesting and never appear in the list you just read, which is how a domain that looks clean from the member side turns out not to be.

The password policy is deliberately not in this note even though the same tools report it, because spending an attempt against a lockout threshold you have not read is the expensive mistake and [[Password-Spraying]] owns that whole decision. Read it there before any credential is tried anywhere.

## Rarely — worth one command, not worth a step

- `nltest /dclist:<domain>` lists every controller in the domain, one per line, with no privilege needed.
- `net accounts /domain` prints the password and lockout policy from the member side, which is the cheap version of what [[Password-Spraying]] reads properly.
- `net localgroup administrators` on a member host shows whether a domain group has been dropped into the local administrators group. That is the cheapest local-admin finding there is and it points straight at [[Active-Directory-Lateral-Movement]].
- `gpresult /r` prints the policies that apply to you, which names the organisational units your account sits in and therefore how this domain is actually organised.
- Who else is logged in, what runs as whom, and the registry's stored credentials belong to [[Windows-Run-Sheet]] and [[Windows-Credential-Harvesting]], not here; they are host questions that happen to be asked from a domain member.

## Next

- [[BloodHound]] — the join these commands cannot make, drawn in one pass
- [[Kerberoasting]] — what a service account name is worth once you have it
- [[Active-Directory-Lateral-Movement]] — where a local-administrator finding goes

## Gaps

- Nothing on trusts: `nltest /domain_trusts` and what a trust means for scope are not covered anywhere in the vault.
- The organisational-unit structure is named in `## Rarely` and never read properly, though it is how a domain's departments and its delegation are laid out.
- No coverage of enumerating from a non-joined machine with a credential, which is the Linux-side equivalent of this whole note.
- The directory section counts objects; it does not read the attributes that matter in bulk, so there is no written way to get every description field in one pass.
