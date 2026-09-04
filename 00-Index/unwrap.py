#!/usr/bin/env python3
"""Join hard-wrapped prose back into one line per paragraph / list item / callout line.

Obsidian renders a single newline as a visible line break unless "Strict line breaks" is on,
so a source file wrapped at 100 columns shows ragged half-empty lines in reading view — the
last word of a wrapped line sits alone. Reflowing is the reader's job, not the file's.

Never touched: frontmatter, fenced code blocks, tables, headings, horizontal rules, and any
line that begins a new block."""
import re, sys, pathlib

FENCE   = re.compile(r'^\s*(`{3,}|~{3,})')
HEADING = re.compile(r'^#{1,6}\s')
LIST    = re.compile(r'^(\s*)([-*+]\s+|\d+[.)]\s+)')
RULE    = re.compile(r'^\s*(-{3,}|\*{3,}|_{3,})\s*$')
TABLE   = re.compile(r'^\s*\|')
QUOTE   = re.compile(r'^\s*>\s?')
CALLOUT = re.compile(r'^\s*>\s*\[!\w+\]')
HTML    = re.compile(r'^\s*<')

def block_start(l):
    """A line that must begin its own output line."""
    return (not l.strip() or HEADING.match(l) or LIST.match(l) or RULE.match(l)
            or TABLE.match(l) or HTML.match(l) or FENCE.match(l))

def unwrap(src):
    lines = src.split('\n')
    out, i, n = [], 0, len(lines)

    # frontmatter passes through untouched
    if lines and lines[0].strip() == '---':
        out.append(lines[0]); i = 1
        while i < n and lines[i].strip() != '---':
            out.append(lines[i]); i += 1
        if i < n:
            out.append(lines[i]); i += 1

    while i < n:
        l = lines[i]

        if FENCE.match(l):                       # code fence: copy verbatim to its closer
            marker = FENCE.match(l).group(1)
            out.append(l); i += 1
            while i < n and not lines[i].lstrip().startswith(marker):
                out.append(lines[i]); i += 1
            if i < n:
                out.append(lines[i]); i += 1
            continue

        if not l.strip() or HEADING.match(l) or RULE.match(l) or TABLE.match(l) or HTML.match(l):
            out.append(l); i += 1
            continue

        if QUOTE.match(l):                       # callout / blockquote
            # A callout's `> [!type]` marker must stay on its own line: text joined onto it
            # becomes the callout TITLE in Obsidian, not its body.
            if CALLOUT.match(l):
                out.append(l.rstrip()); i += 1
                continue
            buf, i = l.rstrip(), i + 1
            while i < n and QUOTE.match(lines[i]):
                body = QUOTE.sub('', lines[i], count=1)
                if not body.strip():             # blank quote line ends the paragraph
                    break
                if LIST.match(body) or HEADING.match(body) or FENCE.match(body):
                    break
                buf += ' ' + body.strip()
                i += 1
            out.append(buf)
            continue

        # paragraph or list item: swallow indented continuation lines
        buf, i = l.rstrip(), i + 1
        while i < n and not block_start(lines[i]) and not QUOTE.match(lines[i]):
            buf += ' ' + lines[i].strip()
            i += 1
        out.append(buf)

    return re.sub(r'[ \t]+$', '', '\n'.join(out), flags=re.M)

if len(sys.argv) < 2:
    sys.exit('usage: unwrap.py <file.md | folder>\n'
             '  a folder is walked recursively; files are REWRITTEN in place.\n'
             '  e.g.  python3 unwrap.py ../02-Techniques/Services/23-Telnet.md\n'
             '        python3 unwrap.py ..            # the whole Playbook')

target = pathlib.Path(sys.argv[1])
if not target.exists():
    sys.exit(f'no such path: {target}')
files = [target] if target.is_file() else sorted(target.rglob('*.md'))

changed = 0
for p in files:
    s = p.read_text(encoding='utf-8')
    r = unwrap(s)
    if r != s:
        p.write_text(r, encoding='utf-8'); changed += 1
print(f'{changed} file(s) rewrapped')
