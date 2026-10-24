# PowerShell History (PSReadLine)

[[Security-Terms#^psreadline|PSReadLine]] writes every command typed at a PowerShell prompt into a plain text file, one file per user, and nothing rotates or truncates it. That makes it the cheapest credential source on a Windows host: no exploit, no privilege, one `type`. It belongs at the front of the sweep on every shell you land in, and again after every account you switch to.

## What did this account type

```cmd
type %userprofile%\AppData\Roaming\Microsoft\Windows\PowerShell\PSReadline\ConsoleHost_history.txt
```

- `type` → cmd.exe's `cat`: print the file to the screen.
- `%userprofile%` → expands to the **current** user's folder, so this one-liner only ever reads your own history. **cmd.exe only.** PowerShell does not expand `%VAR%`; there the path is taken literally, and the failure looks like a missing history file rather than the wrong shell. In PowerShell write `$Env:userprofile` instead, or run the line through `cmd /c`.
- `PSReadline` in the path → spelled with a lowercase `l`, and it is a directory, not the module name. Getting the case wrong is harmless on [[Security-Terms#^ntfs|NTFS]]; getting the *level* wrong (dropping `\PowerShell\`) produces the same path-not-found as a genuinely empty profile.

## Which other users' history can I read

```cmd
dir /s /b C:\Users\*ConsoleHost_history.txt
```

- `/b` → bare format: full paths only, no header or byte counts, so the output is a list you can work down.
- `/s` → recurse. Without it you search only `C:\Users\` itself, which contains no files at all, and the empty result reads as "no history anywhere on the host".
- `C:\Users\` → not `%userprofile%`. The point of this command is to leave your own profile.

## Reading another account's history

```cmd
type C:\Users\<username>\AppData\Roaming\Microsoft\Windows\PowerShell\PSReadline\ConsoleHost_history.txt
```

- `<username>` → substitute the account name from the listing above. Nothing here expands; the literal path is the whole point.
- The path is per-user by design, so there is no single command that reads all of them at once as an unprivileged account. Repeat it per profile.
