---
type: tool
platform: web
status: working
fluency: guided
source: thm
updated: 2026-08-30
---

# Burp Suite

The web proxy. This note covers the one Burp setup that a raw Intruder attack cannot do on its own: brute-forcing a login that defends itself with a fresh [[Security-Terms#^csrf|CSRF]] token and session cookie on every request.

## Session-handling macros — fresh CSRF token + cookie per request

**Why now** — you have a login form to brute-force, you have username and password lists, and a plain Intruder run returns nothing but `403`s. The reason is the defence: the form issues a new hidden CSRF token (a `loginToken`) and a new session cookie on **every page load**, so each guess needs a valid, current token/cookie pair that Intruder's static requests do not carry. Intruder's own "recursive grep" extraction cannot help, because the login response is a redirect with no token in its body to scrape. A session-handling macro solves it: before each attempt it runs a GET to the login page, pulls the fresh token and cookie, and injects them into the request.

Set-up, in order:

1. Capture the login request; send it to Intruder.
2. Set the attack type to `Pitchfork` (one username paired with one password per request, both lists advancing together).
3. Mark **only** `username` and `password` as payload positions with `§`. Do **not** mark the CSRF token or the session cookie — the macro owns those, and marking them makes Intruder overwrite the fresh values with stale payload text.
4. Load the username and password wordlists in the Payloads tab.
5. `Settings > Sessions > Macros > Add`. Select a GET request to the login page from history (or trigger one in the browser first so it exists). Name and save the macro.
6. `Settings > Sessions > Session Handling Rules > Add`.
   - Details tab: give it a description.
   - Scope tab: under "Tools Scope" select only `Intruder`; under "URL Scope" use suite scope or add the target URL manually.
   - Back in Details, under "Rule Actions", `Add > Run a Macro >` select the macro from step 5.
7. Still in Rule Actions, restrict what the macro overwrites:
   - "Update only the following parameters and headers" -> add `loginToken` (or whatever the CSRF field is named).
   - "Update only the following cookies" -> add `session` (or whatever the session cookie is named).
8. Confirm, then run the Intruder attack.

- the marker that is easy to misplace is `§` → wrapping the wrong field boundary (a `§` on the wrong side of an `=`) silently breaks the whole request structure, and every response comes back wrong with no error naming the cause. Place the pair around **only** the payload value.
- the setting that is easy to leave off is the **Tools Scope** restriction to `Intruder` → without it the rule either never fires during the attack or fires against every tool, and the symptom is a uniform wall of `403`s that looks like the macro failing when the rule simply never ran.

**What you will see**

- **Found** — a uniform column of `302` (redirect) responses across the attack, and then **one row whose length differs** from the rest. That distinct length is the valid credential: a good login redirects somewhere different (a dashboard) than a rejected one (back to the form).
- **Empty** — every response the same `302` with identical length, and no outlier, means the run completed but no pair in your lists was valid — a real negative for these wordlists, not a broken macro. Widen the list before re-checking the setup.
- **Error** — a wall of `403` is the macro **not** injecting fresh values. Work the debug checklist below in order; it is almost always one of the four scope/name mismatches. A `200` everywhere (never `302`) usually means the form posts to a different endpoint than you captured, or the payload markers broke the request body.
- **Noise** — a `302` that redirects straight **back to the login page** is a *failed* login, not a success — read the `Location`, not just the code. And Burp's `Cookie Jar` (same Sessions tab) is a separate global feature: enabling `Intruder` there conflicts with this macro and produces intermittent, confusing results. Leave it out.

Debug checklist when you get `403`s:

- the macro appears in the Macros list and points at the correct GET request;
- the Session Handling Rule's Tools Scope has `Intruder` checked;
- URL Scope actually includes the target (suite scope populated, or a correct custom URL);
- the parameter and cookie names typed into Rule Actions match the real field/cookie names **exactly** (case-sensitive);
- the `§` markers wrap only the intended payload positions, nothing else.

**Then** — a valid credential (the outlier length among the `302`s) is spent by refreshing the login page and logging in manually with it; from there the attack surface is [[Authentication-Attacks]]. Persistent `403`s after the checklist means the token/cookie names are wrong — re-capture a fresh GET and read the actual field names out of its response. A different anti-automation defence (rate limiting, a [[Security-Terms#^captcha|CAPTCHA]]) is outside what a macro fixes.

## Reading the output

The success signal for this setup is a uniform field of `302`s with a single outlier length — the outlier is the credential, everything else is a rejected guess. A `403` field means the macro is not injecting a fresh token/cookie pair, and the fix is always in the four scope/name settings on the debug checklist, not in the payloads. Read redirect *targets*, not just codes: a `302` back to `/login` is a failure wearing a success code.

## Next

- [[Authentication-Attacks]] — the credential-stuffing and logic-flaw attacks this macro enables
- [[XSS]] — Burp's Repeater/Intruder for tampering the requests that carry a payload

## Gaps

- No Repeater or Decoder workflow — this note is only the session-handling macro.
- Nothing on Intruder attack types beyond Pitchfork (Sniper, Cluster Bomb) or on the throttling the Community edition imposes on Intruder.
- No macro variant for a token delivered in a response **header** rather than a hidden form field.
