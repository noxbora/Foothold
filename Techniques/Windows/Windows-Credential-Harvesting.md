---
type: technique
platform: windows
status: working
fluency: guided
source: thm
updated: 2026-10-13
---

# Windows — Credential Harvesting

The cheapest escalation on Windows is not an exploit — it is a password somebody left on disk. Run this sweep on every fresh shell before touching tokens, services or kernel CVEs: it costs five commands and it is the one path that needs no vulnerability at all.

Every location below exists because a legitimate feature had to store a secret somewhere. Each is a place to look, in the order it is worth looking; a hit at any of them can end the box.

## Unattended installation answer files

**Why now** — you have a foothold and no admin password, and you want to know whether this host was mass-deployed. Imaging hundreds of machines with nobody at the keyboard means the setup administrator password is written into an answer file, and it is supposed to be scrubbed afterwards — often it is not. You are hoping for that plaintext or base64 admin password.

```cmd
type C:\Unattend.xml
```

```cmd
type C:\Windows\Panther\Unattend.xml
```

```cmd
type C:\Windows\Panther\Unattend\Unattend.xml
```

```cmd
type C:\Windows\system32\sysprep.inf
```

```cmd
type C:\Windows\system32\sysprep\sysprep.xml
```

- Five paths because the file lands in a different one depending on the deployment tool and Windows version. Run all five; the one that exists is not predictable.
- `C:\Windows\Panther\` → the copy administrators most often forget, because it is written during setup and not part of the image they scrub. Check it even when `C:\Unattend.xml` is gone.

```xml
<Credentials>
    <Username>Administrator</Username>
    <Domain>corp.local</Domain>
    <Password>MyPassword123</Password>
</Credentials>
```

**What you will see**

- **Found** — a `<Credentials>` or `<AutoLogon>` block naming a user and a password, as above. The domain field tells you whether it is a local or a domain account, which decides where you spend it.
- **Empty** — the file is genuinely absent on a well-run host; it is meant to be deleted after imaging. Absent closes only this location — move to the next heading, do not conclude the host is clean.
- **Error** — `The system cannot find the file specified.` on all five is the normal, expected result and means exactly "not deployed this way". `Access is denied.` on a path that exists is different: the file is there and your token cannot read it, so note it and retry after any escalation.
- **Noise** — a `<Password>` whose value is an empty string or the literal `*SENSITIVE*DATA* DELETED*` is a scrubbed file, not a find.

> [!important] `<PlainText>false</PlainText>` does not mean encrypted
> Answer-file passwords are often stored base64-encoded, with `PlainText` set to `false`. That flag means "not literal text", not "protected" — decode it. The encoded blob usually has the string `AdministratorPassword` appended before encoding; strip it after decoding.

**Then** — a recovered password goes straight to the account it names: `runas`, [[5985-WinRM]], [[3389-RDP]], or `psexec.py`. It is a **credential-reuse** lead too — try it against every other account and host you know. Absent or denied sends you to the next location below.

## PowerShell history

Whatever the user typed at a PowerShell prompt — passwords included — is on disk in their profile. Second stop on the sweep, and it has its own page: **[[PowerShell-History]]** holds the command, the per-user path, how to reach other users' files, and what an empty file does *not* mean.

## Saved Windows credentials

**Why now** — a password may be stored on this host without ever being readable as text. Credential Manager keeps passwords for "run as another user" so they need not be retyped; you cannot read them back, but you can **spend** them. You are hoping this account has a saved admin or service credential you can replay blind.

```cmd
cmdkey /list
```

```cmd
runas /savecred /user:admin cmd.exe
```

- `cmdkey /list` → the **names** of stored credentials and the target each is bound to; never the passwords themselves.
- `runas /savecred` → runs as that user using the stored credential, without your knowing it.
- `/user:admin` → must match a credential in the list exactly. A bare username with no domain only matches a local account; a stored `Domain:target=...` credential needs the form it was saved under or `runas` silently prompts for a password you do not have.

**What you will see**

- **Found** — `cmdkey /list` prints one or more entries with a `Target:` line and a `User:` line. A `Domain:target=` entry naming an admin or a different user is the prize; `runas /savecred` against it should drop you into `cmd.exe` as that user.
- **Empty** — "Currently stored credentials: * NONE *" is a real answer and closes this location. It reflects **this** account only — a different user you later become may have their own store.
- **Error** — `cmdkey /list` printing entries but `runas` failing is normal, not a wall: stored credentials are bound to a specific target, and `/savecred` only replays one against the target it was saved for. Read the `Target:` line, not just the user.
- **Noise** — `virtualapp/didlogical` and `WindowsLive:target=...` entries are stock Windows single-sign-on artefacts, not admin credentials. Skip them.

**Then** — a working `runas` shell is a lateral move; run the whole sweep again as the new user. A credential that lists but will not replay here tells you an account **used** those creds, which is itself a lead for [[Windows-Privilege-Escalation]]. Empty sends you to the next location.

## AutoLogon registry credentials

**Why now** — `cmdkey` showed you a store you cannot read back, or nothing at all, and you want the one place Windows keeps a password as literal text. If this host boots straight to a desktop with nobody typing anything, some account's password has to be on disk for the boot to use — and the classic autologon setup writes it into the registry in the clear. Fourth stop on the sweep; the command and its three traps belong to [[Windows-Run-Sheet]] step 6, and what follows is what to do with what it prints.

The key is `HKLM\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Winlogon` and it is readable by any user, which is the whole reason a low-privilege shell can reach it. Four of its roughly thirty values matter: `AutoAdminLogon`, `DefaultUserName`, `DefaultDomainName`, `DefaultPassword`, plus `AutoLogonSID` beside them.

**What you will see**

- **Found** — `DefaultPassword    REG_SZ    P@ssw0rd!` beside `DefaultUserName    REG_SZ    <user>`. That is the password, literally; nothing to decode, nothing to crack. `DefaultDomainName` decides where you spend it — the machine name means a local account, a domain name means the credential is worth trying against every host in that domain. `AutoLogonSID` names the same account as a [[Security-Terms#^sid|SID]], and its [[Security-Terms#^rid|RID]] — the last number — tells you what you hold before you spend it: `500` is the built-in Administrator, anything from `1000` up is an ordinary local user, which usually makes this a lateral move rather than the escalation.
- **Empty** — the other values print but there is no `DefaultPassword` line. That is a real answer with a specific cause: the modern Sysinternals [[Security-Terms#^autologon|AutoLogon]] tool stores the password in [[Security-Terms#^lsa-secrets|LSA secrets]] instead of the registry, precisely so this read comes back empty. It closes the plaintext route, not the vector — that secret is recoverable, but only as SYSTEM, so it goes on the list of things to come back for after an escalation.
- **Error** — `ERROR: Access is denied.` on this key is rare and worth noting: it is world-readable by default, so a denial means somebody hardened it deliberately, which is itself a hint that something was in it.
- **Noise** — `AutoAdminLogon    REG_SZ    1` on its own is not a finding; it says the feature is on, not where the password went. `DefaultUserName` alone is stock furniture — Windows records the last interactive user there whether autologon was ever configured or not. A username with no password beside it is a name for your user list and nothing more.

> [!important] Do not skip the key because `AutoAdminLogon` is `0`
> Switching autologon back off clears the flag, not the value. `DefaultPassword` is left behind on plenty of hosts where autologon was set up once, used for a while and then disabled. A `0` tells you the feature is off today, not that no password was written yesterday — read the values, not the switch.

**Then** — the password goes to the account `DefaultUserName` names, and that account's group memberships decide the route: [[3389-RDP]] if it is in Remote Desktop Users, [[5985-WinRM]] or [[445-SMB]] if it is not. Prefer any of them over `runas`, which insists on reading the password from a real console and cannot be handed one on stdin — in the non-interactive shell you are likely holding it hangs or refuses. First two commands on the new session are `whoami /priv` and `whoami /groups`, then run this whole sweep again as that user. An LSA-secrets Empty sends you to [[Windows-Privilege-Escalation]] to get SYSTEM first.

## IIS configuration

**Why now** — you have found a web server on the host (or the box answered on 80/443), and web apps must store their database password somewhere the app can read at startup. On IIS that is `web.config`. You are hoping for a connection string with `Password=` in the clear.

```cmd
type C:\inetpub\wwwroot\web.config
```

```cmd
type C:\Windows\Microsoft.NET\Framework64\v4.0.30319\Config\web.config | findstr connectionString
```

- `findstr connectionString` → `findstr` is cmd.exe's `grep`; the connection string is the line carrying `User ID=` and `Password=`, and piping to `findstr` pulls it out of a long config.
- The two paths are the **per-site** config (`wwwroot`) and the **machine-wide** .NET config. Sites often live outside `wwwroot`; if the app root is elsewhere, `type` that path's `web.config` instead.

**What you will see**

- **Found** — a `<connectionString>` or `<add ... connectionString="...">` line with `Data Source=`, `User ID=`, and `Password=`. That database password is a credential-reuse lead as much as a database login.
- **Empty** — no `web.config`, or one with no connection string, means either IIS is not the app host or the app stores its secret elsewhere (an `appsettings.json`, an environment variable). Closes this location, not the sweep.
- **Error** — `Access is denied.` on `web.config` is common and meaningful: application-pool identities restrict it, so the file exists and a better token will read it. `The system cannot find the file specified.` means no site at that path.
- **Noise** — a connection string using `Integrated Security=SSPI` or `Trusted_Connection=True` carries **no** password — it authenticates as the app-pool identity, so there is nothing to extract from that line.

**Then** — a database password goes to the database it names (try [[1433-MSSQL]] or the relevant service) and to every other account as a reuse test. A denied `web.config` is a reason to come back after [[Windows-Privilege-Escalation]]. The full sweep of config formats is [[Config-File-Looting]].

## PuTTY stored sessions

**Why now** — this is a jump host or an admin's workstation, and the person who used it saved SSH sessions so they need not retype connection settings. PuTTY refuses to store the SSH password, but it stores **proxy** credentials in cleartext. You are hoping a saved session used an authenticated proxy whose username and password were reused.

```cmd
reg query HKEY_CURRENT_USER\Software\SimonTatham\PuTTY\Sessions\ /f "Proxy" /s
```

- `/f "Proxy"` → search for this string in the key data, which narrows a large session tree to the proxy values.
- `/s` → recurse into all subkeys, one per saved session. Without it you read only the parent key, which holds no values, and the empty result reads as "no saved sessions".
- `HKEY_CURRENT_USER` → the hive of the account you are running as. It cannot see another user's saved sessions, so an empty result here says nothing about the other profiles on the box.

**What you will see**

- **Found** — `ProxyUsername` and `ProxyPassword` values with real data. The password is in the clear; the hostname of the session is a second finding (a target you did not know about).
- **Empty** — no PuTTY key, or sessions with no proxy configured. Real, and it closes PuTTY — but the same logic applies to every "remember my password" app on the box, so it points you at the generalisation below rather than at nothing.
- **Error** — `ERROR: The system was unable to find the specified registry key or value.` means PuTTY was never installed for this user, or you are a service account with no `HKCU` hive of its own.
- **Noise** — `ProxyPassword` present but empty, or a session set to `ProxyMethod=0` (no proxy), carries nothing.

> [!note] Simon Tatham wrote PuTTY
> His name is part of the registry path, not a username on the target. Nothing to look up.

**Then** — a proxy credential is a reuse lead like every other secret here. More usefully, the same recovery path exists for **any** software that offers to remember a password — browsers, mail clients, FTP and VNC clients, RDP managers. PuTTY is one worked example; the generalisation is the finding. From here, [[Config-File-Looting]] for the file-based stores.

## With local admin — mimikatz on the box

Everything above needs no privilege; everything from here does. These stores hold hashes and secrets, not files you can `type`, and reaching them means **local administrator**, a mimikatz binary on the target, and — on a live box — Windows Defender either off or fed an obfuscated build, since mimikatz is the single most-signatured tool in existence. Run it from an elevated prompt. What it returns is spent, not read: a plaintext is a bonus, an [[Security-Terms#^nt-hash|NT hash]] is pass-the-hash fuel for [[AD-Authentication]].

### LSASS memory — live sessions

**Why now** — someone with more rights than you may be logged in *right now*. [[Security-Terms#^lsass|LSASS]] holds, per live session, the NT hash and sometimes the plaintext. First thing to try the moment you are admin.

```text
privilege::debug
```

```text
sekurlsa::logonpasswords
```

- `privilege::debug` first → turns on `SeDebugPrivilege`, the right to read another process's memory. Skip it and `sekurlsa` cannot open LSASS, failing with `ERROR kuhl_m_sekurlsa_acquireLSA`.
- it reads **memory**, so it shows only sessions that exist now → a domain admin who logged in yesterday and logged off leaves nothing here.

**What you will see**

- **Found** — one block per session: `Username`, `Domain`, an `NTLM` hash under `msv`, sometimes a clear `Password` under `wdigest` or `kerberos`.
- **Empty** — only your own session and the local accounts, no domain users, is the normal result on a box nobody privileged is using. It closes *this* route, not the note — the cached-logon route below reaches users who logged in and left.
- **Error** — the `acquireLSA` error means you skipped `privilege::debug`, or you are not actually elevated.
- **Noise** — `Password : (null)` is a session with no plaintext retained, not a failure; read the hash instead.

**Then** — a plaintext goes to [[Active-Directory-Lateral-Movement]] as a credential; an NT hash goes to [[AD-Authentication]] to be replayed.

### SAM + SYSTEM — local account hashes

**Why now** — LSASS gave you nothing and you want this host's *local* account hashes regardless of who is logged in. The [[Security-Terms#^sam|SAM]] hive holds them encrypted; the SYSTEM hive holds the boot key that decrypts them. You need both.

```cmd
reg save HKLM\SAM C:\Windows\Temp\SAM
```

```cmd
reg save HKLM\SYSTEM C:\Windows\Temp\SYSTEM
```

```text
lsadump::sam /sam:C:\Windows\Temp\SAM /system:C:\Windows\Temp\SYSTEM
```

- two `reg save` calls, one hive each → both are needed, because the SAM is undecryptable without the SYSTEM boot key.
- `/sam:` and `/system:` must point at the files you just saved → mimikatz reads these copies, not the live registry, so a wrong path is a file-not-found rather than a crypto error.

**What you will see**

- **Found** — `The operation completed successfully.` after each `reg save`, then a `RID` / `User` / `Hash NTLM:` block per local account from `lsadump::sam`. [[Security-Terms#^rid|RID]] 500 is the local Administrator.
- **Empty** — only `Administrator` and `Guest`, no extra users, is a real if dull answer: no local accounts beyond the defaults.
- **Error** — `reg save` with `Access is denied.` means you are not actually elevated. A decryption error from `lsadump::sam` means mismatched hives — you copied only one, or saved them at different moments.
- **Noise** — the `Guest` hash `31d6cfe0…` is the hash of an empty password on every Windows box ever; not a find.

**Then** — a local Administrator hash is pass-the-hash fuel against *other* hosts that share it ([[Active-Directory-Lateral-Movement]]); crack it only if you want the plaintext ([[Hash-Cracking]]).

### LSA cache — domain logons that already left

**Why now** — a domain user logged into this box once and is gone, so LSASS is empty, but Windows cached their logon so they could sign in offline. That cache is the `$DCC2$` hash.

```text
token::elevate
```

```text
lsadump::cache
```

- `token::elevate` → steals a SYSTEM token; the cache lives under a registry key only SYSTEM reads, so without this `lsadump::cache` is access-denied.

**What you will see**

- **Found** — `User : DOMAIN\name` with `MsCacheV2 : <hex>` per cached account, often a domain admin who once touched this workstation.
- **Empty** — no cached entries means no domain user has interactively logged in here; common on a freshly imaged host.
- **Error** — access denied is the missing `token::elevate`.
- **Noise** — the local Administrator can appear here too; the `DOMAIN\` prefix is how you tell a cached *domain* logon from a local one.

**Then** — a `$DCC2$` hash **cannot** be passed, it only cracks. It goes to [[Hash-Cracking]] as mode `mscash2`, nowhere else.

### DPAPI vault — saved app passwords

**Why now** — the user saved an RDP connection, a web login or a Wi-Fi key, and Windows kept it in their Vault under [[Security-Terms#^dpapi|DPAPI]].

```text
vault::list
```

```text
vault::cred /export
```

- `vault::list` names the vaults and items; `vault::cred /export` is the one that prints recovered pairs → run `list` first to know whether `export` has anything to find.

**What you will see**

- **Found** — `vault::cred /export` prints `UserName` / `Credential` pairs in the clear.
- **Empty** — vaults present with `Items (0)` is normal; most accounts save nothing.
- **Error** — a credential shown by `list` but blank on `export` is the load-bearing case: a secret belonging to a *different* user (a service account) is encrypted with *their* DPAPI key, and you cannot decrypt it without running as them. As local admin you read your own and the machine's, not theirs.
- **Noise** — stock single-sign-on vault entries carry nothing worth exporting.

**Then** — a recovered password is a credential-reuse lead like any other; match it to a user and try it across the domain ([[Active-Directory-Lateral-Movement]]).

### Remote — one host, no binary dropped

**Why now** — you hold a local admin credential for a host but no shell on it, and you would rather pull its SAM and cached logons from Kali than RDP in and run mimikatz by hand.

```bash
secretsdump.py 'HOST/Administrator:password@host-ip'
```

- no `-just-dc` here → against an ordinary workstation you *want* the local SAM and the cached domain logons, which is exactly what the bare run returns. `-just-dc` is for a domain controller ([[DCSync]]).
- runs over SMB (Server Message Block, the Windows file-sharing protocol on port 445) via the remote registry → the account must be local admin on the target; a valid-but-unprivileged credential authenticates and then cannot read the hives.

**What you will see**

- **Found** — `Dumping local SAM hashes` then the `user:RID:lm:nt:::` block, then `Dumping cached domain logon information` with `$DCC2$` lines.
- **Empty** — not a state; you get the hives or an access error.
- **Error** — a login failure is a wrong credential; `rpc_s_access_denied` *after* login is a valid credential that is not local admin on this host.
- **Noise** — the empty-LM `aad3b435…` half again, and machine accounts ending `$`.

**Then** — SAM hashes to [[AD-Authentication]] (pass-the-hash) or [[Hash-Cracking]]; `$DCC2$` lines to [[Hash-Cracking]] only.

## Rarely — worth one command, not worth a step

**Why now** — the stores above are empty. These three hold a credential perhaps twice a year, and each is one command.

```cmd
netsh wlan show profile name=* key=clear
```

- Every wireless network this machine has joined, with the pre-shared key in clear text. Useless on a server, occasionally the whole answer on a laptop, and it is the same key people reuse elsewhere.

```cmd
vaultcmd /listcreds:"Windows Credentials" /all
```

- The credential vault behind the graphical manager. It overlaps with `cmdkey` but not completely, and it names the target machine for each entry, which turns a stored credential into a lateral movement plan.

```cmd
findstr /S /I cpassword \\%USERDNSDOMAIN%\SYSVOL\%USERDNSDOMAIN%\Policies\*.xml
```

- Group policy preferences stored a password in a share every domain user can read, encrypted with a key Microsoft published. Patched in 2014, still present in files nobody deleted afterwards.
- Only run this on a domain-joined host; off a domain the path does not resolve and the command returns immediately.

**What you will see**

- **Found** — a `Key Content` line, a vault entry naming another machine, or a `cpassword` attribute in a policy file.
- **Empty** — the normal answer for all three. They are lottery tickets, not steps.
- **Error** — `The system cannot find the path specified` from the last one means the host is not domain-joined, which is a clean answer rather than a denial.
- **Noise** — `netsh` lists profiles for networks that no longer exist, and a profile with no key content is an open network. Neither is a credential.

**Then** — a recovered password goes to [[445-SMB]] and [[5985-WinRM]] to find out what else it opens, and to [[Hash-Cracking]] if what you have is not yet plain text.

## Reading the output

Two things govern the whole sweep, not any one location.

**Every registry read is per-user.** `HKEY_CURRENT_USER` only ever sees the hive of the account you are running as, so an empty PuTTY or Credential-Manager result says nothing about the other users on the box — and nothing about *this* user either if you landed as a service account with no interactive profile. Re-run the whole sweep after every account you become.

**Everything recovered here is a credential-reuse lead first and a local win second.** The same password very often opens a second host, a database, or a domain account — which is where a local administrator password becomes a lateral move. Match every secret to a username (its file owner, the service it configures, a name in the same block) before deciding it is spent.

## Next

- [[PowerShell-History]] — step two of the sweep, kept as its own note
- [[Windows-Privilege-Escalation]] — where a recovered credential gets spent
- [[Config-File-Looting]] — the Linux counterpart to the `web.config` sweep
- [[3389-RDP]] — the usual place a working Windows credential is cashed in

## Gaps

- The no-privilege sweep and the local-admin mimikatz tier are both here now; the domain-wide pull is [[DCSync]]. Still unwritten: capturing [[Security-Terms#^netntlmv2|NetNTLMv2]] over the network (Responder, [[Security-Terms#^scf|SCF]] drops) — capture on the wire, not harvesting from a host.
- `lsadump::secrets` proper — the `HKLM\SECURITY\Policy\Secrets` store behind the Autologon LSA-secrets variant named earlier — sits beside `lsadump::cache` above but has no procedure of its own.
- Browser, mail-client and VNC password stores are named above but have no procedure here.
- Offline DPAPI master-key decryption — lifting a user's master key plus their password to decrypt another session's blobs, the way past the "cannot decrypt another user's vault" wall above — is unwritten.
