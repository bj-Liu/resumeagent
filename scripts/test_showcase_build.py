"""Fail-closed static build checks; requires requirements-showcase.txt and Node."""
import json
import os
import sys
from pathlib import Path
import tempfile
import unittest
from build_showcase import validate


class StaticChecks(unittest.TestCase):
    def setUp(self):
        directory=tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root=Path(directory.name)
        (self.root/'data').mkdir()
        (self.root/'data/evidence.json').write_text(json.dumps({'tests':{'total':1,'passed':1,'skipped':0,'failures':0}}))
        (self.root/'index.html').write_text('<!doctype html><html lang="en"><head><meta charset="utf-8"><title>Check</title></head><body><main id="main"><a href="#main">Main</a></main></body></html>')
        (self.root/'styles.css').write_text('body{color:#123}')
        (self.root/'app.js').write_text('"use strict"; const ok = true;')

    def check(self):
        return validate(self.root,os.environ.get('NODE_BINARY','node'))

    def test_valid_site_and_same_document_anchor(self):
        self.assertEqual(self.check(),4)

    def test_missing_asset_fails(self):
        path=self.root/'index.html'
        path.write_text(path.read_text().replace('</main>','<img alt="test" src="missing.png"></main>'))
        with self.assertRaisesRegex(ValueError,'missing or unconfined'):
            self.check()

    def test_path_traversal_fails(self):
        path=self.root/'index.html'
        path.write_text(path.read_text().replace('#main','../outside.html'))
        with self.assertRaisesRegex(ValueError,'missing or unconfined'):
            self.check()

    def test_bad_javascript_fails(self):
        (self.root/'app.js').write_text('const = ;')
        with self.assertRaisesRegex(ValueError,'JavaScript syntax'):
            self.check()

    def test_bad_css_fails(self):
        (self.root/'styles.css').write_text('body{this is not a declaration}')
        with self.assertRaisesRegex(ValueError,'CSS declaration'):
            self.check()

    def test_inconsistent_evidence_fails(self):
        (self.root/'data/evidence.json').write_text(json.dumps({'tests':{'total':1,'passed':10,'skipped':0,'failures':0}}))
        with self.assertRaisesRegex(ValueError,'Inconsistent test evidence'):
            self.check()


if __name__=='__main__':
    unittest.main(testRunner=unittest.TextTestRunner(stream=sys.stdout,verbosity=2))
