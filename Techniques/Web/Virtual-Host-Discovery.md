# Virtual Host Discovery

One IP address, one open port, and possibly several completely different web applications. A web server picks which site to serve by reading the `Host:` header of the request, so a name that resolves nowhere in DNS can still be a live application — you just have to ask for it by name. This note is how you find those names. Its DNS-based counterpart is [[Subdomain-Discovery]]; same goal, different mechanism, and on a lab box this one is far more often the answer.

> [!important]
> A vhost is a Host-header trick, not a DNS record. Everything you find here is invisible to `nslookup`, `host` and `dig`, and stays unreachable in a browser until you add the name to `/etc/hosts` yourself — one line, `<target IP>  <name>`, on the attacking machine.

## Establish the default response

```bash
curl -s -H 'Host: zz-not-a-real-vhost.htb' http://target.htb/ | wc -c
```

```bash
curl -sI -H 'Host: zz-not-a-real-vhost.htb' http://target.htb/
```

- `-H 'Host: ...'` → the whole technique in one flag. You connect to the IP, but ask for a different site by name
- a name that cannot exist → same rule as any baseline: if you probe with `dev` or `admin` and it happens to be real, you have calibrated your filter against a hit and will filter out the finding
- `| wc -c` → the byte count that `-fs` / `--exclude-length` will take. Record it now
- `-sI` → headers only, on the second call. A `Server:` or `Location:` that changes per vhost is a second discriminator when sizes are too close to separate

## Brute force the Host header

```bash
gobuster vhost -u http://target.htb --domain target.htb --append-domain \
  -w /usr/share/seclists/Discovery/DNS/subdomains-top1million-20000.txt \
  --exclude-length 11952 -t 30
```

- `vhost` → Host-header mode. It does not touch DNS and does not request paths; if you wanted paths you are in the wrong mode and should be in [[Content-Discovery]]
- `--append-domain` → sends `dev.target.htb` rather than the bare word `dev`. **The flag that is easy to omit**, and omitting it makes every request ask for a single-label host that no vhost config matches, so you get a clean run of zero results and conclude wrongly that there are no vhosts. Older gobuster versions appended by default, which is exactly why this trips people
- `--domain` → the base name appended. Get this from the certificate's CN or a redirect, not from a guess; a wrong base domain produces the same silent zero as the flag above
- `--exclude-length 11952` → drop responses of the default page's size. Takes a range too (`--exclude-length 250-320`) when the default varies slightly
- `-t 30` → threads; the same tradeoff as any brute force, and vhost sweeps are noisy by nature

## The same sweep with ffuf, when sizes collide

<!-- dup-ok -->
```bash
ffuf -w /usr/share/seclists/Discovery/DNS/subdomains-top1million-5000.txt \
  -u http://target.htb -H 'Host: FUZZ.target.htb' -fw 1274 -mc all
```

- `-H 'Host: FUZZ.target.htb'` → `FUZZ` goes in the **header**, not the URL. This is the distinction between this note and [[Content-Discovery]]: same tool, same wordlist format, one keyword moved. Put `FUZZ` in the URL by mistake and you will spend the run fuzzing paths and wondering why the results look like a directory listing
- `-fw 1274` → filter by word count, the number to use when the body length varies per request
- `-mc all` → show every status. Vhosts frequently answer 301 or 401 rather than 200, and the default `-mc` set will hide them
- `-fs`, `-fl` → the size and line equivalents, when word count is the one that collides
