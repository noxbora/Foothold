# Active Directory — Username Enumeration

You have a domain name, a domain controller address ([[Domain-Controller-Discovery]] is where both came from), and no account. Every attack in this folder needs a name before it needs a password, and guessing names against a login prompt locks accounts out. This note produces a list of names the domain has confirmed are real, without a single failed login attempt.

## Asking the domain for its own user list

```bash
rpcclient -U "" -N <dc ip> -c enumdomusers | grep -v '\$' | awk -F'[][]' '{print $2}' > users.txt
```

- `-U ""` → an empty user name, which is what makes this a `null session`: a session the server accepts with nobody on the other end of it. The account-management interface is reached over the file-sharing port, so this command needs 445 and no credential.
- `-N` → do not prompt for a password. Leaving it off is not fatal, since the tool asks and an empty answer opens the same session, but it turns a one-line command into an interactive one and stalls anything you put it inside.
- `-c enumdomusers` → run one request and exit rather than dropping into the tool's own shell. That shell is worth knowing about for the follow-up questions — `querydominfo` for the domain's real name and its account total, `enumdomgroups` for the groups, `querygroupmem` for who is in one — but the list is the only thing this step needs.
- `grep -v '\$'` → the filter that belongs in the command, not in a paragraph underneath it. A name ending in `$` is a computer account, and a computer's password is 120 random characters that the machine rotates by itself. It will never answer a spray, and every one you leave in the file spends an attempt against a lockout counter for nothing.
- `awk -F'[][]' '{print $2}'` → the tool prints `user:[jane.smith] rid:[0x650]`, and this takes what sits between the first pair of brackets. Split on spaces instead and you keep `user:[jane.smith]` label and brackets and all, which every later tool reads as a user name and fails on — the whole file failing identically looks exactly like a wrong password.

## Walking the numbers when the list is refused

Every account in a domain has a [[Security-Terms#^sid|SID]], and the tail of that SID is a number, the [[Security-Terms#^rid|RID]]. Asking *who is number 1103* is a translation request, not a list request, so nothing in the refusal above applies to it. Ask it enough times in a row and you have rebuilt the list the domain would not give you.

```bash
nxc smb <dc ip> -u '' -p '' --rid-brute 4000 | grep SidTypeUser
```

- `-u '' -p ''` → the empty strings **are** the nameless session. Leaving both flags off entirely is a different run: the tool then only reads the host banner and never tries to authenticate, which looks like a much quieter answer to a question you never asked.
- `--rid-brute 4000` → the top of the range to walk. The built-in numbers stop below 1000 and accounts created by people start at exactly 1000, so the useful part of the range is everything above it; 4000 covers an organisation of a few thousand objects and costs seconds on a small one.
- `| grep SidTypeUser` → the discriminator, in the command where it belongs. The walk also returns groups, aliases and domains, and on a real domain those outnumber the users. Note what this filter cannot separate: a computer account is a `SidTypeUser` too, so the trailing-`$` filter from the previous section still has to be applied to whatever you keep.

```bash
for i in $(seq 500 2000); do rpcclient -U "" -N <dc ip> -c "queryuser $i" 2>/dev/null | grep -i "User Name"; done
```

- this is the same idea with nothing but the one tool, for a machine where you have no toolkit installed. It asks for one number per iteration, which means one fresh connection per number: 1500 numbers is minutes rather than seconds, and it is 1500 separate sessions in the controller's log instead of one.
- `2>/dev/null` → the easy flag to regret. It hides the failures for every number that is not an account, which is most of them and is the reason the loop is readable at all. It also hides the moment the server stops answering you, so a session that dies at number 700 produces exactly the same silence as 1300 numbers that were genuinely empty. Run the loop once without the redirection and watch the first few, then add it back.
- `seq 500 2000` → start at 500 rather than 1000 and you pick up the built-in accounts as a control. If not even number 500 answers, the walk is not working, and you have learned that in four seconds instead of four minutes.

## Turning people into candidate usernames

Where the names come from in a real engagement: staff profiles on a professional network, commit authorship on public code hosting, breach dumps that carry the mail domain, the "meet the team" page, and recruitment posts that name internal tooling. None of that is the technique — the technique is what you do with a list of humans.

| convention | Jane Smith becomes |
| --- | --- |
| `first.last` | `jane.smith` |
| `firstlast` | `janesmith` |
| `flast` | `jsmith` |
| `first.l` | `jane.s` |
| `first` | `jane` |
| `last.first` | `smith.jane` |

One confirmed mail address settles the entire column, because the local part of a corporate address is almost always the logon name. So a single address found in a commit or a job advert is worth more here than fifty more human names — it tells you which of six lists to build, and the other five never get sent.

> [!important] Two names exist in every domain, and they are your control group
> `krbtgt` and `administrator` are created when the domain is created and cannot be renamed away without leaving the account behind. Put both in the wordlist. If your whole list comes back invalid *and so do those two*, the problem is the realm or the domain controller address, not the convention — and you have just saved yourself from rebuilding a wordlist that was fine.

## Confirming which names are real accounts

```bash
kerbrute userenum -d domain.local --dc <dc ip> usernames.txt -o kerbrute.out
```

- `-d domain.local` → the Kerberos realm, meaning the domain's own name, not the hostname of the machine you are asking. Put the controller's hostname here and every single name returns unknown, which reads exactly like a wordlist in the wrong format and sends you off to rebuild it.
- `--dc <dc ip>` → the one that is easy to omit. Without it the tool looks up the KDC through your own resolver by asking for the domain's service records, and your own resolver has never heard of an internal domain: the run hangs and then reports it could not create a Kerberos client, which reads as a broken installation rather than a missing flag.
- `-o kerbrute.out` → writes the run to a file. What lands in that file is the full log line, timestamp and banner and all, not a bare list of usernames — which is why the next section exists rather than piping this straight into a spray.

> [!important] Lockout-free is not logging-free, and it stops being lockout-free the moment you add a password
> A request with no password attached cannot fail a password check, so the controller's bad-password counter never moves — that is what makes this safe to run across a whole list. It is not quiet: each name writes an authentication-service event on the controller, so a thousand names is a thousand events from one source in a few seconds, which is the single most obvious pattern a defender looks for. And the same tool has a password-spraying mode: that one *does* send a password, those failures *do* count, and it belongs to [[Password-Spraying]]'s rules, not to this section's.

## Cleaning the output into a spray list

```bash
grep "VALID USERNAME" kerbrute.out | awk '{print $NF}' | sed 's/@domain.local//' > users.txt
```

- `$NF` → the last field of the line, whatever the line's length. The username sits at the end behind a date, a time, an arrow and a label, so any fixed field number breaks the first time the log format shifts by a column and hands you a timestamp as a username.
- `sed 's/@domain.local//'` → the one that is easy to omit, and the reason this section is not a footnote. The tools in the next note authenticate with the bare logon name; leave the realm suffix attached and every account in the file fails with a logon failure. The whole list failing identically reads as *the password is wrong*, so you burn an entire spray round, wait out a lockout window, and try a second password against a list that was never going to answer.
- `grep "VALID USERNAME"` first → the file also holds the banner, the version line and the timing line, all of which have a last field that `awk` will happily hand you.

## What the domain's own directory of services already tells you

```bash
nslookup -type=SRV _ldap._tcp.dc._msdcs.domain.local <dc ip>
```

- `-type=SRV` → the record type that maps *a service* to *a host and a port*, rather than a name to an address. A service record answers "where do I go to speak this protocol", which is a question the ordinary record types cannot express.
- `_msdcs` in the middle → a zone the domain keeps for its own internal machinery, and `dc` inside it means domain controllers specifically. Drop that piece and ask for `_ldap._tcp.domain.local` instead and you get every machine offering the directory protocol, controllers and read-only replicas and anything else, with no way to tell them apart.
- the address at the end → the one that is easy to omit. It tells the lookup which server to ask. Leave it off and the question goes to whatever resolver your machine normally uses, which has no knowledge of an internal domain and answers that the name does not exist — which reads as *this domain publishes no controllers*.

```bash
nslookup -type=SRV _kerberos._tcp.domain.local <dc ip>
```

- the same question aimed at the ticket service. The two answers usually name the same hosts, and when they do not, that is the finding: something is offering one service and not the other.
- `-type=MX` on the domain name itself names the mail servers, which is the other half worth having — mail hosts are where a captured credential most often turns out to be useful.
