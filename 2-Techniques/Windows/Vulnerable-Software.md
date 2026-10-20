# Vulnerable / Unpatched Software

The vector that has nothing to do with permissions or tokens: a third-party program installed on the host has a known bug, and that bug hands you code execution as a higher-privileged account. Organisations patch Windows on a schedule and forget the software running on top of it, so this is often the freshest attack surface on an otherwise hardened box.

Two moves: **find what is installed and at what version**, then **find a public exploit for that version**. The second move is [[Public-Exploit-Workflow]] — this note is the first.

## What is installed, and at what version

```powershell
Get-CimInstance Win32_Product | Where-Object { $_.Vendor -notlike "Microsoft*" } | Select-Object Name,Version,Vendor
```

- Reads the **installer database** — every product registered through Windows Installer ([[Security-Terms#^msi|MSI]]).
- The `Vendor` filter is the whole point: Microsoft's own redistributables and runtime packages make up most of the list and none of them are what you are hunting. What is left is the software somebody chose to install, which is the software nobody patched.
- No leading `*` here, deliberately: `Vendor` reads `Microsoft Corporation`, so the string starts with the word and `-notlike "Microsoft*"` is correct. Adding a leading star would also drop vendors whose name merely contains it.
- Slow; it can take a minute to walk the catalogue. That is normal, not a hang — do not kill it and conclude the command is broken.

- The `cmd` fallback for the same question is the `wmic` line in [[Windows-Run-Sheet#Rarely — worth one command, not worth a step|the run sheet]]; `wmic` is deprecated and absent on newer builds, where it fails with `'wmic' is not recognized` rather than an empty list.

## What `wmic` cannot see

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

- `-a` all connections, `-n` numeric, `-o` owning [[Security-Terms#^pid|PID]]. Drop `-o` and you lose the PID, which is the only thing that connects the port back to a process — the whole point of the command.
- `-n` → without it, `netstat` tries to resolve every address and hangs on a host with no route out, so the listing never prints.
- `tasklist /fi "PID eq <pid>"` → the filter must be quoted as one argument; `PID eq 1234` unquoted is read as three arguments and errors.
