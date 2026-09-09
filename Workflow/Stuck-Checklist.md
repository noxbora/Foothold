---
type: workflow
platform: any
status: working
fluency: guided
source: lab
updated: 2026-09-04
---

# Stuck Checklist

The things forgotten most often. Read top to bottom when a box has gone quiet — the point is to be reminded of something, not to be taught it, so **every line ends in a note to open**. An entry that names a thing to try without naming where to go is not usable at one in the morning; follow the link when the reminder alone is not enough.

If nothing here fires, the problem is method rather than memory: [[Linux-Run-Sheet]] or [[Windows-Run-Sheet]] for a host you already hold, [[Pentest-Workflow#Phase 1 — Recon & Enumeration|Phase 1]] for one you do not.

## When the output lies

The section to read first, because these failures do not look like failures — they look like answers, and you walk away from the box believing them.

- **Nothing came back.** That has two meanings and they are opposite: nothing is there, or you are **not permitted to see it**. On Linux they print identically. `crontab -l` lists your jobs only; root's lives in `/var/spool/cron/crontabs/`, mode `600`. Empty means switch method, not "no job exists" → [[PSPY]] to watch jobs fire live, then [[Linux-Run-Sheet#5b — When you cannot see the schedule|run sheet 5b]] for the writable file the job touches
- `find / -writable -type f -not -user $(whoami) 2>/dev/null` is the sharpest version of that search: files you can **write** and do not **own**, regardless of what runs them → [[PSPY]]
- **`2>/dev/null` hid the answer.** It also hides the `Permission denied` that would have told you which of the two empties you got. Drop it once, on a narrow path, before believing a blank result → [[Linux-Run-Sheet]]
- **The credential grep found documentation.** Pages of `password = changeme`, `<your-password>` and `foobar` are a manual, not a secret. `/etc/login.defs`, `/etc/ssh/sshd_config` and everything under `/etc/fwupd/` ship that way on a clean host. Demand an assigned value, drop comment lines, and search application directories before `/etc` → [[Config-File-Looting]] · [[Linux-Run-Sheet#6 — Credentials lying around|run sheet 6]]
- **You found a password and no username.** That is half a credential; the other half is `/etc/passwd`, the file's owner, and the service it configures → [[Linux-Run-Sheet#8 — Stop and connect|run sheet step 8]]
- **The SUID sweep came back clean.** Check the argument: `-perm -4000` with the leading dash, which means "these bits are set". `-perm 4000` matches only files whose permissions are *exactly* that, finds nothing, and reads as a hardened host → [[Linux-SUID-Abuse]]
- **`ss` shows a blank process column.** A permission limit, not an empty result — the port is real and something is listening on it → [[Linux-Local-Enumeration]]
- **A downloaded tool throws a syntax error full of HTML.** You saved a GitHub *page*, not the raw file. `file` it before every run → [[File-Transfer]]
- **The message on screen has an obvious meaning.** That is the warning sign, not the answer: `Permission denied` on a SUID binary is a `nosuid` mount, `Status: Exhausted` is the wordlist and not the hash, and `STATUS_PASSWORD_MUST_CHANGE` means the password is right. Check the string before you act on it → [[Failure-Messages]]

## Scanning

- Did you run `-p-`? The default scans 1000 ports and the answer is often outside them → [[Nmap]]
- UDP is unscanned unless you asked. Don't run a full `-sU`, take the top ports: `sudo nmap -sU --top-ports 20 <ip>`. The usual suspects: SNMP 161, DNS 53, [[Security-Terms#^tftp|TFTP]] 69, IKE 500 → [[Nmap]]
- On UDP, *no response* is reported as `open|filtered` — that is not a closed port, it is an unanswered question → [[Nmap]]
- Some scan types need raw packets and therefore `sudo`; without it Nmap silently downgrades to a different scan and you get different results → [[Nmap]]
- `rustscan -a <ip> -r 1-65535` first, then hand the open ports to Nmap for service detection. Without a `--` block RustScan runs nmap with no `-sV`, so you get ports and no versions → [[RustScan]]
- Re-scan after you get a foothold. Services bound to `127.0.0.1` were never visible from outside → [[Linux-Local-Enumeration]], then [[Pivoting-and-Tunneling]]

## Web

- Read the page source and the comments. Then read the JavaScript — endpoints, API paths and keys live there, not in the rendered page → [[Content-Discovery]]
- A blank page or a `403` is not an empty path. Brute force *underneath* it (`/wp-content/themes/`) rather than moving on → [[Content-Discovery]]
- `robots.txt`, `sitemap.xml`, `/.git/`, `/backup/`, `/admin/` → [[Content-Discovery]]
- Backup, temp and version-control leftovers hand you plaintext source where the live path executes it: `config.php.bak`, `config.php~`, `.git/config` → [[Source-Code-Disclosure]]
- Type the scheme yourself (`http://` / `https://`). Browsers auto-upgrade and quietly change what you are testing — send the request by hand and see it as it is sent → [[Curl-and-Wget]] · [[Burp-Suite]]
- Check the certificate's Common Name and SAN entries — they leak hostnames you have not added yet → [[Virtual-Host-Discovery]]
- Generic wordlist came up empty? Build one from the target's own vocabulary → [[Custom-Wordlist-Attack-Chain]]
- Add the hostname to your hosts file, and remember the target has one too: `/etc/hosts` on Linux, `C:\Windows\System32\drivers\etc\hosts` on Windows → [[Virtual-Host-Discovery]]

## Credentials

- Try the defaults, and try the credential you already have somewhere else. Reuse is the single most productive assumption in this vault → [[Authentication-Attacks]]
- Shell history: `~/.bash_history` on Linux → [[Config-File-Looting]]; [[Security-Terms#^psreadline|PSReadLine]] on Windows → [[PowerShell-History]] · [[Windows-Credential-Harvesting]]
- Config files, web roots, `.env`, connection strings → [[Config-File-Looting]]
- What you found is a hash, not a password — that is one step, not a dead end → [[Hash-Cracking]]

## On a Linux shell

- `ls -la`, everywhere. Dotfiles, `.ssh/`, `.bash_history`, backups — the interesting files are the hidden ones → [[Linux-Local-Enumeration]]
- `sudo -l` and the SUID sweep, before anything clever → [[Linux-Sudo-Abuse]] · [[Linux-SUID-Abuse]]
- `uname -a` for the kernel version — but treat kernel exploits as a last resort → [[Linux-Privilege-Escalation]]
- Is the thing you uploaded actually executable? `chmod +x` → [[File-Transfer]]
- Is anything running that no file reveals? → [[PSPY]]
- You became a second user and did not start over. Each account sees a different filesystem; run the whole sweep again as them → [[Linux-Run-Sheet]]

## On a Windows shell

- `whoami /priv` first — it decides which token path is even open → [[Windows-Privilege-Escalation]]
- Credential sweep before any exploit work → [[Windows-Credential-Harvesting]]
- Fighting the keyboard in an RDP window means you are working in the wrong place → [[3389-RDP]] · [[Shells#Windows — ConPtyShell|ConPtyShell]]

## Tooling

- [[Nikto]] for a single web application; a full vulnerability scanner for a whole host
- Caught a shell that behaves badly? It is a missing PTY, not a missing payload → [[Shells#Shell Stabilisation — TTY Upgrade|Shell Stabilisation]]
- The exploit ran and nothing happened. Before hunting a second exploit, re-read the values you were supposed to edit → [[Public-Exploit-Workflow]]

## Next

- [[Linux-Run-Sheet]] · [[Windows-Run-Sheet]] — when the reminder list runs out and you need the ordered sweep
- [[Linux-Local-Enumeration]] · [[Windows-Privilege-Escalation]] — the two sweeps most of these lines are shortcuts into
- [[START-HERE]] — when you cannot tell which of the above you even need
