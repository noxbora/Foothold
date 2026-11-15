# Nmap

A flag reference, linked from [[Pentest-Workflow#Phase 1 — Recon & Enumeration|Phase 1 — Recon & Enumeration]] rather than stored inside it. The catalog below is deep, but you run one thing on every box — the section immediately below — and reach for the rest only when a default scan is being lied to by a firewall.

## The scan you run first

```bash
sudo nmap -p- --min-rate 1000 -T4 TARGET_IP -oN nmap-allports.txt
```

```bash
sudo nmap -p 22,80,8080 -sC -sV -oA nmap/deep TARGET_IP
```

- `-p-` → scan **all 65535 ports**. Nmap's default is the top 1000, so a service on 8080, 8443, or any high port is simply invisible — and that is exactly where a lab's intended foothold often hides. Omit this and the box looks empty while the answer sits on port 50000. Run `-p-` wide first, then re-scan only the open ports deeply (second line).
- `--min-rate 1000 -T4` → the speed that makes an all-ports scan finish in the time you have. Without it a full sweep can take many minutes, which is why people cancel it and fall back to the 1000-port default — straight into the trap above.
- `-sV` → version detection. The **load-bearing output** of the whole tool: `Apache 2.4.49`, not just "http". That version string is what you paste into an exploit search ([[Public-Exploit-Workflow]]).
- `-sC` → the default safe script set, cheap extra enumeration (titles, anon-FTP, SMB shares) on the ports you already know are open.
- `-oN` / `-oA` → save the output. You will re-read a scan a dozen times; `-oA` writes all three formats at once so you never re-run a five-minute sweep to see one line.
- `sudo` → a SYN scan (`-sS`, the default when root) needs privilege. Without it nmap silently drops to a `-sT` connect scan, which is slower and noisier — it still works, but knowing which you ran matters when reading filtered results.

## ICMP-based host discovery

Nmap doesn't rely only on [[Security-Terms#^arp|ARP]] or TCP for host discovery — it can send different [[Security-Terms#^icmp|ICMP]] message types to figure out if a host is alive.

**ICMP Echo Request** `nmap -PE -sn <target>` Sends a classic ICMP Echo Request (like standard `ping`). Simple and effective, but often blocked by firewalls that drop ICMP.

**ICMP Timestamp Request** `nmap -PP -sn <target>` Sends an ICMP Timestamp Request instead of Echo. Useful when Echo Requests are filtered — some hosts still reply to Timestamp even if they ignore Echo.

**ICMP Address Mask Request** `nmap -PM -sn <target>` Sends an ICMP Address Mask Request. Legacy method, rarely responded to by modern systems, but occasionally bypasses filters that only block Echo/Timestamp.

**Disable port scan, only do discovery** `nmap -sn <target>` Skips port scanning entirely — just performs host discovery (by default uses ARP on local network, ICMP/TCP/UDP probes otherwise). Combine with -PE, -PP, -PM etc. to control which discovery method is used.

**Combining discovery methods** `nmap -PE -PP -PM -sn <target>` Sends multiple ICMP probe types together. A host only needs to respond to ONE of them to be marked as up — this increases discovery accuracy against hosts/firewalls that block some ICMP types but not others.

**TCP SYN Ping** `nmap -PS<port> -sn <target>` Sends a TCP packet with the SYN flag set to the specified port(s). If the host responds with SYN/ACK (port open) or RST (port closed), it's marked as up. Default port if none specified: 80.

**TCP ACK Ping** `nmap -PA<port> -sn <target>` Sends a TCP packet with the ACK flag set. Hosts typically respond with RST since there's no matching connection — this RST confirms the host is alive. Useful against firewalls that block SYN but not ACK.

**UDP Ping** `nmap -PU<port> -sn <target>` Sends a UDP packet to the specified port (default 40125, usually closed). If the host is up, it typically replies with an ICMP Port Unreachable message — that response confirms the host is alive.

## Host Discovery — Response Interpretation

Each probe type has its own logic for what counts as a host being "up." Nmap infers this from the type of response it receives (or doesn't).

**ICMP-based probes (-PE, -PP, -PM)**

- Reply received (Echo Reply / Timestamp Reply / Address Mask Reply) → host is **up**
- No reply (timeout) → host is marked **down** — but this can be a false negative if ICMP is filtered rather than the host actually being offline.

**TCP SYN Ping (-PS)**

- SYN/ACK received → port open, host is **up**
- RST received → port closed, but host is **up** (it responded, so it's alive)
- No reply → host marked **down** (or packet silently dropped by a firewall)

**TCP ACK Ping (-PA)**

- RST received → host is **up** (unexpected ACK triggers a RST from a live system)
- No reply → host marked **down** (or dropped)

**UDP Ping (-PU)**

- ICMP Port Unreachable received → host is **up** (the UDP packet was processed, port was closed, so this error was generated)
- No reply → host marked **down** (unreliable due to UDP's nature)
- (Rare) actual UDP service response → host is **up**, though this isn't the expected mechanism

**Key limitation**: a "down" result can mean two very different things — the host is genuinely offline, or the host is up but a firewall silently dropped the probe. Nmap can't distinguish between these; it only reports "no response." Combining multiple probe types (`-PE -PS80 -PA80 -PU`) reduces the chance of false negatives from any single blocked method.

- `-n` no dns lookup
- `-R` reverse-DNS lookup for all hosts

## Advanced Port Scanning — Flag Manipulation & Evasion

### Uncommon TCP Flag Scans

These scans set TCP flags in unexpected combinations to provoke different responses than a standard SYN scan. Useful against filtered ports or for evading simple firewall/[[Security-Terms#^ids|IDS]] rules.

**TCP Null Scan** `sudo nmap -sN <target>` Sends a packet with no flags set at all. Provokes a response from **closed** ports (RST); open ports typically stay silent.

**TCP FIN Scan** `sudo nmap -sF <target>` Sends a packet with only the FIN flag set. Same logic as Null scan — **closed** ports respond with RST, open ports don't respond. Can bypass firewalls that only filter SYN packets.

**TCP Xmas Scan** `sudo nmap -sX <target>` Sends a packet with URG, PSH, and FIN flags set together (lights up like a "Christmas tree"). Same behavior — provokes a response from **closed** ports only.

**TCP Maimon Scan** `sudo nmap -sM <target>` Sends a packet with FIN and ACK flags set. On some BSD-derived systems, closed ports answer with RST while open ports may stay silent; results are commonly `open|filtered` and require corroboration.

**TCP ACK Scan** `sudo nmap -sA <target>` Sends a packet with only ACK set. Provokes a response (RST) from **both open and closed** ports — mainly used to map firewall rulesets, not to determine open/closed state directly.

**TCP Window Scan** `sudo nmap -sW <target>` Same as ACK scan, but inspects the TCP window size in the RST response to infer open vs closed on certain systems. Provokes a response from **both open and closed** ports.

**Custom Flag Scan** `sudo nmap --scanflags URGACKPSHRSTSYNFIN <target>` Lets you manually define exactly which flags to set, instead of using a preset scan type. Useful for crafting scans that mimic unusual traffic or test specific firewall behavior.

> **Key takeaway**: Null, FIN, and Xmas scans get a reply from **closed** ports only. ACK and Window scans generally get a reply from reachable open or closed ports; Maimon relies on a narrower stack-specific distinction. None of these reliably confirm "open" the way a SYN scan does — they work by elimination/inference.

### Spoofing & Evasion

**Spoofed Source IP** `sudo nmap -S SPOOFED_IP <target>` Sends packets with a forged source IP instead of your real one. Mainly useful for obscuring the scan origin — but note replies won't come back to you unless you control the spoofed IP or are on the same segment.

**Spoofed MAC Address** `--spoof-mac SPOOFED_MAC` Forges the source MAC address on local network scans. Can also accept `0` for a random MAC, or a vendor name (e.g. `Cisco`) to generate a matching MAC prefix.

**Decoy Scan** `nmap -D DECOY_IP1,DECOY_IP2,ME <target>` Makes the scan appear to originate from multiple decoy IPs alongside your real one, so a target/IDS sees several "attackers" and can't easily tell which one is real. `ME` marks your real IP's position in the decoy list.

**Idle (Zombie) Scan** `sudo nmap -sI ZOMBIE_IP <target>` Uses a third-party "zombie" host's IP sequence number behavior to scan a target without ever sending packets from your real IP — the zombie's responses (or lack thereof) are used to infer port state indirectly.

### Fragmentation & Packet Crafting

**Fragment into 8-byte packets** `-f` Splits the TCP header across multiple IP fragments (8 bytes each) to slip past some packet-filtering firewalls/IDS that don't reassemble fragments before inspection.

**Fragment into 16-byte packets** `-ff` Same idea, larger fragment size.

**Custom source port** `--source-port PORT_NUM` Forces the scan to originate from a specific source port — useful for bypassing firewall rules that trust traffic from certain ports (e.g. 53, 20).

**Padding with random data** `--data-length NUM` Appends random data to reach a specified packet length, to avoid signature-based detection that expects Nmap's default (typically empty) packet size.

### Output & Diagnostics

**Explain conclusions** `--reason` Shows exactly why Nmap classified a port as open/closed/filtered (e.g. which flag combination triggered the verdict).

**Verbosity** `-v` verbose / `-vv` very verbose — more detail on scan progress and results.

**Debugging** `-d` debug / `-dd` more detailed debug output — useful when troubleshooting why a scan behaves unexpectedly.

## Service, OS & Output Options

### Service & OS Detection

**Service/Version Detection** `nmap -sV <target>` Determines the specific service and version running on open ports (e.g. not just "port 80 open" but "Apache 2.4.41").

**Light Version Detection** `nmap -sV --version-light <target>` Only tries the most likely probes (2 probes) for faster, less intrusive version detection — trades accuracy for speed.

**Aggressive Version Detection** `nmap -sV --version-all <target>` Tries every available probe (9 probes) against the port to maximize accuracy in identifying the service/version — slower, more traffic generated.

**OS Detection** `nmap -O <target>` Attempts to fingerprint the target's operating system based on how its TCP/IP stack responds to various probes.

**Traceroute** `nmap --traceroute <target>` Maps the network path (hops) to the target, useful for understanding network topology alongside a scan.

### Scripting Engine (NSE)

**Run Specific Scripts** `nmap --script=SCRIPTS <target>` Runs one or more Nmap Scripting Engine ([[Security-Terms#^nse|NSE]]) scripts against the target — used for anything from vulnerability detection to deeper enumeration (e.g. `--script=vuln`, `--script=smb-enum-shares`).

**Run Default Scripts** `nmap -sC <target>` or `nmap --script=default <target>` Runs Nmap's default script set — a safe, general-purpose collection covering basic enumeration for common services.

### Combined Aggressive Scan

**All-in-One** `nmap -A <target>` Equivalent to running `-sV -O -sC --traceroute` together — version detection, OS detection, default scripts, and traceroute in a single flag. Convenient but noisy; not ideal for stealth-focused engagements.

### Output Formats

**Normal Format** `nmap -oN output.txt <target>` Saves output in the standard human-readable format you'd normally see on screen.

**Grepable Format** `nmap -oG output.gnmap <target>` Saves output in a format designed to be easily parsed with `grep`/`awk`/shell scripting — useful for quick automation.

**XML Format** `nmap -oX output.xml <target>` Saves output in XML — useful for feeding into other tools (e.g. importing into reporting frameworks or other parsers).

- **All Formats at Once** `nmap -oA output_basename <target>` Saves the same scan results simultaneously in normal, XML, and grepable formats (creates `output_basename.nmap`, `.xml`, `.gnmap`).
