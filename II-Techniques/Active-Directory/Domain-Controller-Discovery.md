# Domain Controller Discovery — from a subnet to a domain name

A domain does not announce itself. You are handed a range, a tunnel into it and nothing else, and somewhere inside that range one machine answers for the whole domain: every ticket, every password check, every directory query goes through it. This note gets you from the range to the two facts every other note in this folder opens with — the controller's address, and the domain's own name.

## Sweeping the range for anything alive

```bash
fping -agq 10.10.10.0/24
```

- `-g` → the one that is easy to omit, and it is not cosmetic. It is the flag that makes the argument a **range** rather than a single name. Leave it off and the tool hands the whole string to the resolver and prints `10.10.10.0/24: Name or service not known`, which reads as a malformed address and sends you off to check your notes for the right subnet.
- `-a` → print only the addresses that answered. Without it every address in the range gets a line, and the handful that matter sit buried in 250 lines of `is unreachable`.
- `-q` → drops the per-probe commentary, so what is left on the screen is a list you can paste.

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

## Which of these hosts is the controller

```bash
nmap -p 88,135,139,389,445,464,3268 -sV -sC -iL hosts.txt -oN dc-scan.txt
```

- `-sV` → the one that is easy to omit, and omitting it throws away everything this scan is for. Without it you get `389/tcp open ldap` and stop; with it the same line carries the domain's own name, the directory site, the Windows build and the workgroup. You came for those strings, not for the word `open`.
- `-p 88,...` → the port list is chosen around one discriminator. 88 is [[Security-Terms#^kerberos|Kerberos]] and 464 is the password-change service that rides with it; both run on a controller and on nothing else in the domain. 3268 is the global catalog, which is also controller-only. 135, 139 and 445 are on every Windows machine alive and decide nothing on their own — they are here to describe the hosts that are **not** the controller.
- `-sC` → the default scripts, which on these ports add two facts worth having early: the controller's own clock, and whether message signing is required on 445.
- `-iL hosts.txt` → read targets from the file rather than typing them. It also means you scan exactly what the sweep confirmed, with no chance of a typo aiming a scan outside your scope.
- `-oN dc-scan.txt` → keep the output. You will read these banners again in three hours, and re-running the scan to get them back costs more than the file does.

> [!important] The domain string nmap prints is not always the domain name
> Some versions print it with a trailing zero and dot — `Domain: corp.local0.` — and the domain is `corp.local`. Copy the string exactly as it appeared and every tool that takes a realm fails with an unknown-domain error, which reads as a wrong password or a broken install. Check it against the naming context a [[389-LDAP]] root query returns before you trust it.

```bash
echo '10.10.10.10 dc.corp.local corp.local' | sudo tee -a /etc/hosts
```

From there, [[AD-Username-Enumeration]] turns the domain name into a user list, [[445-SMB]] asks the controller what it will show a nameless session, and [[389-LDAP]] asks the directory the same question in its own language. A domain member with no 88 goes to [[445-SMB]] as well — it is usually less hardened than the controller and it holds domain credentials all the same.
