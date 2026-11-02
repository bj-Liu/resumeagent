"""Optional real Selenium QA of the built site, without model/provider calls."""
import argparse
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import sys
from threading import Thread
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from resumeagent.tools.browser import Webserver


class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass


def check(folder, output, browser='edge', driver_path=None):
    folder, output = Path(folder).resolve(), Path(output).resolve()
    if not folder.is_relative_to(ROOT / 'release-dist'):
        raise ValueError('Serve only an isolated release-dist build, never private workspace files')
    output.mkdir(parents=True, exist_ok=True)
    # A prefix exercises project Pages URLs instead of only domain-root hosting.
    server = ThreadingHTTPServer(('127.0.0.1', 0), partial(QuietHandler, directory=str(folder.parent)))
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    browser_api = Webserver(web_type=browser, driver_path=driver_path)
    checks = []
    try:
        driver = browser_api.driver
        def click(by, value):
            element = driver.find_element(by, value)
            driver.execute_script("arguments[0].scrollIntoView({block:'center',behavior:'instant'})", element)
            element.click()
        for width in (1440, 390):
            driver.set_window_size(width, 1000)
            if browser in ('edge','chrome'):
                driver.execute_cdp_cmd('Emulation.setDeviceMetricsOverride',
                    {'width':width,'height':1000,'deviceScaleFactor':1,'mobile':width==390})
            driver.get(f'http://127.0.0.1:{server.server_port}/{folder.name}/')
            driver.set_script_timeout(15)
            driver.execute_async_script('''const done=arguments[arguments.length-1];
              const images=[...document.images]; images.forEach(i=>i.loading='eager');
              Promise.all(images.map(i=>i.decode().catch(()=>null))).then(()=>done(true));''')
            time.sleep(1)
            facts = driver.execute_script('''return {
              viewport: innerWidth, document: document.documentElement.scrollWidth,
              brokenImages: [...document.images].filter(i => !i.complete || i.naturalWidth === 0).map(i=>i.getAttribute('src')),
              metrics: document.querySelectorAll('.metric').length,
              heading: document.querySelector('h1').innerText,
              columns: getComputedStyle(document.querySelector('.hero')).gridTemplateColumns
            }''')
            assert facts['document'] <= facts['viewport'], facts
            assert abs(facts['viewport'] - width) <= 20, facts
            assert not facts['brokenImages'], facts
            assert facts['metrics'] == 3, facts
            click('id', 'tab-quality')
            assert 'not a separate agent class' in driver.find_element('id', 'role-description').text
            click('id', 'tab-planner')
            driver.find_element('id', 'tab-planner').send_keys('\ue014')
            assert driver.find_element('id', 'tab-generator').get_attribute('aria-selected') == 'true'
            if width == 390:
                driver.execute_script("window.scrollTo({top:0,behavior:'instant'})")
                click('css selector', '.menu-toggle')
                assert driver.find_element('id', 'navigation').is_displayed()
                click('css selector', '#navigation a')
                assert driver.find_element('css selector', '.menu-toggle').get_attribute('aria-expanded') == 'false'
            click('id', 'copy-command')
            time.sleep(.2)
            assert driver.find_element('id', 'copy-status').text
            driver.execute_script("window.scrollTo({top:0,behavior:'instant'})")
            driver.save_screenshot(str(output / f'showcase-{width}.png'))
            checks.append({'width': width, **facts, 'tabs_keyboard_menu_copy': 'passed'})
        # Full page capture for layout review.
        driver.set_window_size(1440, 1000)
        if browser in ('edge','chrome'):
            driver.execute_cdp_cmd('Emulation.setDeviceMetricsOverride',
                {'width':1440,'height':1000,'deviceScaleFactor':1,'mobile':False})
        height = driver.execute_script('return document.documentElement.scrollHeight')
        driver.set_window_size(1440, min(height + 100, 16000))
        if browser in ('edge','chrome'):
            driver.execute_cdp_cmd('Emulation.setDeviceMetricsOverride',
                {'width':1440,'height':min(height+10,16000),'deviceScaleFactor':1,'mobile':False})
        driver.save_screenshot(str(output / 'showcase-full.png'))
    finally:
        browser_api.stop()
        server.shutdown()
        server.server_close()
    (output / 'browser-checks.json').write_text(json.dumps(checks, indent=2), encoding='utf-8')
    print(json.dumps(checks, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--folder', default='release-dist/showcase')
    parser.add_argument('--output', default='test-artifacts/release/showcase')
    parser.add_argument('--browser', default='edge', choices=['edge', 'chrome', 'firefox'])
    parser.add_argument('--driver-path')
    args = parser.parse_args()
    check(args.folder, args.output, args.browser, args.driver_path)
