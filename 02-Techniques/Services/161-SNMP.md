---
type: service
platform: any
status: working
fluency: guided
source: reading
updated: 2026-09-03
---

# 161 — SNMP

A management protocol that answers questions about a device: its users, its running processes, its installed software, its listening ports, its network interfaces. Version 1 and version 2c authenticate with a single shared string that is very often left at the factory value, and the answers arrive as a flat tree of numbered entries.

Reach for this note when `161` shows open. It runs over `udp`, so a default `nmap` scan will not find it — its absence from your scan output is not evidence.

## 1 — Is the community string still a default

**Why now** — everything on this page depends on one string. Guessing it is one command and takes seconds, and until it is answered nothing else about the service is worth reading.

```bash
onesixtyone -c /usr/share/wordlists/seclists/Discovery/SNMP/common-snmp-community-strings.txt TARGET
```

- The string is a password with no username attached. `public` grants read and `private` historically grants write, and both survive in production far more often than anyone would guess.
- `onesixtyone` sends one packet per candidate over `udp` and does not retry, so run it twice before believing a negative on a slow or filtered path.
- Version 3 uses real usernames and passwords instead. If everything fails and the host is modern, that is the likely reason and it ends this note.

**What you will see**

- **Found** — a line echoing the target address and the string that worked, usually with the system description beside it.
- **Empty** — nothing at all. Over `udp` this genuinely means either no service, a filtered port, or no matching string, and those three are indistinguishable from here. Confirm the port separately with `nmap -sU -p161` before crossing the service off.
- **Error** — a missing wordlist path is the usual failure. The `seclists` layout moves between distributions; find the file rather than assuming the path.
- **Noise** — a device answering on `public` with nothing but a model name is a real answer and a dead end. Not every reachable service holds anything.

**Then** — a working string goes to section 2. Nothing found goes back to [[Nmap]] for a proper `udp` confirmation, and then to the next service on the list.

## 2 — Reading only the branches that carry answers

**Why now** — you have a valid string. A full walk of the tree returns thousands of lines on a real host, which is exactly the dump this vault refuses to hand you. Each command below asks the tree one question instead.

```bash
snmpwalk -v2c -c public TARGET 1.3.6.1.4.1.77.1.2.25
```

```bash
snmpwalk -v2c -c public TARGET 1.3.6.1.2.1.25.4.2.1.2
```

```bash
snmpwalk -v2c -c public TARGET 1.3.6.1.2.1.25.6.3.1.2
```

```bash
snmpwalk -v2c -c public TARGET 1.3.6.1.2.1.6.13.1.3
```

- Those four numbers are [[Security-Terms#^oid|OID]] paths and each names one branch: user accounts, running processes, installed software, and local listening ports. Walking `1.3.6.1` instead returns all of them plus everything else, which is how a useful service turns into an unreadable screen.
- The process branch is the valuable one, because it prints full command lines. Credentials passed as arguments appear here in clear text and appear nowhere else on the host that you can read.
- A branch that does not exist returns `No Such Object available on this agent`. That is a shape answer about the device, not a failure of your string.
- Expect single figures to low tens of lines from each of these. Hundreds means you walked a parent branch by mistake.

**What you will see**

- **Found** — usernames you did not have, a process line containing a password or a token, software with a version worth searching, a port bound to loopback that your scan could never see.
- **Empty** — a branch that returns nothing while another branch answers is genuine: that device does not publish that table. An empty result from every branch means the string is read-limited rather than wrong.
- **Error** — `Timeout: No Response` after the string already worked usually means rate limiting on the agent. Slow down rather than concluding the service died.
- **Noise** — the process table lists the agent itself and every kernel thread. The line you want has a path and arguments, not a bare name in brackets.

**Then** — usernames go to [[Authentication-Attacks]] and to any login you have found. A credential in a process line goes to the service it belongs to. A loopback port goes to [[Pivoting-and-Tunneling]]. Software versions go to [[Public-Exploit-Workflow]].

## Rarely — worth one command, not worth a step

**Why now** — the branches above came back thin, or the string you found was `private` rather than `public`.

```bash
snmp-check TARGET -c public
```

```bash
snmpwalk -v2c -c public TARGET 1.3.6.1.2.1.4.22.1.2
```

- `snmp-check` formats the common branches into readable sections in one run. It is here rather than in section 2 because it hides which branch each fact came from, and that mapping is what you are trying to learn.
- The last branch is the device's address table: every other host it has recently talked to. On a jump box that is a free map of the internal network.
- A `private` string means writes are possible, which on some devices extends to changing configuration or fetching it over `tftp`. Powerful, loud, and rarely necessary.

**What you will see**

- **Found** — a formatted report, or a list of internal addresses the target has spoken to.
- **Empty** — the normal answer. These are lottery tickets, not steps.
- **Error** — `snmp-check` missing from the box is common; it ships in some distributions and not others.
- **Noise** — the address table includes broadcast and multicast entries and the target's own gateway. Only the specific internal addresses are interesting.

**Then** — internal addresses go to [[Pivoting-and-Tunneling]]. Everything empty means the service gave what it had and the next port on the list is a better use of the hour.

## Reading the output

Every answer here arrives as a numbered path followed by a value, and the numbers are the same on every device in the world. That is the point of the design and it is why this note gives paths rather than names: a name needs a translation file installed locally, a number needs nothing.

The second thing to hold on to is that this service is a **read** of a host you have no shell on. Everything it hands you belongs to some other note — a username, a version, a port, a password. Nothing here is exploited in place.

## Next

- [[Authentication-Attacks]] — where the usernames go
- [[Public-Exploit-Workflow]] — where the software versions go
- [[Pivoting-and-Tunneling]] — where a loopback port or an internal address goes

## Gaps

- Nothing on version 3, which is what a maintained host will be running.
- No coverage of writing with a `private` string, or of the configuration-fetch trick that follows from it.
- The `nmap` scripts for this service are not mentioned and they cover some of section 2 in one command.
