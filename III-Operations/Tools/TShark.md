# TShark

The command-line Wireshark. Reads the same capture files and uses the same display-filter syntax, but prints plain text — so output pipes, greps and redirects to a file. Reach for it when you have been handed a `.pcap`/`.pcapng` and need to pull specific data out of it, not click through it.

## Orient before you filter

```bash
tshark -r traffic.pcapng -z conv,tcp -q
```

- `-r` → read from a file instead of a live interface.
- `-z conv,tcp` → a conversation statistic: every endpoint pair and how much each exchanged.
- `-q` → suppress the per-packet listing so only the summary table prints.

## Pull one field out

```bash
tshark -r traffic.pcapng -Y "http.cookie" -T fields -e http.cookie > cookies.txt
```

- `-Y` → display filter, identical syntax to Wireshark's filter bar.
- `-T fields -e <name>` → print only the named field instead of full packets. `-e` can repeat for several fields.
- the field name is the **internal Wireshark name** (`http.cookie`, lowercase `proto.field`), not the human header name → get it wrong and the filter matches nothing while the capture is full of the data. Confirm a name by clicking the field in Wireshark and reading the status bar.
- `>` → redirect to a file for replay or cracking.
