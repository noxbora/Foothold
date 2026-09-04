---
type: tool
platform: any
status: working
fluency: guided
source: thm
updated: 2026-08-30
---

# TShark

The command-line Wireshark. Reads the same capture files and uses the same display-filter syntax, but prints plain text — so output pipes, greps and redirects to a file. Reach for it when you have been handed a `.pcap`/`.pcapng` and need to pull specific data out of it, not click through it.

## Orient before you filter

**Why now** — you have an unknown capture and no idea what is in it. Filtering blind wastes time; first find out who talked to whom and over what, so you know which protocol and endpoints are worth a filter at all.

```bash
tshark -r traffic.pcapng -z conv,tcp -q
```

- `-r` → read from a file instead of a live interface.
- `-z conv,tcp` → a conversation statistic: every endpoint pair and how much each exchanged.
- `-q` → suppress the per-packet listing so only the summary table prints.

**What you will see**

- **Found** — a table of `A:port <-> B:port` rows sorted by bytes. The dominant pair, and the ports involved, tell you where the interesting traffic is — a big flow to `:80` says HTTP, to `:21` says FTP with credentials likely in the clear.
- **Empty** — no conversations means the file is empty, truncated, or not the format you think — `capinfos traffic.pcapng` confirms packet count and type.
- **Error** — `tshark: The file ... appears to be damaged` means a truncated capture; `editcap` can sometimes salvage it. `Permission denied` reading a live interface (no `-r`) means you need to be in the `wireshark` group or run with privilege.
- **Noise** — high-byte flows that are just a bulk download or [[Security-Terms#^tls|TLS]] — encrypted and uninteresting. The useful flow is often a *small* one on a plaintext protocol, not the biggest bar.

**Then** — a plaintext protocol worth reading goes to the field-extraction step below. An all-TLS capture means the payloads are encrypted; the value is then in metadata (who, when) rather than content.

## Pull one field out

**Why now** — orientation pointed you at a protocol (HTTP cookies, FTP commands, DNS queries) and you want just that field across every matching packet, not whole packet dumps.

```bash
tshark -r traffic.pcapng -Y "http.cookie" -T fields -e http.cookie > cookies.txt
```

- `-Y` → display filter, identical syntax to Wireshark's filter bar.
- `-T fields -e <name>` → print only the named field instead of full packets. `-e` can repeat for several fields.
- the field name is the **internal Wireshark name** (`http.cookie`, lowercase `proto.field`), not the human header name → get it wrong and the filter matches nothing while the capture is full of the data. Confirm a name by clicking the field in Wireshark and reading the status bar.
- `>` → redirect to a file for replay or cracking.

**What you will see**

- **Found** — the field's value on each matching packet: a `session=...` cookie, a `USER admin` / `PASS ...` pair from FTP, a DNS query name. A captured cookie or credential is directly replayable.
- **Empty** — no output almost always means the **wrong field name**, not an empty capture — the single most common [[Security-Terms#^tshark|TShark]] mistake. Confirm the internal name in Wireshark before believing the protocol is absent. It can also mean the display filter excluded everything (`http.cookie` matches only requests that carried one).
- **Error** — `"<name>" isn't a valid ... filter` names an unknown field or a typo — TShark tells you the token it choked on. A filter that mixes read filter (`-R`) and display filter (`-Y`) syntax errors the same way; use `-Y`.
- **Noise** — duplicated values across retransmitted packets, and keep-alive cookies repeated on every request. `sort -u cookies.txt` before treating the count as meaningful.

**Then** — a session cookie or token goes to [[Authentication-Attacks]] to replay, or to [[Curl-and-Wget]] (`-b` / `--header`) to reuse the session from the command line. A plaintext credential goes straight into a login attempt. An empty result sends you back to Wireshark to confirm the field name.

## Reading the output

Start every unknown capture with `-z conv,tcp -q`: the dominant endpoint pairs and ports tell you where to look before you write a filter. Then remember the one rule that saves the most time — a display filter returning nothing is far more often the **wrong internal field name** than an empty capture. The names are Wireshark's own strings (`http.cookie`, lowercase `proto.field`), confirmed from the status bar, and `-T fields -e` needs that exact same name.

## Next

- [[Authentication-Attacks]] — a session cookie or token pulled from a pcap gets replayed
- [[Curl-and-Wget]] — replay a captured request with `-b`/`--header` to reuse the session

## Gaps

- No `-z follow,tcp,ascii,<n>` for reconstructing a single stream end to end.
- Nothing on decrypting TLS with a provided key log, or on extracting transferred files with `--export-objects`.
