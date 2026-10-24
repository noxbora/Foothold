# Password Spraying

One password, tried once against every account in the domain. It is the cheapest way in when you hold names and no credential, and it is the one technique in this folder that can do real damage to the target before it does anything for you — a careless run locks out a floor of staff and ends the engagement in a phone call.

## The shape of the attack, and why the other shape is banned

The domain counts bad passwords against the *account*, never against you. That single fact decides everything:

| | what it does | what the counter sees |
| --- | --- | --- |
| brute force | many passwords against one account | that account's counter climbing to the threshold within minutes |
| spraying | one password against many accounts | one failure on each account, then a long wait |

So spraying is not a slower brute force, it is the transposed matrix. Against a thousand accounts you may send a thousand attempts and still leave every counter sitting at one. Against a single account you may send five and lock it.

It works because complexity rules do not produce unpredictable passwords, they produce predictable ones. A rule demanding an uppercase letter, a digit and a symbol is satisfied by a season and a year with a `!` on the end, by the company's own name with `01!`, and by whatever password the helpdesk assigns on the first day and nobody changes. Those four shapes are the entire opening round.

> [!warning] A lockout is not undone by waiting quietly
> Locked accounts are a real outage for real people, and on an engagement they are the thing that gets you a call from the client rather than a finding in the report. Know the policy before the first attempt, and if you cannot know it, behave as though the threshold is three.

## Reading the policy before you hold a credential

```bash
rpcclient -U "" -N <dc ip> -c getdompwinfo
```

- `-c getdompwinfo` → one request, then exit. What comes back is two lines: the minimum password length, and a properties field.
- `password_properties: 0x00000001` → the bit named `DOMAIN_PASSWORD_COMPLEX`. Complexity means three of the four character classes must appear — uppercase, lowercase, digits, symbols — and the password may not contain more than two consecutive characters of the account holder's own name. That rule is the reason your first round is `Autumn2026!` and not `autumn`: the policy forced a shape, and the shape is guessable.
- what this command does **not** print is the lockout threshold, and it does not say so. Nothing in the two lines it returns mentions failed attempts, the counter or the window, so reading this output and calling the policy read is how people convince themselves they are safe on the strength of a minimum length. The threshold comes from the command below.

```bash
nxc smb <dc ip> -u '' -p '' --pass-pol
```

- `-u '' -p ''` → the empty pair is the nameless session, and it is not the same as leaving both flags off. Without them the tool reads the host banner and never asks the directory anything, which returns quickly and answers nothing.
- this one prints the whole policy: the threshold, the window that resets the counter, how long a lock lasts, the history length and the minimum age. The threshold and the reset window are the two numbers you are here for.
- refused anonymously, try `-u 'guest' -p ''` before giving up. Guest is disabled by default on a modern domain and quietly enabled on plenty of older ones, and it authenticates as a real session while costing you nothing.

## Reading the policy once you do hold a credential

```bash
nxc smb <dc ip> -u '<user>' -p '<password>' --pass-pol
```

- `smb` → the protocol this run speaks. The policy lives in the directory and this reads it over the file-sharing protocol, which is available on every controller and needs no special right beyond being an authenticated member of the domain.
- `--pass-pol` → asks for the domain's password and lockout settings instead of testing access to anything. Without it the same command is a single authentication test, which is useful but is not this.
- `-p '<password>'` in single quotes → for your shell, not for the tool. An unquoted `!` in an interactive shell triggers history expansion and an unquoted `$` expands to nothing, so the tool receives a password you never typed and reports a logon failure for a credential that was correct.

## Spraying one password across the list

```bash
nxc smb <dc ip> -u users.txt -p 'Summer2026!' --continue-on-success
```

- `-u users.txt` → a file of bare logon names, one per line, exactly as [[AD-Username-Enumeration]] produced it. A name with the realm still attached fails as a wrong password and you cannot tell the two apart in the output.
- `-p 'Summer2026!'` → one password, quoted. Not a file.
- `--continue-on-success` → the one that is easy to omit. The tool stops at its first success by default, so a run without this flag finds the first account using the password and never tests the rest of the list. You then believe you have the one reusable credential in the domain, when you have the first one alphabetically — and the four you did not see may include the account that was worth having. Re-running to find them costs a second attempt against everyone.

> [!warning] Two files is a different attack wearing this one's command
> Pass a file to `-u` and a file to `-p` in the same run and the tool pairs every name with every password. That is a brute force against every account in the domain at once, it reaches the lockout threshold in the time it takes to read the first four lines, and nothing in the output warns you first. One password per run is not a style preference, it is the safety property.

## What each failure is actually telling you

| what the line says | what it means | what to do |
| --- | --- | --- |
| logon failure | wrong password for a real account | nothing; this is the expected line |
| account disabled | the account exists and is switched off | drop it from the list — it can never answer |
| account locked out | the counter reached the threshold | stop the run now |
| password must change | **the password was correct** | it is a valid credential with a condition attached |
| account restriction | correct password, this account may not log in from here | note it; another protocol or host may accept it |

The fourth row is the one that gets thrown away. A must-change answer means the controller checked the password and accepted it — you have found a working password and the account simply cannot open a session with it until it is changed. It still sprays elsewhere, because people reuse.

The third row is a stop condition, not a status. One locked account may be that user's own bad morning; two in the same run means your arithmetic was wrong or somebody else is spraying the same domain, and either way every further attempt makes it worse. Stop, re-read the policy, and wait out a full reset window before anything else.

## Slowing the run down, and aiming it elsewhere

```bash
nxc smb <dc ip> -u users.txt -p 'Summer2026!' --continue-on-success --jitter 2-5
```

- `--jitter 2-5` → waits a random two to five seconds between attempts. Random, not fixed: a fixed delay is its own signature, because nothing human logs in on a metronome. It does not change the lockout arithmetic at all — the counter does not care how far apart the failures were, only how many there were inside the reset window.
- the cost is time. A thousand names at three seconds each is most of an hour, which is the honest price and worth paying on anything that is not a lab.
