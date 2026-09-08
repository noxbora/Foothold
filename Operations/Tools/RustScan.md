---
type: tool
platform: any
status: working
fluency: guided
source: reading
updated: 2026-08-31
---

# RustScan

Finds the open TCP ports in seconds, then hands them to nmap. It answers exactly one question — *which ports are open* — and the reason it appears before nmap in every write-up is that it removes the four-minute wait between having an IP and having something to work on. What is running on those ports is still nmap's answer, and RustScan's own default nmap run does not ask for it.

## Getting it onto Kali

**Why now** — you read `rustscan -a ...` in a write-up and your shell answered `command not found`. Kali packages it, so this is thirty seconds, not a build.

```bash
sudo apt install rustscan
```

- Kali ships it in `kali-rolling` (2.4.1 at the time of writing). Debian and Ubuntu do not package it at all, which is why every install guide online is a manual one.

Not on Kali, or the repo version is behind the release:

```bash
wget https://github.com/RustScan/RustScan/releases/latest/download/rustscan.deb.zip
```

```bash
unzip rustscan.deb.zip && sudo dpkg -i rustscan*.deb
```

- the `latest/download/` form → resolves to whatever the newest release is, so the URL does not rot the way a pinned tag does. The asset really is a `.zip` containing a `.deb`; downloading it and running `dpkg -i` straight on it fails with a format error.

**What you will see**

- **Found** — `rustscan --version` prints `rustscan 2.4.1` and the banner appears on the first run.
- **Empty** — `E: Unable to locate package rustscan` means your sources are not Kali's. That is the answer, not a missing update: `apt update` will not conjure it on Debian or Ubuntu, so go to the `.deb` above.
- **Error** — `dpkg: dependency problems prevent configuration` after the manual install is normal and fixed by `sudo apt -f install`, which pulls what the `.deb` assumed you had.
- **Noise** — most tutorials still describe version 2.1.1 through Docker or `cargo`. The flags changed since: timeout was `-T` and is now `-t`, and `--no-nmap` was removed in favour of `--scripts none`. A command copied from a 2021 post fails with an argument error rather than misbehaving quietly, which at least tells you which era you are reading.

**Then** — installed, go to the scan below. If you are working from a box you cannot install onto, this whole note is optional: everything here is a faster front end for [[Nmap]], never a replacement for it.

## The scan you run first

**Why now** — you have an IP and nothing else. The full `-p-` nmap sweep is the slowest thing standing between you and your first real decision, and the temptation to skip it is exactly how people miss the service on port 50000. RustScan collapses that wait: it finds the open ports in seconds and lets nmap fingerprint only the handful that are actually there.

```bash
rustscan -a TARGET_IP --ulimit 5000 -- -sC -sV -Pn -oN nmap-rustscan.txt
```

- `-a` → the target, and the only required flag. It takes a comma-separated list, a CIDR, a hostname, or the path to a newline-delimited file of any of those.
- `--` → **everything after this is passed to nmap verbatim, and this separator is the flag to get wrong.** Leave it out and RustScan's own parser meets `-sC`, does not recognise it, and exits. Run it bare with no `--` block at all and it is worse, because it succeeds: the nmap command RustScan builds by default is `nmap -vvv -p <ports> -4 <ip>` — no `-sV`, no `-sC`. You get a clean list of open ports and not one version string, which is precisely what the next step needs ([[Public-Exploit-Workflow]]).
- `-sV -sC` (nmap side) → version detection and the default script set, on the short port list RustScan just produced. This is the output you keep.
- `-Pn` (nmap side) → RustScan already proved the host completes TCP handshakes. Without `-Pn`, nmap runs its own host discovery first and a host that ignores ping is declared down and never scanned — an empty nmap section under a full list of open ports.
- `-oN` (nmap side) → save it. You will re-read this file a dozen times.
- `-u, --ulimit` → raises the open-file limit for this run. Kali's default is 1024 against a default batch size of 4500, so without it RustScan quietly lowers the batch to fit and prints a warning about it — the scan still runs, slower, and the warning reads like a failure the first time you meet it.
- `-b, --batch-size` (default 4500) → how many ports are in flight at once. **This is the accuracy dial, not only the speed one.** Over a lab VPN a high batch drops probes, and a dropped probe is a port that never appears.
- `-t, --timeout` (default 1500 ms) → how long a port gets to answer before it is written off as closed. Raise it on a slow link for the same reason.
- `--tries` (default 1) → one probe per port, so a single lost packet is a silently missing port. `--tries 2` is the cheap insurance on a flaky VPN.

**What you will see**

- **Found** — an `Open 10.10.11.5:22` line per port as they arrive, then `[~] Starting Script(s)` and nmap's output underneath. The `PORT STATE SERVICE VERSION` table is the artifact; the `Open` lines are only the fast preview.
- **Empty** — `Looks like I didn't find any open ports for <ip>. This is usually caused by a high batch size.` Take that literally. It is the tool saying it went too fast, not the host saying it is shut. Re-run with `-b 500 -t 3000 --tries 2` before you believe a single word of it, and only then treat the host as filtered — which is an [[Nmap]] question, with `-Pn` and a UDP pass.
- **Error** — `File limit is lower than default batch size. Consider upping with --ulimit.` is a warning and the scan continues at a reduced batch. `ERROR. Failed to set ulimit value.` means the value you asked for is above the hard limit, so run it under `sudo` or ask for less. If nmap is not on `$PATH`, the port scan completes and only the script stage fails — you still have your ports.
- **Noise** — a firewall or a tarpit that answers every connection makes all 65535 ports look open. If the list is absurd, it is one device lying and nothing in it is real. And RustScan confirms only that a TCP connection completed: it never tells you what is listening, so a port here is a coordinate, not a service.

**Then** — the nmap table underneath goes where [[Nmap]] says it goes: an HTTP port to [[Web-Server-Checks]], a version string to [[Public-Exploit-Workflow]], and a port with a note of its own to that note — [[21-FTP]], [[22-SSH]], [[445-SMB]]. An empty result that survives the slow re-run goes to [[Stuck-Checklist]].

## Reading the output

The division of labour is the whole value of the tool, and it is also the trap. RustScan answers *which ports*; nmap answers *what is on them*. A RustScan `Open` line means one TCP handshake completed and nothing else — never carry it into a finding as a service name, and never let it end the enumeration, because service detection, script output and the filtered-versus-closed distinction all live on the nmap side.

It is also loud in a way its speed hides. Every port is a full connect, so the target logs the lot, all at once, from one address. There is no quiet mode and no half-open option — if the engagement cares about detection, this is the wrong front end and [[Nmap]] with `-sS` and a rate limit is the right one.

## Rarely — worth one command, not worth a step

**Why now** — the scan above is the one you run on every box. These four exist for a specific reason each, and each is one command.

```bash
rustscan -a TARGET_IP -g
```

- `-g, --greppable` → ports only, one line, no nmap. This is the form you pipe into something else or paste into an `nmap -p` of your own.

```bash
rustscan -a TARGET_IP --udp
```

- `--udp` → UDP mode. It finds only UDP ports that send a response, so an empty result here is close to meaningless — the honest UDP sweep is still `nmap -sU`, and it is slow because UDP is.

```bash
rustscan -a targets.txt -x 10.10.10.1,10.10.10.254 -b 500
```

- `-a` with a file path → one target per line; the same flag, no special syntax.
- `-x, --exclude-addresses` → keep the gateway and the broadcast host out of a range scan. `-e, --exclude-ports` does the same for ports you already know about.

```bash
rustscan -a TARGET_IP -r 1-1000 --scripts none
```

- `-r, --range` → a port range instead of all 65535; `-p 80,443,8080` takes a list, and `--top` takes nmap's top 1000.
- `--scripts none` → stop after the port scan and run nothing. This is what replaced `--no-nmap`, and it is the flag you want when you are timing the sweep itself rather than working a box.

**What you will see**

- **Found** — the same `Open` lines, and with `-g` nothing but the ports.
- **Empty** — for `--udp`, expected and uninformative. For the rest it means what the main scan's Empty means: check the batch size before the host.
- **Error** — an unrecognised flag almost always means you are reading documentation for an older version; `rustscan --help` on your own build is the only source that matches your binary.
- **Noise** — a range scan across a lab subnet reports the gateway and the VPN endpoint as live hosts with open ports. They are infrastructure, not targets, which is what `-x` is for.

**Then** — anything found here rejoins the main flow: hand the ports to [[Nmap]] for versions.

## Next

- [[Nmap]] — where the port list becomes a service map, and where filtered-versus-closed is read properly
- [[Web-Server-Checks]] — the first move on any HTTP port the sweep returned
- [[Stuck-Checklist]] — a sweep that stays empty on a host you are sure is alive

## Gaps

- Nothing on `--scripts custom` and `~/.rustscan_scripts.toml`, the engine that runs your own Lua, Python or shell script against each open port instead of nmap.
- No config-file section: `~/.rustscan.toml` can hold your ulimit, batch size and default nmap arguments so the long command above becomes `rustscan -a TARGET_IP`.
- `--scan-order random` is undocumented here; it exists to spread the scan across the port space rather than walking it in order, which matters against rate-limiting devices and is untested in this vault.
