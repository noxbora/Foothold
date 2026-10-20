# 161 — SNMP

A management protocol that answers questions about a device: its users, its running processes, its installed software, its listening ports, its network interfaces. Version 1 and version 2c authenticate with a single shared string that is very often left at the factory value, and the answers arrive as a flat tree of numbered entries.

## 1 — Is the community string still a default

```bash
onesixtyone -c /usr/share/wordlists/seclists/Discovery/SNMP/common-snmp-community-strings.txt TARGET
```

- The string is a password with no username attached. `public` grants read and `private` historically grants write, and both survive in production far more often than anyone would guess.
- `onesixtyone` sends one packet per candidate over `udp` and does not retry, so run it twice before believing a negative on a slow or filtered path.
- Version 3 uses real usernames and passwords instead. If everything fails and the host is modern, that is the likely reason and it ends this note.

## 2 — Reading only the branches that carry answers

```bash
snmpwalk -v2c -c public TARGET 1.3.6.1.4.1.77.1.2.25
```

```bash
snmpwalk -v2c -c public TARGET 1.3.6.1.2.1.25.4.2.1.2
```

```bash
snmpwalk -v2c -c public TARGET 1.3.6.1.2.1.25.6.3.1.2
```

```bash
snmpwalk -v2c -c public TARGET 1.3.6.1.2.1.6.13.1.3
```

- Those four numbers are [[Security-Terms#^oid|OID]] paths and each names one branch: user accounts, running processes, installed software, and local listening ports. Walking `1.3.6.1` instead returns all of them plus everything else, which is how a useful service turns into an unreadable screen.
- The process branch is the valuable one, because it prints full command lines. Credentials passed as arguments appear here in clear text and appear nowhere else on the host that you can read.
- A branch that does not exist returns `No Such Object available on this agent`. That is a shape answer about the device, not a failure of your string.
- Expect single figures to low tens of lines from each of these. Hundreds means you walked a parent branch by mistake.
