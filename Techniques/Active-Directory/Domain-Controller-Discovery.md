---
type: technique
platform: windows
status: working
fluency: guided
source: thm
updated: 2026-09-24
---

# Domain Controller Discovery — from a subnet to a domain name

A domain does not announce itself. You are handed a range, a tunnel into it and nothing else, and somewhere inside that range one machine answers for the whole domain: every ticket, every password check, every directory query goes through it. This note gets you from the range to the two facts every other note in this folder opens with — the controller's address, and the domain's own name.

## Sweeping the range for anything alive

**Why now** — you hold a range and no idea which addresses are in use. Port-scanning 254 addresses before you know which four exist spends an hour to learn what one sweep answers in seconds.

```bash
fping -agq 10.10.10.0/24
```

- `-g` → the one that is easy to omit, and it is not cosmetic. It is the flag that makes the argument a **range** rather than a single name. Leave it off and the tool hands the whole string to the resolver and prints `10.10.10.0/24: Name or service not known`, which reads as a malformed address and sends you off to check your notes for the right subnet.
- `-a` → print only the addresses that answered. Without it every address in the range gets a line, and the handful that matter sit buried in 250 lines of `is unreachable`.
- `-q` → drops the per-probe commentary, so what is left on the screen is a list you can paste.

**What you will see**

- **Found** — one address per line and nothing else. On a scoped range that is often four: the gateway, the tunnel endpoint, and the two machines you were actually given.
- **Empty** — no output at all. This is the outcome to distrust, because it does not mean the range is empty; it means nothing in it answered an echo request. Go straight to the second command before you accept it.
- **Error** — the name-not-known line above is the missing `-g`. A complaint about opening the socket means the binary lacks the raw-socket capability on your machine, and `sudo` in front of it is the fix.
- **Noise** — the gateway and your own end of the tunnel answer every time and are not targets. Strike them off before the list goes anywhere, or you will spend a scan on the client's router.

> [!important] "Not alive" here means "did not answer an echo request"
> This sweep asks one question, over [[Security-Terms#^icmp|ICMP]], and a Windows host with its firewall at the default setting does not answer it. A domain controller that silently drops ping is invisible to the command above and perfectly reachable on 445 a minute later. Read the result as the hosts you have **confirmed**, never as the hosts that **exist** — the sweep below is the one that finds the quiet ones.

```bash
sudo nmap -sn -PE -PS445,88,3389 -n 10.10.10.0/24 -oG - | awk '/Status: Up/{print $2}' > hosts.txt
```

- `-PS445,88,3389` → the one that is easy to omit, and the whole reason this run finds what the first one missed. It opens a connection attempt against ports Windows keeps open, and a host that ignores ping still has to answer on a port it is listening on. Drop this flag and you have run the first command again with a different program.
- `-sn` → discovery only, no port scan. The port list above is used as a knock, not as a scan.
- `-n` → no reverse name lookups. The name server on an unknown range is the target's, it is slow, and you do not want to ask it 254 questions before you know what it is.
- `-oG -` → grepable output to the screen. It exists so the `awk` can work: the normal output format spreads an address across a sentence, while this one puts it in a fixed field.
- `sudo` → without it, raw packets are not available and the probes quietly become full connections, which is slower and leaves a completed session in the target's logs instead of a half-open one.

**What you will see**

- **Found** — a file with one address per line. `wc -l hosts.txt` is worth running, because a silent pipeline failure also produces a file.
- **Empty** — a zero-length file means nothing answered ICMP **or** those three ports. Widen the knock (`-PS22,80,443,445,3389`) before concluding the range is dead, and if you have a specific address you were told about, scan it with `-Pn` and ignore discovery entirely.
- **Error** — `Failed to open device eth0` means nmap picked the wrong interface: over a tunnel you name it yourself with `-e tun0`. An `awk` that prints nothing while addresses scroll past means the grepable flag was dropped, not that the hosts vanished.
- **Noise** — the gateway and your tunnel endpoint land in this file too, and unlike you, `awk` cannot tell they are yours. Open the file and delete them now, while you still remember which they were.

**Then** — the file goes straight into the port scan below. Two addresses in it and no more is the normal shape of a scoped range; ten means you are looking at a real network and the next scan wants narrowing.

## Which of these hosts is the controller

**Why now** — you have a short list of live hosts and no way to tell which one runs the domain. Nothing labels it, but a controller is the only machine in a domain that **must** offer the ticket service, and that turns the question into a single port.

```bash
nmap -p 88,135,139,389,445,464,3268 -sV -sC -iL hosts.txt -oN dc-scan.txt
```

- `-sV` → the one that is easy to omit, and omitting it throws away everything this scan is for. Without it you get `389/tcp open ldap` and stop; with it the same line carries the domain's own name, the directory site, the Windows build and the workgroup. You came for those strings, not for the word `open`.
- `-p 88,...` → the port list is chosen around one discriminator. 88 is [[Security-Terms#^kerberos|Kerberos]] and 464 is the password-change service that rides with it; both run on a controller and on nothing else in the domain. 3268 is the global catalog, which is also controller-only. 135, 139 and 445 are on every Windows machine alive and decide nothing on their own — they are here to describe the hosts that are **not** the controller.
- `-sC` → the default scripts, which on these ports add two facts worth having early: the controller's own clock, and whether message signing is required on 445.
- `-iL hosts.txt` → read targets from the file rather than typing them. It also means you scan exactly what the sweep confirmed, with no chance of a typo aiming a scan outside your scope.
- `-oN dc-scan.txt` → keep the output. You will read these banners again in three hours, and re-running the scan to get them back costs more than the file does.

**What you will see**

- **Found** — one host with 88 open. That host is the controller, and the rest of its line is the domain: `Domain: corp.local`, `workgroup: CORP`, an OS string like `Windows Server 2019 Datacenter 17763`, and from the Kerberos line a `server time` you should compare against your own clock right now.
- **Empty** — every port filtered on a host that answered the sweep means a host firewall, not an absent service. On a host you reached by TCP knock and cannot scan, the knock told you which port is open; scan that one with `-Pn`.
- **Error** — no output at all and an instant return usually means `hosts.txt` is empty or holds a stray blank line, and nmap scanned nothing. A refusal to run as an unprivileged user applies to the scan types, not to this one; this command needs no root.
- **Noise** — `tcpwrapped` on 636 is not a service you have found: the handshake completed and the far side hung up before speaking. And a host showing 135, 139 and 445 with **no** 88 is not a failure of the scan, it is the answer — that machine has no ticket service, so it is either a domain member or a standalone box, and the workgroup string on its own 445 line is what tells you which. Either way it is a target in its own right.

> [!important] The domain string nmap prints is not always the domain name
> Some versions print it with a trailing zero and dot — `Domain: corp.local0.` — and the domain is `corp.local`. Copy the string exactly as it appeared and every tool that takes a realm fails with an unknown-domain error, which reads as a wrong password or a broken install. Check it against the naming context a [[389-LDAP]] root query returns before you trust it.

**Then** — the controller's address and the domain name go into your own resolver before anything else runs, because Kerberos authenticates to **names** and will not look at an address:

```bash
echo '10.10.10.10 dc.corp.local corp.local' | sudo tee -a /etc/hosts
```

From there, [[AD-Username-Enumeration]] turns the domain name into a user list, [[445-SMB]] asks the controller what it will show a nameless session, and [[389-LDAP]] asks the directory the same question in its own language. A domain member with no 88 goes to [[445-SMB]] as well — it is usually less hardened than the controller and it holds domain credentials all the same.

## Rarely — worth one command, not worth a step

**Why now** — the seven ports above named the controller and you now want the rest of the surface, or the short scan came back looking too clean for a real network.

```bash
sudo nmap -sS -p- -T3 -iL hosts.txt -oN full-ports.txt
```

- `-p-` → all 65535 ports rather than nmap's default top 1000. This is the flag paying for the run's whole cost, and it is the one that finds the management service, the database and the web application nobody mentioned.
- `-sS` → a half-open scan, which needs root. Without `sudo` nmap falls back to completing every connection, so the scan takes longer and each port you touch records a finished session rather than an abandoned one.
- `-T3` → nmap's own default, so writing it changes nothing about the run. It is in the command as a statement that you decided not to go faster, which is a decision worth making deliberately on a client's network.
- the price is real: a full port scan of one host is minutes, not seconds, and a range of them is long enough that you should start it and go and read the banners you already have.

**What you will see**

- **Found** — ports the short list could not have: 5985 for remote management, 1433 for a database, 3389 for the desktop service, 9389 for the directory's web endpoint. Each is a note in this vault and a different way in.
- **Empty** — a host with nothing beyond the ports you already knew is a real answer and a useful one: that machine's whole attack surface is the domain services, so there is no side door to look for.
- **Error** — a scan that dies partway leaves you not knowing how far it got. The output file is written as it goes, so read the file rather than re-running.
- **Noise** — high-numbered ports in the 49152 and above band are the dynamic range that [[Security-Terms#^rpc|RPC]] hands out. They are not findings, they are where the services on 135 actually live.

**Then** — anything new goes to its own service note, and an unfamiliar version string goes to [[Public-Exploit-Workflow]].

## Reading the output

The finding in this note is often an **absence**. A controller is identified by a port that other machines do not have, so the host with 135, 139 and 445 and nothing else has told you what it is not, and its workgroup string finishes the sentence: the domain's own name there means a member, anything else means a machine that never joined. Writing down "no 88" is as much a result as writing down the controller's address, and it is what stops you spending an afternoon asking a workstation for the domain's user list.

The second thing is that everything downstream of here consumes the **name**, not the address. Kerberos will not authenticate to an address, the realm has to be spelled the way the domain spells it, and the single most common way to lose an hour in this folder is to carry a domain name forward that you copied out of a scan without checking it. Two minutes with the resolver line and a root query settle it permanently.

And the discipline the tooling cannot enforce: the gateway and the tunnel endpoint are in your sweep output and are not in your scope. They answer every probe you send, they look exactly like targets, and they belong to the people who gave you the range.

## Next

- [[AD-Username-Enumeration]] — the domain name and the controller address are its two inputs
- [[445-SMB]] — what the controller will show a session with no credential attached
- [[389-LDAP]] — the directory's own answer to "what is this domain called"

## Gaps

- Nothing on UDP. Kerberos, the directory and the name service all answer over UDP, and a controller whose TCP is filtered from where you sit can still be found there; a TCP-only sweep calls that host dead.
- No coverage of a second domain or a trust relationship, so this note silently assumes the range holds exactly one domain.
- The member host is defined only by what it lacks; there is nothing here on reading a workstation's role, its logged-on user, or why it is often the better spray target.
- Nothing on what these sweeps look like from the defender's console, which is what would decide whether to slow them down.
