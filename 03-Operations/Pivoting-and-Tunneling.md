---
type: technique
platform: any
status: working
fluency: guided
source: thm
updated: 2026-09-08
---

# Pivoting and Tunneling

You have a shell on one host, and enumeration found a service that host can reach but your Kali box cannot — a database bound to `127.0.0.1`, or a second machine on an internal subnet. Pivoting turns the host you own into a relay so your own tools can reach that service directly.

The prerequisite is always the same: **find the internal listener first**. `ss -tlnp` on the target ([[Linux-Local-Enumeration]]) lists what is bound to loopback or an internal interface — those are the ports worth forwarding. Forwarding blind, before you know what is listening where, is how the guesswork starts.

Then pick the forward by **how much** you need to reach: one known port (`-L`), a whole subnet of unknown ports (`-D`), or a way back to yourself from a host that cannot dial out (`-R`).

## 1 — One known port: local forward

**Why now** — `ss -tlnp` showed a specific service bound to `127.0.0.1` — a PostgreSQL on 5432, a web admin panel on 8080 — and you have SSH credentials for the host. You know the port and you know the tool you want to point at it; a local forward is the shortest path from your Kali to that one service.

```bash
ssh -L 9999:127.0.0.1:5432 christine@TARGET_IP -N
```

- `-L 9999:127.0.0.1:5432` → bind port **9999 on your machine** and tunnel it to `127.0.0.1:5432` **as resolved on the target**. The `127.0.0.1` here is the target's own loopback, not yours — this is the whole point, since that address is exactly what your external scan could not see.
- `-N` → do not run a remote command, just hold the tunnel open. Without it you also get an interactive shell, which is fine until you type `exit` out of habit and drop the tunnel mid-tool. `-N` makes the session's only job the forward.
- `-f` → optional, background the tunnel after auth so it does not occupy the terminal. Easy to forget it is still running; `ps aux | grep ssh` finds it when a port is mysteriously taken.

**What you will see**

- **Found** — nothing. A working forward prints **no output at all**; the terminal just sits there (or returns to a prompt with `-f`). Silence is success here, which is disorienting the first time. Prove it from a second terminal: `psql -h 127.0.0.1 -p 9999`, `curl 127.0.0.1:9999` — you are now talking to the target's internal service through the tunnel.
- **Empty** — a local connection to port 9999 that is **refused** means the tunnel is up but the remote side has nothing listening on `127.0.0.1:5432` — wrong port, or the service is bound to a different internal address. Re-check `ss -tlnp` on the target for the exact bind.
- **Error** — `channel 2: open failed: administratively prohibited` means the SSH server forbids forwarding (`AllowTcpForwarding no` in its `sshd_config`); no forward type will help on this host, find another pivot. `bind: Address already in use` is your side — port 9999 is taken, so pick another local port. `Permission denied` at connect is the SSH login itself failing, not the tunnel.
- **Noise** — a forward established over a *dead* remote service looks identical to a healthy one until you actually connect through it. The `ssh` session being alive proves the login, not the destination; always test with a real client before trusting it.

**Then** — a reachable local port goes to the service note for that port: [[5432-PostgreSQL]], [[3306-MySQL]], [[1433-MSSQL]]. `administratively prohibited` closes the SSH route — look for a different credentialed host, or a non-SSH pivot (Gaps). A refused local port sends you back to `ss -tlnp` for the real bind address.

## 2 — A whole subnet: dynamic forward (SOCKS) + proxychains

**Why now** — the host you own sits on an internal network (`ip a` / `arp -a` shows a second subnet), and you do not yet know which hosts or ports live there. A single `-L` forward per port does not scale to a scan. A dynamic forward turns the SSH session into a **[[Security-Terms#^socks|SOCKS]] proxy** and lets you run whole tools — nmap, a browser, ffuf — against the internal range through it.

```bash
ssh -D 1080 christine@TARGET_IP -N
```

- `-D 1080` → open a SOCKS proxy on **your** port 1080; every connection sent to it is routed out of the target and resolved from the target's position on the network. One tunnel, every port, every reachable host.
- point tools at it through **proxychains**: add `socks5 127.0.0.1 1080` to `/etc/proxychains4.conf`, then prefix the tool: `proxychains nmap -sT -Pn 10.10.10.20`.
- `-sT` and `-Pn` are **not optional through a proxy** → SOCKS carries full TCP connections only. A SYN scan (`-sS`) sends raw packets the proxy cannot relay and returns all-filtered garbage; host discovery (`-Pn` disables it) relies on [[Security-Terms#^icmp|ICMP]] the proxy also drops, so without `-Pn` nmap decides every host is down and scans nothing.

**What you will see**

- **Found** — through proxychains, each connection prints an `...OK` line (`|S-chain|-<>-127.0.0.1:1080-<>-10.10.10.20:445-<>-OK`). Those `OK`s are your proof the route reaches the internal host. nmap then reports open ports on a machine your Kali cannot ping directly.
- **Empty** — proxychains lines all ending `<--denied` mean the SOCKS proxy could not reach that target: the host is down, the port is closed, or the owned host has no route to it either. Genuinely empty (every internal host denied) can mean you are not on the subnet you assumed — re-check `ip a` on the target.
- **Error** — `proxychains: could not connect to 127.0.0.1:1080` means the `-D` tunnel is not up (the `ssh` died, or you are pointing at the wrong port). `Connection refused` inside a chain that otherwise works is a normal closed-port result, not a proxy failure.
- **Noise** — proxychains is **slow**, and a slow scan looks like a hung one. Keep the port set small (`-p 22,80,443,445,3389`) and expect timeouts; a UDP scan through SOCKS does not work at all and its empty result is meaningless, not a finding.

**Then** — an internal host with open ports becomes your next target: scan it *through* the proxy, and once you have a shell on it the run sheet for its platform starts again from step 1. If it exposes a service you have credentials for, you may prefer a targeted `-L` forward (section 1) to that one port for speed. No reachable hosts at all closes this pivot.

## 3 — A host that cannot dial out: remote forward

**Why now** — you want a reverse shell or a file pull from an internal host, but that host's egress is filtered so it cannot reach your Kali directly — though it *can* reach the pivot host you already own. A remote forward opens a port **on the pivot** that tunnels back through your existing SSH session to a service on your machine.

```bash
ssh -R 8000:127.0.0.1:8000 christine@TARGET_IP -N
```

- `-R 8000:127.0.0.1:8000` → bind port 8000 **on the target**, tunnelling it back to `127.0.0.1:8000` **on your Kali**. The internal host now reaches your web server (or listener) by connecting to the pivot's port 8000, never touching your box directly.
- for the pivot to bind that port on all its interfaces so a *third* host can reach it, the SSH server needs `GatewayPorts yes`; with the default `no`, `-R` binds only the pivot's loopback, which is enough when the pivot itself is the client.
- direction is the trap → `-L` pulls a remote port to you, `-R` pushes a local port out to the remote. Swapping them produces a tunnel that binds cleanly and carries nothing.

**What you will see**

- **Found** — silence again, as with `-L`. Prove it from the target's shell: `curl 127.0.0.1:8000` on the pivot should reach the server running on your Kali, and your server's log shows the request arriving.
- **Empty** — the pivot connects to its own port 8000 but your service never logs it: the tunnel bound but your local service on 8000 is not actually running, or is bound to a different address than `127.0.0.1`.
- **Error** — `Warning: remote port forwarding failed for listen port 8000` means the port is already bound on the target, or `GatewayPorts`/permission forbids that bind — pick another remote port. Same `administratively prohibited` as section 1 if forwarding is off entirely.
- **Noise** — a remote forward whose local target service is down looks established because the bind succeeds; the failure only shows when traffic tries to traverse it.

**Then** — a working `-R` back to your listener lets the internal host connect for a reverse shell ([[Shells]]) or pull a file it could not otherwise fetch ([[File-Transfer]]). A failed bind means choose another remote port; forwarding-disabled means a different pivot.

## Reading the output

Two things true of every forward here.

**A tunnel that binds is not a tunnel that reaches.** `ssh -L/-R/-D` succeeding proves your SSH login and the local bind, nothing more. The service at the far end can be down, misbound, or behind another hop, and the tunnel looks identical either way. Never trust a forward until you have driven a real client through it and seen a real response — that test is the difference between a working pivot and an hour spent debugging a tool that was pointed at a dead port.

**The pivot is a position, not a destination.** Once a forward reaches an internal host, that host is a fresh target with its own version of every question in the [[Linux-Run-Sheet]] — run the sheet against it through the tunnel. Chained boxes are pivots stacked this way: each host you own is the vantage point from which the next one is finally reachable.

## Next

- [[Linux-Local-Enumeration]] — `ss -tlnp` finds the internal listeners worth forwarding
- [[5432-PostgreSQL]] — a worked example of a service reached only through a tunnel
- [[22-SSH]] — the SSH session the forwards ride on
- [[Linux-Run-Sheet]] — run against each internal host the pivot exposes

## Gaps

- No non-SSH pivots: `chisel`, `ligolo-ng`, `sshuttle`, and `socat` relays are the answer when you have a shell but no SSH credentials, and none are covered here.
- Nothing on Windows-side forwarding (`netsh interface portproxy`, or a plink `-R`).
- No `proxychains` vs `proxychains4` config-path detail, or the `dynamic_chain` vs `strict_chain` choice.
