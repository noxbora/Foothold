---
type: technique
platform: windows
status: working
fluency: guided
source: thm
updated: 2026-09-17
---

# Active Directory — Username Enumeration

You have a domain name, a domain controller address, and no account. Every attack in this folder needs a name before it needs a password, and guessing names against a login prompt locks accounts out. This note produces a list of names the domain has confirmed are real, without a single failed login attempt.

## Turning people into candidate usernames

**Why now** — you have human names from somewhere public and nothing the domain recognises. A domain does not store people, it stores logon names, and every organisation picks one convention and applies it to everyone. Find the convention once and the whole staff list becomes a wordlist.

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

**Why now** — you hold candidates and no way to test them that does not risk locking accounts. Kerberos answers the existence question separately from the password question, which is the whole reason this step exists before any password is typed.

```bash
kerbrute userenum -d domain.local --dc <dc ip> usernames.txt -o kerbrute.out
```

- `-d domain.local` → the Kerberos realm, meaning the domain's own name, not the hostname of the machine you are asking. Put the controller's hostname here and every single name returns unknown, which reads exactly like a wordlist in the wrong format and sends you off to rebuild it.
- `--dc <dc ip>` → the one that is easy to omit. Without it the tool looks up the KDC through your own resolver by asking for the domain's service records, and your own resolver has never heard of an internal domain: the run hangs and then reports it could not create a Kerberos client, which reads as a broken installation rather than a missing flag.
- `-o kerbrute.out` → writes the run to a file. What lands in that file is the full log line, timestamp and banner and all, not a bare list of usernames — which is why the next section exists rather than piping this straight into a spray.

**What you will see**

- **Found** — `[+] VALID USERNAME:  jane.smith@domain.local`, one line per real account, and a closing line counting how many of how many were valid.
- **Empty** — the run completes, the count says `0 valid`. Read it as *this convention is wrong*, not *this domain has no users*, and check your two control names before touching the wordlist.
- **Error** — `KRB_AP_ERR_SKEW` is your clock more than thirty seconds away from the domain's; fix the clock, nothing else here will work either. A connection timeout is the address in `--dc` pointing at a member server rather than a controller. `KDC_ERR_C_PRINCIPAL_UNKNOWN` is not an error at all — it is the domain saying *no such account*, and it is what every invalid name in your list quietly produced.
- **Noise** — a valid username is not a usable account. Disabled, expired and locked accounts all answer this question identically, because the controller decides whether the name exists before it decides whether the account may be used.

**Then** — the valid list goes to [[Password-Spraying]], which is the next thing you can do without a credential. It also becomes the target list for anything that later needs names rather than a credential, and the account names in it are worth re-reading once you do hold one, because [[Kerberoasting]] is about which of them carry a service name.

> [!important] Lockout-free is not logging-free, and it stops being lockout-free the moment you add a password
> A request with no password attached cannot fail a password check, so the controller's bad-password counter never moves — that is what makes this safe to run across a whole list. It is not quiet: each name writes an authentication-service event on the controller, so a thousand names is a thousand events from one source in a few seconds, which is the single most obvious pattern a defender looks for. And the same tool has a password-spraying mode: that one *does* send a password, those failures *do* count, and it belongs to [[Password-Spraying]]'s rules, not to this section's.

## Cleaning the output into a spray list

**Why now** — the tool's output file is a log, and the tools that come next want bare logon names, one per line. Every minute spent here is worth it, because the alternative failure is silent and expensive.

```bash
grep "VALID USERNAME" kerbrute.out | awk '{print $NF}' | sed 's/@domain.local//' > users.txt
```

- `$NF` → the last field of the line, whatever the line's length. The username sits at the end behind a date, a time, an arrow and a label, so any fixed field number breaks the first time the log format shifts by a column and hands you a timestamp as a username.
- `sed 's/@domain.local//'` → the one that is easy to omit, and the reason this section is not a footnote. The tools in the next note authenticate with the bare logon name; leave the realm suffix attached and every account in the file fails with a logon failure. The whole list failing identically reads as *the password is wrong*, so you burn an entire spray round, wait out a lockout window, and try a second password against a list that was never going to answer.
- `grep "VALID USERNAME"` first → the file also holds the banner, the version line and the timing line, all of which have a last field that `awk` will happily hand you.

**What you will see**

- **Found** — one bare name per line, no `@`, no spaces. `wc -l users.txt` matches the valid count the tool printed.
- **Empty** — an empty file means the grep matched nothing, so check the file's actual wording before blaming the pipeline; a tool version that prints a different label produces exactly this.
- **Error** — no error to speak of. This pipeline fails silently, which is precisely the risk: `head -3 users.txt` before you spend the file is the whole defence.
- **Noise** — a stray `@` on one line, from a name your `sed` pattern did not match because the realm was spelled differently in that line's output. One bad line is one wasted attempt against one account, not a wasted round.

**Then** — the clean file is the input to [[Password-Spraying]]. Nothing else in the vault consumes it yet.

## What the domain's own directory of services already tells you

**Why now** — you are about to attack a network whose shape you have not drawn. Active Directory publishes its own infrastructure in DNS as service records, because that is how ordinary Windows clients find a controller to log in against. Anything a workstation can look up, you can look up.

```bash
nslookup -type=SRV _ldap._tcp.dc._msdcs.domain.local <dc ip>
```

- `-type=SRV` → the record type that maps *a service* to *a host and a port*, rather than a name to an address. A service record answers "where do I go to speak this protocol", which is a question the ordinary record types cannot express.
- `_msdcs` in the middle → a zone the domain keeps for its own internal machinery, and `dc` inside it means domain controllers specifically. Drop that piece and ask for `_ldap._tcp.domain.local` instead and you get every machine offering the directory protocol, controllers and read-only replicas and anything else, with no way to tell them apart.
- the address at the end → the one that is easy to omit. It tells the lookup which server to ask. Leave it off and the question goes to whatever resolver your machine normally uses, which has no knowledge of an internal domain and answers that the name does not exist — which reads as *this domain publishes no controllers*.

**What you will see**

- **Found** — one line per record carrying four numbers and a name: priority, weight, port, and the host offering the service. Low priority wins; weight splits the load between equal priorities. The port matters, because a service does not have to sit where you expect it to.
- **Empty** — a non-existent-domain answer while you did name a server means the spelling of the record path is wrong, not that the domain is bare. Every domain that works at all publishes these records; a workstation could not log in otherwise.
- **Error** — a timeout means port 53 on that host is filtered or the host is not a controller. A refusal means it answers on 53 and declines you, which is a configuration choice and worth noting.
- **Noise** — a hostname in the answer is not an address, and the answer section may not carry one. You resolve it separately, and it may resolve to something unreachable from where you are.

```bash
nslookup -type=SRV _kerberos._tcp.domain.local <dc ip>
```

- the same question aimed at the ticket service. The two answers usually name the same hosts, and when they do not, that is the finding: something is offering one service and not the other.
- `-type=MX` on the domain name itself names the mail servers, which is the other half worth having — mail hosts are where a captured credential most often turns out to be useful.

**What you will see**

- **Found** — the controllers again, and the ticket port they are actually listening on.
- **Empty** — nothing here while the previous lookup answered means you are being told something real about this domain's layout. Note it, do not explain it away.
- **Error** — same as above, same causes.
- **Noise** — a name that appears in every answer is a controller, not a separate target you have discovered four times.

**Then** — hosts found here are targets for [[445-SMB]] and [[389-LDAP]], and the controller address is the one you hand to every command in [[Password-Spraying]]. A mail host goes in the notebook for the moment you hold a working credential.

## Reading the output

Three different things get called "a user" in the same afternoon, and keeping them apart is most of this note. A *candidate* is a string you invented from a human name. A *valid username* is a candidate the domain has confirmed exists — and that is all it confirms, because existence is decided before usability. An *account you can use* is something no step in this note produces at all: that judgement lives in [[Password-Spraying]] and in [[AD-Authentication]].

The asset this note leaves behind outlives the session. A validated username list stays true for as long as the staff do, it costs nothing to keep, and every later attack in this folder consumes it. Password lists get exhausted, credentials get rotated, tickets expire in hours — the name list does not. Build it carefully once.

## Next

- [[Password-Spraying]] — the first thing the clean list is worth, and the first step that can lock accounts out
- [[Authentication-Coercion]] — the other road to a first credential, for when no password you try is the right one
- [[AD-Authentication]] — where a credential goes once you have one, and what each kind of credential can reach

## Gaps

- Nothing on getting names out of the directory itself: an unauthenticated bind against [[389-LDAP]], or walking the identifier range over [[445-SMB]], both of which hand you real accounts rather than candidates and neither of which is written anywhere in this vault.
- No coverage of generating the six conventions from a name list mechanically, so the table above is currently a rule you apply by hand.
- The event the enumeration writes is named and not shown; there is nothing here on what the run looks like from the defender's console, which is what decides whether you rate-limit it.
- No treatment of what a locked or disabled account looks like at this stage, which matters because it validates identically to a healthy one and you cannot tell them apart until you spray.
