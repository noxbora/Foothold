# RustScan

Finds the open TCP ports in seconds, then hands them to nmap. It answers exactly one question — *which ports are open* — and the reason it appears before nmap in every write-up is that it removes the four-minute wait between having an IP and having something to work on. What is running on those ports is still nmap's answer, and RustScan's own default nmap run does not ask for it.

## Getting it onto Kali

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

## The scan you run first

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
