# File Upload Bypass

An upload form is only a vulnerability when two separate things are true: the server stores your file somewhere you can reach, and it treats that file as code rather than data. Most notes on this subject teach the second half and skip the first, which is why so much time gets spent crafting a payload for a directory nobody can request.

## 1 — Where does the file land, and can you reach it

```bash
curl -s -F "file=@marker.txt" -F "submit=1" http://TARGET/upload.php
```

- Upload a plain text file with a unique string inside it first, never a payload. You are mapping the plumbing, and a benign file will not be quarantined or logged as an attack.
- Read the response body in full. Many applications print the stored path, the stored name or an identifier straight back to you, and that saves the whole search.
- If the response says nothing, the stored name is usually the original name, a timestamp, or a hash. Upload the same file twice: an unchanged name means no rewriting, a changed one tells you the naming scheme.

## 2 — Making the server treat it as code

```bash
curl -s -F "file=@shell.php;filename=shell.php.jpg;type=image/jpeg" http://TARGET/upload.php
```

```bash
curl -s -F "file=@shell.phtml;type=image/png" http://TARGET/upload.php
```

- The extension check is usually a blocklist, and a blocklist is a list of things somebody thought of. `.phtml`, `.php5`, `.phar` and `.inc` all execute on a stock Apache with `php` enabled and are missed constantly.
- `type=` sets the [[Security-Terms#^mime|MIME]] type in the request, which is a value you control and the server frequently believes. It costs nothing to set it correctly and it defeats an entire class of check on its own.
- A magic-byte check reads the first bytes of the file. Prepending `GIF89a` to a text payload satisfies it, because that check has no opinion about what follows.
- Storing and executing are separate permissions. A file written into a directory the web server serves but does not execute is still only data.
