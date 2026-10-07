---
type: technique
platform: windows
status: working
fluency: unseen
source: thm
updated: 2026-10-08
---

# BloodHound — collecting the domain and reading the graph

Every command in [[AD-Authenticated-Enumeration]] answers one question about one object. [[Security-Terms#^bloodhound|BloodHound]] asks all of those questions in one pass, stores the objects and the permissions between them, and then answers the only question that ends an engagement: from what I am holding, what is the shortest route to what I want.

## Collecting the domain from Kali

**Why now** — you hold one domain credential that authenticates ([[AD-Authentication]]) and the address of a controller. Collection needs no privilege, because an ordinary account may read nearly all of this, and that is the whole point of the tool.

```bash
bloodhound-python -u <user> -p '<password>' -d domain.local -ns <dc ip> -c All --zip
```

- `-ns <dc ip>` → the name server to resolve the domain through, and the flag to get wrong. Without it the collector asks your own resolver, fails to find the Kerberos service, prints that it could not get a ticket and quietly falls back to the older [[Security-Terms#^ntlm|NTLM]] authentication. That usually still works, so the run looks fine; in a domain where NTLM has been turned off the same omission is a dead stop that reads like a bad password.
- `-d domain.local` → the full dotted domain. The short name resolves to nothing, and the error names the domain rather than the flag.
- `-c All` → every collection method, which includes asking each computer in the domain who is logged into it and who administers it locally. Those two produce the edges that make the graph worth drawing, and they are also the only parts that need to reach every host rather than just the controller.
- `--zip` → pack the dozen or so result files into one archive for upload. Without it you upload loose files by hand, which is merely tedious until one of them is missed and the graph is silently incomplete.
- single quotes around the password → your own shell eats `!` and `$` otherwise, and a password mangled before it leaves Kali comes back as a logon failure that sends you to re-check the credential.
- `--hashes <lm:nt>` or `-k` instead of `-p` when what you hold is a hash or a ticket rather than a password; which of those authenticates where is [[AD-Authentication]]'s subject.

**What you will see**

- **Found** — a run of informational lines counting what it found: domains, computers, users, groups, containers, then `Compressing output into <timestamp>_bloodhound.zip`. Read those counts rather than skipping to the filename; they are the only receipt you get.
- **Empty** — zero users or zero computers with no error means the bind worked and the query did not, which is almost always the wrong domain name. Zero trusts is normal and says only that this is a single-domain forest. The dangerous empty is a full user and group count with no session or local-administrator data at all, because the graph will then draw no attack path and look exactly like a hardened domain.
- **Error** — a failure to get a Kerberos ticket on its own is the missing `-ns` and is survivable. An invalid server address is `-ns` pointing at nothing. A logon failure *after* a successful domain lookup is the credential or a password your shell rewrote. A refused connection while querying one computer is that host, not the run.
- **Noise** — the computer enumeration prints a line per host and most of them time out on a lab network. Those lines are not failures of the collection and they are not findings either.

**Then** — the archive goes to the ingest step below. A run with no session and no local-administrator data is re-run from a host that can reach the subnet, or deliberately re-run with `-c DCOnly` and a written note that the graph is directory-only, before a single conclusion is drawn from it.

## Ingesting, and the version trap

Upload the archive through the interface's administration tab, in its file-ingest section; it unpacks the files and builds the graph. There is nothing to configure and no command to run, which is why the two things that go wrong here both go wrong silently.

> [!important]
> The collector and the interface are versioned together. An archive from an older collector is either refused outright or partly ingested, and a partial ingest reports success while leaving whole edge types out of the graph. Match the collector to the version of the interface you are uploading into, and treat a graph with no local-administrator edges as unproven rather than clean.

The second one is merging. A second upload adds to the same database rather than replacing it, so a stale collection and a fresh one sit on top of each other and you are looking at sessions from both at once. When the domain has changed, or you have fixed a collection you know was incomplete, clear the database before the new archive goes in.

## Reading the graph instead of browsing it

Searching the graph and clicking around it is how everybody starts and it is the slowest way to use the tool. The method that pays is to name both ends: mark the account you already hold as the start, mark what you want as the target, and let it find the route. Names are normalised to upper case with the domain attached, so you are searching for `USER@DOMAIN.LOCAL`; typing the bare username often finds nothing, which reads as the account being missing from the collection.

Objects are nodes and permissions are edges. An edge is a statement that A can do something specific to B: reset its password, write to its account object, administer that machine, log in to it over the remote desktop. A path is a chain of those statements, and every link in it is a separate technique that you perform yourself. The graph is a plan, not an exploit.

The prebuilt queries are the fastest first pass, and the query language under them is [[Security-Terms#^cypher|Cypher]], which the graph database ([[Security-Terms#^neo4j|Neo4j]]) speaks. One shape is worth recognising even if you never write your own, because it is what the pathfinding button sends:

```text
MATCH p = shortestPath((u:User {name:"USER@DOMAIN.LOCAL"})-[*1..]->(g:Group {name:"DOMAIN ADMINS@DOMAIN.LOCAL"})) RETURN p
```

Reading a path honestly is the skill. The shortest path is not the cheapest one: a single hop might be a password reset you can do from Kali in a second, and the hop after it might need code execution on a host you have no access to at all. Count the hops you can actually walk today, not the hops that were drawn, and if the second one is out of reach, ask for a path to somewhere else instead.

> [!important]
> No path drawn is not the same as no path existing. It means no path exists *in the data you collected*, and the parts of the collection that fail quietly are exactly the parts that produce the interesting edges. Before calling a domain clean, check that your graph has session and local-administrator data in it at all.

## Rarely — worth one command, not worth a step

- `--exclude-dcs` skips the controllers during the per-computer step — the session and local-administrator probing — so the most watched hosts in the domain never see it, at the cost of those edges for the controllers themselves. The directory is still read from a controller. `--ExcludeDCs` is SharpHound's spelling of the same idea; bloodhound-python rejects it.
- `-c DCOnly` asks the controller and touches no member host. It is the quiet option and it costs you precisely the session and local-administrator edges that make a graph worth reading, so it is a first look rather than a collection.
- `SharpHound.exe --CollectionMethods All --Domain domain.local` is the equivalent run from a domain-joined Windows host, and [[Security-Terms#^sharphound|SharpHound]] is the officially supported collector of the two. It is also a binary that [[Security-Terms#^av|AV]] recognises by name, so it gets stopped on write far more often than the Python one.
- `runas /netonly /user:domain\user powershell` authenticates to the domain from a Windows machine that is not joined to it, which is how the Windows collector is run from a host you control rather than one you have compromised.
- [[Security-Terms#^azurehound|AzureHound]] collects the cloud directory instead, for an organisation whose identities live in both places; the graph it produces joins to the same accounts.
- Defenders run this tool too, continuously. A domain that has been hardened against these paths was usually hardened by somebody reading the same graph you are reading.

## Reading the output

The graph's blind spot is its own collection. Everything in it was true at the moment the collector ran, and sessions are the part that rots fastest: an administrator who was logged into a workstation an hour ago is an edge that may no longer exist. Before you spend an evening walking a long path, re-collect and see whether the path you planned is still there, because a session edge is a snapshot and a group membership is a fact.

What the tool cannot tell you is which edge is cheap. It knows that an account can reset another account's password; it does not know that the second account is monitored, or that the machine you would have to run code on is the one with the alerting agent. That judgement is yours and it is the reason a path with four short hops is sometimes worse than a path with two long ones.

A list tells you who is a Domain Admin. A graph tells you who can become one. That is the whole shift, and it is also why the first thing worth doing with a fresh credential is collecting the domain rather than reading it: the collection is one command, and it answers questions you have not thought to ask yet.

## Next

- [[AD-Authenticated-Enumeration]] — the same questions one at a time, for when no collector can be dropped
- [[Active-Directory-Lateral-Movement]] — walking the first edge of a path
- [[AD-Authentication]] — what each hop needs in order to be walked at all

## Gaps

- No edge reference. The graph names dozens of edge types and this note explains none of them individually, which is the next thing to write.
- Delegation, directory replication abuse and permission abuse are edges the graph will happily draw, and nothing in this vault can walk them yet.
- Nothing on clearing the database, which the merge warning above depends on.
- The Cypher example is one query; writing your own is not covered, and the prebuilt list is not inventoried.
- Nothing on what the collection looks like from the defender's side, so the choice between `-c All` and `-c DCOnly` has no evidence behind it.
