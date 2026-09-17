---
type: technique
platform: any
status: working
fluency: unseen
source: thm
updated: 2026-09-17
---

# Exposed Service Looting

[[Config-File-Looting]] searches a host you already have a shell on. This note searches the services an organisation runs for its own developers — code hosting, build servers, internal wikis — which sit on the internal network with weak authentication and hold the credentials their users were in a hurry with. It is frequently the shortest path to a first credential, and it needs no shell anywhere.

## Why these services hold what they hold

**Why now** — a scan of the internal network returned web services on hosts whose names mention code, builds or deployment, and you have no credential for anything.

Developers and administrators handle credentials as a daily working material: a database connection string, a service account for a scheduled job, a key for an external service, a password a deployment needs. Under deadline those land where they are convenient rather than where they are safe — pasted into a file that gets committed, printed by a build script, written into a configuration file on a shared drive, typed into an onboarding page on the wiki.

What makes it worth searching even after a team has cleaned up is that most of those places remember. A password removed from a file in today's version is still in yesterday's version, and a version control system is a machine for keeping yesterday's version forever. The cleanup edits the present; the history is the artefact.

## The history, not the working tree

**Why now** — you can read a repository, whether through an internal code-hosting web interface, a clone you were allowed to make, or a version control directory left served by a web server. Reading the current files is the mistake: they are the version that has been cleaned.

```bash
git log -p | grep -i -E "password|passwd|secret|token|api_key|credential"
```

- `-p` → the one that is easy to omit, and omitting it is the difference between finding everything and finding nothing. Without it the log prints commit messages and authors only, so the search runs across a few hundred words of English prose, matches nothing, and you conclude the repository is clean when you never looked inside a single change.
- `-i` on the search → credentials are written in every case, and `Password` in a configuration key is as common as `password`.
- `-E` with `|` between the words → one pass over the history instead of six. Without `-E` the alternation needs backslashes before each `|`, and a forgotten backslash makes the pattern a literal string that matches nothing, silently.
- what this cannot see: a change on a branch that was never merged. `git log --all -p` widens it to every branch the clone has, which is worth the extra minute.

**What you will see**

- **Found** — a diff line beginning with `+` and holding an assignment. The `+` matters: a line beginning with `-` is the removal, which tells you the value was deleted and that the `+` line adding it is a few commits earlier.
- **Empty** — no matches with `-p` definitely present. Then the repository genuinely has no credential under those six words, and the next step is a tool that searches by shape rather than by vocabulary, because a key with no label around it matches none of them.
- **Error** — a fatal message about not being a repository means you are in a directory containing the project's files rather than the project itself; the version control data is one level up or was never fetched.
- **Noise** — test fixtures and example configuration files are full of the word `password` beside values like `changeme`, `example` and `hunter2`. They match every search, they are not credentials, and on a large repository they are most of what you will read.

**Then** — a value that looks real goes to [[AD-Authentication]] if it is domain-shaped and to [[Config-File-Looting]]'s final section if it is not, because a database password is a password before it is a database thing. A username with no password beside it is still an asset: it goes into the list for [[Password-Spraying]].

## Searching by shape when the vocabulary search comes back empty

**Why now** — the word search found nothing, which rules out labelled credentials and says nothing about unlabelled ones. A long random-looking string is a credential whatever the variable around it is called, and that is a property you can search for without knowing any words.

```bash
trufflehog git file:///absolute/path/to/repo
```

- `git` as the first word → tells the tool to walk the version history rather than scan the files as they stand. The file-scanning mode exists and is a different, smaller job.
- `file://` with three slashes before an absolute path → the one that is easy to omit. The tool takes remote addresses in the same position, so a bare path is read as something to fetch over the network: it fails to resolve, reports a fetch error, and reads as the tool being broken rather than as a missing prefix.
- `--only-verified` → optional and worth knowing about. It attempts to use each finding against the service it appears to belong to and reports only the ones that answer. It removes almost all of the noise and it sends traffic to third parties, which is a decision rather than a default.

**What you will see**

- **Found** — one block per finding, naming the kind of secret it matched, the commit, the file and the line. The kind is a guess from the string's shape; treat it as a hint about where to spend it.
- **Empty** — a clean run over a repository with real history is a real answer, and it is the point at which this service stops being the road in.
- **Error** — a command not found means the tool is not installed on your own machine. A fetch or clone error is almost always the missing prefix above.
- **Noise** — high-entropy strings that are not secrets: commit identifiers, content hashes, minified code, test data, base64 images. On an unverified run this is the bulk of the output, and the discriminator is whether the string sits on the right-hand side of an assignment.

**Then** — same destinations as the section above. A finding with a commit identifier beside it is worth reading in context, because the commit that added a credential often names the system it was for in its message.

## Build servers print what they were given

**Why now** — the network has a build or deployment server with a web interface. These are installed for internal use behind the perimeter, so they are frequently left on their factory administrator password or configured to let anyone read without signing in at all.

A build server is a machine that runs other people's scripts and keeps the output. That output is the loot: a deployment step prints the command it is about to run, an environment dump prints every variable the job was handed, a failing step prints the connection string it failed with. The interface hides stored credentials behind a row of asterisks when it can recognise them, and a script that builds its own command line out of pieces defeats that recognition — the asterisks appear where the tool expected a secret, not everywhere one ends up.

```bash
curl -su 'admin:admin' 'http://ci.domain.local/job/<job>/lastBuild/consoleText' | grep -i -E "password|secret|token|credential"
```

- `-u 'admin:admin'` → the one that is easy to omit, and the failure it produces is the quietest in this note. Without credentials the server answers with a sign-in page, which is a perfectly valid page full of HTML, so the search finds nothing in it and reports nothing wrong. An empty result and a refused request are indistinguishable at the end of that pipe.
- `-s` → silences the progress meter, which otherwise mixes into the output you are reading.
- `/lastBuild/consoleText` → the plain-text form of the log for the most recent run. The interface's own page for the same log is HTML around the same text, and reading the plain form means your search is not matching page markup.
- check the request first, before trusting any empty result: run the same command without the pipe and look at what actually came back. This is the same rule as `2>/dev/null` hiding a permission error — an empty search result proves nothing until you have shown it is not a refusal.

**What you will see**

- **Found** — a line from a build step with a value in it: a connection string, an argument to a command, an exported variable.
- **Empty** — genuinely nothing in that one job's most recent run, which is a statement about one run. Jobs have history, and the interesting credential is often in the run where something broke.
- **Error** — a sign-in page's HTML arriving instead of log text is the credentials. A not-found answer usually means the job name is wrong, and job names with spaces need encoding in the address.
- **Noise** — asterisks where a value should be mean the server recognised a stored secret and masked it, and there is nothing behind them to recover from this log. Do not read masking as absence of credentials on the server; read it as this line not being the leak.

**Then** — a found credential goes to [[AD-Authentication]] if it is a domain account, and to [[Password-Spraying]] if it is a password with no certain owner. A sign-in page means trying the factory password pairs on the interface itself before abandoning the host.

## Rarely — worth one command, not worth a step

**Why now** — the code hosting and the build server are the two that pay off most weeks. These are the places that hold a credential perhaps twice a year, each one a single request you make when the two above came back with nothing but example values.

- The pipeline definition file in a repository — the file that tells the build server what to run. It rarely holds the secret itself and frequently names *where* the secret is stored, which is the next place to look.
- An internal wiki or documentation portal. Onboarding pages exist to tell a new starter how to connect to things, which means they are written to contain exactly what you are looking for, in prose, indexed by the wiki's own search.
- Configuration and unattended-installation files on an open file share, which is [[445-SMB]] to find and [[Config-File-Looting]] to read.
- An unauthenticated bind against [[389-LDAP]], and default community strings on [[161-SNMP]] — both hand over configuration rather than credentials, and device configurations contain credentials.

**What you will see**

- **Found** — one of these produces a credential outright, or names the store that holds one.
- **Empty** — the expected outcome. This section is a list of long shots, run in order of how little each costs.
- **Error** — an authentication requirement on any of them is the answer for that one; move to the next rather than working on it.
- **Noise** — documentation describing a password policy is not a password, and a wiki page listing account names with no values is a spray list rather than a finding.

**Then** — anything found here joins the same two roads: [[AD-Authentication]] for a domain credential, [[Password-Spraying]] for a password whose owner you are guessing.

## Reading the output

The mistake that wastes the most time here is stopping at the first complete credential. A repository that leaked one password usually leaked the team's habits — the naming convention for service accounts, the shape of the password the helpdesk assigns, the year somebody last rotated anything — and those habits are worth more than the one account, because they tell you what to spray. Read the whole history even after the first hit.

The second thing worth keeping straight is that a partial finding is still a finding. A username with no password goes on the spray list. A password with no username goes to [[Config-File-Looting]]'s last section, which exists for exactly that. A service account name with no credential at all tells you a service account exists with that naming pattern, and the pattern generates the names of the others.

## Next

- [[Password-Spraying]] — where a password of uncertain ownership, or a list of bare usernames, is spent
- [[AD-Authentication]] — what a domain credential found here can actually reach
- [[Config-File-Looting]] — the same hunt on a host you have a shell on, and where a password with no username goes

## Gaps

- Nothing on getting at a version control directory left served by a web server, which is how these repositories are most often reachable without an account, and which needs a tool to reassemble.
- No coverage of the build server's own credential store, which holds secrets encrypted with a key on the same disk and is the reason administrator access to one of these is worth more than reading its logs.
- The factory password pairs for these interfaces are referred to and not listed, which makes the advice to try them unactionable as written.
- No treatment of how to search a code-hosting web interface when you cannot clone, which is the common case with read-only web access and no account.
