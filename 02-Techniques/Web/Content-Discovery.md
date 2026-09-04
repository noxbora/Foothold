---
type: technique
platform: web
status: working
fluency: guided
source: lab
updated: 2026-08-31
---

# Content Discovery — Directories and Files

A web root shows you only what it was built to show. This note is the sweep that finds the rest: admin panels, backups, upload directories, API routes, and the file somebody forgot to delete. It runs the moment you know a host answers HTTP, before you have any idea what the application is.

> [!important]
> Every command here decides "found" by **comparing responses to each other**, never against an absolute idea of what a hit looks like. A server that answers `200` with a friendly "page not found" makes every word in your list a hit. Take the baseline first; without it nothing below this line works.

## What a miss looks like on this host

**Why now** — you have a port answering HTTP and nothing else. Before firing thousands of requests you need to know what this server does with a path that certainly does not exist, because that shape is what you will be filtering out for the rest of the engagement.

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

**What you will see**

- **Found** — `404` with a size of `0` or a small constant. The easy case: you can filter on status alone, and anything that is not 404 is worth opening.
- **Empty** — cannot occur here; curl always prints a status line. A blank line means the connection never completed, not that the path was empty.
- **Error** — `curl: (7) Failed to connect` means nothing is listening from where you are. `curl: (60) SSL certificate problem` on an HTTPS target wants `-k`; that is a lab certificate, not a finding.
- **Noise** — `200` with a body of a few thousand bytes is a **soft 404**: the application renders its own error page and reports success. Write the exact byte count down, it is the argument `-fs` needs.

**Then** — a hard 404 means you can sweep on status codes and read the results directly. A soft 404 means you must sweep on size or word count, and every status-only filter will bury you. Either way, carry those two numbers into the sweep below.

## The sweep

**Why now** — you know what a miss looks like, so you can now recognise a hit. This is the pass that turns one URL into a map of the application.

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

**What you will see**

- **Found** — a line like `/admin (Status: 301) [Size: 312]` or `/backup.bak (Status: 200) [Size: 41022]`. What makes it real is that its size differs from the baseline you measured. 200 on a file extension you did not expect, and 401/403 on a directory, are both hits.
- **Empty** — three different things, and they lead in opposite directions. Either the app genuinely has no discoverable paths under this root; or your wordlist does not contain the target's vocabulary, which is the case [[Custom-Wordlist-Attack-Chain]] exists for; or the content lives on a different hostname on this same IP, which is [[Virtual-Host-Discovery]]. Never read empty as "this host has nothing".
- **Error** — `wordlist file does not exist` is a path typo. `connection refused` partway through means you exceeded what the server tolerates, so lower `-t` and rerun. A wall of identical `Status: 200` results from the first word onward is not an error but a soft 404 you failed to filter.
- **Noise** — soft 404s of constant length; `/icons/` and `/manual/` on stock Apache; the framework's own asset directories (`/static/`, `/assets/`, `/vendor/`); and 301s that only add a trailing slash to the path you asked for, which is the same resource, not a new one.

**Then** — a hit on `.git`, `.bak`, `~`, `.swp` or a zip goes straight to [[Source-Code-Disclosure]]. A 403 on a directory is not a wall: it says the directory exists, so recurse into it (next section). Nothing at all sends you to [[Custom-Wordlist-Attack-Chain]] to build a list from the target's own words, and to [[Virtual-Host-Discovery]] to check that you are even talking to the right site.

## When the first pass is flooded, or thin

**Why now** — the sweep returned either everything or nothing, and both mean the same thing: the filter is wrong for this host. `ffuf` is the tool for that because it filters on the response body, not just the status line.

```bash
ffuf -u http://target.thm/FUZZ -w /usr/share/seclists/Discovery/Web-Content/raft-medium-words.txt \
  -recursion -recursion-depth 2 -ac -c -of md -o ffuf-root.md
```

- `FUZZ` → the substitution point, and it must sit **in the URL where the path goes**. Leave it out and ffuf sends the same request for every word, reporting either every word or none. Put it in the host position and you have silently started doing vhost discovery instead
- `-ac` → autocalibrate: ffuf requests a few random paths itself, learns the miss shape, and filters it. This is the baseline step automated, and it is what to reach for the moment a soft 404 is drowning you
- `-recursion -recursion-depth 2` → queue any discovered directory for its own sweep. Depth costs exponentially; 2 is the sane ceiling for a first pass
- `-fs`, `-fw`, `-fl` → filter by response size, word count, line count, when `-ac` guesses wrong. Word count is the most robust of the three, because a page that echoes the requested path changes size on every request while its word count stays fixed
- `-mc all` → show every status code. Use it once, deliberately, when you suspect the app answers with something unusual (405, 500) on paths that exist

**What you will see**

- **Found** — a row whose size or word count sits alone, away from the cluster everything else falls into. One 4,102-byte response among two hundred 1,876-byte responses is the finding, whatever its status code says.
- **Empty** — after `-ac`, an empty result is a much stronger statement than an empty gobuster run: it means the app answered uniformly for every word you tried. That points at the wordlist or the hostname, not at your filtering.
- **Error** — ffuf refusing to start with `FUZZ keyword not found` means the keyword is missing from the URL and from every header. `-ac` combined with a manual `-fs` fights itself and filters everything; use one or the other.
- **Noise** — a page that reflects the requested path in its body defeats size filters entirely, because every miss is a different length. Switch to `-fw`.

**Then** — a directory that appears with 403 or 401 is a target, not a wall: it exists, so enumerate inside it and check whether the restriction is path-based (try `/admin/` versus `/Admin/`, or a trailing `.` or `%2e`). A directory that appears with 200 and an index listing is loot; read every file in it before moving on. A confirmed empty sweep with a good filter sends you to [[Custom-Wordlist-Attack-Chain]].

## Reading the output

Two things span this whole note.

The first is that discovery is comparative all the way down. Every judgement you make here is "this response differs from the others", so the moment you cannot describe the miss shape in a sentence, stop fuzzing and go back to the baseline. Time lost re-measuring is minutes; time lost reading two hundred soft 404s as hits is an afternoon.

The second is that a path is not a finding until you have opened it. Discovery tells you a resource exists; it says nothing about what is inside. Feed every hit back into the question you actually care about — does it take input, does it name a technology, does it leak a path on disk — because a list of thirty discovered directories with nothing read is not progress.

## Next

- [[Source-Code-Disclosure]] — a hit on `.git`, `.bak`, `~` or a backup turns discovery into source
- [[Custom-Wordlist-Attack-Chain]] — when a generic list comes up empty, build one from the target
- [[Virtual-Host-Discovery]] — sparse results can mean the content lives on another vhost

## Gaps

- Nothing on authenticated discovery: sweeping with a session cookie, and the fact that the map changes completely once you are logged in.
- Parameter discovery (`ffuf` against `?FUZZ=value`, arjun) is not here, only path discovery.
- No guidance on choosing between the SecLists wordlists by size and purpose, which is the decision that most changes how long a sweep takes.
- Nothing on rate limiting or [[Security-Terms#^waf|WAF]] evasion beyond lowering `-t`.
