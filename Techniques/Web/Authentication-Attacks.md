---
type: technique
platform: web
status: working
fluency: guided
source: thm
updated: 2026-09-08
---

# Authentication Attacks

Everything here exploits the same underlying flaw: the application **behaves differently** for valid and invalid input, and it does so before it has authenticated you. A signup form that says "already taken", a login that redirects instead of re-rendering, a reset flow that trusts the wrong copy of a parameter, a cookie that carries a decision instead of a reference to one. Find the difference and the rest is mechanical.

The order below is the order to work in: confirm usernames, then spend them on passwords, then — if both are slow — look for the logic flaw that skips the guessing entirely. Session handling for forms that carry a fresh [[Security-Terms#^csrf|CSRF]] token per request is in [[Burp-Suite]].

## Establish the difference by hand

**Why now** — every automated step below needs a filter, and a filter is a description of the difference between success and failure. One manual request pair costs thirty seconds and is the difference between a run you can read and ten thousand identical rows.

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

**What you will see**

- **Found** — a difference in status, in byte count, in the redirect target, or in the body text. Note which one, because that is the flag you will use: status → `-fc` / `-mc`, size → `-fs`, body string → `-mr` / `-fr`.
- **Empty** — both responses identical in every column. That is a well-built login and it means username enumeration is closed here, so go and look for a different endpoint that leaks the same information: signup, password reset, and API routes are frequently inconsistent with the login form even in the same application.
- **Error** — a 405 means the form is not a POST, or not at this path. A 403 with a vendor page is a [[Security-Terms#^waf|WAF]] and will shape everything below. A 302 to a login page on *both* means you have the wrong URL.
- **Noise** — a byte count that differs by a few bytes on every request is a CSRF token or a timestamp in the body, not a signal. Repeat the same request twice; if the size changes between two identical requests, size filtering is unusable and you need `-fr` or `-fw`.

**Then** — a difference on the *username* alone goes to enumeration below. A difference visible only on a correct password goes straight to the spraying section with that filter. No difference anywhere sends you to the logic-flaw and cookie sections, which do not need a filter at all.

## Enumerate valid usernames

**Why now** — you have a signal that distinguishes a real account from an invented one, and a list of candidate names. Turning that signal into a list of confirmed accounts halves the login problem: password guessing against known-good usernames is a different-sized job from guessing both halves at once.

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

**What you will see**

- **Found** — one row per name that produced the "already exists" response. These are confirmed accounts.
- **Empty** — three possibilities that lead different ways. The names in your wordlist may genuinely not exist here, which points at [[Custom-Wordlist-Attack-Chain]] to build names from the target's own people. Or the match string is wrong. Or the `Content-Type` header is missing and nothing was ever parsed. Check the second and third by hand before believing the first.
- **Error** — every request matching means your `-mr` string appears on the error page too; pick a more specific string. A run of 429s or a sudden switch to identical responses is rate limiting, and the results after that point are worthless.
- **Noise** — a signup form that accepts anything and reports success is not leaking; it is creating accounts. Watch for that, because it is noisy on a real engagement and it also means you can log in as a user you made rather than one you guessed.

**Then** — a list of confirmed usernames goes to the spraying section. Empty sends you to [[Custom-Wordlist-Attack-Chain]], which builds names from employee lists, emails and documents, and is the answer whenever a generic list fails against a specific organisation.

## Spray passwords against confirmed usernames

**Why now** — you hold real usernames. Now you spend them, and the constraint that shapes this step is lockout: a few common passwords against many users is safe, while many passwords against one user locks the account and ends the route. Spraying keeps the attempts per account low only while each round is one password; the round itself is still one attempt against every user in the list.

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

**What you will see**

- **Found** — one or two rows standing apart from the rest: a different size, a 302 to a dashboard, or a `Set-Cookie` carrying a session. Confirm by logging in manually before building anything on it.
- **Empty** — the honest reading is "not these passwords for these users". Before accepting it, check that the filter is not hiding the hit — rerun with the filter removed and eyeball ten rows to confirm they really are all failures. Then either widen the password list or accept that credentials are not the way in and move to the logic flaws below.
- **Error** — responses that suddenly become uniform partway through a run mean rate limiting or lockout engaged, and every result after that point is meaningless. A 403 arriving instantly for every request is a WAF that has recognised the tool, or a blanket block on your address.
- **Noise** — an application that returns 200 for both success and failure makes status filtering useless, which is why the baseline matters. Also: a "successful" response that is really a generic error page of a different size. Always confirm a hit by hand.

**Then** — working credentials go to the application, and then to every other service on the host, because reuse across a web login and SSH or SMB is common enough to be worth ten minutes. If the login is behind a per-request CSRF token, this whole approach needs a session-handling macro: [[Burp-Suite]]. If password guessing is closed, [[SQL-Injection]] bypasses the credential check entirely rather than solving it.

## Logic flaws — when the flow trusts the wrong copy of a value

**Why now** — guessing is slow or locked out, so stop attacking the credential and start attacking the process around it. Password reset is the standard weak point, because it deliberately grants access to somebody who cannot log in.

```bash
curl -i 'http://target.thm/customers/reset?email=robert%40target.thm' \
  -H 'Content-Type: application/x-www-form-urlencoded' \
  -d 'username=robert&email=attacker@collector.thm'
```

- the same parameter twice, once in the query and once in the body → this is the entire attack. PHP's `$_REQUEST` merges GET, POST and cookies, and the `variables_order` setting decides which wins. With the common `GPC` order, **POST overwrites GET**
- so the application identifies the account from the value it reads one way, and sends the reset link to the value it reads the other way. Both are "the email parameter" and they are not the same string
- `-i` → show the response headers. The tell is often a redirect or a `Set-Cookie`, not the body
- the generalisation is worth more than the example: wherever a value appears in two places, test which one wins. Query versus body, body versus cookie, a header versus a JSON field, the same key twice in one body (`email=a&email=b`), and the same key in a JSON object

**What you will see**

- **Found** — a reset mail arriving at your address for somebody else's account, or a response confirming the reset was sent while the target account was the one named in the query.
- **Empty** — a normal-looking "if that address exists, we have sent a link" response tells you nothing either way, by design. The only reliable read is whether the mail arrives, so you need a mailbox you control and the patience to wait for it.
- **Error** — a 500 after adding the duplicate parameter is interesting rather than bad: it means the two values collided somewhere in the code, which is the condition you are looking for.
- **Noise** — the application may accept the request and do nothing at all. Absence of an error is not evidence of success here; only the delivered mail is.

**Then** — a redirected reset link is account takeover; use it and move on to what that account can reach. Failure here does not close logic flaws generally — the same question applies to registration, to email change, to any multi-step flow — and the tool for exploring them is [[Burp-Suite]].

## Cookies that carry the decision

**Why now** — before assuming a session cookie is opaque, check whether it is. Some applications store the *answer* to "is this user an admin" on the client instead of a reference to a server-side session that holds it.

```bash
curl -s -b 'logged_in=true; admin=true; role=administrator' http://target.thm/account
```

- `-b` → send cookies. `-H 'Cookie: ...'` does the same; `-b` is less to type and does not conflict with other headers you may add
- read the real cookies first (`curl -i` on the login page, or the browser's storage panel) and set **the names the application actually uses**. Inventing names sets cookies nothing reads and produces a confident-looking negative
- decode before deciding it is opaque: a `.`-separated triple is a [[Security-Terms#^jwt|JWT]] (`base64 -d` the middle part and read the claims); a long hex string may be an [[Security-Terms#^md5|MD5]] of something guessable; base64 is base64 and often decodes to plain text
- a JWT with `"alg": "none"`, or one signed with a weak secret, is the modern version of this bug and is far more common than a literal `admin=true`

**What you will see**

- **Found** — content you should not be able to see: an admin panel, another user's data, a page that previously redirected to login.
- **Empty** — a redirect back to the login page means the server checks a real session, which closes this specific shortcut. That is a normal, well-built application; it says nothing about the other sections.
- **Error** — a 500 after tampering with a signed cookie means the application choked on your value rather than ignoring it, so something reads and parses that cookie. Compare against an untampered request before naming the mechanism; a verbose stack trace usually names it for you.
- **Noise** — a page that renders differently because of a *display* preference cookie (theme, language) is not an authorisation bypass. The test is whether you can reach data, not whether the page changed.

**Then** — a working bypass is access; carry it forward and enumerate what the elevated view exposes. A rejected tamper on a JWT is worth one more step — [[Hash-Cracking]] against the signature can recover a weak secret and turn a rejected token into a valid one.

## Reading the output

Every attack in this note is a differential, so the discipline is the same throughout: know what "no" looks like before you go looking for "yes". The failure mode that costs the most time is a filter chosen by habit rather than by measurement — `-fc 200` on an application that answers 200 for everything filters out every response there is, hit included, so a run that threw away the answer looks exactly like a run that found nothing.

The second thing that spans the note: these attacks interfere with each other. Enumeration creates accounts, spraying triggers lockouts, and a lockout invalidates the very signal your enumeration depended on. Run them in the order above, take the baseline before you make any noise, and if you must guess passwords, guess a few against many users rather than many against one.

## Next

- [[Burp-Suite]] — session-handling macro when a fresh CSRF token is required per request
- [[Custom-Wordlist-Attack-Chain]] — build the username and password lists these attacks consume
- [[SQL-Injection]] — an auth bypass (`' OR '1'='1'--`) skips the credential guessing entirely
- [[389-LDAP]] — the cheapest source of real usernames when a directory answers anonymously
- [[161-SNMP]] — usernames and process command lines from a host you have no shell on

## Gaps

- Nothing on multi-factor bypass: response manipulation, code brute force, and the "remember this device" cookie.
- JWT attacks are mentioned but not worked — `alg: none`, key confusion, and `kid` injection each need their own steps.
- No coverage of [[Security-Terms#^oauth|OAuth]] and [[Security-Terms#^sso|SSO]] flows, where the interesting bugs are in redirect URI handling.
- Nothing on registering an account deliberately and using it to explore authorisation, which is usually faster than attacking authentication at all.
