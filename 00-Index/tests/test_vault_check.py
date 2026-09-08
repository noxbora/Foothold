"""Regression checks for link and metadata validation; no third-party packages."""
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest


CHECKER = Path(__file__).resolve().parents[1] / 'vault-check.py'
NOTE = '''---
type: index
platform: any
status: working
fluency: guided
source: reading
updated: 2026-09-08
---

# Start Here

## Conventions

A small test note. ^example

[[#Conventions]] and [[#^example]]
'''


class VaultCheckTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / '00-Index').mkdir()
        shutil.copy2(CHECKER, self.root / '00-Index/vault-check.py')
        self.note = self.root / '00-Index/Start-Here.md'
        self.note.write_text(NOTE)
        (self.root / '.github').mkdir()
        self.readme = self.root / '.github/README.md'
        self.readme.write_text('[Start](../00-Index/Start-Here.md#conventions)\n')

    def run_check(self):
        return subprocess.run([sys.executable, str(self.root / '00-Index/vault-check.py')],
                              capture_output=True, text=True, timeout=30)

    def assert_failure(self, detail):
        result = self.run_check()
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn(detail, result.stdout)

    def test_valid_links_and_metadata(self):
        result = self.run_check()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn('CLEAN', result.stdout)

    def test_missing_block_anchor(self):
        self.note.write_text(NOTE.replace('[[#^example]]', '[[#^missing]]'))
        self.assert_failure('[[Start-Here#^missing]]')

    def test_anchor_inside_code_does_not_count(self):
        self.note.write_text(NOTE.replace('A small test note. ^example',
                                         '```text\nA small test note. ^example\n```'))
        self.assert_failure('[[Start-Here#^example]]')

    def test_duplicate_basename(self):
        (self.root / 'copy').mkdir()
        (self.root / 'copy/Start-Here.md').write_text(NOTE)
        self.assert_failure('Start-Here.md and ')

    def test_impossible_calendar_date(self):
        self.note.write_text(NOTE.replace('2026-09-08', '2026-02-30'))
        self.assert_failure('not a valid calendar date')

    def test_missing_readme_target(self):
        self.readme.write_text('[Start](../00-Index/Missing.md)\n')
        self.assert_failure('Missing.md: missing file')

    def test_missing_readme_heading(self):
        self.readme.write_text('[Start](../00-Index/Start-Here.md#missing)\n')
        self.assert_failure('Start-Here.md#missing: missing heading')

    def test_fenced_examples_and_external_urls_are_ignored(self):
        self.readme.write_text('```markdown\n[Example](absent.md)\n```\n'
                               '[External](https://example.invalid/absent.md)\n')
        result = self.run_check()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == '__main__':
    unittest.main()
