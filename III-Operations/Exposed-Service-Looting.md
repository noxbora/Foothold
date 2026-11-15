# Exposed Service Looting

[[Config-File-Looting]] searches a host you already have a shell on. This note searches the services an organisation runs for its own developers — code hosting, build servers, internal wikis — which sit on the internal network with weak authentication and hold the credentials their users were in a hurry with. It is frequently the shortest path to a first credential, and it needs no shell anywhere.

## Why these services hold what they hold

Developers and administrators handle credentials as a daily working material: a database connection string, a service account for a scheduled job, a key for an external service, a password a deployment needs. Under deadline those land where they are convenient rather than where they are safe — pasted into a file that gets committed, printed by a build script, written into a configuration file on a shared drive, typed into an onboarding page on the wiki.

What makes it worth searching even after a team has cleaned up is that most of those places remember. A password removed from a file in today's version is still in yesterday's version, and a version control system is a machine for keeping yesterday's version forever. The cleanup edits the present; the history is the artefact.

## The history, not the working tree

```bash
git log -p | grep -i -E "password|passwd|secret|token|api_key|credential"
```

- `-p` → the one that is easy to omit, and omitting it is the difference between finding everything and finding nothing. Without it the log prints commit messages and authors only, so the search runs across a few hundred words of English prose, matches nothing, and you conclude the repository is clean when you never looked inside a single change.
- `-i` on the search → credentials are written in every case, and `Password` in a configuration key is as common as `password`.
- `-E` with `|` between the words → one pass over the history instead of six. Without `-E` the alternation needs backslashes before each `|`, and a forgotten backslash makes the pattern a literal string that matches nothing, silently.
- what this cannot see: a change on a branch that was never merged. `git log --all -p` widens it to every branch the clone has, which is worth the extra minute.

## Searching by shape when the vocabulary search comes back empty

```bash
trufflehog git file:///absolute/path/to/repo
```

- `git` as the first word → tells the tool to walk the version history rather than scan the files as they stand. The file-scanning mode exists and is a different, smaller job.
- `file://` with three slashes before an absolute path → the one that is easy to omit. The tool takes remote addresses in the same position, so a bare path is read as something to fetch over the network: it fails to resolve, reports a fetch error, and reads as the tool being broken rather than as a missing prefix.
- `--only-verified` → optional and worth knowing about. It attempts to use each finding against the service it appears to belong to and reports only the ones that answer. It removes almost all of the noise and it sends traffic to third parties, which is a decision rather than a default.

## Build servers print what they were given

A build server is a machine that runs other people's scripts and keeps the output. That output is the loot: a deployment step prints the command it is about to run, an environment dump prints every variable the job was handed, a failing step prints the connection string it failed with. The interface hides stored credentials behind a row of asterisks when it can recognise them, and a script that builds its own command line out of pieces defeats that recognition — the asterisks appear where the tool expected a secret, not everywhere one ends up.

```bash
curl -su 'admin:admin' 'http://ci.domain.local/job/<job>/lastBuild/consoleText' | grep -i -E "password|secret|token|credential"
```

- `-u 'admin:admin'` → the one that is easy to omit, and the failure it produces is the quietest in this note. Without credentials the server answers with a sign-in page, which is a perfectly valid page full of HTML, so the search finds nothing in it and reports nothing wrong. An empty result and a refused request are indistinguishable at the end of that pipe.
- `-s` → silences the progress meter, which otherwise mixes into the output you are reading.
- `/lastBuild/consoleText` → the plain-text form of the log for the most recent run. The interface's own page for the same log is HTML around the same text, and reading the plain form means your search is not matching page markup.
- check the request first, before trusting any empty result: run the same command without the pipe and look at what actually came back. This is the same rule as `2>/dev/null` hiding a permission error — an empty search result proves nothing until you have shown it is not a refusal.
