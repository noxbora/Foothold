# Curl and Wget

Two HTTP clients for two jobs. **curl** probes and interacts — it prints the response to stdout, so you read status codes, headers and bodies and send crafted requests. **wget** fetches and mirrors — it writes to a file by default. The split (curl to stdout, wget to disk) is the thing to keep straight; most "why did nothing print / why is there no file" confusion is reaching for the wrong one.

## Probe: is it there, and what does it answer?

```bash
curl -I http://TARGET_IP/
```

```bash
curl -s -o /dev/null -w "%{http_code}\n" http://TARGET_IP/admin
```

- `-I` → HEAD request: headers only. Fast identification of the server, framework and redirects without pulling the body.
- `-s` → silent: drop the progress meter so it does not pollute scripted output.
- `-o /dev/null -w "%{http_code}\n"` → throw away the body, print **only** the status code. This is the backbone of any bulk check — it is how you tell `200` from `301` from `403` across a wordlist without reading a single body.
- `-k` → accept a self-signed or expired certificate. **Required** against the certs common in labs; without it an HTTPS probe dies with `SSL certificate problem` and you wrongly read the service as down.
- `-L` → follow redirects. Without it a `301`/`302` shows you the redirect's tiny body, not the destination — so you see a blank page and conclude the path is empty when it moved.

## Interact: send data, carry a session

```bash
curl -X POST -d "user=admin&pass=test" -b "PHPSESSID=abc123" http://TARGET_IP/login
```

```bash
curl -F "file=@shell.php" http://TARGET_IP/upload
```

- `-X POST -d "..."` → send form data as a POST. `-d` implies POST, but naming `-X` keeps it explicit when you are reading back a command later.
- `-b "name=value"` → send a cookie — this is how you replay a session token pulled from a capture ([[TShark]]) or from another response.
- `-F "file=@localfile"` → multipart upload, the `@` reading the file from disk. The tool for testing an upload vulnerability from the command line.
- `-A "<string>"` → set the User-Agent, for a filter that keys on it.
- `-v` → verbose: shows the full request and response including headers, so you can see exactly what you sent when a request behaves unexpectedly. The first thing to add when a POST "does nothing".

## Download and mirror

```bash
wget http://TARGET_IP/backup.zip -O /tmp/backup.zip
```

```bash
wget -r -np -k http://TARGET_IP/exposed/ -P /tmp/loot
```

- `-O <file>` → name the output. Without it wget derives a name from the URL, which for a path ending in `/` becomes a confusing `index.html`.
- `-r -np` → recursive mirror, `--no-parent` so it does not climb above the directory you pointed at and start pulling the whole site.
- `-k` → convert links for offline viewing after the mirror.
- `--header="Cookie: PHPSESSID=abc"` → mirror behind a session, when the exposed directory needs auth you already hold.
- `-q` → quiet, for scripts.
