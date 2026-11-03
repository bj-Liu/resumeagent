"""Synthetic detector checks; no valid credentials or network access."""
import sys
from pathlib import Path
import tempfile
import unittest
from security_audit import kinds
from prepare_release import candidate_files, inspect, published_path


class CredentialDetectorTests(unittest.TestCase):
    def test_provider_token_in_any_file_is_detected(self):
        synthetic=('sk-'+'A'*32).encode()
        self.assertIn('provider_token',kinds(b'example = '+synthetic,set()))

    def test_exact_credential_does_not_need_a_known_format(self):
        synthetic='not-a-real-credential'
        self.assertIn('exact_local_credential',kinds(synthetic.encode(),{synthetic}))

    def test_empty_env_lines_do_not_consume_next_variable(self):
        self.assertEqual(kinds(b'DASHSCOPE_API_KEY=\nDASHSCOPE_REGION=cn-beijing\n',set()),[])

    def test_function_name_is_not_a_literal_secret(self):
        self.assertEqual(kinds(b'secrets = known_credentials(root)\n',set()),[])

    def test_high_entropy_literal_requires_review(self):
        synthetic=b'AbcDef0123456789XYZ_AbcDef0123456789'
        self.assertIn('high_entropy_credential_assignment',kinds(b'API_KEY="'+synthetic+b'"\n',set()))


class PublicConfigurationTests(unittest.TestCase):
    def test_clean_template_takes_precedence_over_private_local_config(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            template = root / 'config.example.yaml'
            template.write_text('LLM_TYPE: qwen\nmodel: fixture-model\n')
            (root / 'config.yaml').write_text('API_KEY: synthetic-private-fixture\n')
            (root / 'config.local.yaml').write_text('API_KEY: another-private-fixture\n')
            files = candidate_files(root)
            self.assertEqual(files, [template])
            self.assertEqual(published_path(template, root), 'config.yaml')
            records, issues = inspect(files, root)
            self.assertEqual(records[0]['path'], 'config.yaml')
            self.assertEqual(issues, [])

    def test_public_checkout_can_repackage_clean_config_yaml(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            public = root / 'config.yaml'
            public.write_text('LLM_TYPE: openai\nmodel: fixture-model\n')
            self.assertEqual(candidate_files(root), [public])
            self.assertEqual(published_path(public, root), 'config.yaml')
            self.assertEqual(inspect([public], root)[1], [])

    def test_config_without_template_is_rejected_if_it_contains_credentials(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            public = root / 'config.yaml'
            public.write_text('API_KEY: synthetic-private-fixture\n')
            _, issues = inspect(candidate_files(root), root)
            self.assertTrue(any(i['kind'] == 'matches local credential value' for i in issues))


if __name__=='__main__':
    unittest.main(testRunner=unittest.TextTestRunner(stream=sys.stdout,verbosity=2))
