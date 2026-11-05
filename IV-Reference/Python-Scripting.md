# Python Scripting — the moving parts

Values, the names they sit behind, the collections that hold many of them and the loops that walk those collections. That is enough to read a proof-of-concept you did not write and change the one line that needs changing. Look things up here; the attack itself lives elsewhere.

## Running it

```bash
python3 script.py
```

Ask for `python3` by name. A bare `python` may not exist at all, or on an older box may still be Python 2, which chokes on the first f-string with `SyntaxError: invalid syntax` and sends you hunting for a typo that is not there.

```bash
python3
```

With no file, you get the interactive `>>>` prompt: type an expression and its value is echoed straight back. It is the quickest way to test one line before it goes into a script. Leave with `exit()` or Ctrl+D.

Blocks are made of indentation, not brackets, and the line that opens one ends in a colon. Drop the colon and you get `SyntaxError: expected ':'`; forget to indent the body and you get `IndentationError: expected an indented block`. A `#` starts a comment that runs to the end of the line.

## `=` and `==`

`=` is an instruction: work out the right-hand side, then bind the result to the name on the left. It answers nothing. `==` is a question: are these two equal? It answers `True` or `False`, and changes nothing. A condition needs an answer, so `if x = 5:` is refused outright — Python 3.10 and newer even suggest `==` in the error.

Because the right-hand side is worked out first, `count = count + 1` is not the paradox it looks like: the old value is read, one is added, and the result overwrites the name. The augmented forms are shorthand for exactly that pattern — `count += 1`, `-=`, `*=`, `/=`, `//=` — and the old value is gone once the line has run.

## Types, and converting between them

The core types are `str` (text: `"hello"`), `int` (whole number: `42`), `float` (number with a decimal point: `3.14`), `bool` (`True`/`False`), `list` (`[1, 2, 3]`) and `dict` (`{22: "SSH"}`). `type(x)` tells you which one you are holding, printed as `<class 'str'>`, `<class 'int'>` and so on.

The four converters: `int("42")` is `42`, `float("3.14")` is `3.14`, `str(42)` is `"42"`, and `bool(0)` is `False`.

`input()` always hands back a `str`, whatever the user typed. `"10" + 1` therefore fails with `TypeError: can only concatenate str (not "int") to str` — wrap it in `int()` first.

```python
port = int(input("Port: "))
```

`int()` refuses a decimal string: `int("3.14")` raises `ValueError: invalid literal for int() with base 10`. Go through `float()` instead. Fed an actual float, `int()` chops towards zero, so `int(-3.7)` is `-3` — not the same thing as `//` below. Surrounding spaces are tolerated: `int(" 42 ")` is `42`.

`str()` goes the other way and turns a value into text: `str(42)` is `"42"`, which is what lets a number be glued onto a string with `+`.

`bool()` is `False` only for empties and zero — `0`, `""`, `[]`, `{}`. Everything else is `True`, which is why `bool("False")` is `True`: a string that says False is still a non-empty string.

## f-strings

```python
print(f"User {username} is on port {port}")
```

The older way hands `print()` several items separated by commas — `print("User", username, "is on port", port)` — and `print()` puts one space between each pair by itself. It works, but the spacing is not yours to control; in an f-string every character is.

Leave off the `f` and there is no error — the braces are simply printed as they are, `{username}` and all.

A format spec goes after a colon inside the braces. `{total:.2f}` means fixed-point with exactly two digits after the point, whatever the number arrived with: it pads (`7` becomes `7.00`) and rounds (`2.567` becomes `2.57`).

Floats are stored in binary, which cannot hold `0.1` exactly, the same way decimal cannot hold one third. The tiny errors surface when they add up: `0.1 + 0.2` prints `0.30000000000000004`, and `0.1 + 0.2 == 0.3` is `False`. `:.2f` hides the noise, but the same cause occasionally drags a half downwards — `2.675` formats as `2.67`, because what is actually stored sits just below it.

## Arithmetic

`/` always returns a float, even when the division comes out even: `6 / 2` is `3.0`. That includes `/=`, which turns an `int` into a `float` behind your back.

`//` divides and rounds down to the floor. Down means towards minus infinity, not towards zero, so `7 // 2` is `3` but `-7 // 2` is `-4`.

`%` is the remainder, and `n % 2 == 0` is the standard even-number test.

`**` raises to a power: `2 ** 8` is `256`, and a 128-bit key has `2 ** 128` possible values. Do not reach for `^` — in Python that is bitwise XOR, so `2 ^ 8` quietly gives `10` with no error at all.

## Conditions

```python
if port == 22:
    print("SSH")
elif port == 80:
    print("HTTP")
else:
    print("Unknown port")
```

`if` runs its block only when the condition is `True`. `elif` (else if) is checked only when everything above it was false, and you can stack as many as you need. `else` takes whatever is left and has no condition of its own. Python stops at the first branch that matches, so order matters: put the narrow test above the broad one, or the broad one swallows it.

The comparison operators, each answering `True` or `False`. With `x = 5`:

- `x == 5` equal — `True`
- `x != 5` not equal — `False`
- `x < 5` less than — `False`
- `x > 5` greater than — `False`
- `x <= 5` less than or equal — `True`
- `x >= 5` greater than or equal — `True`

The `=` in `<=` and `>=` is what lets the edge value itself pass.

Both sides must be the same type for the answer to mean anything. `"22" == 22` is simply `False`, with no error — so a port read with `input()` and never converted falls through every branch to `else`, and the script looks as if it works. `"22" < 22` at least fails loudly, with `TypeError: '<' not supported between instances of 'str' and 'int'`.

The logical operators join conditions: `and` is true only if both sides are, `or` if at least one is, and `not` flips a boolean.

```python
if length >= 8 and has_digit:
```

`if hungry == True:` works, but `if hungry:` says the same thing, and `if not hungry:` is the opposite test.

`any()` answers whether at least one item passes a test: `any(c.isdigit() for c in password)` is `True` as soon as one character is a digit.

## Strings

Single, double and triple quotes all make the same `str`; only triple quotes (`"""..."""`) can span several lines. Pick the outer pair that does not appear inside: `"it's"` works, while `'it's'` ends at the apostrophe and fails with `SyntaxError: unterminated string literal`.

`len(s)` counts characters. Indexes start at 0, and negative ones count from the end, so `s[-1]` is the last character. Reaching past the end raises `IndexError: string index out of range`.

A slice `s[start:end]` includes `start` and stops before `end`; leave either side out to run to that end, so `"Python"[2:]` is `"thon"` and `"Python"[:4]` is `"Pyth"`. Unlike an index, a slice never complains about overshooting — `"Python"[0:100]` is just `"Python"`.

Strings cannot be changed in place: `s[0] = "J"` raises `TypeError: 'str' object does not support item assignment`. Every method hands back a *new* string instead, so `name.lower()` on a line of its own does nothing to `name`. Keep the result.

```python
name = name.lower()
```

The methods worth knowing, with the part people get wrong:

- `.lower()` / `.upper()` — `"HELLO".lower()` is `"hello"`, `"hello".upper()` is `"HELLO"`. The names come from the printer's type cases: capitals were kept in the upper one.
- `.strip()` — `"  hi  ".strip()` is `"hi"`. It trims both ends only, never the middle: `" a b ".strip()` is `"a b"`.
- `.replace(a, b)` — `"cat".replace("c", "b")` is `"bat"`. It replaces every occurrence, not the first: `"banana".replace("a", "o")` is `"bonono"`.
- `.split(sep)` — cuts at each `sep` and hands back a list: `"a,b,c".split(",")` is `['a', 'b', 'c']`. With no argument it splits on any run of whitespace and drops the empties; `.split(" ")` splits on each single space, so `"a  b"` becomes `['a', '', 'b']`.
- `.startswith(x)` / `.endswith(x)` — `"http://site".startswith("http")` and `"file.txt".endswith(".txt")` are both `True`.
- `.count(x)` — how many times `x` appears: `"banana".count("a")` is `3`.
- `.isdigit()`, `.isalpha()`, `.isalnum()`, `.isupper()`, `.islower()` — return `True`/`False`. For `"A"`: `.isupper()` `True`, `.islower()` `False`, `.isdigit()` `False`, `.isalpha()` (a letter?) `True`, `.isalnum()` (a letter or a digit?) `True`. `.isdigit()` is `False` for `"-5"` and `"3.14"`, because a sign or a decimal point is not a digit, so it cannot validate a negative or decimal number.

## `in`, and the case trap

`in` asks a different question depending on what sits on its right:

- a string — is this a substring? `"pass" in "password"` is `True`.
- a list — is this a whole element? `"pass" in ["password"]` is `False`.
- a dict — is this a **key**? Values are not searched, so `"SSH" in services` is `False`.

`not in` is the negation. All of these are case-sensitive: `"Password"` and `"password"` are different strings.

To match regardless of case and still get back the spelling actually stored, lower both sides for the comparison only:

```python
for f in fruits:
    if f.lower() == word.lower():
        print(f)
```

`.lower()` produces a throwaway copy for the test; the list keeps its own spelling, and that is what gets printed. Generating every upper/lower variant of the word instead is a dead end — a 10-letter word has 1024 of them.

## Lists

An ordered collection in square brackets, mixing types freely.

```python
ports = [22, 80, 443, 8080]
```

Lists use the same indexing and slicing as strings — `ports[0]` is `22`, `ports[-1]` is `8080`, `ports[1:3]` is `[80, 443]` — but unlike strings they can be changed in place: `ports[0] = 2222` turns the list into `[2222, 80, 443, 8080]`.

- `.append(x)` — adds to the end: `ports.append(3306)` puts 3306 after 8080.
- `.remove(x)` — removes by value, not by position: `ports.remove(80)` takes out the 80. Only the first occurrence goes; if `x` is absent, `ValueError: list.remove(x): x not in list`.
- `.pop(i)` — removes the item at index `i` and returns it: the call itself turns into the removed value, so `first = ports.pop(0)` keeps what was pulled out. With no argument it takes the last item; past the end it raises `IndexError: pop index out of range`.
- `.sort()` / `.reverse()` — `.sort()` puts the items in ascending order, smallest first; `.reverse()` only flips the current order, it does not sort. Both rearrange the list in place and return `None`. Write `ports = ports.sort()` and `ports` is now `None`; the next method call on it fails with `AttributeError: 'NoneType' object has no attribute ...`.
- `len(lst)` — the number of items.

## Dictionaries

Key–value pairs in curly braces: look the key up, get the value back.

```python
services = {22: "SSH", 80: "HTTP"}
```

`services[22]` returns the value. A missing key raises `KeyError`. `.get()` gives you a fallback instead of a crash, and returns `None` when you leave the fallback out.

```python
services.get(9999, "Unknown")
```

Assigning to a key adds it if it was not there and overwrites it if it was.

```python
services[8080] = "HTTP-Alt"
```

```python
services[22] = "OpenSSH"
```

`del` removes a key and its value together, and raises `KeyError` if the key is not there.

```python
del services[22]
```

To check a key before using it, ask with `in`:

```python
if 22 in services:
    print(f"Port 22 runs {services[22]}")
```

The type of the key matters. `22` and `"22"` are different keys, and a port read with `input()` is the string, so `services[port]` fails with `KeyError: '22'` until it is converted. The quotes in that message are the giveaway.

`.keys()`, `.values()` and `.items()` return the keys, the values and the pairs. For `{22: "SSH", 80: "HTTP"}` they print as `dict_keys([22, 80])`, `dict_values(['SSH', 'HTTP'])` and `dict_items([(22, 'SSH'), (80, 'HTTP')])`. Each pair is a tuple, a fixed sequence in round brackets such as `(22, 'SSH')`, which is why the loop below can unpack it into two names. Looping over a dict directly gives you the keys only.

## Loops

```python
for ip in targets:
    print(f"Scanning {ip}...")
```

`for` walks anything with items in it — a list, a string character by character, a dict's keys — binding each one to the loop name in turn.

`range()` produces a run of numbers for a loop to walk, when there is no list to walk and you just need to count. The rule behind all three forms: counting runs *up to* the stop value, never onto it.

```python
for i in range(5):
    print(i)
```

One argument is the stop, and counting starts at 0, so this prints `0 1 2 3 4` — five numbers, but no 5.

```python
for i in range(1, 6):
    print(i)
```

Two arguments are start and stop. The start is included and the stop is not, so this prints `1 2 3 4 5`: to reach 5, you write 6.

```python
for i in range(0, 20, 5):
    print(i)
```

The third argument is the step, how much to add each time. This prints `0 5 10 15`; 20 is the stop, so it never appears.

A start that is already past the stop gives nothing at all, with no error: `range(5, 1)` is empty and the loop body never runs. Counting down needs a negative step — `range(5, 0, -1)` gives `5 4 3 2 1`.

`print(range(5))` shows `range(0, 5)`, not the numbers, because a range hands out its numbers one at a time instead of storing them. Wrap it in `list()` to see them all: `list(range(5))` is `[0, 1, 2, 3, 4]`.

`i` is the conventional name for a counter like this; when a loop walks real items, name the loop variable after the item instead (`for port in ports`).

```python
for port, name in services.items():
    print(f"{port} = {name}")
```

A string is a sequence too, so `for` walks it one character at a time — the basis of every password check.

```python
for char in password:
    if char.isdigit():
        print(f"Found digit: {char}")
```

```python
attempts = 0
while attempts < 3:
    password = input("Password: ")
    attempts += 1
```

`while` repeats for as long as its condition holds, re-checking it before every pass. Something inside the body has to change what the condition reads — here `attempts += 1` — or the loop never ends; Ctrl+C gets you out.

`break` leaves the loop on the spot: the rest of the body is skipped and the remaining items are never visited.

```python
for port in [22, 80, 443, 8080]:
    if port == 443:
        break
    print(f"Checked port {port}")
```

That prints 22 and 80 only; 8080 is never reached.

`continue` abandons only the current pass and jumps to the next item — the standard way to skip blank lines.

```python
for line in lines:
    if line == "":
        continue
    print(f"Processing: {line}")
```

Rule of thumb: `for` when you know what you are walking, `while` when you are waiting for something to change.

## The failures you will actually meet

- `SyntaxError: invalid syntax. Maybe you meant '==' ...` — an `=` inside a condition.
- `SyntaxError: expected ':'` — the line opening a block lost its colon.
- `IndentationError: expected an indented block` — the body of a block is not indented.
- `TypeError: can only concatenate str (not "int") to str` — a value from `input()` used as a number.
- Every input lands in `else`, no error — an unconverted `input()` string compared with `==` against a number.
- `TypeError: '<' not supported between instances of 'str' and 'int'` — the same mistake with `<` or `>`.
- `ValueError: invalid literal for int() with base 10` — `int()` was handed a decimal or non-numeric string.
- `KeyError: '22'` — the key was looked up as a string, but stored as a number (or the reverse).
- `AttributeError: 'NoneType' object has no attribute ...` — you kept the return value of `.sort()`, `.reverse()` or `.append()`, which is `None`.
- `TypeError: 'str' object does not support item assignment` — tried to change a string in place.

Related: [[Bash-Scripting]] covers the shell side, and [[Public-Exploit-Workflow]] is where you will read and patch other people's Python.
