# Burp Suite

The web proxy. This note covers the one Burp setup that a raw Intruder attack cannot do on its own: brute-forcing a login that defends itself with a fresh [[Security-Terms#^csrf|CSRF]] token and session cookie on every request.

## Session-handling macros — fresh CSRF token + cookie per request

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

Debug checklist when you get `403`s:

- the macro appears in the Macros list and points at the correct GET request;
- the Session Handling Rule's Tools Scope has `Intruder` checked;
- URL Scope actually includes the target (suite scope populated, or a correct custom URL);
- the parameter and cookie names typed into Rule Actions match the real field/cookie names **exactly** (case-sensitive);
- the `§` markers wrap only the intended payload positions, nothing else.
