---
type: technique
platform: web
status: working
fluency: guided
source: lab
updated: 2026-09-03
---

# Source Code Disclosure

Server-side source is the strongest thing a web application can give you short of a shell. It names the parameters, shows the queries, prints the credentials, and turns every other technique in this folder from guessing into reading. This note is about the routes that hand it to you: a version-control directory deployed to the webroot, a backup file left beside the original, and the history behind both.

The most valuable part is usually not the current code. A secret removed from the working tree lives on in the repository's history, and an editor backup preserves the version from before somebody fixed something.

## Probe for the paths that leak source

**Why now** — the content sweep in [[Content-Discovery]] gave you a map of the application, and now you ask a narrower question: did anything get deployed that was never meant to be served? These paths are worth a targeted request each, because a generic wordlist often skips dotfiles and because a hit here changes the whole engagement.

```bash
for p in .git/HEAD .git/config .svn/entries .DS_Store .env composer.json \
         index.php.bak index.php~ index.php.swp backup.zip web.config.bak; do
  printf '%-24s %s\n' "$p" "$(curl -s -o /dev/null -w '%{http_code} %{size_download}' http://target.thm/$p)"
done
```

- `.git/HEAD` → the cheapest and most decisive probe. It is a tiny file with fixed contents (`ref: refs/heads/master`), so its response is unambiguous in a way that `/.git/` is not
- request specific **files**, not the directory → many servers block directory listing while serving the files inside it happily. A 403 on `/.git/` with a 200 on `/.git/HEAD` is the common and entirely exploitable case, and stopping at the 403 is how the finding gets missed
- `~` and `.swp` → editor leftovers. `index.php~` is emacs, `.index.php.swp` is vim, and both are served as plain text because the server has no handler for the extension
- `.bak`, `.old`, `.orig`, `.save`, `.txt` appended to a known filename → the same idea. Take filenames from the sweep you already ran rather than from a wordlist
- printing status **and size** → a 200 with size 0 is not a hit, and a 404 page is often served with a 200. Both numbers together are what tell you

**What you will see**

- **Found** — `200` with a small non-zero size on `.git/HEAD`, or a `200` on a `.bak` file whose size matches the original page. Fetch it and look: `ref: refs/heads/master` confirms a repository; readable PHP source confirms a backup.
- **Empty** — all 404s is a real answer for this list and closes the deployed-artefact route. It does not close source disclosure generally: [[File-Inclusion]] with `php://filter` and [[XXE]] both read source through a completely different mechanism, and neither needs a misplaced file.
- **Error** — a `403` on every path including nonsense ones means a [[Security-Terms#^waf|WAF]] is blocking the pattern, not that the files are protected. A `301` to an HTTPS URL means rerun against `https://`.
- **Noise** — a soft 404 answering `200` for everything, which is why the size column is in the command. Also a `.git` that belongs to the site's *theme* or a vendored library rather than the application: check `.git/config` for the remote URL before assuming it is the target's own code.

**Then** — a live `.git` goes to the mirror section below. A readable `.bak` or `~` is already the prize; open it and read it, then go to [[Config-File-Looting]] for what to look for inside. All 404s sends you to [[File-Inclusion]] as the other route to the same material.

## Mirror the repository

**Why now** — `.git/HEAD` answered, so the metadata is served. The whole repository is a set of files under that directory, and if the server lists directories you can pull all of them with one command.

```bash
wget -r -l inf -np -R 'index.html*' http://target.thm/.git/
```

- `-r` → recursive; it follows links, which is why this needs directory listing enabled
- `-l inf` → removes wget's **default depth limit of 5**. Git's `objects/` tree is deeper than that, so without this you mirror a partial repository that fails to check out with an error about a missing object — which reads like a broken download rather than a truncated one
- `-np` → no parent: stops wget climbing above `/.git/` and mirroring the entire website
- `-R 'index.html*'` → discards the generated directory-listing pages, which are not part of the repository and clutter the result
- output lands in a directory named after the host. `cd` into it; the `.git` subdirectory sits there, so git treats that directory as the repository root

**What you will see**

- **Found** — a directory tree containing `HEAD`, `config`, `index`, `logs/`, `objects/`, `refs/`. Object files are two-character directories full of 38-character filenames.
- **Empty** — a directory containing only `index.html` means listing is disabled, so there were no links for wget to follow. This is the common case and it is **not** a dead end: see the no-listing note below.
- **Error** — `ERROR 403: Forbidden` on `/.git/` while `/.git/HEAD` returned 200 is exactly the no-listing case. A mirror that stops early with no error is usually the missing `-l inf`.
- **Noise** — wget cheerfully mirroring the whole site because `-np` was left off. You will notice from the size and from directories that have nothing to do with git.

**Then** — a complete mirror goes to the validation step below. An incomplete one, or a 403 on the directory, goes to a dedicated dumper: without listing, objects must be pulled by hash, read out of `.git/index` and `.git/logs/HEAD` and followed by hand, which is what tools like `git-dumper` automate.

## Validate and restore the working tree

**Why now** — a mirror that is missing objects fails silently later, in a way that looks like the repository being empty. One command tells you whether you have a usable repository before you spend time on it.

```bash
git status
```

```bash
git restore .
```

```bash
ls -la
```

- `git status` → the validation. Branch and file information means the download is intact; `not a git repository` means the mirror is incomplete or you are in the wrong directory
- files listed as `deleted` is **expected and correct**. Only `.git` was mirrored, so the working tree is empty and git is comparing HEAD against nothing. Reading that as a failed download is the standard wrong turn here
- `git restore .` → repopulates every tracked file from HEAD at once. `git restore README.md` for a single file
- `ls -la` → include hidden files. `.env` is hidden, and it is usually the one you want

**What you will see**

- **Found** — a branch name, a list of deleted files, and after `restore`, the application's source on your disk. Look for `.env`, `config.php`, `wp-config.php`, `settings.py`, `appsettings.json`, `docker-compose.yml`, and any `.sql` dump.
- **Empty** — `git restore` producing no files while `git status` works means HEAD points at an empty tree or an unusual branch. `git branch -a` then restoring from a named branch resolves it.
- **Error** — `unable to read tree` or `object file is empty` names a specific missing object; fetch that object's path directly (`/.git/objects/ab/cdef...`) with curl and retry. `fatal: not a git repository` means you are one directory too high or too low.
- **Noise** — the restored tree may be a framework skeleton with nothing custom in it. Check the commit count and the author names before investing: a repository with three commits from a tutorial is not the application's real history.

**Then** — the restored tree goes to [[Config-File-Looting]] for the credential sweep. But the current tree is the smaller half of the prize; the history below is the larger one.

## Mine the history

**Why now** — you have a valid repository. The working tree shows what the developers left in; the history shows what they took out, and secrets are removed from a tree far more often than they are removed from a repository.

```bash
git log --oneline --all
```

```bash
git show <hash>
```

```bash
git log -p | grep -niE 'password|secret|api[_-]?key|token|BEGIN [A-Z ]*PRIVATE KEY'
```

```bash
git show <hash>:path/to/file
```

- `--all` → every branch and ref, not just the current one. A deleted secret often survives on an abandoned branch, and without this flag you never see it
- `-p` → include the full patch for every commit, which is what makes the `grep` above search content rather than commit messages
- `-i` on the grep → case matters more than you would think; `Password` and `API_KEY` are as common as the lowercase forms
- `git show <hash>:path` → read a file exactly as it was at one commit, without writing anything to disk or changing your working tree
- `git diff <a> <b>` → isolate what changed between two commits, which is how you find the commit that removed a credential
- read the commit **messages** first: `remove password`, `fix config`, `cleanup`, `oops`, `revert` are signposts pointing at the commit that contains the thing that was removed

**What you will see**

- **Found** — a diff line beginning with `-` that contains a real credential. The minus means it was **deleted** in that commit, which is precisely why it is not in the current tree and precisely why it is still here.
- **Empty** — a grep with no hits across full history is a genuine answer and a fairly strong one: this repository never contained a plaintext secret. Move to the restored tree's config files, where the value may be injected at deploy time and the *variable names* still tell you what the application expects.
- **Error** — `unknown revision` on `git show` means the hash is truncated or from a branch you did not fetch. A pager swallowing the output of `git log -p` on a long history: add `--no-pager` or pipe it, as above.
- **Noise** — example credentials in `.env.example`, test fixtures, and vendored dependencies under `vendor/` or `node_modules/`, which are somebody else's code and full of sample keys. Restrict the grep with `-- . ':(exclude)vendor'` when they drown the output.

**Then** — a credential goes to [[Config-File-Looting]] to identify what it opens, and then to [[Authentication-Attacks]] or straight at the service it configures. Source that contains a query built by string concatenation goes to [[SQL-Injection]] with the parameter name already known. A hardcoded path or an included filename goes to [[File-Inclusion]].

## Rarely — worth one command, not worth a step

**Why now** — `.git/HEAD` answered but the mirror came back with almost nothing. The repository is there and the server will not list it, which is a different problem from the one the section above solves.

```bash
git-dumper http://target.thm/.git/ /tmp/loot
```

- Mirroring with a recursive download only works when directory listing is on. When it is off, every file still answers by name and nothing enumerates them, so the fetch has to be driven by the repository's own index instead of by the web server.
- That is exactly what this tool does: read the index, then request each object it names. Install it with `pipx install git-dumper` if the box does not carry it.

```bash
curl -s -o /dev/null -w '%{http_code} %{size_download}\n' http://target.thm/.git/objects/pack/
```

- A repository that has been garbage-collected keeps its history in a handful of pack files rather than thousands of loose objects. When the mirror produced a working tree with no history, this is why.

**What you will see**

- **Found** — a populated directory under `/tmp/loot` that `git log` can read, or a pack directory answering with a listing.
- **Empty** — a dumper run that produces only a few files usually means the index itself is missing, and the history is not recoverable from the outside.
- **Error** — `command not found` is the usual first result; the tool is not installed by default anywhere.
- **Noise** — a `403` on the pack directory with a `200` on `HEAD` is normal and does not mean the objects are unreachable by name.

**Then** — a recovered repository goes back to the history section above, which is where the credentials actually are. Nothing recoverable means the disclosure is limited to the working tree you already have.

## Reading the output

The single reframing this note is worth: source disclosure is not a finding, it is a lens. Its value is entirely in what you read *with* it. A restored repository that nobody greps is worth less than one leaked config file that somebody does, so decide what you are looking for before you start reading — credentials, an injectable query, an included filename, an upload path, an authentication check you can bypass — and search for those, rather than browsing the code.

The second point is that this note has three doors into the same room and they fail independently. A deployed `.git` is one. A `.bak` file is another. `php://filter` through [[File-Inclusion]], and `file://` through [[XXE]], are two more, and neither requires anybody to have misplaced a file. So "no `.git`" closes one route out of four, and the note's own probe section returning all 404s should send you sideways rather than away.

## Next

- [[Config-File-Looting]] — the `.env` / `config.php` the restored tree exposes
- [[Content-Discovery]] — the scan step that surfaces an exposed `.git` in the first place
- [[Authentication-Attacks]] — where a credential found in source gets spent

## Gaps

- No worked method for dumping a repository when directory listing is off — the case that is actually more common than the one this note walks through.
- Nothing on `.svn`, Mercurial, or the `.DS_Store` filename-enumeration trick beyond naming them in the probe list.
- No coverage of JavaScript source maps (`.js.map`), which reconstruct front-end source and often leak internal API routes.
- Nothing on what to do with a `.sql` dump once you have one.
