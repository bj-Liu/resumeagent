"""Single configuration owner; preserve path selection and environment precedence."""
import os
from pathlib import Path

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG_PATH = PROJECT_ROOT / 'config.yaml'
if not DEFAULT_CONFIG_PATH.exists():
    DEFAULT_CONFIG_PATH = Path(__file__).with_name('config.yaml')
CONFIG_PATH = Path(os.environ.get('RESUMEAGENT_CONFIG', DEFAULT_CONFIG_PATH))
if CONFIG_PATH.exists():
    with CONFIG_PATH.open(encoding='utf-8') as stream:
        config = yaml.safe_load(stream) or {}
else:
    # A clean public checkout has no private YAML. Environment-only and offline
    # usage must still import; credentials are checked lazily by the provider.
    config = {}
for key, value in config.items():
    if value is not None and value != '':
        os.environ.setdefault(key, str(value))


def default_model() -> str:
    return config.get('model') or (
        'qwen3.8-max' if config.get('LLM_TYPE') == 'qwen' else 'gpt-4o'
    )
