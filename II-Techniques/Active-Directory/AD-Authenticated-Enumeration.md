# AD Authenticated Enumeration — the domain seen from a member host

Once you are on a domain-joined machine as a domain account, the directory answers questions simply because you are authenticated; almost nothing here needs a privilege. [[▸ Windows-Run-Sheet]] asks what this box can do for you. This note asks what the domain looks like from inside it, using what is already installed before anything is downloaded.

## Am I in a domain, and which controller authenticated me

```cmd
set | findstr /i "USERDOMAIN USERDNSDOMAIN LOGONSERVER"
```

- the filter is the whole point: `set` prints forty-odd variables and three of them answer the domain question.
- `/i` → match without regard to case. The names print in capitals, `findstr` is case-sensitive by default, and a pattern typed in lower case matches nothing at all, which looks exactly like a host with no domain.
- the quotes around the three names → space-separated patterns inside quotes mean "any of these". Without the quotes `findstr` reads the first word as the pattern and every word after it as a filename, and you get `FINDSTR: Cannot open USERDNSDOMAIN`.
- `USERDOMAIN` holds the computer name rather than a domain name whenever the logged-on account is local, so reading it alone makes a domain-joined machine look standalone. `USERDNSDOMAIN` is absent on exactly that logon and present on a domain one, which is why both are in the pattern.
- `LOGONSERVER` names the controller that authenticated this session, which saves you a discovery sweep, and it arrives with its two leading backslashes already attached.

## The account list, with nothing installed

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

## Groups, and which ones are worth anything

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

## The directory itself, when the admin tools are not installed

```powershell
$s = [adsisearcher]'(&(objectCategory=person)(objectClass=user))'; $s.PageSize = 1000; ($s.FindAll()).Count
```

- `[adsisearcher]` → the shorthand for the directory search object Windows ships with ([[Security-Terms#^adsi|ADSI]]). It binds to the current domain by itself, so there is no server to name, no credential to supply and no module to import.
- `objectCategory=person` is the load-bearing half of that filter: a machine account's `objectClass` includes `user`, because the computer class is built on top of the user class, so filtering on `objectClass=user` alone counts every machine in the domain alongside the people. `objectCategory` is single-valued and it separates them.
- `$s.PageSize = 1000` → the one that is easy to omit, and the failure is silent. With paging off the search stops at the server's own result limit of 1000 and returns what it has without a word, so a count of exactly 1000 is a page limit rather than a domain size.
- `($s.FindAll()).Count` → counting is a property of the result set, not an option on the search; there is no count flag anywhere in this interface, which is why the parentheses are doing real work.
- swap the filter for `(objectCategory=computer)` to count machines instead, and add `(!(userAccountControl:1.2.840.113556.1.4.803:=2))` to drop every disabled account from either count.

## With the admin tools present

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

## PowerView, when you can drop a script on the host

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
