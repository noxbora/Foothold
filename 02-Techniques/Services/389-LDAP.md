---
type: service
platform: any
status: working
fluency: guided
source: reading
updated: 2026-09-03
---

# 389 — LDAP

A directory service: a tree of entries describing users, groups, computers and the policies attached to them. On a Windows domain it is the domain controller answering, and the tree is the domain itself. Many directories answer some questions to anyone who asks, which makes this the cheapest source of usernames on the network.

Reach for this note when `389` is open, or `636` for the same service wrapped in [[Security-Terms#^tls|TLS]].

## 1 — Will it answer without credentials, and what is it called

**Why now** — you cannot query a tree without knowing its root, and the root is the one thing the service will tell an anonymous client even when it refuses everything else. This is one command and it decides whether the rest of the note applies.

```bash
ldapsearch -x -H ldap://TARGET -s base namingContexts
```

- `-x` means simple authentication, and with no username that is an anonymous [[Security-Terms#^bind|bind]]. `-s base` asks only the root entry, not its children.
- What comes back is the [[Security-Terms#^dn|DN]] you must put in every later query. On a domain it reads `DC=corp,DC=local` and that maps directly to the domain name `corp.local`.
- A refusal here is still information: it says the directory exists and requires authentication, which turns this into a credential problem rather than an enumeration problem.

**What you will see**

- **Found** — one or more `namingContexts:` lines. Copy the first one exactly; a single wrong component in the DN returns an empty result that looks like an empty directory.
- **Empty** — a result with a success code and no entries means an anonymous bind was accepted but the root is hidden. Rare, and it still tells you the bind works.
- **Error** — `Invalid credentials (49)` means anonymous binds are refused. `Can't contact LDAP server (-1)` means the port or protocol is wrong; try `ldaps://` on `636`.
- **Noise** — the response also lists `supportedLDAPVersion` and similar server capabilities. They are stock and answer nothing about this host.

**Then** — a naming context goes to section 2. A credentials error goes to [[Authentication-Attacks]], and if the host is a domain controller, to whatever password you have already collected.

## 2 — Pulling the people out of the tree

**Why now** — you have the base DN and an anonymous bind that works. A bare search returns every object in the domain, which on a real network is thousands of entries. Each query below asks for one class of object and a handful of attributes.

```bash
ldapsearch -x -H ldap://TARGET -b "DC=corp,DC=local" "(objectClass=person)" sAMAccountName description
```

```bash
ldapsearch -x -H ldap://TARGET -b "DC=corp,DC=local" "(objectClass=group)" cn member
```

- The filter in parentheses is the discriminator and it is the whole point. Without it you get computers, policies, containers and printers mixed with the accounts, and the useful lines are buried.
- Naming the attributes at the end is the second half of the filter. A person entry has dozens of fields and you want two of them; ask for everything and one account fills the screen.
- `description` is the field worth reading twice. Administrators put temporary passwords, ticket numbers and account purposes there, and it is visible to anyone the directory answers.
- A filter that matches nothing returns a clean success with zero entries, which looks exactly like a directory with no users. Test your filter against `(objectClass=*)` with a `-z 5` size limit before believing a zero.

**What you will see**

- **Found** — account names you did not have, group memberships that name administrators, and occasionally a password sitting in a description field.
- **Empty** — zero entries against a base DN that worked in section 1 usually means anonymous read is allowed at the root and denied below it. That is a real configuration and it ends this route.
- **Error** — `Size limit exceeded (4)` means the query worked and the server truncated it. You have results; narrow the filter rather than retrying.
- **Noise** — service and machine accounts vastly outnumber people on a domain. Names ending in `$` are computers, not users.

**Then** — usernames go to [[Authentication-Attacks]] for spraying and to any web login you have found. A password in a description goes straight to [[445-SMB]] or [[5985-WinRM]] to test it. Group membership naming an administrator goes to the Active Directory notes.

## Rarely — worth one command, not worth a step

**Why now** — anonymous binds are refused, or you now hold a credential and want the whole picture rather than two attributes.

```bash
ldapsearch -x -H ldap://TARGET -D "corp\\bora" -w PASSWORD -b "DC=corp,DC=local" "(objectClass=user)"
```

```bash
nmap -p389 --script ldap-rootdse TARGET
```

- With a credential the anonymous restrictions disappear and the same filters return far more per entry. That is a different job from this note and belongs with the Active Directory material.
- The `nmap` script does section 1 in one line. It is here rather than above because it hides which query produced which fact, and on this service that mapping is what you are learning.
- Port `636` is the same directory over `TLS`. When `389` refuses a bind, `636` sometimes does not, and that is one command to check.

**What you will see**

- **Found** — a full user object, or the root information the anonymous query would not give.
- **Empty** — the normal answer without a credential. These are lottery tickets, not steps.
- **Error** — `ldap_bind: Invalid credentials (49)` with a real username means the password is wrong, not the method.
- **Noise** — the root entry lists supported controls and extensions, which is a long block and answers nothing here.

**Then** — a successful authenticated bind moves you out of this note entirely and into domain enumeration. Everything empty means the directory is closed and the usernames must come from somewhere else.

## Reading the output

Results arrive as blocks of `attribute: value` lines separated by blank lines, one block per entry. Counting blank lines is the fastest way to know how many objects came back before you read any of them.

The trap on this service is the silent empty. A wrong base DN, a misspelled attribute and a genuinely empty branch all return the same clean success with no entries. Always have one query you know returns something, and run it whenever a result surprises you.

## Next

- [[Authentication-Attacks]] — where the usernames go
- [[445-SMB]] — the next thing to try a recovered password against
- [[Public-Exploit-Workflow]] — when the server banner names a product and version

## Gaps

- Nothing on authenticated enumeration, which is where this service actually pays on a domain.
- No coverage of the tooling that dumps the whole directory into readable files.
- Password spraying against this port directly is not covered, and it is quieter than doing it over `445`.
