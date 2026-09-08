---
type: technique
platform: windows
status: working
fluency: guided
source: thm
updated: 2026-08-31
---

# Vulnerable / Unpatched Software

The vector that has nothing to do with permissions or tokens: a third-party program installed on the host has a known bug, and that bug hands you code execution as a higher-privileged account. Organisations patch Windows on a schedule and forget the software running on top of it, so this is often the freshest attack surface on an otherwise hardened box.

Two moves: **find what is installed and at what version**, then **find a public exploit for that version**. The second move is [[Public-Exploit-Workflow]] — this note is the first.

## What is installed, and at what version

**Why now** — you have a shell and the standard privilege checks came back thin. Before you reach for a kernel CVE you ask what non-Microsoft code is running, because that is the software the admin patches last. You are hoping for a named product with a specific version string you can drop into a CVE search.

```powershell
Get-CimInstance Win32_Product | Where-Object { $_.Vendor -notlike "Microsoft*" } | Select-Object Name,Version,Vendor
```

- Reads the **installer database** — every product registered through Windows Installer ([[Security-Terms#^msi|MSI]]).
- The `Vendor` filter is the whole point: Microsoft's own redistributables and runtime packages make up most of the list and none of them are what you are hunting. What is left is the software somebody chose to install, which is the software nobody patched.
- No leading `*` here, deliberately: `Vendor` reads `Microsoft Corporation`, so the string starts with the word and `-notlike "Microsoft*"` is correct. Adding a leading star would also drop vendors whose name merely contains it.
- Slow; it can take a minute to walk the catalogue. That is normal, not a hang — do not kill it and conclude the command is broken.

- The `cmd` fallback for the same question is the `wmic` line in [[Windows-Run-Sheet#Rarely — worth one command, not worth a step|the run sheet]]; `wmic` is deprecated and absent on newer builds, where it fails with `'wmic' is not recognized` rather than an empty list.

**What you will see**

- **Found** — a third-party product with a version to the digit: `Druva inSync 6.6.3`, `PDF24 Creator 11.15.1`, a backup agent, a database, an antivirus. A vendor name that is not Microsoft is the whole point; write down name **and** version exactly.
- **Empty** — a list of nothing but Microsoft redistributables, or a genuinely short list. This is **not** a clean host — it is the MSI-only view, and the next section is where the rest hides. Empty here sends you onward, it does not close the vector.
- **Error** — `Get-CimInstance : ... Provider load failure` or a hang on `Win32_Product` is a known cost: enumerating that class triggers an MSI consistency check per product. Fall back to the registry query below, which is faster and reads more.
- **Noise** — `Microsoft Visual C++ ... Redistributable`, `.NET`, `Windows SDK` entries are stock and almost never the path. Skip to the non-Microsoft vendor lines.

**Then** — a named product with a version goes straight to [[Public-Exploit-Workflow]]. A thin or Microsoft-only list is not the end: go to the next section and enumerate by hand, because `wmic` is structurally blind to anything installed outside MSI.

## What `wmic` cannot see

**Why now** — the MSI list was short, and you know it only sees products installed through Windows Installer. A program dropped in by a zip, a portable `.exe`, or anything bundled with a service will not appear there. This looks where the installer database does not.

```cmd
dir "C:\Program Files" "C:\Program Files (x86)"
```

```cmd
reg query HKLM\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall /s /f DisplayName
```

```powershell
Get-CimInstance Win32_Process | Where-Object { $_.ExecutablePath -notlike "*\Windows\*" -and $_.ExecutablePath } | Select-Object Name,ProcessId,ExecutablePath
```

```cmd
sc query state= all | findstr /i "SERVICE_NAME"
```

- `reg query ... /s /f DisplayName` → walks the uninstall keys, where installers record themselves whether or not they used MSI. `/s` recurses; without it you read one key and miss everything.
- The process query filters on **path**, not on the account: almost everything on a Windows host runs as SYSTEM, so that is not a discriminator. `C:\Windows\` is. `-and $_.ExecutablePath` drops the system processes whose path is unreadable — without it they all pass, because `$null` is not like anything.
- `sc query state= all` → the space after `state=` is **mandatory**. `state=all` with no space is misparsed and returns only active services, hiding exactly the stopped third-party service you are hunting for.
- `tasklist /v` → the `/v` adds the window title and the running-as user, which is what turns a process name into "this is running as a service account".

**What you will see**

- **Found** — a vendor folder under `Program Files` with no matching MSI entry, an uninstall key naming a product and its `DisplayVersion`, or — the highest-value tell — a **running service or process** belonging to third-party software. Software that ships a service is software running with that service account's privileges, which is what you want to abuse.
- **Empty** — genuinely nothing outside Microsoft in any of the four views is a real answer, and it closes this vector: the escalation is a misconfiguration or a token, not a bad version. Go back to [[Windows-Privilege-Escalation]].
- **Error** — `Access is denied` on parts of the `reg query` walk is normal; it continues past keys it cannot read. The denial marks a hive some other account controls, not a stop.
- **Noise** — `Common Files`, `Windows Defender`, `Windows Media Player`, `Internet Explorer` and `WindowsApps` under `Program Files` are stock. In `sc query`, the dozens of `SERVICE_NAME` lines beginning with a Windows component name are the OS itself — filter to the odd one out.

**Then** — a version string goes to [[Public-Exploit-Workflow]]. A running third-party service is the strongest lead: carry it into the next section to find out what it listens on and as whom, because a local privileged service is the recurring shape of this whole bug class.

## The pattern the case studies teach

Version-to-exploit is the mechanical half. The half worth internalising is the *shape* of the bug that keeps recurring in this class:

A local helper service runs as **SYSTEM** and listens on a **[[Security-Terms#^loopback|loopback]]** port (`127.0.0.1`) — invisible from the outside, reachable by any local user. It exposes functions (often over **RPC**) that were meant to run a handful of bundled binaries, and a caller can ask it to run one. The whole privilege boundary then rests on **one input-validation check** inside that service. Two ways that check tends to be too weak:

- **No check at all** — the "run a binary" function runs *any* command you hand it, as SYSTEM.
- **A prefix check that trusts the string, not the resolved path** — the service confirms your command *starts with* `C:\Program Files\Vendor\...`, then Windows resolves the path and walks it wherever it actually leads. `C:\Program Files\Vendor\..\..\Windows\System32\cmd.exe` passes the string test and lands in `System32`. Same **directory traversal** you use in [[File-Inclusion]], same root cause as the `%00` truncation there: the guard inspects the path one way, the OS interprets it another.

So the enumeration question is not only "is this version vulnerable" but "**what is it listening on, and as whom**":

```cmd
netstat -ano | findstr LISTENING
```

```cmd
tasklist /fi "PID eq <pid>"
```

**Why now** — your software list named a third-party service and you want to know whether it is the local-privileged-listener shape above. This ties a listening port to the process behind it, and the process to a product you can search for a CVE on — before you ever fire an exploit.

- `-a` all connections, `-n` numeric, `-o` owning [[Security-Terms#^pid|PID]]. Drop `-o` and you lose the PID, which is the only thing that connects the port back to a process — the whole point of the command.
- `-n` → without it, `netstat` tries to resolve every address and hangs on a host with no route out, so the listing never prints.
- `tasklist /fi "PID eq <pid>"` → the filter must be quoted as one argument; `PID eq 1234` unquoted is read as three arguments and errors.

**What you will see**

- **Found** — a port bound to `127.0.0.1` (not `0.0.0.0`) on an odd high number, whose PID resolves to a third-party product running as SYSTEM. That combination — local + privileged + accepting input — is the thing to search for a CVE on.
- **Empty** — no loopback-only listeners, or every listener resolves to a Windows component. Real, and it says this particular product is not the listening-service shape; it may still have a client-side or file-parsing CVE, so the version search in [[Public-Exploit-Workflow]] is still worth running.
- **Error** — a blank owner or `Access is denied` from `tasklist` against a PID you do not own is a permission limit, not proof the process is gone: the port is real and something privileged is behind it.
- **Noise** — `0.0.0.0:135` (RPC endpoint mapper), `0.0.0.0:445` (SMB), `0.0.0.0:5985` ([[Security-Terms#^winrm|WinRM]]), and `127.0.0.1` ports owned by `svchost` are stock Windows. The interesting line is the one whose PID is *not* `svchost`, `System`, or `lsass`.

**Then** — a loopback-only privileged listener goes to [[Public-Exploit-Workflow]] to find the matching CVE, then to [[Windows-Run-Sheet#3 — What runs with more privilege than me|run sheet step 3]] for how it fits the ranked method. Nothing privileged listening sends you back to the version search on the software itself, or on to the other vectors in [[Windows-Privilege-Escalation]].

## Reading the output

Two failures of interpretation cost the most time in this vector.

**A loopback-only listener is a positive finding, not something to dismiss.** "Only listens on localhost" reads as *safe* from the network and *reachable* from your foothold — those are the same fact seen from two sides. Anything local, privileged, and accepting input is worth the CVE search even though your external nmap never saw it.

**Zero public exploits for a version is not proof of safety.** The exploit may live on GitHub rather than Exploit-DB, or the CVE may be public with no released [[Security-Terms#^poc|PoC]]. Search the product name plus version on the web, not only `searchsploit`. This is the same "zero hits is a result, not a wall" point from [[Public-Exploit-Workflow]].

> [!warning] Read the exploit before you run it
> Public privesc exploits for named products often ship as a script that fires packets or spawns a process as SYSTEM. Confirm the target version matches to the digit and read what the payload actually sends — the verify/modify steps in [[Public-Exploit-Workflow]] are not optional here just because the exploit has a friendly write-up.

## Next

- [[Public-Exploit-Workflow]] — turn the version string into a working exploit
- [[Windows-Privilege-Escalation]] — the other vectors, and how this one ranks against them
- [[Windows-Run-Sheet#3 — What runs with more privilege than me|run sheet step 3]] — the enumeration step that surfaces a bound-to-loopback privileged service

## Gaps

- No worked example of talking to a raw RPC / custom TCP service by hand (crafting the request packets). This note covers *finding* the target; hand-driving a bespoke protocol is exploit- and product-specific and lives in the public exploit, not here.
- Nothing on driver-level vulnerabilities (a vulnerable signed driver loaded by a privileged process) — same "unpatched third-party code" family, different tooling.
- Metasploit's `post/windows/gather` software-enumeration modules are not covered; this is the manual path.
