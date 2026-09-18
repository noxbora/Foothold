---
type: reference
platform: any
status: working
fluency: guided
source: reading
updated: 2026-09-11
---

# Bash Scripting — writing down what you already type

The syntax that turns a command you have typed twice into a file you can run, and lets you read somebody else's script without guessing. Look things up here; the shape of an attack lives elsewhere.

## The file, and the three ways to run it

A shell is the program that reads a line, works out what you meant, and starts the program you named. `bash` — Bourne Again Shell, a pun on the older `sh` that Stephen Bourne wrote — is the one behind your terminal, so a script is not a new language. It is the same lines, in a file, run from top to bottom without you.

The first line should be `#!/bin/bash`. Those two characters are a mark the kernel looks for at the very start of a file, and the path after them names the interpreter that gets fed the file. Leave the line out and the file still runs, because whatever shell launched it reads it instead — which is harmless when you launch it yourself and silent trouble when a scheduled job launches it under `/bin/sh`, a smaller shell that does not understand everything bash does. A missing first line never fails at the top; it fails on one strange line halfway down.

```bash
chmod +x scan.sh
```

Omit that and `./scan.sh` answers `Permission denied` — a mode problem, not a syntax one, and the file was refused before a single line of it was read.

```bash
bash scan.sh
```

This one needs only the read bit, because you are starting bash and handing it a file to read rather than asking the kernel to run the file. It is the fastest way past a missing execute bit on a box where you cannot change the mode.

```bash
source scan.sh
```

Also spelled `. scan.sh`. It runs the lines in the shell you are already sitting in instead of a new one, so anything the script sets is still there afterwards. Use it when that is the point, and not otherwise — a script that exits will now exit your shell.

The `./` is not decoration. A bare name is hunted for through a list of directories, and the directory you are standing in is not on that list, so `scan.sh` comes back `command not found` while the file sits in front of you. A name containing a slash is treated as a path instead, and `./` is the shortest slash you can write. See [[Linux-PATH-Abuse]] for what else that list decides.

## Variables

A variable is a name with a value parked behind it. Assign with `name=value` and **no spaces around the `=`** — with spaces, bash reads the first word as a command to run, so `target = 10.10.10.5` answers `target: command not found` and nothing is assigned.

```bash
target=10.10.10.5
```

Read it back by putting `$` in front of the name. A name you never set expands to nothing at all, silently, with no error and no warning: that is how a typo in `rm -rf $DIR/files` becomes `rm -rf /files`. Braces fence the name where the next character would otherwise be read as part of it — `$target_bak` is a different, unset name and vanishes, while `${target}_bak` is the value with `_bak` on the end.

## Quoting, and the bug that eats filenames

Three spellings, three different results. `"$f"` expands the variable and keeps the result as one argument even when it contains spaces. `'$f'` expands nothing and gives you the two characters and the name. `$f` bare expands, then chops the result at every space and tab into separate arguments.

That last one is the bug worth memorising. With `f` holding `my notes.txt`, `rm $f` asks for two files, `my` and `notes.txt`, reports `No such file or directory` twice, and leaves the real file exactly where it was. Two errors for one filename is the signature. Quote every variable unless you specifically want the chopping.

The same rule applies to a script's arguments as a group: `"$@"` hands each one on whole, while a bare `$@` re-chops them.

## Command substitution and arithmetic

`$(command)` runs the command and drops its output in place of itself.

```bash
count=$(wc -l < hosts.txt)
```

Backticks are the older spelling of the same thing; `$(...)` nests inside itself and backticks do not, so prefer it. Note the `<` above: `wc -l < file` prints the number alone, while `wc -l file` prints the number and the filename, and the filename then travels into your variable and ruins whatever you do with it next.

Arithmetic needs its own brackets, because bash treats everything as text until told otherwise. `$((count + 1))` gives you a number; `$count + 1` gives you the three words `5 + 1`.

## Arguments and a usage guard

Inside a script, `$1` is the first word you typed after its name, `$2` the second, `$0` the script's own name, and `$#` how many arguments arrived. A script that hardcodes its target is a script you edit on every host; one that reads `$1` is a script you reuse.

```bash
if [ $# -lt 1 ]; then echo "usage: $0 <target>"; exit 1; fi
```

Without that guard, running the script with nothing at all leaves `$1` empty, and every command built on it runs against a blank — which is the difference between a tool that complains and a tool that does something you did not intend. `exit 1` also matters: any number other than zero tells whatever called your script that it failed.

## Exit status, `&&` and `||`

Every command leaves a number behind and `$?` holds the last one: `0` succeeded, anything else did not. It describes only the command that just finished, so read it immediately or park it in a variable with `rc=$?` — running anything else first, `echo` included, overwrites it.

The two joiners are built on that number. `a && b` runs `b` only if `a` succeeded; `a || b` runs `b` only if `a` failed. That is why `grep -q pattern file && echo found` reads the way it does, and why `command || true` is the standard way to say "I expect this one to fail and I do not care".

## Tests: `[ ]`, `[[ ]]`, and the comparison you picked by accident

`[ ]` is a command, not punctuation — which is why it needs spaces inside the brackets and why an unquoted empty variable breaks it. `[ $x = y ]` with `x` unset becomes `[ = y ]`, and bash answers `unary operator expected`. Quote it and the test simply fails as it should.

The useful file tests are `-f` a regular file exists, `-d` a directory exists, `-r` you can read it, `-w` you can write it, `-x` you can execute it, `-z` a string is empty and `-n` a string is not.

```bash
if [ -w /etc/passwd ]; then echo "writable"; fi
```

String comparison uses `=` and `!=`; number comparison uses `-eq -ne -lt -le -gt -ge`. Mixing them is the classic slip: `[ "$n" -gt 5 ]` with `n` holding `abc` answers `integer expression expected`, and `[ "$a" = "$b" ]` compares text, so `10` and `010` are different strings while `-eq` calls them equal.

`[[ ]]` is bash's own version. It does not word-split, so an unquoted variable cannot break it, and it adds pattern matching with `==` plus regular expressions with `=~`. It is the better choice in a bash script and unavailable in `/bin/sh`, which is exactly the trap described at the top of this note.

## Loops

`for` walks a list you can see; `while read` walks a file a line at a time.

```bash
for ip in 10.10.10.5 10.10.10.9; do echo "$ip"; done
```

A file is the more common case, and there is a right way to do it.

```bash
while IFS= read -r line; do echo "[*] $line"; done < hosts.txt
```

Three parts of that line are easy to drop. Without `-r`, a backslash in the line is treated as an escape and silently disappears. Without the empty `IFS=` in front, leading and trailing spaces are stripped from every line. Without the `< hosts.txt` at the end, the loop reads from your keyboard and hangs there looking like it is working.

Do not reach for `for line in $(cat hosts.txt)`. It chops on every space, so a line with two words becomes two iterations, and a file of hostnames with a stray space quietly doubles your work.

## Hardening a script you will run more than once

```bash
set -euo pipefail
```

`-e` stops the script at the first command that fails, instead of carrying on with a broken assumption. `-u` turns an unset variable into an error instead of silence, which kills the `rm -rf $DIR/` class of accident outright. `-o pipefail` makes a pipeline report failure when any stage fails, not just the last one — without it, `curl ... | grep x` looks successful even when `curl` never connected.

The cost is worth knowing before you meet it: with `-e`, a command whose non-zero exit you expected — `grep` finding nothing is the usual one — now kills the whole script. Write that line as `grep -q pattern file || true` and the intent is on the page.

## The failures you will actually meet

- `target: command not found` on an assignment — you put spaces around the `=`.
- `Permission denied` on `./script.sh` — the execute bit is missing; `chmod +x` it, or run it with `bash script.sh`.
- `No such file or directory` twice for one file — an unquoted variable holding a space was chopped in two.
- `unary operator expected` — an unquoted variable inside `[ ]` was empty, so the test lost its left-hand side.
- `integer expression expected` — a numeric comparison such as `-gt` was handed something that is not a number.
- `$'\r': command not found` — the file was saved with Windows line endings, so every line ends in an invisible carriage return that bash counts as part of the command name. `dos2unix script.sh` fixes it.
- `syntax error near unexpected token 'done'` — nearly always a missing `;` before `do`, or a `do` that was never opened.

Related: [[Linux-PATH-Abuse]] decides which file a bare command name resolves to, [[Cron-Jobs]] is where a script's missing first line and thin environment come back to bite, and [[Failure-Messages]] collects the messages whose plain reading points at the wrong cause.
