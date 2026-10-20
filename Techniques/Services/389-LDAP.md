# 389 — LDAP

A directory service: a tree of entries describing users, groups, computers and the policies attached to them. On a Windows domain it is the domain controller answering, and the tree is the domain itself. Many directories answer some questions to anyone who asks, which makes this the cheapest source of usernames on the network.

## 1 — Will it answer without credentials, and what is it called

```bash
ldapsearch -x -H ldap://TARGET -s base namingContexts
```

- `-x` means simple authentication, and with no username that is an anonymous [[Security-Terms#^bind|bind]]. `-s base` asks only the root entry, not its children.
- What comes back is the [[Security-Terms#^dn|DN]] you must put in every later query. On a domain it reads `DC=corp,DC=local` and that maps directly to the domain name `corp.local`.
- A refusal here is still information: it says the directory exists and requires authentication, which turns this into a credential problem rather than an enumeration problem.

## 2 — Pulling the people out of the tree

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
