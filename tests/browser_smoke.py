"""Run manually from the repository root; requires an installed browser/driver."""
import argparse
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from PIL import Image
from resumeagent.tools.browser import Webserver
from resumeagent.llm.client import config

if __name__ == '__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--browser',choices=['chrome','firefox','edge'],default='edge')
    args=parser.parse_args()
    config['render_wait']=1
    browser=Webserver(web_type=args.browser)
    try:
        output=browser.get_screenshot('demo/index.html','test-artifacts/selenium-index.png')
        with Image.open(output) as image:
            print('SELENIUM_OK',output,image.size)
    finally:
        browser.stop()
