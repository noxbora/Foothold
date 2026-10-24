# Failure Messages — the ones that point at the wrong cause

Every note in this vault carries its own outcomes block, and that is where a message gets its full treatment. This note is the index for one narrow class of them: messages whose plain reading sends you to the wrong place.

Admission rule, so this file never becomes a second copy of the vault: an entry belongs here only if believing the message costs you time. `Connection refused` on a port nmap already called closed is honest, and stays out. `Permission denied` on a binary that is visibly SUID is not, and comes in.

How to use it: you have a string on screen. Search it here, read the one line, then open the note behind it. The sections are named after the wrong conclusion rather than after the tool, because the wrong conclusion is the thing you are about to act on.

## "You do not have permission"

- `553 Could not create file.` — FTP, immediately after `put`. One argument was given, so the client sent the whole local path as the remote filename and the server refused a name it cannot create. A filename error wearing a permission error's clothes. Retry as `put <local> <remote>` before concluding the share is read-only. → [[21-FTP]]
- `Permission denied` running a binary that `ls -l` shows as `-rwsr-sr-x` — the bit is set and not in effect, which means the filesystem is mounted `nosuid`. The permissions you are staring at are correct and irrelevant. `mount | grep <the path>` settles it. → [[NFS-No-Root-Squash]], [[Linux-SUID-Abuse]]
- `Permission denied` on `/var/spool/cron/crontabs/` — normal on every healthy system, because the directory is mode 700 by design. This is a permission answer, not an absence answer, and it does not mean there are no jobs. → [[Cron-Jobs]], [[PSPY]]
- `Permission denied` running a script that is present and executable — a `noexec` mount, usually on `/tmp`. Hand the file to an interpreter instead of executing it, as in `sh /tmp/linpeas.sh`. → [[Linux-Automated-Enumeration]], [[PSPY]]
- `failed to apply fstab options` — you are not root. It has nothing to do with `/etc/fstab`, and reading it as a mount-configuration problem costs an hour. → [[NFS-No-Root-Squash]]
- `Permissions 0644 for 'id_rsa' are too open` — about the file on your own machine, not about the target. `chmod 600 id_rsa` and try again; the key has not been judged yet. → [[Config-File-Looting]]
- `Permission denied (publickey)` — the server never looked at your password, because password authentication is off in its `sshd_config`. A password you trust is still unproven. `(publickey,password)` is the variant that means it was tried and refused. → [[22-SSH]]
- `ERROR: ... Read-only file system` on an rsync push — the module is declared `read only = yes` in `rsyncd.conf`. The remote filesystem is fine, the daemon is configured. `Permission denied` on one file during a pull is that file not being world-readable. → [[873-rsync]]
- `Permission denied` lines flooding a `find` you thought you had silenced — the `2>/dev/null` landed on the pipeline instead of on `find` itself. → [[Linux-Local-Enumeration]], [[Linux-SUID-Abuse]]
- `ERROR: The system was unable to find the specified registry key or value.` — three situations collapse into one sentence: the key is absent, the value is absent, or your token cannot read it. Query the key and filter the output rather than naming the value with `/v`, which is what keeps them apart. → [[Windows-Credential-Harvesting]], [[Windows-Privilege-Escalation]]
- `chmod: changing permissions: Operation not permitted` on a mounted export — `no_root_squash` is not in effect on the path you actually mounted, one step earlier than the `ls -l` that would have shown it. → [[NFS-No-Root-Squash]]

## "There is nothing here"

- `No such file or directory` on a script named by a live cron entry — a finding, not a failure. The entry is orphaned, and if the command is a bare name with no slash in it you own it outright. → [[Cron-Jobs]], [[Linux-PATH-Abuse]]
- `Note: Host seems down. If it is really up ... try -Pn`, or `0 hosts up` — the host is not answering ping, which most Windows and firewalled hosts do not. Nothing has been scanned yet. → [[Nmap]]
- `All 65535 scanned ports are in ignored states` — not a clean host. Your probes are being dropped, so "empty" here means "blocked", which is the opposite next move. → [[Nmap]]
- `clnt_create: RPC: Program not registered` — the portmapper answered, so something is running; NFSv3 is simply not behind it. Mount with `-o vers=4`. A hang instead of this message is port 111 filtered. → [[2049-NFS]], [[NFS-No-Root-Squash]]
- `Status: Exhausted` from hashcat — this list did not contain it. It is not a verdict on the hash. Confirm the mode first, then a bigger list, then rules, then a mask. → [[Hash-Cracking]]
- `No password hashes left to crack (see FAQ)` from john — the opposite of a failure: everything in the file is already cracked and cached, and `john --show hash.txt` prints it. Reading it as a failure and re-running is a loop this message reliably causes. → [[Hash-Cracking]]
- An instant hashcat result that prints nothing new — a potfile hit from an earlier run, not a fresh crack. → [[Hash-Cracking]]
- `all tested parameters do not appear to be injectable` from sqlmap — on a parameter you confirmed by hand, this means the default level and risk were too low, not that you were wrong. → [[SQL-Injection]]
- `atq: command not found` — a statement about the toolbox, not about scheduled jobs. → [[Cron-Jobs]]
- `nobody nogroup` where you expected `root root` — not a message at all, and it is the whole failure: you mounted a path where root is being squashed, or the running config differs from `/etc/exports`. → [[NFS-No-Root-Squash]]
- `0 valid` from a whole username wordlist against a domain — a wrong naming convention or a wrong realm, not a domain without users. `krbtgt` and `administrator` exist in every domain ever created: put both in the list, and if they come back invalid too, the wordlist was never the problem. → [[AD-Username-Enumeration]]
- A non-existent-domain answer for a domain's own service records — the question went to your usual resolver, which has never heard of an internal directory zone. Name the controller as the last argument before concluding the domain publishes nothing. → [[AD-Username-Enumeration]]
- A `git log` search for `password` matching nothing — without `-p` the search ran over commit messages and never entered a single change. The history has not been read yet. → [[Exposed-Service-Looting]]
- An empty search over a build server's console log fetched without credentials — what came back was a sign-in page, which is a valid document containing no credentials. At the end of a pipe, a refusal and an empty log look identical. → [[Exposed-Service-Looting]]

## "The password is wrong"

- `Token length exception` or `No hashes loaded` from hashcat — a format error before any cracking started. The mode does not match the hash, or a line break got in when the wrapped hash was copied out of the terminal. The password is not the problem. → [[Hash-Cracking]], [[Kerberoasting]]
- `Token length exception` on a `user::DOMAIN:...` string given to `-m 1000` — a category error, not a typo. Thirty-two hex characters and nothing else is an NT hash; anything longer, anything with colons in the middle, is a response that has to be cracked before it authenticates. → [[AD-Authentication]]
- `KRB_AP_ERR_SKEW(Clock skew too great)` — the clock and nothing else. It says nothing whatsoever about the credential you are holding. → [[AD-Authentication]], [[Kerberoasting]]
- `KDC_ERR_PREAUTH_FAILED` against `KDC_ERR_C_PRINCIPAL_UNKNOWN` — the first is a wrong password or hash, the second a wrong username or a misspelled domain. `KDC_ERR_S_PRINCIPAL_UNKNOWN` is about the target you named, not about you. → [[AD-Authentication]]
- `STATUS_PASSWORD_MUST_CHANGE` and `STATUS_ACCOUNT_DISABLED` — the password you recovered is correct. The account cannot currently use it, which still makes the pair worth spraying elsewhere. Reading these as a failed login throws away a working credential. → [[AD-Authentication]]
- `STATUS_ACCESS_DENIED` against `STATUS_LOGON_FAILURE` — the first is a valid credential without the right being asked for; only the second is a wrong username, password or domain. → [[AD-Authentication]], [[445-SMB]]
- `Access denied for user 'root'@'<you>' (using password: NO)` — MySQL is reporting that you sent no password. Passwordless access is off and the account has not been judged. `using password: YES` is the one that means the pair is wrong. → [[3306-MySQL]]
- `Host '<you>' is not allowed to connect` — a host-based restriction, checked before any credential. The same account may work from the box itself. → [[3306-MySQL]]
- `ERRCONNECT_LOGON_FAILURE` after a password containing `!`, `$` or a backtick — your own shell rewrote the string before xfreerdp ever saw it. Single quotes stop all three; double quotes do not stop `!`. → [[3389-RDP]]
- An RDP session that authenticates and then drops — the account is valid but not in Remote Desktop Users, or NLA is refusing the authentication type. An authorisation problem, not a wrong password. → [[3389-RDP]]
- `[ERROR] all children were disabled, dying` from hydra — the service dropped every connection, so lower `-t`. Repeated `[ERROR] could not connect` is the same throttle. Neither says anything about the wordlist. → [[21-FTP]]

## "The host is unreachable"

- `Connection refused` against a timeout — refused means something answered, so the host is up and that port is closed. A timeout means a firewall swallowed the probe. The two demand opposite next moves. → [[Nmap]], [[Shells]]
- `channel 2: open failed: administratively prohibited` — the SSH server forbids forwarding, with `AllowTcpForwarding no` in its config. No forward type will help on this host; find another pivot. → [[Pivoting-and-Tunneling]]
- `bind: Address already in use` — your side, not theirs. The local port is taken, often by a listener you started earlier and forgot. → [[Pivoting-and-Tunneling]], [[Linux-Sudo-Abuse]]
- `Warning: remote port forwarding failed for listen port 8000` — the port is already bound on the target, or `GatewayPorts` forbids the bind. Pick another remote port. → [[Pivoting-and-Tunneling]]
- `Device "tun0" does not exist` — the VPN is down. Every unreachable-target symptom in the session traces back here before anything else. → [[Public-Exploit-Workflow]]
- `MongoNetworkError: connect ECONNREFUSED` on a port the scan called open — bound to loopback and reachable only through a tunnel. → [[27017-MongoDB]], [[Pivoting-and-Tunneling]]
- `Failed to resolve "..."` — the name needs an `/etc/hosts` entry, which is normal when only a virtual host name is served. → [[Nmap]], [[Virtual-Host-Discovery]]

## "The tool is broken"

- `HTML document text` from `file` on something you just downloaded — you fetched a repository page, not the release asset. Those are different URLs, and the page is the one a search result hands you. → [[Linux-Automated-Enumeration]], [[PSPY]]
- `cannot execute binary file: Exec format error` — an architecture mismatch. The file is intact and built for another CPU. → [[PSPY]], [[Shells]]
- `base64: invalid input` — the blob is not clean base64. Usually markup, a prompt or wrapped whitespace travelled with it. → [[File-Inclusion]], [[File-Transfer]]
- `File ... cannot be loaded because running scripts is disabled` after you set the execution policy — something outranks `-Scope Process`, either Constrained Language Mode or a policy pushed centrally. → [[Windows-Automated-Enumeration]]
- `This script contains malicious content`, or a failure naming `AmsiScanBuffer` — that is AMSI and not the network. The bytes arrived and were blocked in memory, so downloading it again changes nothing. → [[File-Transfer]]
- `FUZZ keyword not found` — ffuf refused to start, because the placeholder is missing from the URL and from every header. A run that finishes instantly did not read the wordlist either. → [[Content-Discovery]], [[Virtual-Host-Discovery]]
- `E319: Sorry, the command is not available in this version` — this vim was compiled without the feature. The escape is closed on this binary, not on the technique. → [[Linux-SUID-Abuse]], [[Linux-Capabilities]]
- `certutil` reporting `The remote server returned an error: (404)` — a wrong path on your own web server, not a blocked transfer. → [[File-Transfer]]
- A username enumeration run that hangs and then reports it could not create a Kerberos client — the domain controller was not named, so the tool asked your own resolver where the ticket service lives. The installation is fine. → [[AD-Username-Enumeration]]
- A fetch or clone error from a secret scanner pointed at a directory on your own disk — the `file://` prefix is missing, so an absolute path was read as a remote address. → [[Exposed-Service-Looting]]
- A capture listener that starts cleanly, prints its banner and catches nothing — the interface it was given exists, so it reports itself as running while listening where nothing will ever arrive. A start failure naming a port instead is the local file-sharing service holding it. → [[Authentication-Coercion]]

## The messages that never come

Nothing is printed in these cases, and that is exactly what makes them expensive. They belong in this note because the silence is itself the misleading message.

- A filter that matches nothing excludes nothing. `-notlike "*\Windows\*"` needs the leading star because `PathName` starts with `C:`, while `-notlike "\Microsoft\*"` must not have one because `TaskPath` really does start with a backslash. Get it wrong and the full list returns looking like a host covered in findings. → [[Windows-Run-Sheet]]
- `-notlike '"*'` spelled with double quotes matches nothing, so the unquoted-service-path sweep hands back every service on the host. Read the count before reading the rows. → [[Windows-Service-Abuse]]
- `schtasks /query /fo list | findstr` looks filtered and is not: `/fo list` prints a paragraph per task, so removing the name line leaves the body behind. `/fo csv` is one line per task and filters correctly. → [[Windows-Run-Sheet]]
- `$null -notlike "*x*"` is true, so every pathless system process passes a `Win32_Process` filter unless the condition also requires `$_.ExecutablePath`. → [[Windows-Run-Sheet]]
- A `2>/dev/null` on the first run of anything — the denial you needed went to standard error and you deleted it in the same breath. The redirect is right for the second run, never the first. → [[Linux-Run-Sheet]]
- A `.ccache` still exported in `KRB5CCNAME` authenticates as whoever it belongs to, quietly and successfully, which is why a tool can act as the wrong user with no error at all. A forgotten export produces the opposite symptom, a password prompt after `-no-pass`. → [[AD-Authentication]]
