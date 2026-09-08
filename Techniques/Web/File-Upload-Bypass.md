---
type: technique
platform: web
status: working
fluency: guided
source: reading
updated: 2026-09-03
---

# File Upload Bypass

An upload form is only a vulnerability when two separate things are true: the server stores your file somewhere you can reach, and it treats that file as code rather than data. Most notes on this subject teach the second half and skip the first, which is why so much time gets spent crafting a payload for a directory nobody can request.

Reach for this note when anything accepts a file: an avatar, an import, a document, a bulk upload, a support attachment.

## 1 — Where does the file land, and can you reach it

**Why now** — you have an upload form and nothing else. Answer this before touching extensions, because a working payload in an unreachable directory is worth nothing and this test costs one upload.

```bash
curl -s -F "file=@marker.txt" -F "submit=1" http://TARGET/upload.php
```

- Upload a plain text file with a unique string inside it first, never a payload. You are mapping the plumbing, and a benign file will not be quarantined or logged as an attack.
- Read the response body in full. Many applications print the stored path, the stored name or an identifier straight back to you, and that saves the whole search.
- If the response says nothing, the stored name is usually the original name, a timestamp, or a hash. Upload the same file twice: an unchanged name means no rewriting, a changed one tells you the naming scheme.

**What you will see**

- **Found** — the response contains a path, or your marker string is retrievable at a guessable location under `/uploads/`, `/files/`, `/images/` or the application's own media route.
- **Empty** — an upload that succeeds and reveals nothing. Not a dead end: run [[Content-Discovery]] against the likely directories, since the file exists somewhere and directory listing is often left on.
- **Error** — a size, type or extension rejection here is information you wanted anyway, because it tells you which check runs first. Note the exact wording; it changes as you get past each layer.
- **Noise** — a success message means the form accepted the request, not that a file was written. Confirm by retrieving the marker, never by trusting the banner.

**Then** — a retrievable file goes to section 2. A stored but unreachable file means the value is in what the application does with it later, so read [[XXE]] if it parses the file and stop treating this as a shell path.

## 2 — Making the server treat it as code

**Why now** — you can retrieve what you upload. Now you are attacking whichever check the application actually performs, and there are only three places to look: the extension, the declared type, and the bytes.

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

**What you will see**

- **Found** — retrieving the uploaded file runs it: your marker output appears instead of the file's text, or a parameter you added is echoed back.
- **Empty** — the file is served as plain text or downloaded. This is the most common outcome and it is a real answer: storage works, execution does not, and the directory has execution turned off.
- **Error** — a rejection that names your extension means the check is on the name. A rejection that survives a corrected extension means it is on the content. Which one complains tells you what to change next.
- **Noise** — an image that renders correctly proves nothing either way, because a valid image with a payload appended is still a valid image.

**Then** — execution goes to [[Shells]] for the upgrade to something interactive. Storage without execution goes to the Rarely section below, where the target stops being the uploaded file and becomes the configuration around it.

## Rarely — worth one command, not worth a step

**Why now** — the directory stores but will not execute, or the check reads the file's real content. These are single attempts against a specific defence, not a search.

```bash
curl -s -F "file=@evil.svg;type=image/svg+xml" http://TARGET/upload.php
```

```bash
curl -s -F "file=@.htaccess;filename=.htaccess" http://TARGET/upload.php
```

- An `svg` is markup, not a raster image, so it carries script and entity declarations into a page that trusts it. When a site accepts it as an avatar it is usually accepting it unfiltered.
- Uploading an `.htaccess` into a directory that stores but does not execute can turn execution back on for that directory. It only works on Apache with overrides permitted, which is exactly why it is here and not above.
- A double extension, a trailing dot, a trailing space or a null byte in the name all target the gap between the check and the write. They belong to old stacks; try one, not all six.

**What you will see**

- **Found** — the `svg` renders and your marker executes in the page, or the previously inert directory starts executing after the config upload.
- **Empty** — the normal answer on a maintained stack. These are lottery tickets, not steps.
- **Error** — a rejection naming the file type means there is an allowlist, which ends this line of attack cleanly.
- **Noise** — a stored `.htaccess` that changes nothing looks identical to one that was silently discarded. Re-request the earlier upload to tell them apart.

**Then** — a rendering `svg` goes to [[XSS]] and, if entities are parsed, to [[XXE]]. Everything empty here means the upload is a storage bug rather than an execution bug, and that goes in the report rather than in another hour.

## Reading the output

Upload work fails in one specific way: you change three things at once and something works, and you cannot say what. Every attempt should differ from the last in exactly one dimension — name, declared type, or bytes.

The second trap is grading by the upload response. The response tells you the form accepted your request. Only retrieving the file tells you what the server did with it, and those two answers disagree more often than they agree.

## Next

- [[Shells]] — where a working upload goes the moment it executes
- [[Content-Discovery]] — how to find the storage directory when the response will not say
- [[Command-Injection]] — the same goal by another route when the upload is a dead end

## Gaps

- No coverage of upload endpoints that hand the file to a converter, which moves the attack from execution to the parser.
- Nothing on signed or pre-signed upload URLs, which are now the common pattern in cloud-hosted applications.
- Zip extraction and path traversal inside the archive are not covered at all.
