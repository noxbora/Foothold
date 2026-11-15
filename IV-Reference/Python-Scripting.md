# Python Scripting — the moving parts

Values, the names they sit behind, the collections that hold many of them and the loops that walk those collections; then the functions, error handling, files and libraries that turn a handful of lines into a tool. That is enough to read a proof-of-concept you did not write and change the one line that needs changing. Look things up here; the attack itself lives elsewhere.

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

The core types are `str` (text), `int` (whole number), `float` (number with a decimal point), `bool` (`True`/`False`), `list` and `dict`. `type(x)` tells you which one you are holding, printed as `<class 'str'>`, `<class 'int'>` and so on.

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

Reusing the outer quote inside the braces — `f"{services.get(port, "Unknown")}"` — works from Python 3.12 on; anything older stops with a `SyntaxError`. Switch to the other quote inside, or work the value out on the line above.

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

The comparison operators, each answering `True` or `False`: `==` equal, `!=` not equal, `<` less than, `>` greater than, `<=` less than or equal, `>=` greater than or equal.

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

The numbers are positions, not counts, so the two halves are not mirror images: `[:4]` is the first four characters, but `[2:]` is not the last two — it skips the first two and keeps the rest. To take the last few, count from the end with a negative number: `"Python"[-2:]` is `"on"`, and `"Python"[:-2]` drops the last two to give `"Pyth"`.

Counting characters breaks as soon as the lengths vary. `"192.168.1.15"[-2:]` happens to give `15`, but `"192.168.1.5"[-2:]` gives `.5`. When the piece you want is fenced off by a separator, split on the separator instead: `"192.168.1.5".split(".")[-1]` is `"5"` whatever its length.

Strings cannot be changed in place: `s[0] = "J"` raises `TypeError: 'str' object does not support item assignment`. Every method hands back a *new* string instead, so `name.lower()` on a line of its own does nothing to `name`. Keep the result.

```python
name = name.lower()
```

The methods worth knowing, with the part people get wrong:

- `.lower()` / `.upper()` — the names come from the printer's type cases: capitals were kept in the upper one.
- `.strip()` — trims whitespace from both ends only, never from the middle. The newline `\n` that ends a line read from a file counts as whitespace, so it goes too.
- `.replace(a, b)` — replaces every occurrence, not the first, in one left-to-right pass that never rescans its own result: `"....//".replace("../", "")` leaves `"../"` behind.
- `.split()` — with no argument, splits on any run of whitespace and drops the empties; `.split(" ")` splits on each single space, so `"a  b"` becomes `['a', '', 'b']`. The pieces are always strings, even when they look like numbers — `"22,80".split(",")` is `['22', '80']` — so convert each one inside the loop; `int()` on the whole list is a `TypeError`. A separator at the very start, or two in a row, leaves an empty string in the list: `"/a/b".split("/")` is `['', 'a', 'b']`.
- `.startswith(x)` / `.endswith(x)` / `.count(x)` — exactly what they say.
- `*` with a number repeats a string: `"*" * 5` is `"*****"`, so `"*" * len(password)` logs how long a password was without logging the password.
- `.isdigit()`, `.isalpha()`, `.isalnum()`, `.isupper()`, `.islower()` — return `True`/`False`. `.isdigit()` is `False` for `"-5"` and `"3.14"`, because a sign or a decimal point is not a digit, so it cannot validate a negative or decimal number. An empty string is `False` too. It is the check to run *before* `int()` on anything a user typed: test the string, then convert on a line of its own with `port = int(port)`.

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

An ordered collection in square brackets, mixing types freely. Lists use the same indexing and slicing as strings, but unlike strings they can be changed in place: `ports[0] = 2222`.

- `.append(x)` — adds to the end. The value goes inside the parentheses, `ports.append(443)`; start from an empty list `[]`, not `""` (an empty string) or `{}` (an empty dict), neither of which has `.append()`.
- `.remove(x)` — removes the first occurrence only; if `x` is absent, `ValueError: list.remove(x): x not in list`.
- `.pop(i)` — removes the item at index `i` and returns it: the call itself turns into the removed value, so `first = ports.pop(0)` keeps what was pulled out. With no argument it takes the last item; past the end it raises `IndexError: pop index out of range`.
- `.sort()` / `.reverse()` — `.sort()` puts the items in ascending order, smallest first; `.reverse()` only flips the current order, it does not sort. Both rearrange the list in place and return `None`. Write `ports = ports.sort()` and `ports` is now `None`; the next method call on it fails with `AttributeError: 'NoneType' object has no attribute ...`. For a sorted copy that leaves the original alone, use `sorted(ports)` — a function, not a method, so `ports.sorted()` fails with `AttributeError: 'list' object has no attribute 'sorted'`.
- `len(lst)` — the number of items.

## Dictionaries

Key–value pairs in curly braces: look the key up, get the value back.

```python
services = {22: "SSH", 80: "HTTP"}
```

`services[22]` returns the value, and the key can just as well come from a variable: `services[port]`. The brackets take a key, never a position, so `services[0]` looks for a key `0`. A missing key raises `KeyError`. `.get()` gives you a fallback instead of a crash, and returns `None` when you leave the fallback out.

```python
services.get(9999, "Unknown")
```

Assigning to a key adds it or overwrites it; `del services[22]` removes it.

The type of the key matters. `22` and `"22"` are different keys, and a port read with `input()` is the string, so `services[port]` fails with `KeyError: '22'` until it is converted. The quotes in that message are the giveaway.

`.keys()`, `.values()` and `.items()` return the keys, the values and the pairs. Each pair is a tuple, a fixed sequence in round brackets such as `(22, 'SSH')`, which is why the loop below can unpack it into two names. Looping over a dict directly gives you the keys only. `len(services)` counts the pairs. To ask whether a key exists, write `port in services`; `port in services.items()` is always `False`, because a bare key never equals a pair.

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

`while` repeats for as long as its condition holds, re-checking it before every pass. Something inside the body has to change what the condition reads — here `attempts += 1` — or the loop never ends; Ctrl+C gets you out. The check happens only there, at the top: a value that crosses the line halfway through the body still finishes that pass, so print-then-decrement and decrement-then-print give different output.

`break` leaves the loop on the spot: the rest of the body is skipped and the remaining items are never visited.

```python
for port in [22, 80, 443, 8080]:
    if port == 443:
        break
    print(f"Checked port {port}")
```

That prints 22 and 80 only; 8080 is never reached.

`continue` abandons only the current pass and jumps to the next item — the standard way to skip blank lines. Nothing below it in the body runs for that pass, so a counter of skipped items has to sit above it.

```python
for line in lines:
    if line == "":
        continue
    print(f"Processing: {line}")
```

Rule of thumb: `for` when you know what you are walking, `while` when you are waiting for something to change.

## Functions

```python
def greet(name):
    print(f"Hello, {name}")
```

`def` defines a function: a named block written once and run as often as you like. Nothing in the body runs when it is defined; it runs only when called, by name with parentheses — `greet("Alice")`. Leave the parentheses off and nothing happens, with no error: the bare name is just the function itself, which is why `print(greet)` shows `<function greet at 0x...>`. The `def` has to sit above the line that calls it, or that line fails with `NameError`.

The *parameter* is the name in the definition (`name`); the *argument* is the value handed over in the call (`"Alice"`). A call must supply one argument per parameter, in the same order, or it fails with `TypeError: greet() missing 1 required positional argument: 'name'`.

```python
def check_length(password, min_length=8):
    return len(password) >= min_length
```

`return` hands a value back and leaves the function on the spot; nothing below it runs on that call. The call itself turns into the returned value, so keep it: `ok = check_length(pw)`. A function that runs off its end without a `return`, or hits a bare `return`, hands back `None`. Printing is not returning: `print()` puts the value on screen and the caller still gets `None`.

A default value (`min_length=8`) makes that argument optional; pass one and it overrides the default. Defaults come after every parameter without one — `def f(a=1, b):` is refused with `SyntaxError: parameter without a default follows parameter with a default` (`non-default argument follows default argument` before Python 3.12). Never make a list or dict the default: it is built once, when the function is defined, so every call shares and keeps piling into the same one. Default to `None` and build the list inside.

`return score, feedback` sends back several values at once, packed into a tuple, and the caller unpacks them by position: `score, feedback = check_password(pw, common)`. The count on the left must match, or it fails with `ValueError: too many values to unpack` / `not enough values to unpack`.

A triple-quoted string on the first line of the body is a docstring: it documents the function, `help(check_password)` prints it, and it runs nothing.

A name created inside a function is local: it exists only for the length of that call and is invisible outside it, so `print(result)` after the call fails with `NameError: name 'result' is not defined`. Get a value out with `return`, never by reaching in. The other direction half-works: a function can read a name defined outside it, but assigning to that name inside creates a separate local one and leaves the outer one untouched.

Wrapping the whole program in `def main():` and calling `main()` on the last line keeps its names local too, and gives the script one obvious place to start reading.

## Error handling

An error nobody catches is an exception. Python prints a traceback — the chain of calls that led there, ending with the failing line and the exception's type and message — and the script stops dead. In a loop over a thousand hosts, one bad value takes the other 999 down with it.

```python
try:
    port = int(text)
except ValueError:
    print("Not a number")
```

The `try` block runs first. If nothing goes wrong, the `except` block is skipped entirely. If a line raises, the rest of the `try` block is abandoned at that line and Python jumps to the first `except` whose type matches; afterwards the script carries on below the whole structure. An exception that matches no `except` crashes the script exactly as before. Keep only the risky lines inside `try`: everything in there is guarded, including the mistakes you would want to see.

The type to catch is the first word of the traceback's last line:

- `ValueError` — the right type, an unusable value: `int("abc")`.
- `FileNotFoundError` — `open()` for reading on a path that does not exist.
- `ZeroDivisionError` — `10 / 0`, and `//` or `%` by zero.
- `KeyError` — a dict key that is not there.
- `IndexError` — a list or string index past the end.

Several `except` blocks can hang off one `try`, each handling its own error; only the first match runs, so the specific ones go first.

`except Exception as e:` catches almost everything, and `e` holds the message to print. It swallows bugs along with the errors you expected, so it belongs last, under the specific ones, if at all. It deliberately lets Ctrl+C (`KeyboardInterrupt`) through; a bare `except:` with no type catches that too, and a `while True` loop wrapped in one can no longer be stopped with Ctrl+C.

```python
while True:
    try:
        port = int(input("Port: "))
        break
    except ValueError:
        print("Whole number, please.")
```

The retry loop: `break` sits inside `try`, after the risky line, so it is reached only when the conversion worked. A failure jumps over it to `except`, and the loop asks again.

## Files

```python
with open("wordlist.txt", "r") as f:
    for line in f:
        word = line.strip()
```

`open()` takes a path and a mode. `with` is a context manager: it closes the file the moment the indented block ends, even when an error escapes the block. The older pattern — `f = open(...)`, work, `f.close()` — leaves the file open whenever something fails before `close()`. Once the block has ended the file is shut, and `f.read()` there fails with `ValueError: I/O operation on closed file.`

A relative path is resolved from the directory you are standing in when you run the script, not from where the script lives: run `python3 tools/check.py` from your home directory and it looks for `~/wordlist.txt`, failing with `FileNotFoundError`. Run it from the script's folder, or give the full path.

- `"r"` — read; also the default when the mode is left out. The file must exist.
- `"w"` — write. Creates the file, or **empties an existing one the instant it is opened**, before a single line is written.
- `"a"` — append. Creates the file, or adds to the end of what is already there.

Reading:

- `.read()` — the whole file as one string. A second `.read()` returns `""`: the position is already at the end.
- `.readline()` — the next line only.
- `.readlines()` — a list of every line.
- `for line in f` — one line at a time, never the whole file in memory at once: the way to walk a wordlist of millions.

Every line read keeps its trailing newline, `.readlines()` included — `['admin\n', 'root\n']` — and `"admin" == "admin\n"` is `False`, so the word never matches anything. `.strip()` each line before using it.

On Kali, text mode decodes the bytes as UTF-8. Real-world wordlists, rockyou.txt among them, contain bytes that are not valid UTF-8, and the read dies halfway with `UnicodeDecodeError: 'utf-8' codec can't decode byte ...`. `open(path, encoding="latin-1")` maps every possible byte to a character, so it never fails.

```python
with open("results.txt", "a") as f:
    f.write(f"Open: {port}\n")
```

`.write()` adds no newline of its own: leave out `\n` and every result lands on one line. It takes only a string — `f.write(22)` fails with `TypeError: write() argument must be str, not int` — so go through an f-string or `str()`.

## Libraries

A library (module) is code someone else wrote, pulled in with `import`. The standard library ships with Python; there is nothing to install.

```python
import os
```

Brings in the whole module; its contents are reached through the module name — `os.getcwd()`.

```python
from datetime import datetime
```

Brings in one name, used bare — `datetime.now()`. Mixing the two styles is the classic trap: after `import datetime`, `datetime.now()` fails with `AttributeError: module 'datetime' has no attribute 'now'`, because the module and the class inside it share a name. The long form is `datetime.datetime.now()`.

```python
import datetime as dt
```

An alias — a shorter name for the same module: `dt.datetime.now()`.

Never name your own script after a module it imports — `string.py`, `random.py`, `requests.py`. Python finds your file first and imports that instead, and the next line fails with `AttributeError: module 'string' has no attribute 'digits'`. Rename the file.

- `os` — the operating system: current directory, file listings, environment variables.
- `sys` — the interpreter itself. `sys.argv` is the command-line arguments as a list: `sys.argv[0]` is the script's own name, the first real argument is `sys.argv[1]`, and every one of them is a string.
- `random` — random numbers and choices.
- `datetime` — dates, times, timestamps.
- `json` — reads and writes JSON (JavaScript Object Notation), the format most APIs answer in.
- `hashlib` — hashing. It hashes bytes, not text: `hashlib.sha256("abc")` fails with `TypeError: Strings must be encoded before hashing`.
- `string` — ready-made character sets: `string.ascii_uppercase` (A–Z), `string.digits` (0–9), `string.punctuation`.

```python
hashlib.sha256("password".encode()).hexdigest()
```

`.encode()` turns the text into bytes; `.hexdigest()` turns the raw hash into the familiar hex string. Change one character of the input and the whole hash changes.

The `string` sets are plain ASCII (American Standard Code for Information Interchange). `string.punctuation` is exactly these 32 symbols: `` !"#$%&'()*+,-./:;<=>?@[\]^_`{|}~ `` — no space, no `£`, no `é`. Likewise `"Ç" in string.ascii_uppercase` is `False`, while `"Ç".isupper()` is `True`. A check built on these sets simply does not count such characters.

### pip

Third-party libraries live on PyPI (the Python Package Index) and are installed with pip, Python's package installer. On Kali a bare `pip install` is refused with `error: externally-managed-environment`: the system Python belongs to APT, and since Python 3.12 Kali stops pip installing into it, `--user` included. The ways round it, best first:

```bash
sudo apt install python3-requests
```

Kali's own packaged copy, when one exists: `python3-` plus the library's name.

```bash
python3 -m venv venv
```

```bash
source venv/bin/activate
```

```bash
pip install requests
```

A virtual environment: a private Python in the `venv` folder that pip may install into freely. It works only while activated — the prompt shows `(venv)` — and the same script run outside it fails with `ModuleNotFoundError: No module named 'requests'`. `deactivate` leaves it.

```bash
pipx install <tool>
```

For a Python tool you run as a command rather than import: pipx gives each tool a venv of its own and puts the command on your PATH. Pre-installed since Kali 2024.4.

`--break-system-packages` forces pip through regardless, and can break tools Kali itself depends on. Last resort.

The install name and the import name do not always match: `pip install beautifulsoup4` is `import bs4` (HTML parsing), and `pip install pwntools` is `from pwn import *` (exploit and CTF toolkit). The rest of the usual set imports under its own name: `requests` (HTTP requests), `scapy` (crafting, sending and sniffing packets), `paramiko` (SSH client and server).

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
- `SyntaxError: cannot assign to function call` — a call sits where a plain name belongs: on the left of `=` (`notes.append() = x`) or straight after `for` (`for line.strip() in lines`).
- `TypeError: 'int' object is not iterable` — a `for` was handed a single number. Walk `range(n)` to repeat `n` times; to walk values collected one by one, `.append()` each to a list instead of overwriting one name.

Related: [[Bash-Scripting]] covers the shell side, and [[Public-Exploit-Workflow]] is where you will read and patch other people's Python.
