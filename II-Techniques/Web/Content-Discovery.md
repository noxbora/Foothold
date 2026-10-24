# Content Discovery — Directories and Files

A web root shows you only what it was built to show. This note is the sweep that finds the rest: admin panels, backups, upload directories, API routes, and the file somebody forgot to delete. It runs the moment you know a host answers HTTP, before you have any idea what the application is.

> [!important]
> Every command here decides "found" by **comparing responses to each other**, never against an absolute idea of what a hit looks like. A server that answers `200` with a friendly "page not found" makes every word in your list a hit. Take the baseline first; without it nothing below this line works.

## What a miss looks like on this host

```bash
curl -s -o /dev/null -w '%{http_code} %{size_download} %{redirect_url}\n' \
  http://target.thm/zz-no-such-path-9f2a
```

```bash
curl -s -o /dev/null -w '%{http_code} %{size_download} %{redirect_url}\n' \
  http://target.thm/zz-no-such-path-9f2a/
```

- `-o /dev/null` → discard the body; you want the numbers, not the page
- `-w '%{http_code} %{size_download}'` → status and byte count, which are exactly the two values every filter flag further down takes. Skip this and you will be choosing `-fs` by guesswork
- the random suffix → it has to be a path nobody could have. `test`, `admin` and `backup` are in every wordlist and may genuinely exist, which makes them useless as a control
- run it twice, with and without the trailing slash → many frameworks 404 one and 301 the other, and that difference alone can double your false-positive count

## The sweep

```bash
gobuster dir -u http://target.thm -w /usr/share/seclists/Discovery/Web-Content/raft-medium-directories.txt \
  -x php,html,txt,bak -t 40 -b 404 -o gobuster-root.txt
```

- `dir` → path and file brute force. `gobuster` has other modes and picking the wrong one is a silent failure: `dns` and `vhost` ignore your URL path entirely
- `-w` → the wordlist. **The single most common failure in this note.** Kali ships SecLists at `/usr/share/seclists/`, some images at `/usr/share/wordlists/seclists/`, and a pip install puts it somewhere else again. A path that does not exist makes gobuster exit immediately with `wordlist file does not exist`, which reads like a broken tool rather than a typo — check with `ls` before blaming the target
- `-x php,html,txt,bak` → also request each word with these extensions. Match them to the stack you saw in the response headers: `.php` on Apache/PHP, `.aspx` on IIS. Guessing all of them multiplies request count for nothing
- `-b 404` → the status codes treated as a miss. Set this from the baseline, not from habit
- `-t 40` → threads. Higher is faster and much louder; a lab box will start returning 429 or simply dropping connections, which looks exactly like the paths not existing
- `-o` → write to a file. You will want to diff this against the run you do after finding a second vhost, and you will not remember the first one
- `-k` → skip [[Security-Terms#^tls|TLS]] verification, needed on any lab HTTPS target
- `-r` → follow redirects. Useful to see the destination, but it hides the 301 itself, so the distinction between "exists, redirects" and "exists, renders" disappears

## When the first pass is flooded, or thin

```bash
ffuf -u http://target.thm/FUZZ -w /usr/share/seclists/Discovery/Web-Content/raft-medium-words.txt \
  -recursion -recursion-depth 2 -ac -c -of md -o ffuf-root.md
```

- `FUZZ` → the substitution point, and it must sit **in the URL where the path goes**. Leave it out and ffuf sends the same request for every word, reporting either every word or none. Put it in the host position and you have silently started doing vhost discovery instead
- `-ac` → autocalibrate: ffuf requests a few random paths itself, learns the miss shape, and filters it. This is the baseline step automated, and it is what to reach for the moment a soft 404 is drowning you
- `-recursion -recursion-depth 2` → queue any discovered directory for its own sweep. Depth costs exponentially; 2 is the sane ceiling for a first pass
- `-fs`, `-fw`, `-fl` → filter by response size, word count, line count, when `-ac` guesses wrong. Word count is the most robust of the three, because a page that echoes the requested path changes size on every request while its word count stays fixed
- `-mc all` → show every status code. Use it once, deliberately, when you suspect the app answers with something unusual (405, 500) on paths that exist
