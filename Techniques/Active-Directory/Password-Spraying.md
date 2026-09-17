---
type: technique
platform: windows
status: working
fluency: unseen
source: thm
updated: 2026-09-17
---

# Password Spraying

One password, tried once against every account in the domain. It is the cheapest way in when you hold names and no credential, and it is the one technique in this folder that can do real damage to the target before it does anything for you — a careless run locks out a floor of staff and ends the engagement in a phone call.

## The shape of the attack, and why the other shape is banned

**Why now** — you hold a validated name list from [[AD-Username-Enumeration]] and nothing else, and you are about to send passwords at a domain that counts failures per account.

The domain counts bad passwords against the *account*, never against you. That single fact decides everything:

| | what it does | what the counter sees |
| --- | --- | --- |
| brute force | many passwords against one account | that account's counter climbing to the threshold within minutes |
| spraying | one password against many accounts | one failure on each account, then a long wait |

So spraying is not a slower brute force, it is the transposed matrix. Against a thousand accounts you may send a thousand attempts and still leave every counter sitting at one. Against a single account you may send five and lock it.

It works because complexity rules do not produce unpredictable passwords, they produce predictable ones. A rule demanding an uppercase letter, a digit and a symbol is satisfied by a season and a year with a `!` on the end, by the company's own name with `01!`, and by whatever password the helpdesk assigns on the first day and nobody changes. Those four shapes are the entire opening round.

> [!warning] A lockout is not undone by waiting quietly
> Locked accounts are a real outage for real people, and on an engagement they are the thing that gets you a call from the client rather than a finding in the report. Know the policy before the first attempt, and if you cannot know it, behave as though the threshold is three.

## Reading the lockout policy before you spend an attempt

**Why now** — you have obtained one working credential from somewhere else — from [[Exposed-Service-Looting]], from a capture, from an earlier spray — and before spending it on anything clever you ask it the one question that makes every later attempt safe.

```bash
nxc smb <dc ip> -u '<user>' -p '<password>' --pass-pol
```

- `smb` → the protocol this run speaks. The policy lives in the directory and this reads it over the file-sharing protocol, which is available on every controller and needs no special right beyond being an authenticated member of the domain.
- `--pass-pol` → asks for the domain's password and lockout settings instead of testing access to anything. Without it the same command is a single authentication test, which is useful but is not this.
- `-p '<password>'` in single quotes → for your shell, not for the tool. An unquoted `!` in an interactive shell triggers history expansion and an unquoted `$` expands to nothing, so the tool receives a password you never typed and reports a logon failure for a credential that was correct.

**What you will see**

- **Found** — the threshold, the window that resets the counter, how long a lock lasts, the minimum length, and whether complexity is enforced. The threshold and the reset window are the two numbers you write down.
- **Empty** — a threshold printed as `None` or `0` means no lockout policy is configured at all. That is a real answer and a rare gift; it means the constraint on this attack is detection, not lockouts.
- **Error** — a logon failure here is your credential, not your syntax. An access-denied answer with the credential plainly accepted means this account may authenticate but not read the policy, which is unusual and worth noting.
- **Noise** — the minimum length and complexity flag tell you what the *policy* demands, not what users chose. A minimum of eight with complexity on is exactly the configuration that produces `Summer2026!` across a whole department.

**Then** — do the arithmetic before the next section: attempts you may send in one window is the threshold minus one, and then minus one again. The second subtraction is not caution for its own sake — real users mistype their own passwords, and an account sitting at one failure of its own that you push to the threshold is locked by you. With a threshold of five and a thirty-minute window, three passwords per half hour is the honest number.

## Spraying one password across the list

**Why now** — you have the name list, you have a number of safe attempts, and you have picked the one password most likely to be shared by the most people. This is the attempt itself.

```bash
nxc smb <dc ip> -u users.txt -p 'Summer2026!' --continue-on-success
```

- `-u users.txt` → a file of bare logon names, one per line, exactly as [[AD-Username-Enumeration]] produced it. A name with the realm still attached fails as a wrong password and you cannot tell the two apart in the output.
- `-p 'Summer2026!'` → one password, quoted. Not a file.
- `--continue-on-success` → the one that is easy to omit. The tool stops at its first success by default, so a run without this flag finds the first account using the password and never tests the rest of the list. You then believe you have the one reusable credential in the domain, when you have the first one alphabetically — and the four you did not see may include the account that was worth having. Re-running to find them costs a second attempt against everyone.

> [!warning] Two files is a different attack wearing this one's command
> Pass a file to `-u` and a file to `-p` in the same run and the tool pairs every name with every password. That is a brute force against every account in the domain at once, it reaches the lockout threshold in the time it takes to read the first four lines, and nothing in the output warns you first. One password per run is not a style preference, it is the safety property.

**What you will see**

- **Found** — a `[+]` line naming the domain, the account and the password. That is a credential, and it is the first one you have.
- **Empty** — every line a logon failure. The password is wrong for everyone, which is information: it does not mean the convention is wrong or the names are bad, both of which were already proven in the previous note.
- **Error** — a connection failure against the controller before any account is tested is the address or the protocol, not the credentials, and it costs no attempts. Signing errors on older tooling are a configuration mismatch with the controller and also cost nothing.
- **Noise** — `(Pwn3d!)` after a success means that account is a local administrator on the host you aimed at, which against a domain controller is the whole domain. It is an extra fact about an already-successful login, not a separate outcome.

**Then** — a success goes straight to [[AD-Authentication]] to find out what the credential actually opens, and then to [[Kerberoasting]], because any working domain credential is worth a roast before anything else. A wholly empty round means waiting out the reset window and spraying the next password, not spraying it now.

## What each failure is actually telling you

**Why now** — the output of a spray is mostly failures, and three of them are not the same failure. Reading them as one block is how an account gets locked while you watch.

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

**Why now** — the lockout arithmetic is satisfied and the remaining problem is that a thousand authentications from one address in four seconds is a shape no normal client makes.

```bash
nxc smb <dc ip> -u users.txt -p 'Summer2026!' --continue-on-success --jitter 2-5
```

- `--jitter 2-5` → waits a random two to five seconds between attempts. Random, not fixed: a fixed delay is its own signature, because nothing human logs in on a metronome. It does not change the lockout arithmetic at all — the counter does not care how far apart the failures were, only how many there were inside the reset window.
- the cost is time. A thousand names at three seconds each is most of an hour, which is the honest price and worth paying on anything that is not a lab.

**What you will see**

- **Found** — the same `[+]` line, an hour later.
- **Empty** — the same empty round, and no way to tell from the output that the jitter did anything. It is a bet on the defender, not a change in the result.
- **Error** — a run that dies partway leaves you not knowing how much of the list was tested. Save the output to a file whenever the run is long enough that you will not be watching it.
- **Noise** — nothing new. Jitter adds no failure modes of its own, which is why it is cheap.

**Then** — the same list and the same password can be sprayed at the other doors the domain opens: the remote-management service, the remote-desktop service, the database service, the directory itself. The tool takes the protocol as its first word, so the command changes by one word. That matters when the file-sharing port is filtered from where you sit, and it matters because an account can be permitted on one of these and refused on another — a restriction answer over one protocol is worth retrying over another.

## Reading the output

The password that works is rarely clever, and it is almost never the fifth thing you try — spraying pays off in the first two rounds or it does not pay off at all. Spend your thinking on choosing the round rather than on running more of them: the current season with the current year and a symbol, the organisation's own name with a small number, the word `Welcome` with a year, and whatever the helpdesk assigns on day one, which is usually the most productive of the four because it is issued to everyone and changed by nobody.

The asymmetry worth keeping in mind is that this attack is loud in exactly one direction. Nothing you do here is hidden from the controller — every attempt is a logged authentication from a single source — but nothing you do here is *blocked* either, as long as you stay under the threshold. You are not evading anything. You are relying on nobody reading the log, which is a bet about the organisation rather than about the technology.

## Next

- [[AD-Authentication]] — what a found credential can and cannot authenticate to
- [[Kerberoasting]] — the first thing any working domain credential is worth
- [[Authentication-Coercion]] — where to go when every password round comes back empty

## Gaps

- No coverage of spraying the ticket service directly, which is the alternative when the file-sharing port is filtered, and which produces a different set of error codes this note does not list.
- Nothing on building the password list from the target itself — the organisation's own vocabulary, its breach history, the wordlists derived from its website — so the four shapes above are currently a fixed opening round.
- The defender's view is asserted and not shown: no note of which event a failed spray writes, or what distinguishes it from an ordinary morning of mistyped passwords.
- No treatment of what to do when the policy read is impossible because no credential exists yet, beyond the rule of assuming three.
