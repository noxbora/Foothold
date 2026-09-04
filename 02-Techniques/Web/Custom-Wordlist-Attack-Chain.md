---
type: technique
platform: web
status: solid
fluency: guided
source: lab
updated: 2026-08-31
---

# Custom Wordlist Attack Chain

Generic wordlists encode what is common on the internet. They do not contain the target's product names, project codenames, office locations, or the surname of the person who built the server. This chain builds a list out of the target's own vocabulary, cleans it into something a tool can consume, and then spends it on directory discovery and login brute force.

Three stages, and each one is only worth doing because the next one exists: **collect**, **clean**, **use**. The clean stage is the one people skip and the one that decides whether the whole chain is worth anything.

A useful custom list mixes three categories:

- Company keywords — products, project names, slogans, office locations
- Technology keywords — framework or [[Security-Terms#^cms|CMS]] specific paths (WordPress plugins, Laravel routes)
- Generic keywords — `admin`, `api`, `assets`, `dev`, `login`, `settings`

## Stage 1 — Collect

### Crawl the site for its own words

**Why now** — a generic sweep from [[Content-Discovery]] came back thin, which means the target's paths are named in a vocabulary no public wordlist contains. The application publishes that vocabulary on every page it serves; you just have to collect it.

```bash
cewl -d 2 -m 3 --lowercase --with-numbers -e --email_file emails.txt -w cewl_words.txt \
  http://target.local
```

- `-d 2` → crawl depth. Spidering means open a page, follow its links, follow the links on those, and so on; depth is how many hops out from the start page it goes. Depth 2 is a good first pass, depth 3 on a large site takes a long time for diminishing returns
- `-m 3` → minimum word length. Below 3 you collect `a`, `of`, `to` and the list becomes noise
- `--lowercase` → normalises at collection time, which saves work in stage 2
- `-e --email_file emails.txt` → harvest email addresses as well, into a separate file. **Easy to omit**, and omitting it throws away the highest-value output of the whole crawl: emails give you the organisation's username format for free
- `-w` → write to a file. Without it the words go to stdout and vanish

**What you will see**

- **Found** — a few hundred to a few thousand words, one per line, mixed case unless you passed `--lowercase`. Product names and internal jargon among them are exactly what you came for.
- **Empty** — a nearly empty list usually means the crawl never left the first page: a site that renders its content with JavaScript gives `cewl` almost nothing, because it does not execute scripts. That is a tooling limit, not a quiet target — collect from the JS bundles and the API responses by hand instead.
- **Error** — a connection error means the host or the scheme is wrong. A crawl that runs for a very long time is depth, not a hang; lower `-d`.
- **Noise** — boilerplate: `privacy`, `cookies`, `copyright`, `javascript`, the CMS's own name repeated across every page. It survives cleaning and dilutes the list, which is why stage 3 filters results rather than trusting the list.

**Then** — the raw words go into stage 2 before any tool touches them. The emails go to the username derivation below, and to [[TheHarvester]] if you want to widen that search beyond the site itself.

### Mine hosted documents

**Why now** — published PDFs, spreadsheets and presentations carry internal jargon, author names, software versions and contact details that never appear in page text. They are also frequently forgotten in a `/docs/` directory that the content sweep already found.

```bash
wget -r -A pdf,docx,xlsx -np -nH http://target.local/docs/
for f in $(find target.local/docs -name '*.pdf'); do
  strings -n 5 "$f" | grep -vP '^[/<>%0-9\\]|^(stream|endstream|endobj|xref|trailer|startxref)$' >> raw_words.txt
done
```

- `-A pdf,docx,xlsx` → an accept filter on extension, so you download documents and not the whole site
- `-np` → no parent, or wget climbs out of `/docs/` and mirrors everything
- `strings -n 5` → prints runs of readable text five characters or longer from a binary file
- the `grep -v` → **the step that makes this usable.** `-v` inverts the match, keeping lines that do *not* match, and the pattern drops PDF structural markers. Without it, `raw_words.txt` is mostly `endobj` and hex fragments, and the noise survives every later filter
- also worth reading, though not covered here: document metadata (`exiftool`) names the author, the software and often the internal file path

**What you will see**

- **Found** — a long file of readable fragments including names, department names, project codenames and software versions. Author names are the payoff, since they feed username generation.
- **Empty** — no documents downloaded means the directory was not listable or holds nothing. Check with a plain `curl` on the directory before assuming; wget needs links to follow, the same limitation as in [[Source-Code-Disclosure]].
- **Error** — `strings: command not found` on a minimal system; `tr -cd '\11\12\15\40-\176'` is a crude fallback. A PDF that yields nothing is compressed or encrypted, which `strings` cannot read.
- **Noise** — font names, PDF producer strings (`Microsoft Word`, `Acrobat Distiller`), and encoding fragments. The `grep -v` catches the structural ones; the rest is diluted away in cleaning.

**Then** — `raw_words.txt` merges with `cewl_words.txt` in stage 2. Author names go to the permutation step below.

### Extract emails and derive usernames

**Why now** — you have documents and pages full of addresses. An email address is a username plus a domain, and the local part is very often the exact account name on every internal system.

```bash
grep -RhiaoP '[A-Za-z0-9._%+-]+@target\.com' target.local/docs | sort -u > emails_docs.txt
```

```bash
grep -Po '^[^@]+' emails_docs.txt > users_from_emails.txt
```

- `-R` recursive, `-h` suppress filenames, `-i` case-insensitive, `-o` print **only the matched address** rather than the whole line, `-a` treat binary files as text, `-P` Perl regex
- `-a` is the one that matters here → without it `grep` reports `Binary file matches` and prints nothing, which looks exactly like finding no addresses in a directory full of them
- `-o` similarly → without it you get whole lines of PDF noise wrapped around each address
- `^[^@]+` → one or more characters that are not `@`, anchored to the line start. Strips the domain and leaves the local part as a username candidate
- escape the dot in the domain (`target\.com`) → an unescaped `.` matches any character and pulls in addresses at other domains

**What you will see**

- **Found** — a deduplicated list of addresses at the target's domain, and from them a list of username candidates. The **format** is worth as much as the names: `first.last@`, `flast@` and `f.last@` are three different organisational conventions and knowing which one is in use multiplies the value of every name you find later.
- **Empty** — no addresses may mean the documents use a different domain than you assumed. Widen the pattern to `[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+` once and see what domains actually appear.
- **Error** — `grep: invalid option -- P` on a system with BSD grep; use `grep -E` with a slightly looser pattern, or `ggrep`.
- **Noise** — addresses belonging to vendors, printers, and mailing lists (`noreply@`, `postmaster@`, `info@`). They are real and they are not people, so they are poor username candidates and excellent spray targets for a shared mailbox.

**Then** — the usernames merge into `users.txt` in stage 2, and get spent in stage 3 and in [[Authentication-Attacks]].

### Harvest names from public pages

**Why now** — a staff directory, a team page, or an author list gives you real human names, which is the raw material for username permutation. Names are more durable than any wordlist entry — people stay in an organisation longer than a password policy lasts.

```bash
curl -s http://social.target.local/ | grep -Po '(?<=<h3 class="profile-name">)[^<]+' > names.txt
```

- `(?<=...)` → a positive lookbehind: the text before the match is required but **not included** in the output. So the tag anchors the match without being printed
- `[^<]+` → everything up to the next `<`, which is the closing tag
- read the page source first and match the tag that is actually there → this selector is an example, and copying it without checking gives you an empty file that looks like a page with no names on it
- for anything JavaScript-rendered, this fails silently; take the JSON the page fetches instead

**What you will see**

- **Found** — one name per line, usually `First Last`. Check for and strip titles and suffixes before the permutation step.
- **Empty** — an empty file almost always means the selector, not the page. Confirm by grepping the raw HTML for a name you can see in the browser.
- **Error** — no error is produced by a selector that matches nothing, which is exactly what makes this step deceptive. Always check `wc -l names.txt`.
- **Noise** — names of authors of quoted articles, testimonial names, and stock-photo captions. They cost you a few wasted login attempts each.

**Then** — into the permutation step immediately below.

### Build username permutations

**Why now** — you have real names and, from the email format, evidence of which convention the organisation uses. Generating the two or three plausible forms is cheap; guessing the convention wrong and spraying a list of names that do not exist is not.

```bash
awk '{print tolower($1)"."tolower($2)}' names.txt > users_first.last.txt
```

```bash
awk '{print tolower(substr($1,1,1))tolower($2)}' names.txt > users_flast.txt
```

```bash
awk '{print tolower($1)tolower(substr($2,1,1))}' names.txt > users_firstl.txt
```

- `awk` splits each line on whitespace; `$1` is the first field, `$2` the second
- `substr($1,1,1)` → one character starting at position 1, which produces the initial
- `tolower()` on everything → case mismatches cost you real hits against case-sensitive systems and cost you nothing against case-insensitive ones
- these produce `alex.johnson`, `ajohnson`, and `alexj` from `Alex Johnson`
- a middle name or a two-word surname breaks the field positions → check a few lines of output against the input before generating thousands

**What you will see**

- **Found** — three files, each the same length as `names.txt`. If one is shorter, some input lines had fewer than two fields.
- **Empty** — an empty output means `names.txt` was empty or single-column; go back one step.
- **Error** — `awk` does not error on a missing `$2`; it substitutes an empty string. So the failure mode is silent and shows up as usernames like `alex.` — which is why the check above matters.
- **Noise** — permutations of names that were noise in `names.txt` to begin with. The cost is linear in list length, so trim the source rather than the output.

**Then** — all three files merge into `users.txt` in stage 2. The email-derived list from earlier is the fourth input, and it is the most reliable of them because it is observed rather than inferred.

## Stage 2 — Clean

Raw output is noisy: duplicates, mixed case, punctuation fragments, Windows line endings. A bloated list wastes brute-force time; a fragmented one tries `Helios`, `helios` and `HELios` as three separate candidates and gets three separate failures.

### Merge and normalise the words

**Why now** — you have several collection outputs of varying quality. Everything downstream is priced per line, so this is where you decide how long every later stage takes.

```bash
cat cewl_words.txt raw_words.txt | sort -u > words_raw.txt
```

```bash
cat words_raw.txt | tr '[:upper:]' '[:lower:]' | tr -d '\r' \
  | grep -P '^[a-z0-9][a-z0-9._-]{4,}$' | sort -u > words_clean.txt
```

```bash
wc -l words_clean.txt && head words_clean.txt
```

- `sort -u` → sorts alphabetically and discards duplicates
- `tr '[:upper:]' '[:lower:]'` → one canonical case, so the same word is one candidate
- `tr -d '\r'` → deletes carriage returns left by Windows-authored documents. **The invisible one.** A trailing `\r` makes every request ask for `admin%0D` instead of `admin`, so a perfectly good list produces a run of clean 404s and you conclude the words were wrong
- `grep -P '^[a-z0-9][a-z0-9._-]{4,}$'` → keep entries starting with a letter or digit followed by four or more letters, digits, dots, underscores or dashes. Minimum five characters total, and no punctuation fragments
- `wc -l` then `head` → **the sanity check, and it is the read for this whole stage.** Do not skip it; it is the only place the pipeline tells you whether it worked

**What you will see**

- **Found** — a few hundred entries, all lowercase, all well formed, in `head`'s first ten lines. That is a healthy list.
- **Empty** — zero lines out of a non-empty input means the `grep` pattern rejected everything, usually because the input still had uppercase or leading punctuation. Check the order of the pipeline: lowercasing must come before the pattern.
- **Error** — no error is emitted by a filter that drops everything, which is why `wc -l` is part of the command rather than an optional follow-up.
- **Noise** — thousands of lines, or visible mixed case and punctuation in `head`, means the clean stage failed. Fix it here; every later stage multiplies this list's problems by its own request count.

**Then** — `words_clean.txt` is the input to directory discovery in stage 3 and to [[Content-Discovery]]. A list that fails its sanity check goes back to collection, not forward.

### Merge the usernames

**Why now** — four sources of username candidates, and the tools take one file.

```bash
cat users_first.last.txt users_flast.txt users_firstl.txt users_from_emails.txt \
  | tr -d '\r' | sort -u > users.txt
```

- same `tr -d '\r'` as above, for the same invisible reason
- `sort -u` collapses the overlap between conventions, which is often substantial
- if the email evidence showed one clear convention, **use only that file**. Three conventions triples your request count and lockout risk to cover forms you already have evidence against

**What you will see**

- **Found** — a single deduplicated file, typically a few dozen to a few hundred lines.
- **Empty** — one of the source files was missing and `cat` printed an error to stderr that scrolled past. Check with `wc -l` on each input.
- **Error** — `cat: users_firstl.txt: No such file or directory` goes to stderr while the redirect still creates a perfectly valid-looking `users.txt` from the files that did exist. The command appears to succeed and the list is quietly short.
- **Noise** — usernames derived from names that were never real people. They cost one failed attempt each, which matters when a lockout policy counts them.

**Then** — `users.txt` is the `-L` input to hydra in stage 3 and the username list for [[Authentication-Attacks]].

### Generate a pattern-based password list

**Why now** — [[Security-Terms#^osint|OSINT]] revealed a password *format* rather than a password: a policy notice, a default documented in a manual, a pattern visible in a leaked example. Generating exactly that space is far better than guessing broadly, because it is small and it is certain to contain the answer if the format is right.

```bash
crunch 11 11 -t Helios20%%! -o pass_helios.txt
```

```bash
wc -l pass_helios.txt
```

- both `11` values → minimum and maximum length, and they must match the template's length
- `-t` → the template. `%` is replaced by a digit, so two `%` gives `00` to `99` and exactly 100 lines
- placeholders: `%` digit, `@` lowercase letter, `,` uppercase letter, `^` symbol
- **estimate the size before running.** Charset size raised to the power of the number of placeholders is the line count: six `^` symbols over a 16-symbol set is 16^6, which is 16 million lines and roughly 200MB. `crunch` prints its estimate and asks nothing before filling your disk
- `-o` → write to file rather than stdout

**What you will see**

- **Found** — a file whose length matches your arithmetic. 100 lines for two `%`, and if it is not 100 you have miscounted the template.
- **Empty** — crunch refusing to run with a length that does not match the template is the usual cause: `crunch 8 8 -t Helios20%%!` is an 11-character template with an 8-character bound.
- **Error** — a disk filling up mid-run. Delete the partial file; a truncated password list will silently miss the answer and you will trust the negative.
- **Noise** — none, by construction. That is the point of this approach over a generic list.

**Then** — `pass_helios.txt` is the `-P` input to hydra in stage 3. If no format is known, a generic list plus the target's own words from `words_clean.txt` is the fallback.

## Stage 3 — Use

### Directory and file discovery with the custom list

**Why now** — you have a list built from the target's vocabulary, and a generic sweep that already failed. This is the payoff for stages 1 and 2, and it asks a question no public wordlist can ask.

```bash
ffuf -w words_clean.txt -u http://target.local/FUZZ -e .php,.html,/ -mc 200,301,302 \
  -ac -o ffuf-custom.json
```

- `-w` → your cleaned wordlist
- `FUZZ` → the placeholder each word is substituted into. It must sit where the path goes; move it into the host position and you are doing [[Virtual-Host-Discovery]] instead, with the same command and completely different meaning
- `-e .php,.html,/` → test each word with these suffixes appended. The trailing `/` is the one that finds directories
- `-mc 200,301,302` → match only these statuses. Add `401,403` when you want to map what exists but is protected, which is often the more interesting map
- `-ac` → autocalibrate against the server's miss shape. Without it a soft 404 makes every word a hit; with it, most filtering problems disappear
- the same tool covers subdomains, parameters and API endpoints — the only change is where `FUZZ` sits

**What you will see**

- **Found** — paths that a generic list would never have contained: a product name, a project codename, an internal tool's name. These are the highest-value hits in web discovery because nobody else has found them.
- **Empty** — with `-ac` on and a well-formed list, empty is a real answer. It means the paths are not named after the site's own vocabulary, and the next question is whether you are even on the right host — [[Virtual-Host-Discovery]].
- **Error** — `FUZZ keyword not found` means the placeholder is missing from the URL. A run that finishes instantly did not read the wordlist; check the path.
- **Noise** — the boilerplate words from stage 1 (`privacy`, `contact`, `about`) matching real but uninteresting pages. Expected, and cheap.

**Then** — hits go back into the application: read each one, look for input, and route it to the matching technique. Full method in [[Content-Discovery]].

### Login brute force with the custom lists

**Why now** — you hold usernames derived from real people and a password space derived from a real format. This is a far narrower attack than a generic credential list, which is what makes it viable against a login that has any rate limiting at all.

```bash
hydra -L users.txt -P pass_helios.txt -f -V -t 4 target.local \
  http-post-form '/path/login.php:username=^USER^&password=^PASS^:S=SUCCESS_STRING'
```

- `-L` username file, `-P` password file. Lowercase `-l` / `-p` take a single value instead
- `-f` → stop at the first valid pair. Without it hydra keeps going and buries the hit
- `-V` → print every attempt, so you can see it is actually sending what you think it is
- `-t 4` → four parallel threads. Raise cautiously: high counts trip lockouts, and a lockout does not just end this attack, it invalidates every result after it fired
- the `http-post-form` argument is three colon-separated parts: the path to the form handler, the POST body with `^USER^` and `^PASS^` placeholders, and the success or failure condition. `S=` matches a string present on **success**, `F=` a string present on **failure**
- **read the form's actual HTML before writing part two.** Field names are frequently not `username` and `password`, and a missing hidden field — a [[Security-Terms#^csrf|CSRF]] token especially — makes every attempt fail identically, which reads as "no valid credentials" rather than "the request was malformed"
- prefer `F=` over `S=` when you can → you know exactly what failure looks like because you have seen it; you are guessing at success

**What you will see**

- **Found** — `[80][http-post-form] host: target.local  login: alex.johnson  password: Helios2023!` Confirm it by logging in manually before building anything on it.
- **Empty** — hydra completing with no valid pair means these usernames with these passwords do not work. Before accepting that, check the three silent failures: a wrong field name, a missing CSRF token, and a condition string that never matches. Send one request by hand with a password you know is wrong and confirm the failure string appears.
- **Error** — `Can not connect` is the host or port. A run that reports **every** pair as valid means your `S=` string appears on the failure page too; switch to `F=`.
- **Noise** — an application that returns the same page for lockout and for failure. Once locked out, every remaining result is meaningless and the run should be stopped, not finished.

**Then** — working credentials go into the application and then at every other service on the host, because reuse is common. Everything else about the login attack surface, including the CSRF-token case, is in [[Authentication-Attacks]].

## Output map

| File              | Contents                    | Used for                      |
| ----------------- | --------------------------- | ----------------------------- |
| `cewl_words.txt`  | Site keywords               | merged into `words_clean.txt` |
| `raw_words.txt`   | Strings from PDFs           | merged into `words_clean.txt` |
| `emails_docs.txt` | Addresses at the domain     | username format evidence      |
| `words_clean.txt` | Cleaned keyword list        | ffuf directory discovery      |
| `names.txt`       | Employee names              | username generation           |
| `users.txt`       | All username permutations   | hydra `-L`                    |
| `pass_helios.txt` | Pattern-generated passwords | hydra `-P`                    |

## Reading the output

The chain has one checkpoint and everything depends on it: `wc -l` and `head` after cleaning. Expect a few hundred lowercase, well-formed entries. Thousands of lines, or mixed case and punctuation fragments in `head`, means the clean stage failed — and the cost of ignoring that is paid twice over, once in wasted requests and once in a negative result you will wrongly trust.

The deeper point is about what a custom list is *evidence* of. A generic sweep failing tells you nothing about the target. A **custom** sweep failing, built from the site's own words and its own people, is a real statement: the naming here is not derived from anything public, so brute force is the wrong instrument and you should be reading the application instead — its JavaScript, its API responses, its error messages. Knowing when to stop guessing is most of what this chain buys you.

## Next

- [[Content-Discovery]] — spend `words_clean.txt` on `ffuf` directory discovery
- [[Authentication-Attacks]] — spend `users.txt` / `pass_*.txt` on the login attacks
- [[TheHarvester]] — widen the email and name collection beyond the target's own site

## Gaps

- Nothing on rule-based mutation: taking `words_clean.txt` and generating `Helios2023!`, `helios123` and similar with hashcat rules, which is where a keyword list becomes a password list.
- No coverage of collecting from JavaScript bundles and API responses, which is where a modern application's vocabulary actually lives and where `cewl` cannot reach.
- Nothing on `exiftool` metadata as a name source, despite documents being downloaded here anyway.
- No guidance on list size versus engagement time — the tradeoff that decides whether a run is worth starting at all.
