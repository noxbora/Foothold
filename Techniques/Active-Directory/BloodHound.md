# BloodHound — collecting the domain and reading the graph

Every command in [[AD-Authenticated-Enumeration]] answers one question about one object. [[Security-Terms#^bloodhound|BloodHound]] asks all of those questions in one pass, stores the objects and the permissions between them, and then answers the only question that ends an engagement: from what I am holding, what is the shortest route to what I want.

## Collecting the domain from Kali

```bash
bloodhound-python -u <user> -p '<password>' -d domain.local -ns <dc ip> -c All --zip
```

- `-ns <dc ip>` → the name server to resolve the domain through, and the flag to get wrong. Without it the collector asks your own resolver, fails to find the Kerberos service, prints that it could not get a ticket and quietly falls back to the older [[Security-Terms#^ntlm|NTLM]] authentication. That usually still works, so the run looks fine; in a domain where NTLM has been turned off the same omission is a dead stop that reads like a bad password.
- `-d domain.local` → the full dotted domain. The short name resolves to nothing, and the error names the domain rather than the flag.
- `-c All` → every collection method, which includes asking each computer in the domain who is logged into it and who administers it locally. Those two produce the edges that make the graph worth drawing, and they are also the only parts that need to reach every host rather than just the controller.
- `--zip` → pack the dozen or so result files into one archive for upload. Without it you upload loose files by hand, which is merely tedious until one of them is missed and the graph is silently incomplete.
- single quotes around the password → your own shell eats `!` and `$` otherwise, and a password mangled before it leaves Kali comes back as a logon failure that sends you to re-check the credential.
- `--hashes <lm:nt>` or `-k` instead of `-p` when what you hold is a hash or a ticket rather than a password; which of those authenticates where is [[AD-Authentication]]'s subject.

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
