"""Synthetic detector checks; no valid credentials or network access."""
import sys
import unittest
from security_audit import kinds


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


if __name__=='__main__':
    unittest.main(testRunner=unittest.TextTestRunner(stream=sys.stdout,verbosity=2))
