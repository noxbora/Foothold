---
type: reference
platform: any
status: working
fluency: guided
source: reading
updated: 2026-10-02
---

# Security & Technical Terms

## A

_**Accountability**_: Refers to the principle of holding users and systems responsible for their actions by ensuring that activities can be traced back to a specific entity, typically achieved through logging, auditing, and the accounting component of access control.

_**ACE (Access Control Entry)**_: one row in a Windows access control list: one trustee (a user or a group) plus the rights it is granted or denied on one object. An ACL is nothing but an ordered list of ACEs, so when a tool reports that you can write to a service, it is one ACE that says so — and that single row is the whole finding. ^ace

_**Acknowledge**_: To accept, admit, or show awareness of something. To confirm the receipt of data or a message in networking and communication protocols.

_**ACL (Access Control List)**_: the permission list attached to every securable Windows object — file, registry key, service, Active Directory object. Every object carries two: the DACL, which decides who may do what, and the SACL, which decides what gets logged. A report that says "weak ACL" always means the DACL. The Linux equivalent, set with `setfacl`, is a per-file extension to the usual owner/group/other bits and shows up as a trailing `+` in `ls -l`. ^acl

_**ADSI (Active Directory Service Interfaces)**_: the programming interface Windows ships for talking to a directory, and the reason `[adsisearcher]` works in any PowerShell on a domain-joined host with nothing installed and nothing downloaded. It binds to the current domain using the token you are already holding, which makes it the fallback when the administration tools are absent and you cannot write a script to disk. ^adsi

_**AES (Advanced Encryption Standard)**_: the block cipher used almost everywhere modern encryption is required, in 128-bit and 256-bit key sizes. In a domain it matters because Kerberos can encrypt a ticket with either AES or the older [[Security-Terms#^rc4|RC4]], and which one was used decides the cracking mode and how expensive the crack is. ^aes

_**AlwaysInstallElevated**_: a pair of Windows registry values — one under HKLM, one under HKCU — that together let any user install an MSI package with SYSTEM privileges. It exists so an administrator can push software to users who are not admins. Both halves must be set to 1; that is why the check reads two keys and why finding only one is not a finding. ^alwaysinstallelevated

_**AMSI (Antimalware Scan Interface)**_: a Windows interface that hands script content — PowerShell, VBScript, an Office macro, a .NET assembly loaded in memory — to the installed antivirus at the moment it is about to run, after any unpacking or decoding. This is why a script that sits happily on disk dies the second you execute it, and why obfuscating the file alone changes nothing. ^amsi

_**ANSI escape codes**_: the invisible control sequences a program prints to colour text and move the cursor — `\033[31m` and friends. They matter when output is redirected: a colourised script piped into a file leaves those sequences in the file, so a later `grep` for a word that is on screen finds nothing because the word is broken by an escape sequence. Most tools take a `--no-color` flag for exactly this reason. ^ansi

_**Anycast**_: a network routing method in which traffic sent to a single IP address is delivered to the nearest or best-performing node among multiple servers sharing that address — commonly used in DNS infrastructure and DDoS mitigation.

_**API Key**_: a unique identifier used to authenticate requests to an API — if leaked or hardcoded into source code, it can allow unauthorized access to services, data, or cloud resources.

_**APIPA (Automatic Private IP Addressing)**_: the 169.254.x.x address a Windows machine gives itself when no DHCP server answers. Seeing one is a diagnosis, not a configuration: the machine is on a network segment where nothing handed out an address, so it can talk to nobody. ^apipa

_**ARP (Address Resolution Protocol)**_: how a host on a local network turns an IP address into the MAC address it must actually write onto the wire. Every machine keeps a small cache of the answers. ARP carries no authentication at all — any host can answer for any address — which is why the local segment is the classic place for a machine-in-the-middle. ^arp

_**Arrays**_: A data structure consisting of a collection of elements, each identified by at least one array index or key.

_**Artifact**_: Refers to any piece of digital evidence or data left behind by user or system activity, such as log entries, registry keys, browser history, or temporary files, which forensic investigators analyze to reconstruct events or detect malicious activity.

_**AS-REP**_: the first reply a Kerberos domain controller sends back to an authentication request. Normally the client must prove it knows the password before the DC will send it (pre-authentication). An account flagged "do not require Kerberos preauthentication" gets that reply sent to anybody who asks, and part of the reply is encrypted with the account's password — so it can be cracked offline. Harvesting those replies is AS-REP roasting. ^as-rep

_**ASCII**_: the 1963 character set: 128 characters, one byte each, English letters, digits and punctuation only. Everything else — accented letters, Turkish characters, emoji — needs a wider encoding such as UTF-8. The relevance here is transfer: a binary sent through a channel that assumes ASCII arrives corrupted, which is what "binary mode" in FTP and Base64 encoding both exist to prevent. ^ascii

_**ASIA key prefix**_: The identifier prefix marking a temporary STS access key, which is valid only until its expiration timestamp and only when accompanied by its session token — as opposed to `AKIA`, a long-lived IAM user key.

_**Asset**_: A useful or valuable thing, person, or quality; in a technical context, any data, device, or other component of an environment that supports information-related activities.

_**At scale**_: describing an operation or attack carried out across a large number of systems, targets, or users simultaneously, rather than against a single target.

_**Auth Coercion**_: forcing a service or host to authenticate to a machine the attacker controls, so that its credential material arrives on its own rather than being read off disk. Nothing is stolen and nobody is pressured — a protocol feature is invoked against its owner, which is what separates it from coercion in the social-engineering sense. On Windows the privilege being abused (typically `SeImpersonatePrivilege`) is the constant; the trigger used to make the service connect back — RogueWinRM, PrintSpoofer, GodPotato — changes with the OS version. ^auth-coercion

_**AutoLogon**_: the Windows feature that signs a fixed account in at boot with nobody at the keyboard, used for kiosks, lab machines and anything that must come back up unattended. Configured through the control panel it writes the password as literal text into `DefaultPassword` under the `Winlogon` registry key, readable by every user on the box; configured through the Sysinternals tool of the same name it writes the password into [[Security-Terms#^lsa-secrets|LSA secrets]] instead, where only SYSTEM can reach it. Two ways to set up one feature, with completely different consequences for you. ^autologon

_**AV (Antivirus)**_: the endpoint product that inspects files and, through [[Security-Terms#^amsi|AMSI]], scripts. On a lab box it matters mainly as an explanation for a command that ran perfectly yesterday and silently produces nothing today: the binary was quarantined between the two attempts. ^av

_**AXFR**_: the DNS zone transfer request. A secondary name server uses it to copy an entire zone from the primary in one go. A server configured to answer it for anyone hands over every record in the domain at once — hosts, subdomains, internal addresses — which is the fastest and quietest subdomain list you will ever get. Its absence is the normal case, not a failure. ^axfr

_**AzureHound**_: the [[Security-Terms#^bloodhound|BloodHound]] collector for the cloud directory rather than the on-premises one. Same idea from a different source: it gathers cloud identities, roles and application permissions and feeds them into the same graph, which is what makes a path running from a workstation into a cloud subscription visible at all. ^azurehound

## B

_**Bastion host**_: a hardened server exposed to an untrusted network (often the internet) that acts as the sole entry point into a private network, minimizing the attack surface.

_**Bind (LDAP)**_: the authentication step that opens an LDAP session. A simple bind sends a distinguished name and a password; an anonymous bind sends neither, and many directories still accept one and answer part of the tree. The word is the protocol's own term for logging in, not a network binding. ^bind

_**BITS (Background Intelligent Transfer Service)**_: a Windows service that transfers files in the background using bandwidth nobody else is using; Windows Update is built on it. `bitsadmin` and `Start-BitsTransfer` are worth knowing because the download is performed by a trusted system service rather than by your process. ^bits

_**Blend in**_: to avoid detection by appearing as normal, legitimate activity or traffic — as in malware that blends in with regular network traffic or an attacker who blends in with employees during a physical social engineering attempt.

_**Bloat**_: To become swollen or larger than normal. In computing, it refers to software that is slow and uses too much memory/disk space because it has too many unnecessary features.

_**BloodHound**_: a tool that collects Active Directory objects and their permissions, then draws them as a graph so you can ask "what is the shortest path from this account to Domain Admin" instead of reading permissions one object at a time. A collector (SharpHound) runs on the domain and produces JSON; the GUI answers the questions. ^bloodhound

_**BOLA (Broken Object Level Authorization)**_: An API authorization flaw where an endpoint accepts an object identifier from the request and returns or modifies the object without verifying the requester owns it, allowing any authenticated user to reach other users' objects by substituting the identifier. Known as IDOR in the broader web application context. It can appear in query strings ( `?owner_id=13`), request body fields (`{"user_id": 13}`), and custom headers (`X-User-ID: 13`). Any location where an object identifier is accepted without validation against the authenticated user is a potential vector.

_**BOM (Byte Order Mark)**_: a few invisible bytes some editors put at the very start of a file to declare its encoding. It causes trouble far out of proportion to its size: a PowerShell script or a wordlist saved with a BOM has three invisible characters before its first real character, so the first line silently fails to match, parse or execute while looking perfectly correct on screen. ^bom

_**Buffer**_: A temporary region of memory used to hold data while it is being moved or processed. ^buffer

_**Burp macro**_: a Burp Suite feature that automatically replays a predefined sequence of requests (e.g. to refresh an authentication token or session value) before or during other requests, used to maintain valid sessions during automated testing.

## C

_**CA (Certificate Authority)**_: the party whose signature turns a TLS certificate into one a browser will accept. Its own certificate is already in the operating system's trust store. A self-signed certificate is one where the subject signed for itself and no CA was involved, which is why a browser warns and why `curl` needs `-k` against a lab box. ^ca

_**CAPTCHA**_: the challenge a site shows to tell a human from a script. Meeting one during a login attack is a finding in itself: it means the endpoint you are hitting is the one the developers expected to be attacked, and the interesting endpoint is usually another one — a mobile API, a password-reset flow, an older form still reachable by URL. ^captcha

_**ccache (credential cache)**_: the file a Kerberos client keeps its tickets in on Linux, by default `/tmp/krb5cc_<uid>`. It is an ordinary file owned by the user, so root on a compromised host can copy anyone's, and the `KRB5CCNAME` variable is how a tool is told which one to read. A stolen ccache authenticates as its owner with no password involved, for as long as the ticket inside it has left to live. ^ccache

_**CDN (Content Delivery Network)**_: a network of edge servers that caches a site close to its visitors. It matters in recon because the address a domain resolves to belongs to the CDN, not to the origin server: your scan is talking to Cloudflare, and the ports, banners and even the WAF you see are the CDN's, not the target's. ^cdn

_**CIDR**_: the `/24` in `10.10.10.0/24` — the number of leading bits that are fixed, so `/24` fixes the first three octets and leaves 256 addresses. It is how a range is written to a scanner in one argument instead of a list. ^cidr

_**CIFS**_: the older name for [[445-SMB|SMB]], still used in `mount -t cifs` and in tool options. Treat the two words as the same protocol; the distinction only matters for very old dialects. ^cifs

_**Clock skew**_: the difference between two machines' clocks. Kerberos refuses any request whose timestamp is more than five minutes from the domain controller's, because the timestamp is what proves the request is live rather than a recording being replayed. It is the most common Kerberos failure on a lab network and it reports itself as `KRB_AP_ERR_SKEW`, which says nothing about your credential. ^clock-skew

_**CMS (Content Management System)**_: software that keeps a site's pages in a database and renders them through templates — WordPress, Joomla, Drupal. Identifying the CMS is worth real time, because it converts a unique target into a known one: known file layout, known default paths, a version number, and a public exploit history. ^cms

_**CNAME**_: a DNS record that says "this name is an alias for that other name". It matters twice: it reveals the service a subdomain is really pointing at (an S3 bucket, a SaaS host), and if the name it points at no longer exists, the subdomain can be taken over. ^cname

_**Coercion**_: the use of threats, pressure, or force to compel a target into performing an action — such as coercing an employee into revealing credentials or granting unauthorized access.

_**Cognito Identity Pool**_: An AWS service that exchanges an identity — including an anonymous, unauthenticated one when configured to allow it — for temporary IAM credentials, letting a client-side application call AWS APIs directly without a backend.

_**Command and Control (C2)**_: A communication channel established between compromised systems and the attacker's infrastructure, allowing the attacker to send commands and receive data after gaining access to a target.

_**Competency**_: the demonstrated ability to perform a task or role to a required standard; in offensive security, the practical skills and knowledge validated through hands-on exploitation rather than theory alone.

_**Compliance**_: Compliance is the act of following rules, laws, policies, standards, or regulations set by an authority, organization, or system.

_**Compromise**_: Refers to the unauthorized access, control, or breach of a system, account, network, or data by an attacker, resulting in a loss of confidentiality, integrity, or availability.

_**Conduit**_: Refers to a channel or pathway through which data or communication flows, which in security contexts can be exploited by attackers as a route to transmit malicious traffic, exfiltrate data, or pivot through a network.

_**ConPTY (Pseudo Console)**_: the Windows API, added in Windows 10 1809, that finally gave Windows a true pseudo-terminal — the thing Linux has always had as a [[Security-Terms#^pty|PTY]]. It is the reason `ConPtyShell` gives a fully interactive Windows shell with working arrow keys, tab completion and Ctrl-C, where a plain reverse shell gives a half-broken one. ^conpty

_**Consent**_: Agreement on the part of a subject or user to allow a specific activity (like data processing).

_**Content Discovery**_: The process of finding files, directories, and hidden resources on a web server that aren't linked from the main application, typically using tools like Gobuster, ffuf, or Dirbuster combined with wordlists to brute-force possible paths.

_**Convention**_: A custom, practice, or generally accepted way of doing something. A large gathering, meeting, or conference. Agreed-upon rules, standards, or best practices in software development.

_**Correlate**_: Refers to the process of identifying relationships or patterns between different data points, logs, or events, often used in security analysis to link related activities and detect potential threats or attack patterns.

_**Covert**_: describing actions or techniques deliberately designed to remain hidden or undetected — as in covert channels, covert exfiltration, or covert persistence mechanisms.

_**CSP (Content Security Policy)**_: an HTTP response header listing which sources of script, style, image and frame the browser is permitted to load for this page. It is a defence layered on top of output encoding: your injection can reach the page intact and still never execute, because the header forbids inline script. Read it before concluding a payload failed. ^csp

_**CSRF (Cross-Site Request Forgery)**_: getting a logged-in victim's browser to send a state-changing request that you composed — the browser attaches their session cookie automatically, so the server sees an authentic request. The standard defence is a per-form random token the attacker cannot read; a login form carrying one is also the reason a naive password-spraying script gets rejected before the password is ever checked. ^csrf

_**CSS (Cascading Style Sheets)**_: the language describing how a page looks. It matters offensively in two small ways: a stylesheet is a file the server serves, so it can leak paths and framework versions, and CSS alone can be enough to exfiltrate data from a page when script is blocked. ^css

_**Cypher**_: the query language of the [[Security-Terms#^neo4j|Neo4j]] graph database, and therefore the language BloodHound's search bar and prebuilt queries are written in. A query describes a shape — this kind of node, joined by that kind of edge, to that kind of node — and the database returns every instance of the shape it holds. "Shortest path to Domain Admins" is one line of it. ^cypher

## D

_**DAC (Discretionary Access Control)**_: A form of access control where the owner of the resource specifies which subjects can access, and the access permissions can be transferred to other subjects.

_**DACL (Discretionary Access Control List)**_: the half of a Windows [[Security-Terms#^acl|ACL]] that grants and denies access — the list read on every open. "Discretionary" means the object's owner may change it, which is the whole point when you own an object you should not: you can rewrite your own permissions. ^dacl

_**DC (Domain Controller)**_: the Windows server that holds a writable copy of the Active Directory database and answers authentication for the domain. Every Kerberos ticket, every password change and every replication request goes through one, which is why it is both the goal and the loudest place to make noise. ^dc

_**DCSync**_: asking a domain controller to replicate account data to you — including password hashes — using the same API a second DC would use. Nothing is exploited; the permission to replicate is simply held by an account it should not be. Any account with the two replication rights on the domain object can do it from anywhere on the network. ^dcsync

_**Deobfuscation**_: Analyzing and converting obfuscated code back into readable form; never recovers the exact original (names, comments are lost). Tools: obf-io.deobfuscate.io, `dcode.fr/javascript-unobfuscator`.

_**Deprecate**_: Refers to the process of marking a method, feature, or technology as obsolete, signaling that it should no longer be used, often due to security vulnerabilities or better alternatives being available.

_**Deserialization**_: The process of converting serialized data (data transformed into a format suitable for storage or transmission) back into its original object or data structure. the process of converting stored or transmitted data back into an object — a common attack vector when untrusted data is deserialized without validation, potentially allowing remote code execution.

_**DHCP (Dynamic Host Configuration Protocol)**_: the protocol by which a machine joining a network is handed an address, a gateway and a DNS server. Two consequences worth carrying: the DNS server it hands out is usually the internal one, which is what makes internal name resolution work at all, and a machine that never got a DHCP answer falls back to [[Security-Terms#^apipa|APIPA]] and is effectively offline. ^dhcp

_**Dig**_: (Domain Information Groper): A command-line network administration tool used to query DNS (Domain Name System) servers. It retrieves information such as IP addresses, mail servers, name servers, and other DNS records associated with a domain name.

_**Directory Traversal**_: forcing a program to reach files outside its intended folder by feeding it relative path segments (`../`), which the OS resolves before the program sees the result — so a check that inspects the raw string can be walked straight past. Also called path traversal; the same mechanism underlies LFI on the web and allowlist bypasses in privileged local services.

_**Discreet**_: acting carefully and intentionally to avoid drawing attention or leaving traces — used to describe an attacker's or operator's cautious behavior during an engagement.

_**Dissect**_: Refers to the process of analyzing malware, network traffic, or code to understand its structure, behavior, or vulnerabilities.

_**DLL (Dynamic Link Library)**_: A type of file that contains instructions that other programs can call upon to do certain things. This way, several programs can share the abilities programmed into a single file.

_**DMZ (Demilitarized Zone)**_: In networking, a DMZ is used to host public-facing services (e.g., web servers, email servers) while isolating them from the rest of the internal network to reduce the risk of unauthorized access.

_**DN (Distinguished Name)**_: an entry's full address inside an LDAP directory, written as a comma-separated path from the entry up to the root, as in `CN=bora,OU=Staff,DC=corp,DC=local`. The rightmost components form the base DN that every search must be given; one wrong component returns zero results rather than an error. ^dn

_**DNS Leak**_: a security flaw in which DNS queries are sent outside an encrypted tunnel (such as a VPN), revealing a user's browsing activity or real IP address to unintended third parties.

_**DNS Tunneling**_: a technique that encodes data within DNS queries and responses to covertly exfiltrate information or establish a command-and-control channel, exploiting the fact that DNS traffic is rarely blocked or inspected.

_**DOCTYPE**_: the declaration at the very top of an XML or HTML document naming its document type. In XML it is also where entities are declared, which is why every [[Security-Terms#^xxe|XXE]] payload begins with one: the DOCTYPE is the only place an external entity can be introduced. ^doctype

_**DOM (Document Object Model)**_: a live, tree-structured, in-memory representation of a web page's HTML that JavaScript can read and modify; changes to it update the rendered page immediately without a server round-trip.

_**Domain Generation Algorithm (DGA)**_: A technique used by malware to automatically generate large numbers of domain names using a predefined algorithm, making C2 infrastructure resistant to takedowns by rotating through thousands of potential connection points.

_**DOS (Disk Operating System)**_: A family of operating systems that run from a hard disk drive or other disk storage media. It primarily uses a command-line interface (CLI) where users enter text-based commands to interact with the hardware and manage files.

_**Dovecot**_: Dovecot is an open-source IMAP and POP3 server for Unix-like operating systems. It allows users to securely retrieve and manage their email messages stored on a server.

_**DPAPI (Data Protection API)**_: the Windows service applications call to encrypt a secret without inventing their own crypto. The key is derived from the user's password, so the ciphertext is bound to that user on that machine. Chrome cookies, saved RDP credentials, Wi-Fi keys and many password managers all sit behind it — which is why stealing the encrypted blob is useless without either the user's password or SYSTEM on the box. ^dpapi

_**Drill**_: a structured practice exercise simulating a security incident or attack scenario — such as a tabletop drill or red team drill — used to test an organization's detection and response capabilities.

_**DTD (Document Type Definition)**_: the schema section of an XML document, declaring which elements are allowed and which entities exist. This is where [[Security-Terms#^xxe|XXE]] lives: an entity declared in the DTD can point at a local file path or a URL, and a parser with external entities enabled will go and fetch it. ^dtd

## E

_**EDR**_: EDR (Endpoint Detection and Response) refers to a cybersecurity solution that monitors endpoint devices (like computers, servers, and mobile devices) to detect, investigate, and respond to suspicious activities or threats in real time.

_**ELF (Executable and Linkable Format)**_: the binary format Linux executables, shared libraries and core dumps use — the counterpart of Windows PE. `file` naming something ELF tells you two useful things at once: it will not run on Windows, and its architecture (x86-64, ARM) must match the target or it will refuse to start with an error that looks nothing like an architecture problem. ^elf

_**Enclave**_: Refers to a secure, isolated segment of a network or system that is separated from the broader environment to protect sensitive data or critical operations, such as a secure enclave within a CPU (e.g., Intel SGX) or a restricted network zone accessible only to authorized users.

_**ens3**_: A Linux predictable network-interface name. It commonly appears as a primary Ethernet interface in virtual machines; the exact name is derived from device topology and is not a universal expansion of ‘Ethernet Network Slot 3’.

_**Enticement**_: the use of attractive lures — such as fake credentials, honeypots, or tempting file names — to draw an attacker into a controlled trap or monitored environment.

_**Epoch**_: Refers to a reference point in time, most commonly the Unix epoch (00:00:00 UTC on January 1, 1970), from which timestamps are measured in seconds; widely used in logs, file metadata, and forensic analysis to record and correlate when events occurred.

_**Errant**_: Refers to an error or unintended behavior within a system, such as an errant script or process that causes unexpected or undesired outcomes.

_**Escaping**_: Escaping (output encoding) means transforming user data so the browser treats it as plain text, not code, for example, turning `<` into `&lt`; so `<script>` becomes harmless text. A filter (input validation) checks that the input looks allowed (letters, numbers, length), but doesn’t stop data from becoming code when it’s later placed into a page. For example, raw user input `<script>alert(1)</script>` will be  escaped for HTML becomes `&lt;script&gt;alert(1)&lt;/script&gt`.

_**Exfiltration**_: Exfiltration is the unauthorized transfer of data from a computer or network to an external location, typically performed by a threat actor after gaining access.

## F

_**Fast Flux**_: A technique that associates a single domain name with rapidly rotating IP addresses — often belonging to compromised devices acting as proxies — to make C2 infrastructure difficult to block or trace.

_**Favicon**_: A small icon associated with a website, whose hash can be fingerprinted (e.g. via Shodan) to identify the web application or framework in use, aiding in technology identification during reconnaissance. (OWASP host a database of common framework icons' md5s: `https://wiki.owasp.org/index.php/OWASP_favicon_database`)

_**FIFO (named pipe)**_: a file on disk that is really a queue: one process writes into it, another reads out of it, and nothing is ever stored. Created with `mkfifo`. It is the trick behind the classic "no bash, no python" reverse shell — the pipe carries output back to the network socket that carried the command in. ^fifo

_**Fingerprinting**_: the process of identifying a system's software, versions, or configuration (e.g. OS, web server, framework) by analyzing its observable characteristics and responses.

_**Foremost**_: It means "most important," "leading," or "at the front." Foremost is a forensic data recovery tool for Linux used to recover deleted files or extract data from disk images.

_**Fortify**_: to strengthen a system, network, or application against attack by implementing additional security controls, hardening configurations, or patching vulnerabilities.

_**Forward secrecy**_: a property of a key exchange protocol ensuring that session keys are not compromised even if the server's long-term private key is later compromised, since each session uses a unique, ephemeral key.

_**FQDN (Fully Qualified Domain Name)**_: the complete name of a host including every label up to the root — `dc01.corp.example.com`, not `dc01`. It matters against Windows and Kerberos far more than against Linux: a ticket is issued for a name, so authenticating to an IP address when the ticket names a host fails in a way that reads like a password problem. ^fqdn

## G

_**GID (Group ID)**_: the number Linux actually uses for a group; the name in `/etc/group` is only a label on top of it. `id` prints your real GID and every supplementary group you carry. It is worth reading carefully, because file access is decided by the numbers, and a group you were added to in a previous session is not in effect until you get a new login shell. ^gid

_**GodPotato**_: one of the "potato" tools — see [[Security-Terms#^potato|the potato family]]. Works on Windows Server 2012 through 2022 and Windows 8 through 11, which is what makes it the current default when the older ones fail. ^godpotato

_**Golden Ticket**_: a ticket-granting ticket forged offline using the [[Security-Terms#^krbtgt|KRBTGT]] account's password hash. Because every legitimate ticket-granting ticket in the domain is encrypted with that same key, a forged one is indistinguishable from a real one and can name any user and any group. It survives password resets of the account being impersonated, and is only invalidated by resetting KRBTGT twice. ^golden-ticket

_**Google Dorking**_: the technique of using advanced Google search operators to find sensitive information, exposed files, or vulnerable systems that are publicly indexed but not intended to be easily discovered.

_**GPO (Group Policy Object)**_: the container Active Directory uses to push settings — scripts, scheduled tasks, registry values, local group membership — to every machine or user in a scope. Write access to a GPO that applies to a machine is effectively code execution on that machine, delivered by the domain itself. ^gpo

_**GPP (Group Policy Preferences)**_: an older Group Policy feature for setting local passwords across a domain. The password was stored in an XML file in [[Security-Terms#^sysvol|SYSVOL]] as `cpassword`, encrypted with an AES key Microsoft published in its own documentation — so every domain user could read and decrypt it. Patched in 2014 by removing the ability to create new ones; existing files were left in place, which is why they still turn up. ^gpp

_**GPU (Graphics Processing Unit)**_: relevant here only for hash cracking: a GPU runs thousands of simple operations in parallel, which is exactly the shape of a brute-force. It is the difference between an MD5 wordlist finishing in seconds and finishing next week — and the reason `hashcat` inside a virtual machine, where the GPU is not passed through, is far slower than the same command on the host. ^gpu

_**Granular**_: Consisting of small grains or particles; in a technical context, characterized by a high level of detail or the ability to control small, individual components within a larger system.

_**GTFOBins**_: a public catalogue at gtfobins.github.io of ordinary Unix binaries and the exact syntax that makes each one read a file, write a file, or spawn a shell. Its value is that it turns a list of SUID binaries or sudo rules into a yes/no answer in seconds: if the binary has a page, the abuse is already written out; if it does not, move on rather than inventing one. LOLBAS is the same idea for Windows. ^gtfobins

## H

_**HackTricks**_: a large public wiki of offensive technique, organised by the situation you are in rather than by tool. Useful as a second opinion when a technique note here ends without a next move; treat its command lines as material to understand, not to paste. ^hacktricks

_**Handle**_: A unique identifier or index held by an application to access a system resource. ^handle

_**Heuristic**_: Refers to a detection method that identifies threats based on behavior, patterns, or rules rather than known signatures, allowing security tools like antivirus or IDS to detect new or unknown malware and suspicious activity.

_**HKLM / HKCU**_: the two Windows registry hives you meet constantly. `HKEY_LOCAL_MACHINE` holds machine-wide settings and normally needs administrator rights to write. `HKEY_CURRENT_USER` is your own profile and you can always write it. A check that reads both — [[Security-Terms#^alwaysinstallelevated|AlwaysInstallElevated]] is the classic — is asking whether an administrator set the machine half, because the user half you could set yourself. ^hklm

_**Honeypot**_: a decoy system or resource deliberately set up to lure attackers, allowing defenders to detect, monitor, and study malicious activity in a controlled environment.

_**Hook into**_: A phrasal verb meaning to connect to, attach to, or intercept another system, process, or data stream so you can receive, modify, or respond to its events or information.

_**HTTP/3**_: the third major version of the Hypertext Transfer Protocol, built on QUIC instead of TCP, offering faster connection establishment and improved performance over unreliable networks.

## I

_**IAAA (Identification, Authentication, Authorization, Accounting)**_: A foundational security framework describing the four steps of access control — Identification (claiming an identity), Authentication (proving it), Authorization (granting appropriate access), and Accounting (tracking and logging actions) — used to manage and secure user access to systems and resources.

_**IAM (Identity and Access Management)**_: in AWS, the service that decides which identity may call which API on which resource. Every credential you find is an IAM identity with a policy attached, and the first question about any of them is not "is it valid" but "what is it permitted to do" — `aws sts get-caller-identity` answers the first, enumeration of its policies answers the second. ^iam

_**IANA**_: The Internet Assigned Numbers Authority is the organization responsible for coordinating some of the key elements that keep the global Internet running — including global IP address allocation, DNS root zone management, and protocol parameter assignment. IANA operates under the oversight of ICANN and works with Regional internet registries and standards bodies.

_**ICMP**_: the protocol `ping` and `traceroute` are built on — control and error messages for IP rather than data. It matters in two places: a host that does not answer a ping is very often alive and simply filtering ICMP, which is why `nmap -Pn` exists; and where TCP is blocked outbound, ICMP is sometimes not, which is what an ICMP tunnel exploits. ^icmp

_**IDOR (Insecure Direct Object Reference)**_: A web vulnerability where an application exposes references to internal objects (such as files, database records, or user IDs) without proper access control, allowing an attacker to manipulate these references (e.g., changing a URL parameter) to access unauthorized data or resources.

_**IDS (Intrusion Detection System)**_: a sensor that watches traffic or host activity and alerts on patterns it recognises. On a lab box its practical effect is the same as a WAF's: a default `nikto` or a noisy scan produces a wall of results that are the sensor answering, not the application. ^ids

_**IIS (Internet Information Services)**_: Microsoft's web server software built into Windows Server, commonly fingerprinted during reconnaissance and targeted for misconfigurations, outdated versions, or known vulnerabilities.

_**IKE (Internet Key Exchange)**_: A protocol used to negotiate and establish Security Associations (SAs) and cryptographic keys for IPsec. IKE performs authentication (e.g., pre‑shared keys, certificates), negotiates algorithms and parameters, and runs a Diffie‑Hellman key exchange to derive session keys. Common versions are IKEv1 and IKEv2; IKEv2 is the modern standard and supports features like NAT traversal (UDP/4500), EAP authentication, and MOBIKE.

_**IMDS (Instance Metadata Service)**_: the link-local address `169.254.169.254`, reachable only from inside a cloud instance, that hands the instance its own configuration and its temporary credentials. Version 1 answers a plain request, which is what makes it the first target of any [[Security-Terms#^ssrf|SSRF]]; version 2 requires a token fetched with a `PUT` first. ^imds

_**Impacket**_: a Python library implementing the Windows network protocols from scratch, and the collection of example scripts built on it that most Active Directory work runs through — `smbclient.py`, `psexec.py`, `secretsdump.py`, `GetUserSPNs.py`, `getTGT.py`. Because the implementation is its own, it accepts hashes and tickets where a Windows client would insist on a password. ^impacket

_**Induce**_: to cause or bring about a particular state or outcome; in security contexts, to deliberately trigger a condition or behavior in a target system (e.g., inducing an error to leak information, or inducing a race condition to exploit a timing window).

_**Infiltrate**_: Infiltrate means to enter or gain access to a place, organization, or system secretly, often to gather information or cause harm. Refers to the act of covertly gaining unauthorized access to a system, network, or organization, typically without detection, in order to steal data, plant malware, or conduct further malicious activity.

_**information_schema**_: a built-in database in SQL systems that stores metadata about all other databases on the server, including table names, column names, and data types, commonly queried during SQL injection to enumerate database structure.

_**Ingestion**_: Refers to the process of collecting and importing data, such as logs, network traffic, or threat intelligence feeds, into a system like a SIEM for analysis, monitoring, and detection.

_**Interoperable**_: The ability of computer systems or software to exchange and make use of information.

_**Intervention**_: an action taken to interrupt, disrupt, or prevent a security incident or attack — such as a defensive intervention to block an ongoing intrusion or a manual intervention in an automated response pipeline.

_**ISO/IEC 27001**_: International standard for Information Security Management Systems (ISMS).

_**ISP (Internet Service Provider)**_: the company providing a connection. It appears in this vault for one practical reason: some ISPs filter outbound ports, so a reverse shell to a high port on your home connection can fail for reasons that have nothing to do with the target. ^isp

_**Itinerary**_: A detailed plan or record of a journey, listing destinations, dates, and times; often exposed in leaked emails or booking confirmations and used in OSINT to profile a target's location and availability.

## J

_**JBoss**_: a Java application server (now WildFly). It appears in recon because its management consoles and deployment endpoints have a long exploit history, and because a Java stack trace leaking from a page is often the first sign one is behind it. ^jboss

_**JuicyPotato**_: one of the "potato" tools — see [[Security-Terms#^potato|the potato family]]. It was the standard for years and stopped working on Windows 10 1809 and Server 2019, which is exactly why PrintSpoofer and GodPotato exist. ^juicypotato

_**JWT (JSON Web Token)**_: a token in three dot-separated Base64 parts: a header naming the algorithm, a payload of claims (who you are, what you may do, when it expires), and a signature over the first two. The payload is encoded, not encrypted — anyone holding the token can read it. The whole security rests on the signature, which is why the classic attacks are algorithm confusion, `alg: none`, and a weak signing key cracked offline. ^jwt

## K

_**KASLR (Kernel Address Space Layout Randomisation)**_: the kernel loading itself at a different base address on every boot, so an exploit cannot hardcode where a kernel function lives. It is why a kernel exploit often needs an information leak first, and why a proof-of-concept that worked in the author's virtual machine may simply crash on yours. ^kaslr

_**KDC (Key Distribution Center)**_: the Kerberos service that issues tickets, running on every domain controller. It has two halves: the authentication service, which checks who you are and gives you a [[Security-Terms#^tgt|ticket-granting ticket]], and the [[Security-Terms#^tgs|ticket-granting service]], which trades that for tickets to individual services. Every Kerberos error beginning `KDC_ERR_` comes from here. ^kdc

_**KeePass**_: an offline password manager storing everything in a single `.kdbx` file protected by a master password and optionally a key file. Finding a `.kdbx` on a box is a genuine prize: the file can be taken away and attacked offline with `keepass2john` and `hashcat`, and if it opens it usually holds credentials for other machines. ^keepass

_**Kerberoasting**_: asking the domain for a service ticket to an account that has a [[Security-Terms#^spn|service principal name]], then cracking it offline. The ticket is encrypted with the service account's password, and any authenticated user may request one for any service, so the attack needs no privilege and produces no failed logins. ^kerberoasting

_**Kerberos**_: the authentication protocol Windows domains use by default. You prove yourself once to the [[Security-Terms#^kdc|domain controller]], receive a ticket, and present that ticket to services — the reverse of [[Security-Terms#^ntlm|NTLM]], where you authenticate to the service and it checks with the controller. It needs names rather than addresses, and clocks that agree, and both of those are where it fails in practice. ^kerberos

_**KRB5CCNAME**_: the environment variable naming which [[Security-Terms#^ccache|ccache]] file a Kerberos client should use. Tools invoked with `-k` read it; if it is unset they look for the default cache and, finding nothing, fail with a Kerberos error rather than a helpful one. Exporting it with a full path is the difference between a ticket working and a tool quietly asking for a password. ^krb5ccname

_**KRBTGT**_: the disabled domain account whose password hash encrypts every ticket-granting ticket the domain issues. Its hash is the domain's master key: anyone holding it can forge a [[Security-Terms#^golden-ticket|Golden Ticket]] for any user, and clearing that access requires resetting the account's password twice, since the previous password is still honoured. ^krbtgt

## L

_**LAMP**_: an acronym for a web development stack consisting of Linux, Apache, MySQL, and PHP.

_**LAN (Local Area Network)**_: the network segment a machine sits on directly, reachable without a router. Its importance in an engagement is that services bound to the LAN interface are often bound with no authentication at all, on the assumption that only trusted machines are on it — which stops being true the moment you have a shell on one of them. ^lan

_**LDAP (Lightweight Directory Access Protocol)**_: the protocol used to query a directory — in practice, Active Directory. Port 389 plain, 636 over TLS. It is how a machine asks "which users exist, which groups do they belong to, what are the attributes of this computer object", and an anonymous bind that answers those questions gives you the domain's structure without a single credential. ^ldap

_**Lease**_: a temporary allocation or rental agreement — in cybersecurity commonly seen in DHCP leases (temporary IP address assignments) or cloud resource leases where infrastructure is rented for a defined period.

_**LES (linux-exploit-suggester)**_: a shell script that reads the kernel version and distribution of the box it runs on and lists known local privilege-escalation exploits matching it, each with a confidence rating. It suggests; it does not verify. Every result still needs the box checked for the conditions the exploit actually requires. ^les

_**Leverage**_: Refers to the act of using or exploiting a resource, tool, vulnerability, or technique to gain an advantage, such as an attacker leveraging a flaw to escalate privileges or a defender leveraging threat intelligence to improve security.

_**LFI (Local File Inclusion)**_: a web application taking a filename from the request and including it, so a path you supply is read and rendered — or executed, if the language treats an included file as code. The difference from directory traversal is that difference: traversal reads the file, inclusion runs it, which is why PHP applications turn LFI into a shell so often. ^lfi

_**LinEnum**_: an older Linux enumeration script — the predecessor to LinPEAS in most workflows. Smaller and quieter, with plain unhighlighted output, which makes it a reasonable second run when LinPEAS produces too much to read. ^linenum

_**LinPEAS**_: the Linux half of [[Security-Terms#^peass|PEASS-ng]]: one shell script that runs several hundred local privilege-escalation checks and colour-codes what it finds — red on yellow means "this is very probably exploitable". It finds candidates; it does not confirm them, and a clean run is not proof that nothing is there. ^linpeas

_**Living Off the Land (LOTL)**_: attacking with the software already on the target — `net`, `wmic`, `certutil`, `schtasks`, `powershell` on Windows; `curl`, `python3`, `tar` on Linux — rather than uploading your own. It buys cover, not capability: a signed binary that fires on that host daily sits in the noise, while a dropped `.exe` is unsigned, unfamiliar, and flagged by the EDR on sight. Detection moved off the file and onto the behaviour years ago — `certutil` fetching a remote file, or Word spawning `cmd.exe`, is damning whoever signed it. The curated lists are LOLBAS (Living Off the Land Binaries And Scripts) for Windows and GTFOBins (Get The F*** Out Binaries) for Linux. ^lotl

_**LM hash**_: the pre-2000 Windows password hash. It uppercases the password, pads it to 14 characters, splits it into two halves of seven and hashes each half separately without a salt — so a 14-character password is two 7-character problems and cracks almost instantly. Disabled by default since Windows Vista; if you see one in a dump on a modern system, someone turned it back on. ^lm-hash

_**LocalSystem**_: the highest local account on Windows (`NT AUTHORITY\SYSTEM`) — more privileged than a member of the local Administrators group. Most services run as it. It has no password, cannot be logged into interactively, and on the network it presents itself as the machine account, which is why a SYSTEM shell on a domain-joined host is also a domain identity. ^localsystem

_**Loopback**_: the `127.0.0.1` / `::1` address that always refers to the same host, never leaving it. A service bound only to loopback is unreachable from the network but fully reachable by any local process — which makes such services invisible in an external scan yet prime targets once you have a foothold. ^loopback

_**LSA Secrets**_: a protected area of the registry (`HKLM\SECURITY\Policy\Secrets`) where Windows keeps passwords that a machine — not a person — must be able to use at boot: service account passwords, cached domain credentials, the autologon password when it was set with the Sysinternals Autologon tool. Encrypted with a machine key and unreadable even to a local administrator until they become SYSTEM, which is why a secret found here is a *post*-escalation prize rather than a way in. ^lsa-secrets

_**LSASS (Local Security Authority Subsystem Service)**_: the Windows process that performs authentication and, as a side effect, holds credential material for every session on the box in its memory — hashes, Kerberos tickets, sometimes cleartext. This is why dumping `lsass.exe` is the single most valuable action on a Windows host, and why it is also the single most heavily monitored one. ^lsass

## M

_**MAC (Mandatory Access Control)**_: A strict access control model where access policies are governed by a central authority, and users cannot override or modify these policies.

_**Machine account**_: the account a domain creates for a computer when it joins, named after the computer with a `$` on the end. It is a real account with a real password, which is how a machine authenticates on its own rather than through a person, and that password is 120 random characters rotated automatically — so a trailing `$` in any list of names means there is nothing there to crack. The account can still hold privileges, and some attacks use one rather than break it. ^machine-account

_**Macro**_: a scripted sequence of commands or actions embedded in documents (such as Office files) that execute automatically, often abused by attackers to deliver malware when the document is opened.

_**MariaDB**_: the community fork of MySQL, created after Oracle's acquisition. For nearly everything here it is MySQL: same client, same port, same syntax. It matters when a version-specific exploit is involved, because their version numbers diverged long ago. ^mariadb

_**MD5**_: a 128-bit hash function from 1992, now broken for collision resistance and far too fast for password storage. You will meet it constantly anyway: as file-integrity checksums, and as `$1$` password hashes on old Unix systems. In a hash list, 32 hex characters with no prefix is the shape to recognise. ^md5

_**md5crypt**_: the Unix password hashing scheme marked `$1$` in `/etc/shadow` — MD5 applied a thousand times with a salt. Do not confuse it with raw MD5: they are different hashcat modes, and feeding a `$1$` hash to the raw-MD5 mode produces a line-length error rather than a result. ^md5crypt

_**Merge**_: To unite, combine or blend into one. In version control, it refers to integrating changes from another branch into the current one.

_**MERN**_: an acronym for a web development stack consisting of MongoDB, Express, React, and Node.js.

_**Middleware**_: software that sits between components of an application (e.g. between a server's routing and business logic) and processes requests or responses, often used for tasks like authentication, logging, or input validation.

_**MIME type**_: the label attached to a file to say what it is, such as `image/jpeg` or `text/html`. In an upload it is a value the client sets and the server frequently trusts, so it states what the sender claims rather than what the bytes actually contain. ^mime

_**Minification**_: Removing unnecessary characters (whitespace, comments, long variable names) from code to reduce file size, without hiding logic. Tools: terser, beautifier.io (reverse).

_**MITM (machine-in-the-middle)**_: sitting between two parties who believe they are talking directly. On a local segment it is usually reached by [[Security-Terms#^arp|ARP]] poisoning or by answering name-resolution broadcasts nobody else claims; over TLS it requires a certificate the client will accept, which is exactly what Burp's CA certificate is for. ^mitm

_**MPM (Multi-Processing Module)**_: the part of Apache that decides how it handles concurrent requests — one process per request, threads, or an event loop. It surfaces in privilege escalation because the MPM decides which user the request handler runs as, and an `itk`-style MPM runs each virtual host as its own user rather than as `www-data`. ^mpm

_**MSF (Metasploit Framework)**_: the exploitation framework whose console is `msfconsole`. Its module strings look like paths — `exploit/windows/smb/ms17_010_eternalblue` — and the format is exact: a wrong separator or a missing segment produces "failed to load module" rather than a search suggestion. ^msf

_**MSI**_: the Windows Installer package format — a small database describing files, registry keys and custom actions to run during installation. It matters because installation runs with the installer service's privileges, which is what [[Security-Terms#^alwaysinstallelevated|AlwaysInstallElevated]] turns into a privilege escalation, and because an MSI is a perfectly ordinary way to carry a payload. ^msi

_**MTU (Maximum Transmission Unit)**_: The largest Layer‑3 packet size (in bytes) that can traverse a link in a single frame without fragmentation. Common values: Ethernet 1500; PPPoE 1492; VPN/tunnels (IPsec/GRE/VXLAN, etc.) reduce effective MTU; “jumbo frames” ~9000 require end‑to‑end support.

_**MX record**_: the DNS record naming the mail servers for a domain. In enumeration it hands you hostnames you did not have (`mail.target.com`) and tells you whether mail is handled on the target's own infrastructure or by a provider you are not in scope to touch. ^mx-record

## N

_**NAC (Network Access Control)**_: A security mechanism that controls access to a network by enforcing policies, such as verifying the identity of users or devices and ensuring that endpoint devices meet security standards.

_**NAS (Network Attached Storage)**_: a small appliance whose only job is to serve files over the network, usually via SMB and NFS. They are worth attention because they are rarely patched, frequently run an old Linux with a web administration panel, and by definition hold the data everyone else was careful about. ^nas

_**NAT (Network Address Translation)**_: a router rewriting addresses so many private hosts share one public address. It is why a reverse shell to your own machine needs a port forwarded, why a bind shell on a NATed target is unreachable from outside, and why FTP in active mode fails from behind it while passive mode works. ^nat

_**NCURSE**_: A programming library used to create text-based user interfaces in a terminal, providing window management, colors, and input handling.

_**Neo4j**_: a graph database, meaning one that stores objects and the connections between them as equally real things instead of storing rows and working the connections out afterwards. BloodHound keeps a collected domain in one, and that is what makes "the shortest path between these two accounts" a single query rather than a script. ^neo4j

_**NetBIOS**_: a naming and session layer from the 1980s that Windows still carries for compatibility — the source of those 15-character uppercase computer names, and of UDP 137/138 and TCP 139 sitting next to SMB on 445. Its name-resolution broadcasts are unauthenticated, which is what a responder-style tool answers. ^netbios

_**NetNTLMv2**_: the response a Windows client sends when it authenticates over the network with NTLM: the account's hash used to sign a server-supplied challenge. It is not the NT hash and cannot be passed like one — but it can be cracked offline, which is why forcing a machine to authenticate to you is worth doing. Recognisable by its `::` separated form containing a username and a domain. ^netntlmv2

_**NFS (Network File System)**_: the Unix protocol for mounting a remote directory as if it were local, on port 2049. The security model is the reason it appears here: the server traditionally trusts the client's own report of which UID is asking. `showmount -e` lists what is exported and to whom. ^nfs

_**NIC**_: A Network Interface Card (NIC) is a hardware component that connects a computer or device to a network, enabling it to send and receive data.

_**NIST**_: National Institute of Standards and Technology (USA).

_**NLA (Network Level Authentication)**_: an RDP setting requiring the client to authenticate before the server presents a desktop session. With it on, an RDP port gives you nothing without credentials; with it off, you reach a login screen — and that screen leaks the OS version, the domain name and sometimes a list of logged-in users. ^nla

_**Nonrepudiation**_: Refers to the security principle that ensures a party cannot deny the authenticity of their actions or communications, typically achieved through digital signatures, logging, and cryptographic methods, providing proof of origin and integrity.

_**NoSQL**_: databases that do not use tables and SQL — MongoDB, Redis, CouchDB. They matter twice: injection works differently, since the query is a structure rather than a string (so the payloads are operators like `$ne` and `$gt`, not quotes), and several of them historically shipped with no authentication at all on a port bound to every interface. ^nosql

_**NS record**_: the DNS record naming the authoritative nameservers for a zone. It is the answer you want before any other DNS move: those servers are the ones to ask directly for a zone transfer, and querying anything else means asking a cache what it happens to remember rather than asking the zone what is true. ^ns-record

_**NSE (Nmap Scripting Engine)**_: the Lua scripts bundled with Nmap that turn a port scan into a service interrogation — banner parsing, default-credential checks, known-vulnerability probes, enumeration of SMB shares and DNS records. `--script` selects them by name or category. This is where most of Nmap's actual findings come from. ^nse

_**NT hash**_: the modern Windows password hash: MD4 of the password in UTF-16, unsalted, no iteration. Unsalted means two accounts with the same password have the same hash, and no iteration means cracking is fast. It is also the value used directly in a pass-the-hash attack — you do not need to crack it to authenticate with it. ^nt-hash

_**NTFS**_: the Windows filesystem. Two features matter offensively: it stores per-object [[Security-Terms#^acl|ACLs]], so file permissions are far more expressive than Unix's owner/group/other bits; and it supports alternate data streams, where a file can carry hidden extra content that `dir` does not show. ^ntfs

_**NTLM**_: the Windows authentication protocol used whenever Kerberos cannot be — an IP address instead of a hostname, a workgroup machine, a local account. It is a challenge-response scheme, so the password itself never crosses the network. Three things sharing the name confuse everyone and should be kept apart: the protocol; the [[Security-Terms#^nt-hash|NT hash]] stored on the machine, which can be passed as-is without cracking; and the [[Security-Terms#^netntlmv2|NetNTLMv2]] response seen on the wire, which cannot be passed but can be cracked. ^ntlm

_**NTP (Network Time Protocol)**_: A protocol for synchronizing the clocks of computers and network devices over packet‑switched networks. NTP arranges time sources in strata (stratum 0 = reference clocks, stratum 1 = directly connected servers, etc.), typically uses UDP port 123, and can synchronize time with millisecond to sub-millisecond accuracy depending on network conditions and configuration.

_**NTPD (Network Time Protocol Daemon)**_: It refers to the daemon (background service) that implements the Network Time Protocol (NTP). It is responsible for synchronizing the system clock of a computer with an accurate time source over a network.

_**NVD**_: the National Vulnerability Database, a U.S. government repository of standards-based vulnerability data maintained by NIST that enriches CVE records with severity scores (CVSS), affected-product identifiers (CPE), and weakness classifications (CWE).

_**NXDOMAIN**_: the DNS answer meaning "this name does not exist" — as opposed to an empty answer, which means the name exists but has no record of the type you asked for. The distinction is exactly the Found/Empty problem in miniature, and a resolver that returns an address for every random name you try is wildcarding, so none of your subdomain results mean anything. ^nxdomain

## O

_**OAuth**_: a delegation protocol: it lets an application act on your behalf at another service without ever seeing your password. It is authorisation, not authentication, which is the source of most of its bugs — redirect URIs that are not validated strictly, tokens leaking through the referrer, and scopes granted more broadly than the application needs. ^oauth

_**Obfuscation**_: Deliberately transforming code into a hard-to-read form to resist reverse engineering, while keeping identical behavior. Tools: obfuscator.io, ToolPix.

_**Offset**_: The amount or distance by which something is out of line or displaced. In computing, it is an integer indicating the distance (displacement) between a beginning object and a given element or point. ^offset

_**OID (Object Identifier)**_: a dotted numeric path naming one branch or one value in an SNMP tree, such as `1.3.6.1.2.1.25.4.2.1.2` for running processes. The numbers are standardised worldwide, so the same path means the same thing on every device, and asking for one branch is what turns a thousand-line dump into an answer. ^oid

_**On-Premises**_: Refers to IT infrastructure, software, or services that are hosted and run locally on hardware physically located within an organization's own facilities, rather than in the cloud, giving the organization direct control over security and data.

_**Open Relay**_: a misconfigured mail server that accepts and forwards email from any sender to any recipient without authentication, commonly abused by attackers for spam campaigns and phishing.

_**OpenCL**_: the framework hashcat uses to talk to a GPU (or a CPU) for parallel work. Practically, it is the thing that has to be installed and working before hashcat will run at all — "No devices found/left" is an OpenCL problem, not a hash problem. ^opencl

_**OSI model**_: the seven-layer reference model — physical, data link, network, transport, session, presentation, application. Nothing implements it exactly; its use is as shared vocabulary for where a problem lives. "Layer 3 reaches it but layer 7 does not" says in four words that the host is up and the service is refusing you. ^osi

_**OSINT (Open Source Intelligence)**_: collecting information from sources that are simply published — certificate transparency logs, DNS records, code repositories, job listings, employee profiles. Its defining property is that the target's own systems are never touched, so nothing is logged and nothing can fail. ^osint

_**OSSTMM (Open Source Security Testing Methodology Manual)**_: A security testing methodology developed by ISECOM that applies the scientific method to penetration testing, producing quantifiable and repeatable results through metrics rather than subjective risk judgments.

_**Outage**_: Refers to a period during which a system, service, or network is unavailable or non-functional, which can result from cyberattacks (such as DDoS), hardware failures, or misconfigurations, impacting availability.

_**Overpass-the-Hash**_: using an [[Security-Terms#^nt-hash|NT hash]] to request a Kerberos ticket rather than to authenticate over NTLM. The result is a normal ticket, so everything downstream looks like ordinary domain traffic and the attack works against hosts that have NTLM switched off. Also called pass-the-key. ^overpass-the-hash

_**Override**_: to bypass or forcibly replace a security control, permission, or setting — as in overriding access controls, overriding a security policy, or overriding sanitization logic to inject malicious input.

## P

_**Page cache**_: the kernel's in-memory copy of file contents, shared by every process reading that file, used to avoid slow disk access. ^page-cache

_**Parent-Child Process Relationship**_: the hierarchical link between a process that spawns another, tracked by EDR/blue teams to spot anomalies like an Office app launching a shell.

_**Parity**_: Refers to a method of error detection that uses an extra bit (parity bit) to check whether data has been altered or corrupted during transmission or storage, helping ensure data integrity; also used more broadly to mean equivalence or equal status between systems.

_**Pass-the-Hash**_: authenticating with an [[Security-Terms#^nt-hash|NT hash]] instead of a password. NTLM puts the hash directly into its challenge-response, so the plaintext is never needed and cracking is optional — which is why a strong, uncrackable password protects nothing once its hash has been read. ^pass-the-hash

_**Pass-the-Ticket**_: reusing a Kerberos ticket taken from memory or from a [[Security-Terms#^ccache|ccache]] file to act as its owner. No password and no hash are involved, and the ticket works until it expires, which makes it the quietest way to reuse a credential and the hardest to revoke. ^pass-the-ticket

_**PATH**_: the ordered list of directories a shell searches when you type a command name with no slash in it. Order is everything: the first match wins, so a writable directory appearing before `/usr/bin` means you decide what `ls` is. A script that calls a command by bare name rather than by absolute path inherits whatever PATH it runs under, which is the whole of PATH abuse. ^path-var

_**PayloadsAllTheThings**_: a public repository of payloads and bypasses organised by vulnerability class. Its use is as a syntax reference when your injection is being filtered and you need the next encoding to try, not as a list to work through top to bottom. ^payloadsallthethings

_**PDU (Protocol Data Unit)**_: Refers to a unit of data specified in a protocol at each layer of the OSI model, where each layer encapsulates the data from the layer above with its own headers and trailers; for example, a segment at the transport layer, a packet at the network layer, and a frame at the data link layer.

_**PE (Portable Executable)**_: the Windows binary format — `.exe`, `.dll`, `.sys`. The counterpart of Linux's ELF. `file` naming something PE32+ tells you it is 64-bit Windows, which matters because a 32-bit process cannot load a 64-bit DLL and the error it gives says nothing about architecture. ^pe

_**PEAP (Protected Extensible Authentication Protocol)**_: An EAP (Extensible Authentication Protocol) encapsulation that creates a TLS‑protected tunnel between the client and the authentication server to protect inner authentication methods and credentials. PEAP relies on a server‑side certificate to establish the encrypted tunnel and then runs an inner EAP method (commonly MSCHAPv2 or EAP‑GTC) for user authentication. It is widely used for WPA/WPA2/WPA3‑Enterprise (802.1X) wireless authentication.

_**PEASS-ng**_: the project (Privilege Escalation Awesome Scripts SUITE, next generation) that ships [[Security-Terms#^linpeas|LinPEAS]] and [[Security-Terms#^winpeas|WinPEAS]]. Knowing the umbrella name is useful mainly because the releases page is where the current binaries actually live. ^peass

_**PEM**_: the text container for keys and certificates — Base64 between `-----BEGIN ...-----` and `-----END ...-----` lines. Worth recognising on sight, because an SSH private key found on a box is in exactly this shape, and because `chmod 600` on it is required before OpenSSH will use it. ^pem

_**Peripheral**_: An auxiliary device that connects to and works with a computer system to put information into or get information out of it.

_**Permissive**_: allowing a wide range of actions or access with few restrictions, often used to describe a lax configuration or policy that increases security risk.

_**PGP**_: a public-key system for encrypting and signing files and mail. It appears in recon because a published PGP key carries an email address and a name, and in loot because a private key file on a box is the kind of secret whose passphrase is worth attacking offline. ^pgp

_**PID (Process ID)**_: the number identifying a running process. Two uses here: it is what you pass to tools that read another process's memory, and watching PIDs appear and disappear is how `pspy` sees a cron job run without needing root to read the crontab. ^pid

_**PII (Personally Identifiable Information)**_: data that identifies a specific person — names, addresses, identity numbers, health records. In a real engagement it is what the scope document is most careful about: finding it usually proves the impact of a vulnerability, and copying it off the target is usually forbidden. ^pii

_**PoC (Proof of Concept)**_: code published to demonstrate that a vulnerability is real. It is written to prove a point, not to be reliable: hardcoded offsets, a specific kernel build, a callback address that must be edited. Reading a PoC before running it is what separates it from a working exploit. ^poc

_**POP3**_: an old mail-retrieval protocol on port 110 (995 over TLS) that downloads messages and by default deletes them from the server. It matters mostly as a credential surface: it is plaintext unless wrapped in TLS, and the same password usually works elsewhere. ^pop3

_**Potato family (RogueWinRM, PrintSpoofer, JuicyPotato, GodPotato)**_: a set of Windows tools that all do the same thing by different routes: they persuade a privileged service to authenticate to something the attacker controls, then impersonate the resulting token to become SYSTEM. They exist because [[Security-Terms#^seimpersonate|SeImpersonatePrivilege]] is held by every service account, and the privilege is the constant while the trigger is not — each tool works on a different range of Windows versions, so when one fails the answer is the next tool, not a different technique. ^potato

_**PowerSploit**_: an old and now archived collection of offensive PowerShell modules, organised by what they do — recon, privilege escalation, persistence, exfiltration. Nobody runs the framework as a whole; what survives in daily use is [[Security-Terms#^powerview|PowerView]] out of its recon folder. Having been famous by name for years, every scanner recognises it on sight. ^powersploit

_**PowerUp**_: a PowerShell script from the PowerSploit project that checks a Windows host for the common privilege-escalation misconfigurations — unquoted service paths, writable service binaries, weak service ACLs, stored credentials — and can also perform the abuse it finds. Older than WinPEAS and far noisier to antivirus, but its `Invoke-AllChecks` output is short enough to read in full. ^powerup

_**PowerView**_: the domain enumeration half of [[Security-Terms#^powersploit|PowerSploit]] — a single PowerShell script, imported into a session on a domain-joined host, offering one consistent set of verbs (`Get-DomainUser`, `Get-DomainGroup`, `Get-DomainComputer`) over the same directory the built-in commands read. It earns its place by carrying the queries nobody wants to write by hand, such as which accounts hold a service name. ^powerview

_**Pre-authentication**_: the step where a Kerberos client encrypts the current time with its password hash to prove it knows the password before the [[Security-Terms#^kdc|KDC]] will reply. Turning it off for an account, which some legacy applications require, means the KDC will send that account's encrypted reply to anybody who asks — the whole basis of [[Security-Terms#^as-rep|AS-REP]] roasting. ^pre-authentication

_**Preprocessing**_: Refers to the preparation and cleaning of raw data before analysis, such as normalizing logs, filtering noise, or formatting network traffic, making it suitable for tasks like threat detection, machine learning, or SIEM ingestion.

_**Primitive**_: the fundamental capability an exploit grants, described independently of the final goal — for example a controlled 4-byte write into the page cache, rather than "root". Reaching root requires applying the primitive, often repeatedly, against a suitable target. ^primitive

_**PrintSpoofer**_: one of the "potato" tools — see [[Security-Terms#^potato|the potato family]]. It abuses the Print Spooler service to make it connect to a named pipe you control, and it was the answer when JuicyPotato stopped working on Windows 10 1809 and Server 2019. ^printspoofer

_**Priv2Admin**_: a reference table mapping each Windows privilege (`SeImpersonatePrivilege`, `SeBackupPrivilege`, and the rest) to the concrete technique that turns it into administrator. Its use is immediately after `whoami /priv`: it converts a list of names into a list of next moves. ^priv2admin

_**PrivescCheck**_: a PowerShell script that enumerates Windows privilege-escalation opportunities and, unlike WinPEAS, groups its output by severity with an explanation of why each item matters. Useful as the second opinion when WinPEAS produced a wall of yellow. ^privesccheck

_**Process Injection**_: A technique where an attacker inserts malicious code into the address space of a legitimate running process, allowing the code to execute under the guise of a trusted process to evade detection, escalate privileges, or maintain persistence.

_**Proprietary**_: Owned and controlled by a person or company; not open or freely shared. Often refers to closed-source software, protocols, or formats that are distributed under restrictive licenses.

_**Provenance**_: Refers to the documented origin, history, and chain of custody of data, files, or evidence, used in forensics and supply chain security to verify authenticity, track where something came from, and detect tampering or unauthorized changes.

_**Pseudo-Code**_: Pseudo-code is a simplified, informal way of writing the steps of an algorithm, using a mixture of natural language and programming-like structures, without strict syntax of any programming language.

_**PsExec**_: the Sysinternals tool that runs a command on a remote Windows machine by copying a service binary over SMB and starting it. Everything named "psexec" — Impacket's, Metasploit's — is a reimplementation of that idea. It needs administrative rights on the target and it writes to disk, so it is both powerful and loud. ^psexec

_**PSReadLine**_: the PowerShell module that gives the console its editing and history. It writes every command typed into a plain text file per user, kept across reboots and not cleared by closing the window — which is why that file is one of the first things worth reading on a Windows box. ^psreadline

_**PTES (Penetration Testing Execution Standard)**_: a published methodology dividing an engagement into seven phases, from pre-engagement interaction through reporting. Its value here is as a checklist against which to notice that you skipped a phase — most commonly that you went from scanning to exploitation without ever doing threat modelling. ^ptes

_**PTR record**_: the DNS record that maps an address back to a name — the reverse of the usual lookup. On an internal range it is often the fastest inventory available, because the naming is rarely random: `dc01`, `sql02`, `backup`. ^ptr-record

_**PTY (Pseudo-Terminal)**_: It is a software-based terminal that emulates a real terminal, enabling programs to run as if they are connected to an actual TTY device. ^pty

## R

_**\r\n (CRLF)**_: a two-character sequence — carriage return (`\r`) followed by line feed (`\n`) — used to mark the end of a line in many network protocols (e.g. HTTP, SMTP, FTP), even though modern operating systems like Linux use just `\n` for line endings internally.

_**RBAC (Role-Based Access Control)**_: An access control model where permissions are assigned based on roles within the organization, rather than to specific individuals.

_**RC4**_: an old stream cipher, fast and broken, still accepted by Kerberos for backwards compatibility. A ticket encrypted with it is the cheapest kind to attack offline, so a domain that still permits RC4 is measurably easier to roast than one that does not — which is why disabling it is a standard hardening step. ^rc4

_**RCE (Remote Code Execution)**_: running commands of your choosing on a target over the network. It is the outcome, not the technique: command injection, deserialisation, file upload and template injection all end there. The distinction worth keeping is between code execution and a shell — the first is one command at a time with no session, and turning it into the second is a separate step. ^rce

_**Redundancy**_: Having backups or duplicates so that if one component fails, the system can continue to operate without interruption.

_**Regulatory Compliance**_: The act of adhering to laws, regulations, guidelines, and specifications set by governmental or regulatory authorities.

_**Render**_: To cause to become; to provide; to make; or to produce (especially visually). to cause something to be in a particular state — as in "render a system unavailable" or "render a vulnerability exploitable," describing the outcome of an attack or action on a target.

_**Repudiate**_: Refers to the act of denying or rejecting responsibility for an action or communication, such as a user denying they sent a message or performed a transaction; the security goal of nonrepudiation exists to prevent this.

_**Resilience**_: Resilience is the ability to recover quickly from difficulties, damage, or disruptions, or to withstand and adapt to challenges without collapsing. Refers to a system's ability to withstand and recover from cyberattacks, failures, or disruptions, ensuring continuity of operations and minimizing damage.

_**Resilient**_: describing a system or network that can withstand, recover from, or adapt to attacks, failures, or disruptions while continuing to function.

_**REST (Representational State Transfer)**_: An architectural style for designing networked applications that uses standard HTTP methods (GET, POST, PUT, DELETE) to perform operations on resources, commonly used in web APIs; in security, REST APIs are frequent targets for attacks like broken authentication, injection, and IDOR.

_**Retention**_: Refers to the practice and policies governing how long data, such as logs, backups, or records, is stored and kept before deletion, which is critical for compliance, forensic investigations, and incident response.

_**RFB (Remote Frame Buffer)**_: RFB (Remote Frame Buffer) is a simple protocol used for remote access to graphical user interfaces. It allows users to interact with a remote system's desktop environment over a network, and is primarily used by VNC (Virtual Network Computing) applications.

_**RFC (Request for Comments)**_: A published technical memorandum from the Internet Engineering Task Force (IETF) and related groups that describes Internet protocols, procedures, best practices, and conventions. RFCs can be informational, experimental, standards‑track (which may become Internet Standards), or Best Current Practice (BCP). They serve as the authoritative references for protocol behavior, configuration guidance, and interoperability requirements.

_**RFC 1918**_: RFC 1918 (Request for Comments 1918) is a technical document that defines private IP address ranges for use in local area networks (LANs) or private networks. These IP addresses are not routable on the public internet and are used to conserve global IP address space.

_**RFI (Remote File Inclusion)**_: file inclusion where the path you supply is a URL rather than a local path, so the application fetches and includes a file from a server you control. Far rarer than [[Security-Terms#^lfi|LFI]] because PHP's `allow_url_include` has defaulted to off for many years — but when it is on, it hands over code execution in one request. ^rfi

_**RID (Relative Identifier)**_: the last part of a Windows [[Security-Terms#^sid|SID]] — the number that distinguishes one account from another inside the same domain or machine. The well-known ones are worth memorising: 500 is the built-in Administrator, 501 Guest, 512 Domain Admins. Reading a SID from right to left tells you what an account is before you know its name. ^rid

_**Risk-driven**_: An approach or process guided primarily by the identification, assessment, and management of risks.

_**robots.txt**_: a file placed at a website's root that instructs web crawlers which paths they are allowed or disallowed to access, useful in reconnaissance since disallowed paths often reveal sensitive or hidden directories.

_**RPC (Remote Procedure Call)**_: a mechanism that lets one process expose functions (procedures) so another process can invoke them as if calling them locally, passing arguments and getting results over a socket. Widely used by Windows services; a procedure that runs a command while its service runs as SYSTEM turns a design feature into a privilege-escalation path. ^rpc

_**RSAT (Remote Server Administration Tools)**_: the optional Windows feature that puts the server management tools, the ActiveDirectory PowerShell module among them, onto a machine that is not a server. It matters because `Get-ADUser` and its relatives exist on a domain controller and nowhere else by default, so a module-not-found error on a workstation is this feature being absent rather than a permission you are missing. ^rsat

_**Rubeus**_: a Windows tool for everything Kerberos — requesting tickets, roasting accounts, passing and forging them. It runs on a domain-joined host and takes the place of the Python tooling you would otherwise run from Kali, which makes it the natural choice when what you hold is a shell on a domain machine rather than a credential on your own. ^rubeus

_**Runtime**_: in Java, a built-in class (`java.lang.Runtime`) that provides an interface to the host operating system, most notably its `exec()` method for running arbitrary OS commands; a frequent target in code-execution exploits, since reaching it from within a sandboxed script typically means full remote command execution on the server.

## S

_**S3 (Simple Storage Service)**_: AWS object storage. Buckets are addressed by name at a predictable URL, which is why guessing bucket names is a recon technique, and why a bucket whose listing permission is granted to "any authenticated AWS user" is exposed to anyone with a free account — not to nobody, which is how it is usually misread. ^s3

_**SAM (Security Account Manager)**_: the Windows registry hive holding local account password hashes, on disk at `C:\Windows\System32\config\SAM`. It is locked while Windows runs, so it is taken either from a backup copy, from a volume shadow copy, or with a privilege that bypasses the lock. It is decrypted with the SYSTEM hive, so both files are needed. ^sam

_**SAML**_: an XML-based standard for single sign-on between an identity provider and an application. Its bugs come from the XML: the assertion is signed, so attacks target how the signature is validated and how the parser handles comments and duplicate elements rather than the protocol logic. ^saml

_**SAN (Subject Alternative Name)**_: an extension field in an X.509 certificate that lists additional hostnames, IP addresses, or domains the certificate is valid for — often examined during certificate transparency reconnaissance to discover related subdomains.

_**Scalability**_: Refers to how well a security system or protocol can expand to protect larger or more complex infrastructures without compromising performance or security.

_**Scan (DynamoDB)**_: An operation that reads every item in a table without requiring a key, making it a direct path to full-table disclosure wherever a policy grants it to an untrusted principal.

_**SCF (Shell Command File)**_: a small Windows file format that can tell Explorer to fetch an icon from a UNC path. Dropping one in a writable share means that anyone who merely opens the folder — no clicking — causes their machine to authenticate to the host you named, handing you a [[Security-Terms#^netntlmv2|NetNTLMv2]] response. ^scf

_**SCM (Service Control Manager)**_: the Windows component that starts, stops and configures services — the thing `sc.exe` and `Get-Service` talk to. It matters because each service is a securable object with its own [[Security-Terms#^dacl|DACL]]: the right to change a service's configuration means the right to change the binary it runs and the account it runs as, and services run at boot as SYSTEM. ^scm

_**SDK (Software Development Kit)**_: the libraries and tools an application uses to talk to a platform. Relevant in cloud work because an SDK reads credentials from predictable places — environment variables, `~/.aws/credentials`, an instance metadata endpoint — so finding where the SDK looks tells you where the credentials are. ^sdk

_**SeAssignPrimaryTokenPrivilege**_: a Windows privilege allowing a process to start a new process under a different token — the companion of [[Security-Terms#^seimpersonate|SeImpersonatePrivilege]], which only allows acting as another token within an existing thread. Service accounts often hold both, and tools in [[Security-Terms#^potato|the potato family]] use whichever is present. ^seassignprimarytoken

_**SeBackupPrivilege**_: a Windows privilege that lets an account read any file regardless of its ACL, because backup software must be able to. It does not grant write access and it does not make you an administrator — but it is enough to copy the SAM and SYSTEM hives off a live system, which amounts to the same thing. ^sebackup

_**Security Headers (securityheaders.com)**_: A free online scanner created by Scott Helme (now a Snyk project) that analyzes a website's HTTP response headers and assigns a security grade (A+ to F). It checks for headers like `Content-Security-Policy`, `Strict-Transport-Security`, `X-Frame-Options`, and `X-Content-Type-Options`, helping identify missing protections against attacks such as XSS, clickjacking, and protocol downgrade.

_**Segregate**_: Refers to the practice of separating systems, networks, data, or users into isolated segments to limit access and contain potential breaches, reducing the attack surface and preventing lateral movement.

_**SeImpersonatePrivilege**_: a Windows privilege allowing a process to act using another account's token after that account authenticates to it. Service accounts hold it by default, which is why a web shell running as a service user has it. Combined with something that makes a privileged service connect back to you, it is SYSTEM — see [[Security-Terms#^potato|the potato family]]. ^seimpersonate

_**SeRestorePrivilege**_: the write-side counterpart of [[Security-Terms#^sebackup|SeBackupPrivilege]]: it lets an account write any file regardless of its ACL. That includes replacing a binary a service runs, or a DLL it loads, which turns it directly into code execution as that service. ^serestoreprivilege

_**Service Ticket**_: what Kerberos actually hands to a service. It is issued by the [[Security-Terms#^tgs|ticket-granting service]] and encrypted with the service account's password hash, so the service can open it without ever contacting the domain controller — and so anyone who obtains one can attack that password offline. ^service-ticket

_**SeTakeOwnershipPrivilege**_: a Windows privilege allowing an account to take ownership of any object without being granted access to it. Ownership is enough, because an object's owner may always rewrite its [[Security-Terms#^dacl|DACL]] — so this privilege is two steps from full control of anything on the machine. ^setakeownership

_**SFTP**_: file transfer carried inside an SSH session on port 22 — not FTP with TLS, which is FTPS and a different protocol on different ports. It matters practically: if SSH is open you already have file transfer, and an account restricted to SFTP-only may still be usable for reading files even when it cannot get a shell. ^sftp

_**SGID (Set Group ID)**_: the counterpart of [[Security-Terms#^suid|SUID]] for groups: an executable with the SGID bit runs with the group of the file rather than the group of the user running it. Shows as `s` in the group column of `ls -l`. On a directory it means something different and often more useful — new files inside inherit the directory's group instead of the creator's. ^sgid

_**SHA family (SHA-1, SHA-256, SHA-512)**_: a family of hash functions, distinguished by output length: 40, 64 and 128 hex characters respectively. Recognising the length identifies the hash type, which is the argument hashcat needs. Note the difference between the bare hash and the password form: `$6$` at the start of a Unix hash means sha512crypt — SHA-512 applied thousands of times with a salt — and that is a different, far slower cracking mode than raw SHA-512. ^sha

_**SharpHound**_: the official BloodHound collector, written for Windows and run on a domain-joined host. It is the data-gathering half and nothing more: it asks the domain for group memberships, logon sessions, permissions and trusts, and writes the answers out as files for the interface to ingest. The Python collector `bloodhound-python` does the same job from Linux and is not officially supported. ^sharphound

_**Shellcode**_: a small piece of machine code injected into a process, typically to spawn a shell with that process's privileges. ^shellcode

_**SID (Security Identifier)**_: the string Windows actually uses to identify an account or group — `S-1-5-21-1004336348-1177238915-682003330-512`. Names are only labels mapped onto it, which is why renaming an account changes nothing about its access. The tail is the [[Security-Terms#^rid|RID]]; the long middle section identifies the domain or machine, so two SIDs sharing it come from the same place. ^sid

_**Silver Ticket**_: a forged [[Security-Terms#^service-ticket|service ticket]], made with one service account's password hash rather than the domain's master key. It grants access to that one service only, and it is never presented to a domain controller, which makes it quieter than a [[Security-Terms#^golden-ticket|Golden Ticket]] and far narrower. ^silver-ticket

_**sitemap.xml**_: a file placed at a website's root listing its pages and structure for search engine crawlers, useful in reconnaissance for discovering site content and hidden endpoints.

_**SLAAC**_: Stateless Address Autoconfiguration is an IPv6 mechanism that allows a host to automatically generate its own IPv6 addresses using network prefix information advertised by routers (Router Advertisements), without requiring a stateful server like DHCPv6. SLAAC typically creates link-local and global addresses and relies on processes such as Duplicate Address Detection (DAD) to avoid address conflicts.

_**SMBv1**_: the first dialect of SMB, disabled by default since Windows 10 1709 and the protocol version EternalBlue attacks. Finding it enabled is itself a finding: it means the host is either old or deliberately configured for compatibility with something old. ^smbv1

_**Smuggle**_: to covertly move malicious data, code, or commands past a security control — such as smuggling payloads through a WAF or IDS by obfuscating or splitting the content to avoid detection.

_**SNI (Server Name Indication)**_: the TLS extension where the client states which hostname it wants before the certificate is chosen, so one address can serve many sites over HTTPS. It is the HTTPS equivalent of the Host header: if a virtual host only answers to its own name, connecting to the IP address gives you the default site and not the one you are looking for. ^sni

_**SNMP (Simple Network Management Protocol)**_: An application‑layer protocol used for collecting and organizing information about managed devices on IP networks and for modifying that information to change device behavior. SNMP agents on network devices expose management data in a Management Information Base (MIB) and communicate with management systems using operations such as GET, SET, and TRAP/INFORM over UDP (typically ports 161 for agents and 162 for traps).

_**SOA record**_: the "start of authority" record, one per zone, holding the primary nameserver, an administrative email address (written with the `@` as a dot) and a serial number the zone's owner bumps on every edit. The email address is a real person's, which makes it a username candidate. ^soa-record

_**SOAP**_: an XML-based protocol for calling remote services, older and heavier than REST. Two consequences: the message is XML, so [[Security-Terms#^xxe|XXE]] is on the table, and a service often publishes a WSDL document describing every method and parameter it accepts — a complete map of the attack surface, offered voluntarily. ^soap

_**SOCKS**_: a proxy protocol that forwards whole TCP connections rather than understanding what is inside them, so it carries any protocol. This is what makes it the shape of a pivot: `ssh -D`, chisel or ligolo present a SOCKS port on your machine, and `proxychains` pushes other tools through it so they reach a network they have no route to. ^socks

_**soft-404**_: a page that returns HTTP 200 while actually saying "not found" in its body — a friendly error page instead of a status code. It is the reason a content-discovery run reports hundreds of hits that are all the same page, and the reason `--fs` or `--fw` filtering by response size exists: the status code has stopped carrying the information, so the length has to. ^soft-404

_**splice()**_: a system call that moves data into a pipe by referencing the underlying pages rather than copying them. ^splice

_**SPN (Service Principal Name)**_: the name a Kerberos client asks for a ticket to, in the form `service/host.domain` — `cifs/server1.corp.local`, `http/intranet.corp.local`. It maps a service to the account running it, which is why it must be registered in the directory, why Kerberos cannot be used against a bare IP address, and why an account carrying one is [[Security-Terms#^kerberoasting|roastable]]. ^spn

_**Spool**_: Refers to the temporary storage of data, such as print jobs or file transfers, which can be a target for attackers attempting to intercept or manipulate the data in the spool.

_**SQLi (SQL Injection)**_: getting the database to treat data you supplied as part of the query. The classification worth knowing is by how the answer reaches you: in-band (the result is printed, which includes UNION-based), blind (only the application's behaviour differs — a boolean or a delay), and out-of-band (the database is made to contact a server you control). Which one you are in decides the tooling, not the payload. ^sqli

_**SQLite**_: a database that is a single file with no server behind it, used by browsers, phone applications and small web applications. Its significance on a target is exactly that: finding `database.db` or `app.sqlite` on disk is finding the whole database, readable without credentials. ^sqlite

_**SSID (Service Set Identifier)**_: The name or identifier of a wireless network (Wi-Fi) that allows devices to connect to it. It is broadcast by the router or access point for visibility by nearby devices.

_**SSO (Single Sign-On)**_: one authentication serving many applications. In an engagement its meaning is leverage: one set of credentials is worth many services, and the interesting weakness is usually not the login page but the trust between the identity provider and an application that accepts its assertion too loosely. ^sso

_**SSRF (Server-Side Request Forgery)**_: making the server itself issue a request to a URL you choose. Its value is position rather than content: the server can reach things you cannot — a database on loopback, an internal admin panel, and in cloud environments the instance metadata service that hands out credentials to anything able to ask from inside. ^ssrf

_**STARTTLS**_: an email protocol command that upgrades a plaintext connection to an encrypted TLS connection on the same port, rather than using a separate encrypted port from the start.

_**Strace**_: It is a diagnostic, debugging, and troubleshooting tool for Linux. It is used to monitor and intercept system calls and signals made by a process.

_**STS (Security Token Service)**_: the AWS service that issues temporary credentials — an access key beginning `ASIA`, a secret, and a session token that must accompany them. Every temporary credential set expires, and omitting the session token produces an authentication failure that reads as though the key itself were wrong. ^sts

_**Subdomain takeover**_: a vulnerability where an attacker claims control of a subdomain by pointing it at a third-party service (e.g. cloud hosting, SaaS) that no longer has a valid resource there, since the DNS record was left pointing to a now-unclaimed service.

_**Sublist3r**_: a subdomain enumeration tool that queries public sources — search engines, certificate transparency, DNS aggregators — rather than brute-forcing names. That makes it fast and completely silent from the target's point of view, and also incomplete: it finds what has been published, not what exists. ^sublist3r

_**SUID (Set User ID)**_: A Unix permission bit that makes an executable run with the file owner's effective user ID rather than the invoking user's ID. Misconfigured SUID programs can become privilege-escalation paths. ^suid

_**SYSVOL**_: a folder on every domain controller, shared to the whole domain and readable by every domain user, holding Group Policy files and logon scripts. That combination — writable by administrators, readable by everyone — is why credentials left in a script or a [[Security-Terms#^gpp|GPP]] file there are exposed to the entire domain. ^sysvol

## T

_**Tailgate**_: a physical social engineering technique in which an unauthorized person follows closely behind an authorized individual to gain access to a restricted area without using credentials.

_**TCP flags (SYN, ACK, RST, FIN, PSH, URG)**_: single bits in the TCP header that carry the state of a connection. The three that matter when reading a scan: SYN opens, ACK acknowledges, RST refuses. An open port answers a SYN with SYN-ACK; a closed one answers with RST; a filtered one answers with nothing at all — and that third case, silence, is the same silence you get from a host that is down, which is why filtered and dropped are reported as one state. ^tcp-flags

_**Telnet**_: a remote-login protocol on TCP port 23 that predates SSH and encrypts nothing — the login and the whole session cross the wire in the clear. It survives on printers, switches, routers and embedded boards, where it is often left open or on vendor defaults. The `telnet` *client* has a second life unrelated to the protocol: it opens a bare TCP socket to any port, which is the standard way to read a service banner by hand. ^telnet

_**TFTP**_: a stripped-down file transfer protocol on UDP port 69 with no authentication whatsoever. It survives in network device provisioning and PXE boot. Being UDP, it crosses some egress filters that block TCP, which occasionally makes it the only file transfer that works. ^tftp

_**TGS (Ticket Granting Service)**_: the half of the [[Security-Terms#^kdc|KDC]] that trades a [[Security-Terms#^tgt|ticket-granting ticket]] for a [[Security-Terms#^service-ticket|service ticket]]. The reply it sends is written `TGS-REP`, and that reply is the material Kerberoasting cracks. ^tgs

_**TGT (Ticket Granting Ticket)**_: the first ticket Kerberos issues, proving you authenticated. It is encrypted with the [[Security-Terms#^krbtgt|KRBTGT]] hash so only a domain controller can read it, you cannot see inside your own, and it is what you present to ask for everything else. Typical lifetime is ten hours. ^tgt

_**TheHarvester**_: an OSINT tool that collects email addresses, subdomains, hostnames and employee names for a domain from public sources. Its output feeds two things directly: a username list for spraying, and a subdomain list to resolve. ^theharvester

_**TLS / SSL (Transport Layer Security)**_: the encryption layer under HTTPS and many other protocols. SSL is the obsolete original; every current version is TLS, and the two names are used interchangeably in tool names and options long after the thing itself was replaced. Two practical consequences: a certificate carries names — subject and Subject Alternative Names — that leak internal hostnames, and a plain `nc` to a TLS port produces nothing readable, which is what `openssl s_client` is for. ^tls

_**Trail**_: Refers to the traces or records left behind by activity within a system, such as an audit trail that logs user actions and events, which can be used to track behavior, investigate incidents, or detect malicious activity.

_**Triage**_: Refers to the process of prioritizing and categorizing security incidents, alerts, or vulnerabilities based on their severity and potential impact, allowing analysts to address the most critical threats first during incident response.

_**TShark**_: the command-line Wireshark. Same capture engine and the same display filters, printing to standard output — which is what makes it usable over a shell on a remote box, and scriptable. `-Y` takes a display filter, applied after capture; `-f` takes a capture filter, applied before, and mixing the two syntaxes is the usual first error. ^tshark

_**TTY (Teletypewriter)**_: It is a terminal interface that allows direct interaction with a system through a command-line session. It traditionally refers to a physical or virtual terminal connected to the system.

_**TXT record**_: a DNS record holding free text, written for machines rather than people. It leaks because of what gets put there: SPF and DKIM mail policy, and domain-ownership proof tokens that name every SaaS provider the organisation has ever signed up to. ^txt-record

_**Typosquatting**_: A type of attack where an attacker registers domain names that are misspellings or close variations of legitimate domains (e.g., `gooogle.com` instead of `google.com`), hoping to catch users who mistype URLs, in order to deliver malware, steal credentials, or conduct phishing.

## U

_**UAC (User Account Control)**_: the Windows prompt that appears when an action needs administrative rights. The mechanism underneath is what matters: an administrator's session carries two tokens, a filtered one used by default and a full one used after the prompt. So a shell as an administrator is not an administrative shell until it is elevated, and a bypass is a way of obtaining the full token without the prompt. ^uac

_**UDF (User Defined Function)**_: a function added to a database by loading a shared library from disk. In MySQL and PostgreSQL it is the standard route from database access to command execution: write a library into the plugin directory, register a function pointing at it, call it. It needs file-write permission and a known directory, which is why those two checks come first. ^udf

_**UID (User ID)**_: the number Linux actually uses to identify a user; the name is a label in `/etc/passwd` mapped onto it. Root is UID 0 — and it is the number, not the name, that grants the power, so a second account with UID 0 is a second root. This is also why NFS without root squashing is dangerous: the server believes the client's claim about which UID is asking. ^uid

_**Unauthenticated role**_: The IAM role a Cognito Identity Pool assumes on behalf of callers who have not logged in; its attached policy is the only authorization boundary protecting anything the anonymous client can reach.

_**UNC path**_: the Windows way of naming a network location: `\\server\share\file`. It matters beyond file access, because many Windows features accept one where a local path is expected — and simply resolving a UNC path makes the machine authenticate to the server named in it, which is the mechanism behind [[Security-Terms#^scf|SCF]] files and forced-authentication tricks. ^unc

_**UPX**_: an executable packer that compresses a binary and unpacks it in memory at run time. It appears in two places: legitimately, to make a tool small enough to transfer, and defensively, because packing changes a file's signature. `upx -d` reverses it, and a packed binary that antivirus flags on sight is usually flagged for the packing rather than the payload. ^upx

_**UTF-8 / UTF-16LE**_: two ways of writing text as bytes. UTF-8 uses one byte per ASCII character and is what Linux and the web assume; UTF-16LE uses two, and is what several Windows tools emit. This is why a file produced on Windows can look like every character is separated by a space or a null when read on Linux, and why `iconv` appears in transfer steps. It is also why PowerShell's `-Encoding` argument is worth setting deliberately rather than accepting the default. ^utf16

## V

_**Vigilant**_: Vigilant means being alert and watchful, especially to avoid danger, mistakes, or attacks. It describes someone or something that carefully monitors for potential threats or problems. Watchful and alert to potential threats or anomalies; describes the proactive monitoring mindset in security operations.

_**VM Obfuscation**_: An advanced technique compiling code into custom bytecode run by a unique embedded JS virtual machine; no automated online deobfuscator exists, requiring manual reverse engineering.

_**VNC (Virtual Network Computing)**_: A graphical desktop-sharing system that uses the Remote Frame Buffer (RFB) protocol to control another computer remotely. It allows users to access and interact with the desktop environment of a remote machine as if they were sitting in front of it.

_**VoIP (Voice over IP)**_: Technology and set of protocols that deliver voice and multimedia communication (telephony) over Internet Protocol (IP) networks instead of the traditional circuit‑switched telephone networks. Common components and protocols include SIP, RTP/RTCP, SRTP, H.323, and media gateways. VoIP systems must handle signaling, media transport, NAT traversal, and often integrate with PSTN gateways.

_**VPN (Virtual Private Network)**_: an encrypted tunnel putting your machine on a remote network as though it were plugged in there. In lab work it is the thing that has to be up before anything else works, and the first suspect when a target that answered yesterday answers nothing today — a dropped tunnel and a filtered host look identical from a scanner. ^vpn

## W

_**WAF (Web Application Firewall)**_: a filter in front of a web application that inspects requests and blocks ones matching known attack patterns. The important consequence is that a blocked request is not a failed attack: the response comes from the WAF, not the application, so the payload never reached the code and proved nothing about it. A sudden change in response time, status code or body length across otherwise identical requests is how you notice one. ^waf

_**WAP (Wireless Access Point)**_: A network device that provides wireless (Wi‑Fi) connectivity by bridging wireless clients to a wired LAN. APs advertise SSIDs, handle authentication/association, and may implement security (WPA2/WPA3, 802.1X). Misconfiguration (open SSIDs, weak encryption, default admin credentials, enabled WPS) or outdated firmware makes APs a common attack vector.

_**Wayback Machine**_: an archive (website) of historical snapshots of websites, useful in reconnaissance for uncovering old pages, endpoints, or files that have since been removed from the live site.

_**WebDAV (Web Distributed Authoring and Versioning)**_: an extension of HTTP that allows clients to create, edit, move, copy, and delete files directly on a web server — essentially turning a web server into a remote file system. Misconfigured WebDAV (e.g. allowing PUT/MOVE methods without proper auth) lets an attacker upload malicious files (like a webshell) directly to the server.

_**WebSocket**_: A communication protocol providing full-duplex, persistent connections over a single TCP connection, allowing both client and server to send data at any time. Unlike HTTP's request-response model, the connection stays open after an initial handshake (initiated via the `Upgrade: websocket` header), using the `ws://` or encrypted `wss://` scheme. Common in real-time applications (chat, gaming, live feeds); from a security standpoint, WebSocket traffic can bypass traditional HTTP-based WAFs and filters, creating an attack surface for issues like Cross-Site WebSocket Hijacking (CSWSH) and message injection.

_**Werkzeug**_: A comprehensive WSGI web application library for Python that serves as the underlying foundation for the Flask framework; in security contexts, its debugger console (if left enabled in production) can expose a PIN-protected interactive shell that attackers may exploit for remote code execution.

_**WES-NG (Windows Exploit Suggester — Next Generation)**_: a tool that takes the output of `systeminfo`, compares the installed patch list against Microsoft's vulnerability database, and lists the missing patches with their known exploits. It runs on your own machine, not on the target — the target only has to produce `systeminfo` output — which makes it the quietest Windows enumeration step available. ^wes-ng

_**WinPEAS**_: the Windows half of [[Security-Terms#^peass|PEASS-ng]]: one executable running several hundred local privilege-escalation checks — service permissions, unquoted paths, stored credentials, registry misconfigurations, installed software — and colour-coding the results, where red on yellow means very probably exploitable. It comes from the PEASS-ng releases page, it is unsigned, and [[Security-Terms#^amsi|AMSI]] and antivirus both know it well, which is why the `.bat` and obfuscated variants exist. Like LinPEAS it produces candidates, not conclusions. ^winpeas

_**WinRM (Windows Remote Management)**_: Microsoft's remote management protocol, on TCP 5985 plain and 5986 over TLS — the transport under PowerShell Remoting. It carries SOAP over HTTP. Membership in the local Remote Management Users group is enough to use it, which is why an account that cannot RDP can often still get a full PowerShell session. `evil-winrm` is the usual client. ^winrm

_**WLAN (Wireless Local Area Network)**_: a local network reached over Wi-Fi rather than a cable. It appears in enumeration because a machine with a wireless interface has stored the networks it has joined, and on Windows those profiles hold the pre-shared key in recoverable form. ^wlan

_**WPA / WPA2 / WPA3 (Wi-Fi Protected Access)**_: A security protocol developed to secure wireless networks by providing data encryption and strong access control mechanisms. It uses TKIP (Temporal Key Integrity Protocol) to dynamically generate unique encryption keys for each device, ensuring better security. WPA2, an upgraded version, employs AES (Advanced Encryption Standard) for stronger protection. WPA3 introduces enhancements like Simultaneous Authentication of Equals (SAE) for stronger key exchange, 192-bit encryption for enterprise networks, and protections against attacks on open networks such as Wi-Fi Easy Connect. ^wpa

_**Write Blocker**_: A hardware or software tool used in digital forensics that allows read-only access to a storage device, preventing any modification of the original data to preserve evidence integrity during an investigation.

_**www-data**_: A service account commonly used by web-server processes on Debian/Ubuntu-based systems. The actual account depends on the distribution and configuration; a shell as `www-data` often indicates a web foothold with limited privileges.

## X

_**x86-64 / ARM**_: the two processor architectures you will meet. A compiled exploit must match the target's architecture or it will not run, and the error — "cannot execute binary file" or an immediate crash — says nothing about architecture. `uname -m` on Linux and `echo %PROCESSOR_ARCHITECTURE%` on Windows settle it before you waste a transfer. ^x86-64

_**XInclude**_: an XML feature for pulling one document into another. It matters because it is a second route to [[Security-Terms#^xxe|XXE]]: when an application blocks or strips the DOCTYPE declaration, an XInclude element inside the body can still make the parser fetch a file, and the usual defence never looked at it. ^xinclude

_**XSS (Cross-Site Scripting)**_: getting script of your choosing to run in another user's browser in the context of the target site. Three kinds: reflected, where the payload travels in the request and comes back in the response; stored, where the application saves it and serves it to everyone; and DOM-based, where the payload never reaches the server at all and is written into the page by the site's own JavaScript. The third is invisible in server logs, which is also why it is missed. ^xss

_**XXE — XML External Entity**_: When a web app parses user-supplied XML without disabling external entities, an attacker can define an entity that reads files from the server. ^xxe
