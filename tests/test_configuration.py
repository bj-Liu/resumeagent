"""Configuration precedence and shared file I/O regressions, using fixture values only."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from resumeagent.config import config, default_model
from resumeagent.tools.filesystem_helpers import atomic_write, read_json, write_json


class ConfigurationTests(unittest.TestCase):
    def test_missing_private_yaml_allows_clean_checkout_import(self):
        with tempfile.TemporaryDirectory() as directory:
            missing=Path(directory)/'not-created.yaml'
            environment=dict(os.environ,RESUMEAGENT_CONFIG=str(missing))
            code='from resumeagent.config import config; assert config == {}; from resumeagent.main import HomepageDesignAgent; print("CLEAN_IMPORT_OK")'
            output=subprocess.check_output([sys.executable,'-c',code],env=environment,
                                           cwd=Path(__file__).resolve().parents[1],text=True)
            self.assertIn('CLEAN_IMPORT_OK',output)
    def test_config_consumers_share_one_loaded_mapping(self):
        from resumeagent.llm.client import config as llm_config
        from resumeagent.tools.browser import cfg as browser_config
        self.assertTrue(config is llm_config)
        self.assertTrue(config is browser_config)

    def test_explicit_file_and_environment_precedence(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'fixture config.yaml'
            path.write_text(
                'CONFIG_FIXTURE: file-value\nCONFIG_EMPTY: file-value\n'
                'CONFIG_NULL: null\nCONFIG_BOOL: false\nmodel: fixture-model\n',
                encoding='utf-8',
            )
            environment = dict(os.environ, RESUMEAGENT_CONFIG=str(path),
                               CONFIG_FIXTURE='environment-value', CONFIG_EMPTY='')
            for key in ('CONFIG_NULL', 'CONFIG_BOOL'):
                environment.pop(key, None)
            code = (
                'import json, os; from resumeagent.config import CONFIG_PATH, default_model; '
                'print(json.dumps({"path":str(CONFIG_PATH),"model":default_model(),'
                '"values":[os.environ.get(k) for k in '
                '["CONFIG_FIXTURE","CONFIG_EMPTY","CONFIG_NULL","CONFIG_BOOL"]]}))'
            )
            output = subprocess.check_output([sys.executable, '-c', code], env=environment,
                                             cwd=Path(__file__).resolve().parents[1], text=True)
            result = json.loads(output)
            self.assertEqual(result['path'], str(path))
            self.assertEqual(result['model'], 'fixture-model')
            # Preserve setdefault behavior, including an existing empty environment value.
            self.assertEqual(result['values'], ['environment-value', '', None, 'False'])

    def test_default_model_selection_is_unchanged(self):
        for values, expected in (({'LLM_TYPE':'qwen'}, 'qwen3.8-max'),
                                 ({'LLM_TYPE':'openai'}, 'gpt-4o'),
                                 ({'model':'custom-deployment'}, 'custom-deployment')):
            with patch.dict(config, values, clear=True):
                self.assertEqual(default_model(), expected)


class FilePersistenceTests(unittest.TestCase):
    def test_failed_atomic_write_preserves_the_previous_file(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'page.html'
            path.write_text('previous', encoding='utf-8')
            with patch('tempfile.NamedTemporaryFile', side_effect=OSError('fixture failure')):
                with self.assertRaises(OSError):
                    atomic_write(path, 'new')
            self.assertEqual(path.read_text(encoding='utf-8'), 'previous')
            self.assertEqual(list(Path(directory).iterdir()), [path])

    def test_json_roundtrip_keeps_unicode_and_data_types(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'nested' / 'pages.json'
            pages = [{'title':'中文页面', 'is_main_page':True, 'relationship':{'links':[]}}]
            write_json(path, pages, ensure_ascii=False)
            self.assertEqual(read_json(path), pages)
            self.assertIn('中文页面', path.read_text(encoding='utf-8'))


if __name__ == '__main__':
    unittest.main()
