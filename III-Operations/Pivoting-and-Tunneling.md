# Pivoting and Tunneling

You have a shell on one host, and enumeration found a service that host can reach but your Kali box cannot — a database bound to `127.0.0.1`, or a second machine on an internal subnet. Pivoting turns the host you own into a relay so your own tools can reach that service directly.

The prerequisite is always the same: **find the internal listener first**. `ss -tlnp` on the target ([[Linux-Local-Enumeration]]) lists what is bound to loopback or an internal interface — those are the ports worth forwarding. Forwarding blind, before you know what is listening where, is how the guesswork starts.

Then pick the forward by **how much** you need to reach: one known port (`-L`), a whole subnet of unknown ports (`-D`), or a way back to yourself from a host that cannot dial out (`-R`).

## 1 — One known port: local forward

```bash
ssh -L 9999:127.0.0.1:5432 christine@TARGET_IP -N
```

- `-L 9999:127.0.0.1:5432` → bind port **9999 on your machine** and tunnel it to `127.0.0.1:5432` **as resolved on the target**. The `127.0.0.1` here is the target's own loopback, not yours — this is the whole point, since that address is exactly what your external scan could not see.
- `-N` → do not run a remote command, just hold the tunnel open. Without it you also get an interactive shell, which is fine until you type `exit` out of habit and drop the tunnel mid-tool. `-N` makes the session's only job the forward.
- `-f` → optional, background the tunnel after auth so it does not occupy the terminal. Easy to forget it is still running; `ps aux | grep ssh` finds it when a port is mysteriously taken.

## 2 — A whole subnet: dynamic forward (SOCKS) + proxychains

```bash
ssh -D 1080 christine@TARGET_IP -N
```

- `-D 1080` → open a SOCKS proxy on **your** port 1080; every connection sent to it is routed out of the target and resolved from the target's position on the network. One tunnel, every port, every reachable host.
- point tools at it through **proxychains**: add `socks5 127.0.0.1 1080` to `/etc/proxychains4.conf`, then prefix the tool: `proxychains nmap -sT -Pn 10.10.10.20`.
- `-sT` and `-Pn` are **not optional through a proxy** → SOCKS carries full TCP connections only. A SYN scan (`-sS`) sends raw packets the proxy cannot relay and returns all-filtered garbage; host discovery (`-Pn` disables it) relies on [[Security-Terms#^icmp|ICMP]] the proxy also drops, so without `-Pn` nmap decides every host is down and scans nothing.

## 3 — A host that cannot dial out: remote forward

```bash
ssh -R 8000:127.0.0.1:8000 christine@TARGET_IP -N
```

- `-R 8000:127.0.0.1:8000` → bind port 8000 **on the target**, tunnelling it back to `127.0.0.1:8000` **on your Kali**. The internal host now reaches your web server (or listener) by connecting to the pivot's port 8000, never touching your box directly.
- for the pivot to bind that port on all its interfaces so a *third* host can reach it, the SSH server needs `GatewayPorts yes`; with the default `no`, `-R` binds only the pivot's loopback, which is enough when the pivot itself is the client.
- direction is the trap → `-L` pulls a remote port to you, `-R` pushes a local port out to the remote. Swapping them produces a tunnel that binds cleanly and carries nothing.
