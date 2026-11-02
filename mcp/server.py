"""Script entry point. Intentionally no local mcp/__init__.py: do not shadow the official SDK."""
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from resumeagent.mcp_server import main

if __name__ == '__main__':
    main()
