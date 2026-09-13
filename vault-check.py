#!/usr/bin/env python3
"""PLAYBOOK vault check — the things Dataview cannot see.

Dataview queries frontmatter; it cannot inspect link topology or note structure.
This covers the rest. Run from anywhere:

    python3 vault-check.py            # from the Playbook root
    python3 /path/to/vault-check.py   # from anywhere

Exit code is 0 when clean, 1 when any check fails — so it can gate a commit hook.

Three modes do something else and exit 0 instead of checking anything:

    --gaps            every `## Gaps` line in the Playbook — the backlog of missing work
    --fluency         what the vault leans on hardest that you cannot yet do
    --unwrap <path>   REWRITE a file (or a folder, recursively) so each paragraph, list
                      item and callout line is one source line again. This is the repair
                      for the hard-wrap check: the check finds the damage, this undoes it.
"""
import os, re, sys, collections, datetime, pathlib
from urllib.parse import unquote, urlsplit

# ── --unwrap: the repair tool, kept in here so the vault carries one script ──
# Obsidian renders a single newline as a visible break, so a paragraph wrapped at 100
# columns shows ragged half-empty lines in reading view. Reflowing is the reader's job.
# Never touched: frontmatter, fenced code, tables, headings, rules, block starts.
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

if '--unwrap' in sys.argv:
    args = sys.argv[sys.argv.index('--unwrap') + 1:]
    if not args:
        sys.exit('usage: vault-check.py --unwrap <file.md | folder>\n'
                 '  a folder is walked recursively; files are REWRITTEN in place.')
    target = pathlib.Path(args[0])
    if not target.exists():
        sys.exit(f'no such path: {target}')
    targets = [target] if target.is_file() else sorted(target.rglob('*.md'))
    changed = 0
    for p in targets:
        s = p.read_text(encoding='utf-8')
        r = unwrap(s)
        if r != s:
            p.write_text(r, encoding='utf-8'); changed += 1
    print(f'{changed} file(s) rewrapped')
    sys.exit(0)


HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = HERE                                       # the Playbook root: this file sits in it
if '--stamp' in sys.argv:
    # Set `updated` to today on every STAGED note whose staged diff carries a real
    # content change. Frontmatter-only edits are filtered out, exactly as the
    # `updated` check filters them, so stamping can never restamp itself and a run
    # with nothing to do writes nothing. Called from .githooks/pre-commit, which is
    # the whole point: the date stops being something to remember.
    import subprocess
    def _g(*a):
        try:
            r = subprocess.run(('git', '-C', ROOT) + a, capture_output=True,
                               text=True, timeout=30)
            return r.stdout if r.returncode == 0 else ''
        except Exception:
            return ''
    top = _g('rev-parse', '--show-toplevel').strip() or ROOT
    today = datetime.date.today().isoformat()
    fm = re.compile(r'^[+-](---|type|platform|status|fluency|source|updated):?')
    stamped = []
    for rel in _g('diff', '--cached', '--name-only', '--diff-filter=ACM').split('\n'):
        if not rel.endswith('.md'):
            continue
        patch = _g('diff', '--cached', '-U0', '--', rel)
        body = [l for l in patch.split('\n')
                if l and l[0] in '+-' and not l.startswith(('+++', '---')) and not fm.match(l)]
        if not body:
            continue
        f = pathlib.Path(top) / rel
        if not f.exists():
            continue
        s = f.read_text(encoding='utf-8')
        if not s.startswith('---\n'):
            continue
        r = re.sub(r'(?m)^updated: \d{4}-\d{2}-\d{2}$', 'updated: ' + today, s, count=1)
        if r != s:
            f.write_text(r, encoding='utf-8')
            _g('add', '--', rel)
            stamped.append(rel)
    if stamped:
        print('stamped updated: ' + today)
        for s in stamped:
            print('   ' + s)
    sys.exit(0)


HUBS = {'START-HERE', 'Pentest-Workflow', 'Linux-Run-Sheet', 'Windows-Run-Sheet'}
SKELETON_TYPES = {'technique', 'service', 'tool'}

notes, text = {}, {}
duplicate_names = []
for r, d, fs in os.walk(ROOT):
    d[:] = [x for x in d if not x.startswith('.')]
    for f in fs:
        if f.endswith('.md'):
            p = os.path.join(r, f)
            if f[:-3] in notes:
                duplicate_names.append(f'{notes[f[:-3]]} and {os.path.relpath(p, ROOT)}')
                continue
            notes[f[:-3]] = os.path.relpath(p, ROOT)
            text[f[:-3]] = open(p, encoding='utf-8', errors='replace').read()

def field(n, k):
    m = re.match(r'---\n(.*?)\n---\n', text[n], re.S)
    if not m: return None
    m2 = re.search(rf'(?m)^{k}:\s*(.+)$', m.group(1))
    return m2.group(1).strip() if m2 else None

def prose(t):
    """Strip fenced blocks and inline code so documented link *syntax*
    is not mistaken for a real link."""
    t = re.sub(r'```.*?```', '', t, flags=re.S)
    t = re.sub(r'`[^`\n]*`', '', t)
    return t

inbound = collections.defaultdict(set)
outbound = collections.defaultdict(set)
for n in notes:
    for m in re.finditer(r'\[\[([^\]]+)\]\]', prose(text[n])):
        raw = m.group(1)
        if '<' in raw or '>' in raw:          # template placeholder
            continue
        tgt = raw.split('|')[0].split('#')[0].strip()
        if tgt and tgt != n:
            outbound[n].add(tgt)
            inbound[tgt].add(n)

fail = collections.OrderedDict()
fail['Duplicate note names (ambiguous wikilinks)'] = sorted(duplicate_names)

fail['Broken links (target note does not exist)'] = sorted(
    f'{s} -> [[{t}]]' for s in notes for t in outbound[s] if t not in notes)

fail['Orphans (nothing links here)'] = sorted(
    notes[n] for n in notes if n not in HUBS and not inbound[n])

fail['No frontmatter'] = sorted(
    notes[n] for n in notes if not field(n, 'type'))

fail['Missing ## Next (technique/service/tool)'] = sorted(
    notes[n] for n in notes
    if field(n, 'type') in SKELETON_TYPES and '## Next' not in text[n])

fail['Links only to hubs (no lateral link)'] = sorted(
    notes[n] for n in notes
    if field(n, 'type') in SKELETON_TYPES and not (outbound[n] - HUBS))

fail['H1 missing'] = sorted(
    notes[n] for n in notes if not re.search(r'(?m)^# ', prose(text[n])))

def heading_levels(n):
    return [len(m.group(1)) for m in re.finditer(r'(?m)^(#{1,6})\s+\S', prose(text[n]))]

fail['Heading structure (not exactly one H1, or a skipped level)'] = sorted(
    notes[n] for n in notes
    if (lambda lv: lv and (lv.count(1) != 1 or lv[0] != 1
                           or any(b - a > 1 for a, b in zip(lv, lv[1:]))))(heading_levels(n)))

def bad_anchors(n):
    heads = {m.group(1).strip()
             for m in re.finditer(r'(?m)^#{1,6}\s+(.+?)\s*$', prose(text[n]))}
    return heads

anchor_issues = []
for n in notes:
    for m in re.finditer(r'\[\[([^\]]+)\]\]', prose(text[n])):
        raw = m.group(1).split('|')[0]
        if '#' not in raw:
            continue
        tgt, anchor = raw.split('#', 1)
        tgt = tgt.strip() or n
        anchor = anchor.strip()
        if tgt not in notes:
            continue
        if anchor.startswith('^'):
            resolves = bool(re.search(r'(?m)(?:^|\s)' + re.escape(anchor) + r'\s*$', prose(text[tgt])))
        else:
            resolves = anchor in bad_anchors(tgt)
        if not resolves:
            anchor_issues.append(f'{notes[n]} -> [[{tgt}#{anchor.strip()}]]')
fail['Heading or block anchors that do not resolve'] = sorted(set(anchor_issues))

# Inline Markdown file links, including the repository's hidden README.
# This deliberately does not crawl external URLs or treat examples as live links.
markdown_links = []
documents = [(os.path.join(ROOT, notes[n]), text[n]) for n in notes]
readme = os.path.join(ROOT, '.github', 'README.md')
if os.path.isfile(readme):
    documents.append((readme, open(readme, encoding='utf-8').read()))
for path, body in documents:
    # Keep inline code in labels; remove fences only.
    body = re.sub(r'```.*?```', '', body, flags=re.S)
    for m in re.finditer(r'(?<!!)\[[^\]\n]+\]\((<[^>]+>|[^\s)]+)\)', body):
        raw = m.group(1).strip('<>')
        parts = urlsplit(raw)
        if parts.scheme or parts.netloc:
            continue
        target = os.path.normpath(os.path.join(os.path.dirname(path), unquote(parts.path))) if parts.path else path
        issue = None
        if not os.path.isfile(target):
            issue = 'missing file'
        elif parts.fragment and target.endswith('.md'):
            target_text = open(target, encoding='utf-8').read()
            heads = re.findall(r'(?m)^#{1,6}\s+(.+?)\s*$', re.sub(r'```.*?```', '', target_text, flags=re.S))
            slugs = {re.sub(r'[^\w\- ]', '', h.lower()).replace(' ', '-') for h in heads}
            if unquote(parts.fragment) not in slugs:
                issue = 'missing heading'
        if issue:
            markdown_links.append(f'{os.path.relpath(path, ROOT)} -> {raw}: {issue}')
fail['Relative Markdown links that do not resolve'] = sorted(markdown_links)

INVISIBLE = {'\u00a0': 'NBSP', '\u200b': 'zero-width space',
             '\u00ad': 'soft hyphen', '\ufeff': 'BOM'}
fail['Invisible characters (break search, and paste badly into a shell)'] = sorted(
    f'{notes[n]}: {name} x{text[n].count(ch)}'
    for n in notes for ch, name in INVISIBLE.items() if ch in text[n])

fail['Trailing whitespace'] = sorted(
    notes[n] for n in notes
    if any(l != l.rstrip() for l in text[n].split('\n')))

bad_callouts = []
for n in notes:
    for c in set(re.findall(r'\[!(\w+)\]', text[n])):
        if c not in {'note', 'important', 'warning'}:
            bad_callouts.append(f'{notes[n]}: [!{c}]')
fail['Callouts outside the 3-word vocabulary'] = sorted(bad_callouts)

# One home per command. A long block that appears in two notes will drift: you fix it in
# one place and the other quietly keeps the old version. Short blocks are exempt on
# purpose — `id`, `sudo -l`, `getcap -r / 2>/dev/null` are idioms a sweep note is entitled
# to restate. Deliberate repetition opts out with `<!-- dup-ok -->` on the line above the
# fence.
DUP_MIN = 40

code_owner = collections.defaultdict(set)
for n in notes:
    if n == 'START-HERE':                         # its skeleton block *is* the template
        continue
    for m in re.finditer(r'(?m)^(<!-- dup-ok -->\n)?```[^\n]*\n(.*?)^```', text[n], re.S):
        if m.group(1):                            # explicitly allowed
            continue
        body = '\n'.join(l.rstrip() for l in m.group(2).strip().split('\n') if l.strip())
        if len(body) >= DUP_MIN:
            code_owner[body].add(n)

fail[f'Same code block in two notes (>{DUP_MIN} chars)'] = sorted(
    '{}: {}'.format(' + '.join(sorted(v)), b.splitlines()[0][:64])
    for b, v in code_owner.items() if len(v) > 1)

# Demand vs depth. `status` says what you think of a note; inbound links say how much the
# vault leans on it. A note eight others point at, holding 130 words, is the one that fails
# you mid-engagement — and no status field surfaces it.
DEMAND_MIN, DEPTH_MIN = 5, 175

def depth(n):
    """Prose words, code blocks and frontmatter excluded."""
    t = re.sub(r'^---\n.*?\n---\n', '', text[n], flags=re.S)
    return len(re.sub(r'```.*?```', '', t, flags=re.S).split())

fail[f'Load-bearing but thin (>={DEMAND_MIN} inbound, <{DEPTH_MIN} words)'] = sorted(
    f'{notes[n]}  ({len(inbound[n])} inbound, {depth(n)} words)'
    for n in notes
    if field(n, 'type') in SKELETON_TYPES
    and len(inbound[n]) >= DEMAND_MIN and depth(n) < DEPTH_MIN)

# Frontmatter is the vault's only machine-readable surface. Dataview selects on it, and a
# value outside its vocabulary does not raise an error — it silently drops the note out of
# every query that filters on that field. The `No frontmatter` check above only asks whether
# `type` exists; this asks whether the whole block means anything.
FIELDS = ['type', 'platform', 'status', 'fluency', 'source', 'updated']
VOCAB = {'type':     {'workflow', 'technique', 'service', 'tool', 'reference', 'index'},
         'platform': {'linux', 'windows', 'web', 'cloud', 'any'},
         'status':   {'seed', 'working', 'solid'},
         'fluency':  {'unseen', 'guided', 'cold', 'teach'},
         'source':   {'thm', 'htb', 'lab', 'field', 'reading'}}
TODAY = datetime.date.today().isoformat()

def frontmatter(n):
    m = re.match(r'---\n(.*?)\n---\n', text[n], re.S)
    return dict(re.findall(r'(?m)^(\w+):[ \t]*(.*?)[ \t]*$', m.group(1))) if m else None

schema = []
for n in notes:
    f = frontmatter(n)
    if f is None:
        continue                                  # already reported as 'No frontmatter'
    if list(f) != FIELDS:
        schema.append(f'{notes[n]}: fields are {list(f)}, expected {FIELDS}')
        continue
    for k in VOCAB:
        if f[k] not in VOCAB[k]:
            schema.append(f'{notes[n]}: {k}: {f[k]!r} is not one of {sorted(VOCAB[k])}')
    if not re.fullmatch(r'\d{4}-\d{2}-\d{2}', f['updated']):
        schema.append(f'{notes[n]}: updated: {f["updated"]!r} is not YYYY-MM-DD')
    elif f['updated'] > TODAY:
        schema.append(f'{notes[n]}: updated: {f["updated"]} is in the future')
    else:
        try:
            datetime.date.fromisoformat(f['updated'])
        except ValueError:
            schema.append(f'{notes[n]}: updated: {f["updated"]!r} is not a valid calendar date')

fail['Frontmatter outside the six-field schema'] = sorted(schema)

# A folder is this vault's second index, and an index only works if it means exactly one
# thing. `Techniques/` is grouped by the SURFACE attacked — what is in front of you —
# because that is the question you have when you do not yet know a note's name. The other
# question, "what am I trying to do", is `Workflow/`'s job. Both axes were in use at once
# until 2026-08-28: recon notes were split across three folders, credential notes sat under
# a goal name, and two notes with no home at all lived loose at `Techniques/` root. A
# convention nothing enforces is a convention that drifts, so this map is the enforcement.
#
# A `None` platform means the folder constrains `type` only. Services are cross-platform by
# nature (SMB is both), and a tool note's `platform` describes what the tool targets, not
# where the note belongs.
PLACEMENT = {
    # Start-Here sits loose at the Playbook root, on its own. It is the entrance and the
    # only meta note left in the vault, so the root claims `index` and nothing else.
    '':                               ({'index'},     {'any'}),
    'Workflow':                    ({'workflow'},  {'any'}),
    'Techniques/Web':              ({'technique'}, {'web'}),
    # `service` = a note about ONE port. A technique that works against services in
    # general attacks the same surface but is not a port, so it keeps `type: technique` —
    # the folder is the surface, the type says which of the two it is. None is filed that
    # way today; the allowance stays because the distinction is the rule, not the example.
    'Techniques/Services':         ({'service', 'technique'}, None),
    'Techniques/Linux':            ({'technique'}, {'linux'}),
    'Techniques/Windows':          ({'technique'}, {'windows'}),
    'Techniques/Active-Directory': ({'technique'}, {'windows'}),
    'Techniques/Cloud':            ({'technique'}, {'cloud'}),
    # The tie-breaker that keeps the surface axis honest: a technique that belongs to no
    # single surface and is used in more than one phase is an operation, not a technique of
    # somewhere. `platform: any` is exactly that test, so it is the folder's entry condition.
    'Operations':                  ({'technique'}, {'any'}),
    'Operations/Tools':            ({'tool'},      None),
    'Reference':                   ({'reference'}, {'any'}),
}

place = []
for n in notes:
    d = os.path.dirname(notes[n]).replace(os.sep, '/')
    rule = PLACEMENT.get(d)
    if rule is None:
        place.append(f'{notes[n]}: nothing claims {d or "the vault root"}/ — '
                     f'every note belongs to one of the {len(PLACEMENT)} folders')
        continue
    types, plats = rule
    t, p = field(n, 'type'), field(n, 'platform')
    if t not in types:
        place.append(f'{notes[n]}: type: {t!r} does not belong in {d}/ '
                     f'(expected {" or ".join(sorted(types))})')
    if plats and p not in plats:
        place.append(f'{notes[n]}: platform: {p!r} does not belong in {d}/ '
                     f'(expected {" or ".join(sorted(plats))})')

fail['Folder placement (folder must match type and platform)'] = sorted(place)

# Start-Here promises everything is reachable in at most two hops. `Orphans` above only
# catches notes with zero inbound links — a note can be well linked and still sit four hops
# from the entrance, which makes it invisible to anyone who does not already know it exists.
HOPS = 2
reach = {'START-HERE'}
frontier = {'START-HERE'}
for _ in range(HOPS):
    frontier = {t for n in frontier for t in outbound[n] if t in notes} - reach
    reach |= frontier

fail[f'More than {HOPS} hops from START-HERE (unreachable from the entrance)'] = sorted(
    notes[n] for n in notes if n not in reach)

# The one rule that cannot be repaired later: room-specific material must never enter the
# Playbook. It is easy to miss by eye because it hides inside code spans and command
# examples rather than prose — both violations found on 2026-08-27 did exactly that.
# Deliberately NOT matched: `.thm` / `.htb` placeholder domains, the `thm` / `htb` values of
# `source:`, and the platform names used to talk about the platforms themselves. Opt a line
# out with `<!-- room-ok -->` on it, the same escape hatch as `<!-- dup-ok -->`.
ROOM = re.compile(r'(?i)\b(attackbox|tryhackme|this room|we have provided'
                  r'|for your convenience|deploy the machine|answer the question)\b')

residue = []
for n in notes:
    for i, line in enumerate(text[n].split('\n'), 1):
        m = ROOM.search(line)
        if m and '<!-- room-ok -->' not in line:
            residue.append(f'{notes[n]}:{i}: "{m.group(0)}" in: {line.strip()[:60]}')

fail['Room-specific residue (the doctrine in START-HERE)'] = sorted(residue)

# A-Z reference files are append-heavy, so they drift silently: an entry lands at the end of
# its letter instead of in order, a blank line goes missing, a colon slips inside the bold.
# None of it breaks rendering, which is exactly why nobody ever notices.
ENTRY = re.compile(r'^_\*\*(.+?)\*\*_: \S')
sortkey = lambda t: t.lstrip('\\').lower()

lex = []
for n in notes:
    if len(re.findall(r'(?m)^## [A-Z]$', text[n])) < 5:      # not a lexicon
        continue
    lines = text[n].split('\n')
    groups = []
    for i, line in enumerate(lines, 1):
        h = re.match(r'^## ([A-Z])$', line)
        if h:
            groups.append((h.group(1), []))
            continue
        if not line.startswith('_**'):
            continue
        m = ENTRY.match(line)
        if not m:
            lex.append(f'{notes[n]}:{i}: not in `_**Term**_: text` form')
            continue
        if groups:
            groups[-1][1].append((m.group(1), i))
        if i < len(lines) and lines[i].startswith('_**'):
            lex.append(f'{notes[n]}:{i}: no blank line before the next entry')

    counts = collections.Counter(sortkey(t) for _, g in groups for t, _ in g)
    lex += [f'{notes[n]}: "{t}" is defined {c} times' for t, c in counts.items() if c > 1]

    for letter, g in groups:
        for (a, _), (b, ln) in zip(g, g[1:]):
            if sortkey(a) > sortkey(b):
                lex.append(f'{notes[n]}:{ln}: "{b}" should sort before "{a}" under ## {letter}')
        for t, ln in g:
            if not t.startswith('\\') and sortkey(t)[0].upper() != letter:
                lex.append(f'{notes[n]}:{ln}: "{t}" is filed under ## {letter}')

fail['Lexicon drift (order, duplicates, entry format)'] = sorted(lex)

# `updated` is the one frontmatter field that can go quietly false. The others are checked
# against a vocabulary; a date is just a date, and Start-Here's stale panel runs entirely
# on it. Git knows when a note really changed, so ask git — but only when git is there, so
# the linter still works on a copy of the vault that was never a repository. Commits that
# touch nothing but the frontmatter block do not count as the note changing: bumping the
# date must not itself make the date wrong.
def git(*a):
    import subprocess
    try:
        r = subprocess.run(('git', '-C', ROOT) + a, capture_output=True, text=True, timeout=30)
        return r.stdout if r.returncode == 0 else None
    except Exception:
        return None

FM_LINE = re.compile(r'^[+-](---|type|platform|status|fluency|source|updated):?')

WORKDAY_START = 6          # a commit before this hour belongs to the previous day
stale, checked = [], git('rev-parse', '--is-inside-work-tree')
if checked:
    first = (git('rev-list', '--max-parents=0', 'HEAD') or '').split()
    # A NUL separator cannot be passed through argv — it raises inside subprocess, the
    # exception is swallowed, and the check then reports 'ok' having examined nothing.
    # Both fields are space-free, so a plain space works and the header is unambiguous.
    # `--name-status -M` rather than `--name-only`, because a note that MOVED has not
    # changed. Restricting `git show` to the new path alone hides the rename from git: it
    # cannot match the old blob, renders the file as freshly added, and every note in a
    # reorganised folder reports itself stale. The 2026-08-28 folder restructure flagged 23
    # notes that way — all false, none fixable by editing a date.
    # `--date=format:%Y-%m-%d %H` rather than `--date=short`, because a working session that
    # runs past midnight is still the same session. Obsidian Git commits on a timer, so an
    # evening's work lands at 00:42 and every note it touched reports itself a day stale.
    # A commit before WORKDAY_START is therefore credited to the previous calendar day —
    # the day the person was actually working, which is what `updated` claims to record.
    log = git('log', '--format=%H %ad', '--date=format:%Y-%m-%d %H', '--name-status',
              '-M', '--') or ''
    HEADER = re.compile(r'^([0-9a-f]{40}) (\d{4}-\d{2}-\d{2}) (\d{2})$')
    last = {}                        # new path -> [(sha, date, old path or None), ...] newest first
    sha = date = None
    for line in log.split('\n'):
        h = HEADER.match(line)
        if h:
            sha, date, hour = h.groups()
            if int(hour) < WORKDAY_START:
                date = (datetime.date.fromisoformat(date)
                        - datetime.timedelta(days=1)).isoformat()
            continue
        cols = line.rstrip().split('\t')          # 'R099\told\tnew', or 'M\tpath'
        if len(cols) < 2 or not sha:
            continue
        was = cols[1] if cols[0].startswith('R') and len(cols) > 2 else None
        last.setdefault(cols[-1], []).append((sha, date, was))

    # A check that cannot see anything must say so, not pass quietly.
    if not last:
        stale.append('git is present but returned no file history — this check did not run')

    for n in notes:
        f = frontmatter(n)
        if not f or 'updated' not in f:
            continue
        pre = os.path.basename(ROOT) + '/'
        history = last.get(pre + notes[n])
        prefixed = history is not None
        history = history if prefixed else last.get(notes[n], [])
        for sha, date, was in history:
            if sha in first or date <= f['updated']:
                break                             # the import commit, or already honest
            # A rename needs BOTH paths in the pathspec. Given only the new one, git has
            # nothing to match the old blob against; with both plus `-M` a pure move comes
            # back as a rename header carrying no body lines at all, which is the truth.
            if was is None:
                paths = [notes[n]]
            else:
                paths = [was[len(pre):] if prefixed and was.startswith(pre) else was,
                         notes[n]]
            patch = git('show', '--format=', '-U0', '-M', sha, '--', *paths) or ''
            # `l[:1] in '+-'` is a trap: an empty string is a substring of everything,
            # so blank lines — and `git show --format=` starts with one — would count as
            # changed content and every date bump would report itself.
            body = [l for l in patch.split('\n')
                    if l and l[0] in '+-' and not l.startswith(('+++', '---'))
                    and not FM_LINE.match(l)]
            if body:                              # a real content change, later than the field
                stale.append(f'{notes[n]}: updated {f["updated"]}, but changed on {date}')
                break

fail['`updated` older than the last real change (git)'] = sorted(stale)

# `--gaps` prints every open hole the vault admits to, so the backlog in Start-Here can be
# regenerated from the notes instead of hand-maintained (and drifting).
if '--gaps' in sys.argv:
    total = 0
    for n in sorted(notes):
        found = []
        for m in re.finditer(r'(?m)^#{2,3} Gaps\s*$', text[n]):
            body = text[n][m.end():]
            body = re.split(r'(?m)^#{1,3} ', body)[0]
            found += [l.strip() for l in body.split('\n') if l.strip().startswith('- ')]
        if found:
            total += len(found)
            print(f'\n{notes[n]}')
            for l in found:
                print(f'  {l}')
    print(f'\n{total} open gap(s) across the vault')
    sys.exit(0)

# `--fluency` answers the question `status` never could. `status` grades the NOTE; `fluency`
# grades the reader, and the two are independent — a `solid` note you have never opened is
# the most dangerous object in the vault, because nothing about it looks wrong. Ranking by
# inbound links picks the notes the rest of the vault already decided were load-bearing, so
# the top of this list is not a reading list, it is the list of things most likely to stop
# him on the next box. It is where next week's DOJO mats come from.
FLUENCY_ORDER = {'unseen': 0, 'guided': 1, 'cold': 2, 'teach': 3}

if '--fluency' in sys.argv:
    # `index` and `reference` are excluded, and the exclusion is the point. Security-Terms
    # tops any inbound ranking at 59 because every note links its jargon there — but a
    # dictionary is looked up, never learned, and a lookup note at the head of this list
    # would push the real answer off the top of the screen every single week.
    SKIP = {'index', 'reference'}
    rows = [(len(inbound[n]), FLUENCY_ORDER.get(field(n, 'fluency'), 0), n)
            for n in notes
            if field(n, 'type') not in SKIP
            and field(n, 'fluency') in ('unseen', 'guided')]
    rows.sort(key=lambda r: (-r[0], r[1], r[2]))
    print('What the vault leans on that you do not own yet\n' + '=' * 48)
    print('Most-depended-on first. Anything with 5+ inbound is a note other notes')
    print('send you to mid-box, so meeting it for the first time there is too late.\n')
    for ib, _, n in rows:
        print(f'  {ib:>3} in   {field(n, "fluency"):<7} {field(n, "status"):<8} {notes[n]}')
    have = [n for n in notes if field(n, 'type') not in SKIP
            and field(n, 'fluency') in ('cold', 'teach')]
    print(f'\n{len(rows)} note(s) to go, {len(have)} owned')
    sys.exit(0)

# ---------------------------------------------------------------------------------------
# CHECK 20 — the four layers. Added 29 Aug 2026, after a page of correct commands turned out
# to be unusable on a live box. A command answers a question; without the question, the
# reader is reciting. Every section that carries an EXECUTABLE fence must therefore also
# carry `**Why now**` (what you already hold that makes this the next move), `**What you
# will see**` (Found / Empty / Error / Noise — Empty being the one that decides whether an
# absent result means "clean" or "not permitted to see it"), and `**Then**` (a destination
# for every outcome). Non-executable fences are exempt by language: ```text holds diagrams,
# chains and tables, which are illustrations rather than steps. `<!-- layers-ok -->` on the
# line above a fence exempts a section that genuinely shows anatomy rather than an action.
RUNNABLE = ('bash', 'sh', 'shell', 'console', 'zsh', 'cmd', 'bat', 'powershell', 'ps1',
            'python', 'sql', 'ruby', 'perl', 'php')
LAYERS = ('**Why now**', '**What you will see**', '**Then**')
LAYERED_TYPES = {'technique', 'service', 'tool', 'workflow'}

layers = []
for n in notes:
    if field(n, 'type') not in LAYERED_TYPES:
        continue
    lines = text[n].split('\n')
    # Walk the note section by section, tracking the current heading and whether the
    # section contains a runnable fence, an exemption comment, and each of the three layers.
    sec, start, fence, runnable, exempt, seen = None, 0, None, False, False, set()

    def close(end):
        if sec is not None and runnable and not exempt:
            missing = [l for l in LAYERS if l not in seen]
            if missing:
                layers.append(f'{notes[n]}:{start}: "{sec}" runs a command but has no '
                              f'{", ".join(missing)}')

    for i, l in enumerate(lines, 1):
        if fence is not None:
            if l.startswith(fence):
                fence = None
            continue
        m = re.match(r'^(`{3,}|~{3,})\s*([A-Za-z0-9+-]*)', l)
        if m:
            fence = m.group(1)
            if m.group(2).lower() in RUNNABLE:
                runnable = True
            continue
        if l.strip() == '<!-- layers-ok -->':
            exempt = True
            continue
        h = re.match(r'^(#{2,6})\s+(.*)', l)
        if h:
            close(i)
            sec, start, runnable, exempt, seen = h.group(2).strip(), i, False, False, set()
            continue
        for lay in LAYERS:
            if lay in l:
                seen.add(lay)
    close(len(lines))

fail['Command without its four layers (Why now / What you will see / Then)'] = sorted(layers)


# ---------------------------------------------------------------------------------------
# CHECK 21 — hard-wrapped prose. Added 29 Aug 2026 for a rendering reason, not a style one.
# Obsidian shows a single newline as a real line break unless "Strict line breaks" is on, so
# a paragraph wrapped at 100 columns renders ragged: the last word of each source line sits
# alone against the right margin, and zooming does not fix it because the breaks are in the
# file. One line per paragraph, per list item, per callout body line — the reader's window
# does the wrapping. `vault-check.py --unwrap <path>` repairs a file that drifted.
WRAP_OK = re.compile(r'^(\s*$|#{1,6}\s|\s*[-*+]\s|\s*\d+[.)]\s|\s*\||\s*>|\s*<|'
                     r'\s*(`{3,}|~{3,})|\s*(-{3,}|\*{3,}|_{3,})\s*$)')

wrapped = []
for n in notes:
    lines, fence, infm = text[n].split('\n'), None, False
    for i, l in enumerate(lines):
        if i == 0 and l.strip() == '---':
            infm = True
            continue
        if infm:
            infm = l.strip() != '---'
            continue
        m = re.match(r'^\s*(`{3,}|~{3,})', l)
        if fence is not None:
            if l.lstrip().startswith(fence):
                fence = None
            continue
        if m:
            fence = m.group(1)
            continue
        # A heading, table row, rule or HTML line legitimately precedes a paragraph — only a
        # paragraph or a list item can have a continuation line, so only those are examined.
        if (not l.strip() or i + 1 >= len(lines)
                or re.match(r'^(#{1,6}\s|\s*\||\s*<|\s*(-{3,}|\*{3,}|_{3,})\s*$)', l)):
            continue
        nxt = lines[i + 1]
        if nxt.strip() and not WRAP_OK.match(nxt):
            wrapped.append(f'{notes[n]}:{i+2}: prose continues on the next line — join it '
                           f'(Obsidian renders the break)')
            break                       # one report per note is enough to send you to it

fail['Hard-wrapped prose (renders as a ragged line break)'] = sorted(wrapped)

# ---------------------------------------------------------------------------------------
# CHECK 22 — jargon used without a definition anywhere in the vault. Added 30 Aug 2026,
# after 2.5 hours went into a box where the block was not the technique but the vocabulary:
# the notes said SID, LSASS, soft-404 and WinPEAS, and nothing in the vault said what any of
# them were or where they came from. A note may explain a term inline, but "explained
# somewhere in one note" is not a vault the reader can look things up in — so the rule is
# that every acronym and product name in prose has an entry in an A-Z reference note, and
# the first use in a note links to it.
#
# The A-Z notes are the dictionary of record; ALLOW is everything deliberately not in it —
# protocols that already have their own service note, products, file formats, CVE ids, and
# the fragments the tokeniser produces from combined forms. Anything else is a real gap:
# define it in Reference/Security-Terms.md, or add it here and say why.
LEX_NOTES = ('Security-Terms', 'English-Vocabulary')

ALLOW = set("""
ad apache2 asp attackbox aws base64 base64encoded bind bsd bsdderived busybox cn
conptyshell cpu cpubound ctf cups cve dav db docx dojo eof ftp ftps github gnu gnuonly gui h1
head html htb http https httpsonly icloud ie ipv4 itm4n javascript javascriptrendered js kb
macos mb mongodb mssql mysql net nfsv3 nfsv4 nfsv4only none null one openbsd openssl
openssllisten options os pa pdf peas php phpbb playbook pm post postbased postgresql
powershell powershellnative pp privesc ps pspy pu put putty rdp rhel rss saas
rustscan seassignprimarytoken sebackup seclist seimpersonate serestore setakeownership smb smtp
smtps ssh ssm svg trace udp union unionbased unprotected uri url urlencode urlencoded us
wordpress xlsx
""".split())

def lexkey(x):
    x = x.strip()
    if len(x) > 2 and x.endswith('s') and not x.endswith('ss'):
        x = x[:-1]
    return re.sub(r'[^a-z0-9]', '', x.lower())

defined = set()
for n in LEX_NOTES:
    if n not in text:
        continue
    for m in re.finditer(r'(?m)^_\*\*(.+?)\*\*_: ', text[n]):
        head = m.group(1)
        defined.add(lexkey(head))
        for part in re.findall(r'[A-Za-z][A-Za-z0-9./-]{1,24}', head):
            defined.add(lexkey(part))
    # an expansion in parentheses defines the acronym in front of it just as well
    for a in re.findall(r'\(([A-Za-z][A-Za-z0-9 ,.-]{1,44})\)', text[n]):
        defined.add(lexkey(a))

def known(tok):
    if lexkey(tok) in defined or lexkey(tok) in ALLOW:
        return True
    parts = tok.split('-')
    return len(parts) > 1 and any(lexkey(p) in defined or lexkey(p) in ALLOW for p in parts)

TOKEN = re.compile(r'\b[A-Za-z][A-Za-z0-9]*[A-Z0-9][A-Za-z0-9]*(?:-[A-Za-z0-9]+)*\b')

jargon = []
for n in notes:
    if n in LEX_NOTES:
        continue
    seen, fence, infm = set(), None, False
    for i, line in enumerate(text[n].split('\n'), 1):
        if i == 1 and line.strip() == '---':
            infm = True
            continue
        if infm:
            infm = line.strip() != '---'
            continue
        m = re.match(r'^\s*(`{3,}|~{3,})', line)
        if fence is not None:
            if line.lstrip().startswith(fence):
                fence = None
            continue
        if m:
            fence = m.group(1)
            continue
        clean = re.sub(r'`[^`]*`', ' ', line)
        clean = re.sub(r'\[\[[^\]]*\]\]', ' ', clean)
        clean = re.sub(r'https?://\S+', ' ', clean)
        for tok in TOKEN.findall(clean):
            if known(tok) or lexkey(tok) in seen:
                continue
            seen.add(lexkey(tok))
            jargon.append(f'{notes[n]}:{i}: "{tok}" is used but defined nowhere — '
                          f'add it to Reference/Security-Terms.md')

fail['Jargon with no entry in the A-Z reference'] = sorted(jargon)

# ---------------------------------------------------------------------------------------
# CHECK 23 — a `**What you will see**` block that does not label all four outcomes. Added
# 30 Aug 2026: check 20 proved the three layer markers were present, not that the block
# under the middle one was complete, and five blocks had quietly shipped without an
# **Error** line — including the Windows column of the run sheet, which had only **Noise**.
# Empty is the outcome the whole doctrine exists for and Error is the one that separates
# "the command failed" from "the answer is no", so a block missing either sends you back to
# guessing. A parenthesised qualifier is fine (`**Found (blind, boolean)**`); a block with
# no outcome bullets at all is prose about the doctrine, not a block, and is skipped.
OUTCOMES = ('Found', 'Empty', 'Error', 'Noise')

incomplete = []
for n in notes:
    lines = text[n].split('\n')
    for i, line in enumerate(lines):
        if not line.startswith('**What you will see**'):
            continue
        seen = set()
        for l in lines[i + 1:]:
            if l.startswith('**Then**') or re.match(r'^#{1,6}\s', l):
                break
            m = re.match(r'^\s*[-*]\s*\*\*([A-Za-z]+)\b', l)
            if m and m.group(1) in OUTCOMES:
                seen.add(m.group(1))
        if not seen:                      # prose that merely names the layer
            continue
        gone = [o for o in OUTCOMES if o not in seen]
        if gone:
            incomplete.append(f'{notes[n]}:{i+1}: block labels no {", ".join(gone)} '
                              f'outcome — say what that case looks like, or why it cannot happen')

fail['`What you will see` missing an outcome (Found/Empty/Error/Noise)'] = sorted(incomplete)

# ---------------------------------------------------------------------------------------
# CHECK 24 — one runnable command per fence. Added 31 Aug 2026. Obsidian's copy button
# copies a whole fence, so two commands in one block means neither can be taken with a
# click; the fence is also the only visual boundary saying where one command ends. A single
# command that spans lines is still one command, so continuations are joined before
# counting: a trailing backslash, an indented line, a leading pipe. A block containing a
# heredoc or any shell control keyword (for/while/if/case/function) is a script rather than
# a list of commands and is skipped — splitting one of those would break it.
# A ```text fence escapes the split above by language, which is how four stacked `sublist3r`
# invocations survived the 31 Aug pass: they were a flag reference, tagged text, and every one
# of them was still a command you would want to copy with one click. So text and untagged
# fences are judged by SHAPE instead — a line is command-shaped when it starts with a binary
# name and the next token is a flag (`tool -x`, `tool --long`). That deliberately spares the
# things a text fence is legitimately for: output samples, ASCII tables, comparison lines with
# an `->` arrow, and interactive-client verbs that take no flags (`get`, `SHOW DATABASES;`,
# `lcd /tmp`). Two command-shaped lines in one text fence is the defect; one is a reference.
SPLITTABLE = {'bash', 'sh', 'cmd', 'powershell'}
LOOSE = {'text', ''}
CMD_SHAPED = re.compile(r'^[a-z][a-z0-9._+-]{1,20}(\.(sh|py|pl|exe))?(\s+[a-z][a-z0-9-]{1,15})?\s+-{1,2}[A-Za-z][A-Za-z0-9-]*(\s|$)')
CTRL_KW = re.compile(r'^\s*(for|while|do|done|if|then|elif|else|fi|case|esac|function|\{|\}|\)|;;)\b')

def commands_in(body, lang):
    """None when the block is a script rather than a list; else its logical commands."""
    if any('<<' in l for l in body):
        return None
    out, buf = [], ''
    for l in body:
        if not l.strip():
            if buf:
                out.append(buf); buf = ''
            continue
        if CTRL_KW.match(l):
            return None
        if buf and (buf.rstrip().endswith('\\') or l[:1] in ' \t' or l.lstrip().startswith('|')):
            buf += '\n' + l
        else:
            if buf:
                out.append(buf)
            buf = l
    if buf:
        out.append(buf)
    if lang in ('cmd',):
        return [x for x in out if not x.strip().lower().startswith((':: ', '::', 'rem '))]
    return [x for x in out if not x.strip().startswith('#')]

stacked = []
for n in notes:
    lines = text[n].split('\n')
    i = 0
    while i < len(lines):
        m = re.match(r'^```(\w*)\s*$', lines[i])
        if not m:
            i += 1
            continue
        lang = m.group(1).lower()
        j = i + 1
        while j < len(lines) and not lines[j].startswith('```'):
            j += 1
        if lang in SPLITTABLE:
            cmds = commands_in(lines[i + 1:j], lang)
            if cmds is not None and len(cmds) > 1:
                stacked.append(f'{notes[n]}:{i+1}: {len(cmds)} commands in one block — '
                               f'one per fence, so each copies with a single click')
        elif lang in LOOSE:
            shaped = [l for l in lines[i + 1:j]
                      if CMD_SHAPED.match(l) and '->' not in l and '→' not in l]
            if len(shaped) > 1:
                stacked.append(f'{notes[n]}:{i+1}: {len(shaped)} command-shaped lines in a '
                               f'```{lang or "plain"} fence — a flag reference is still a list of '
                               f'commands; one per fence, tagged bash')
        i = j + 1

fail['More than one command in a code block (breaks the copy button)'] = sorted(stacked)

# ---------------------------------------------------------------------------------------
# CHECK 25 — a sweeping command must carry its own filter. Added 31 Aug 2026, after he put
# it plainly: a note that prints two hundred rows and then explains in a `**Noise**` bullet
# which hundred and ninety to ignore has handed the work back to the reader at the exact
# moment they are least able to do it. The discriminator is knowledge, and knowledge belongs
# inside the command. So: any command in DUMPERS must also contain something that narrows
# the result. `<!-- raw-ok -->` above the fence exempts a deliberate unfiltered baseline —
# used where reading the whole list once is the point, and the note says so.
DUMPERS = [
    (r'\btasklist\b',                                  'tasklist'),
    (r'\bps\s+(aux|-ef)\b',                            'ps'),
    (r'\bwmic\s+(service|product)\s+get\b',            'wmic'),
    (r'\bschtasks\s+/query\b(?![^\n]*\s/tn\b)',        'schtasks /query'),
    (r'\bnetstat\s+-\w+',                              'netstat'),
    (r'\bss\s+-\w*l\w*',                               'ss'),
    (r'\bGet-CimInstance\s+Win32_(Service|Process|Product)\b', 'Get-CimInstance'),
    (r'\bGet-ScheduledTask\b',                         'Get-ScheduledTask'),
    (r'\bsystemctl\s+list-(units|timers)\b',           'systemctl list-'),
    (r'\bfind\s+/\s[^\n]*-perm\b',                     'find / -perm'),
    (r'\bGet-ChildItem\b[^\n]*-Recurse\b',             'Get-ChildItem -Recurse'),
]
NARROWERS = ('| grep', '|grep', '| findstr', '|findstr', 'Where-Object', '-notlike',
             '| Select-String', '-Include', '-Filter', '/fi ', '/c:', '| awk', '| sort',
             '| head', '| xargs')

dumping = []
for n in notes:
    lines = text[n].split('\n')
    i = 0
    while i < len(lines):
        m = re.match(r'^```(\w*)\s*$', lines[i])
        if not m:
            i += 1
            continue
        lang = m.group(1).lower()
        j = i + 1
        while j < len(lines) and not lines[j].startswith('```'):
            j += 1
        raw_ok = i >= 1 and lines[i - 1].strip() == '<!-- raw-ok -->'
        if lang in SPLITTABLE and not raw_ok:
            body = '\n'.join(lines[i + 1:j])
            if not any(t in body for t in NARROWERS):
                for pat, name in DUMPERS:
                    if re.search(pat, body):
                        dumping.append(f'{notes[n]}:{i+1}: `{name}` with nothing to narrow it '
                                       f'— put the discriminator in the command, or mark the '
                                       f'fence <!-- raw-ok --> and say why the whole list is '
                                       f'the point')
                        break
        i = j + 1

fail['Sweeping command with no filter (hands the eliminating back to you)'] = sorted(dumping)

# ---------------------------------------------------------------------------------------
# CHECK 26 — English only. Added 1 Sep 2026, after a Turkish sentence he had said in chat
# was quoted verbatim inside a note and sat there unread. The vault is written in
# English without exception, and the cheapest way to enforce that mechanically is by
# character class: anything outside plain ASCII must be a typographic mark on the list
# below. A letter from any other alphabet fails and names itself, so a stray sentence in
# any language is caught the day it lands rather than the next time somebody reads the file.
TYPOGRAPHY = set('—–‑─…·→↓↔§¹²'
                 '“”‘’×±°≈≤≥')

nonenglish = []
for n in notes:
    for i, line in enumerate(text[n].split('\n'), 1):
        bad = sorted({c for c in line if ord(c) > 127 and c not in TYPOGRAPHY})
        if bad:
            nonenglish.append(f'{notes[n]}:{i}: non-English character(s) {" ".join(bad)} '
                              f'— the vault is English only. If the character is legitimate '
                              f'typography, add it to TYPOGRAPHY in this script and the '
                              f'exception is on the record')

fail['Non-English text (the vault is English only)'] = sorted(nonenglish)

# ---------------------------------------------------------------------------------------
# CHECK 27 — no wall of text. Added 1 Sep 2026, from a phone screenshot of a 580-word
# paragraph in this very note: one unbroken grey block with nothing findable inside it.
# Prose here is deliberately never hard-wrapped, which means one source line is exactly one
# paragraph — so paragraph length is line length in words, and the check is trivial. 120
# words is around nine lines on a phone, which is where a reader stops scanning and starts
# skipping. Fences and tables are exempt: their line shape is content, not prose. The fix is
# never to delete material, it is to break the paragraph where the thought turns.
PARA_MAX = 120

walls = []
for n in notes:
    lines = text[n].split('\n')
    infence = False
    infm = bool(lines) and lines[0].strip() == '---'
    for i, line in enumerate(lines, 1):
        if infm:
            if i > 1 and line.strip() == '---':
                infm = False
            continue
        if line.startswith('```'):
            infence = not infence
            continue
        if infence or line.startswith('|') or line.startswith('#'):
            continue
        body = re.sub(r'^\s*(>\s?)+', '', line)
        body = re.sub(r'^\s*([-*+]|\d+\.)\s+', '', body)
        w = len(body.split())
        if w > PARA_MAX:
            walls.append(f'{notes[n]}:{i}: {w}-word paragraph — anything over {PARA_MAX} is '
                         f'a wall on a phone. Break it where the thought turns; do not cut it')

fail[f'Paragraph over {PARA_MAX} words (a wall of text on a phone)'] = sorted(walls)

# ---------------------------------------------------------------------------------------
# CHECK 28 — emphasis that will not render. Added 1 Sep 2026, from the same screenshot:
# `families.**Links:**` printed its own asterisks instead of bolding, because `**` cannot
# open or close emphasis flush against a word character. Markdown wants whitespace or an
# opening bracket in front of an opening `**`, and whitespace or punctuation after a closing
# one. Glue it to a letter and the parser gives up and prints the marker as literal text —
# silently, and only visible in reading view, which is not where notes get written. Inline
# code is stripped first, so a note documenting the syntax is not accused of using it.
GLUED = re.compile(r'[A-Za-z0-9.,;:!?)]\*\*[A-Za-z0-9]')

glued = []
for n in notes:
    infence = False
    for i, line in enumerate(text[n].split('\n'), 1):
        if line.startswith('```'):
            infence = not infence
            continue
        if infence:
            continue
        if GLUED.search(re.sub(r'`[^`\n]*`', '', line)):
            glued.append(f'{notes[n]}:{i}: `**` flush against a word — Markdown will print '
                         f'the asterisks instead of bolding. An opening `**` needs a space '
                         f'before it, a closing one needs a space or punctuation after it')

fail['Emphasis markers that will not render'] = sorted(glued)

print(f'PLAYBOOK vault check — {len(notes)} notes, {len(fail)} checks\n' + '=' * 46)
bad = 0
for label, items in fail.items():
    if items:
        bad += len(items)
        print(f'\n{label}  ({len(items)})')
        for i in items:
            print(f'   {i}')
    else:
        print(f'  ok   {label}')

links = sum(len(v) for v in outbound.values())
hub = sum(len(outbound[h]) for h in HUBS if h in outbound)
print(f'\nGraph: {links} links, {hub} from hubs '
      f'({100*hub//links if links else 0}%), {links-hub} lateral')
print('CLEAN' if not bad else f'\n{bad} item(s) need attention')
sys.exit(0 if not bad else 1)
