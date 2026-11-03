"""Real-browser presentation QA. Uses existing media and makes no model requests."""
import argparse
import base64
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
from selenium.webdriver.support.ui import WebDriverWait

VIDEO = 'https://github.com/bj-Liu/resumeagent/releases/download/demo-20261103/resumeagent-demo-20261103-3x.mp4'


class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass


class PreviewServer(ThreadingHTTPServer):
    def handle_error(self, request, client_address):
        if isinstance(sys.exc_info()[1], (ConnectionResetError, BrokenPipeError)):
            return
        super().handle_error(request, client_address)


def check(folder, output, browser='edge', driver_path=None, url=None):
    folder, output = Path(folder).resolve(), Path(output).resolve()
    if not folder.is_relative_to(ROOT / 'release-dist'):
        raise ValueError('Serve only an isolated release-dist build')
    if url and url != 'https://bj-liu.github.io/resumeagent/':
        raise ValueError('Live checks are restricted to the project Pages URL')
    output.mkdir(parents=True, exist_ok=True)
    server = PreviewServer(('127.0.0.1', 0), partial(QuietHandler, directory=str(folder.parent)))
    Thread(target=server.serve_forever, daemon=True).start()
    api = None
    report = {'paid_model_calls': 0, 'viewports': [], 'video': [], 'javascript_disabled': {}, 'readme': {}}
    target = url or f'http://127.0.0.1:{server.server_port}/{folder.name}/'
    try:
        api = Webserver(web_type=browser, driver_path=driver_path)
        driver = api.driver
        driver.set_page_load_timeout(60)
        driver.set_script_timeout(30)

        def resize(width):
            driver.set_window_size(width, 1000)
            if browser in ('edge', 'chrome'):
                driver.execute_cdp_cmd('Emulation.setDeviceMetricsOverride',
                    {'width': width, 'height': 1000, 'deviceScaleFactor': 1, 'mobile': width == 390})

        def screenshot(name, full=False):
            if full and browser in ('edge', 'chrome'):
                height = driver.execute_script('return document.documentElement.scrollHeight')
                result = driver.execute_cdp_cmd('Page.captureScreenshot', {
                    'format': 'png', 'captureBeyondViewport': True,
                    'clip': {'x': 0, 'y': 0, 'width': driver.execute_script('return innerWidth'),
                             'height': min(height, 18000), 'scale': 1}})
                (output / name).write_bytes(base64.b64decode(result['data']))
            else:
                driver.save_screenshot(str(output / name))

        def click(identifier):
            item = driver.find_element('id', identifier)
            driver.execute_script("arguments[0].scrollIntoView({block:'center',behavior:'instant'})", item)
            item.click()

        def images_ready():
            driver.execute_async_script('''const done=arguments[arguments.length-1];
            const images=[...document.images].filter(i=>i.getAttribute('src'));
            images.forEach(i=>i.loading='eager');
            Promise.all(images.map(i=>i.decode().catch(()=>null))).then(()=>done(true));''')

        for width in (1440, 390):
            resize(width)
            driver.get(target)
            images_ready()
            facts = driver.execute_script('''const image=document.getElementById('studio-image');
              const box=image.getBoundingClientRect(); return {
              viewport:innerWidth, document:document.documentElement.scrollWidth,
              language:document.documentElement.lang, heading:document.querySelector('h1').innerText,
              sections:[...document.querySelectorAll('main>section')].map(s=>s.id||'hero'),
              brokenImages:[...document.images].filter(i=>i.getAttribute('src')&&(!i.complete||!i.naturalWidth)).map(i=>i.getAttribute('src')),
              architectureImages:document.querySelectorAll('img[src$="architecture.svg"]').length,
              gui:{natural:[image.naturalWidth,image.naturalHeight],display:[box.width,box.height],objectFit:getComputedStyle(image).objectFit},
              videoSources:[...document.querySelectorAll('video source')].map(s=>s.src)
            }''')
            assert facts['viewport'] == width and facts['document'] <= width, facts
            assert facts['language'] == 'zh-CN' and 'ResumeAgent' in facts['heading'], facts
            assert not facts['brokenImages'] and facts['architectureImages'] == 1, facts
            assert facts['sections'] == ['hero', 'demo', 'results', 'workflow', 'architecture', 'engineering', 'verification'], facts
            gui = facts['gui']
            assert gui['natural'] == [1400, 820], gui
            assert abs(gui['display'][0] / gui['display'][1] - 1400 / 820) < .01, gui
            assert facts['videoSources'] == [VIDEO], facts
            driver.find_element('id', 'studio-image').click()
            assert driver.find_element('id', 'image-viewer').get_dom_attribute('open') is not None
            click('close-image')
            if width == 390:
                driver.execute_script("window.scrollTo({top:0,behavior:'instant'})")
                driver.find_element('css selector', '.menu-toggle').click()
                assert driver.find_element('id', 'navigation').is_displayed()
                driver.find_element('css selector', '#navigation a').click()
                assert driver.find_element('css selector', '.menu-toggle').get_attribute('aria-expanded') == 'false'
            driver.execute_script("window.scrollTo({top:0,behavior:'instant'})")
            screenshot(f'showcase-{width}.png')
            screenshot(f'showcase-full-{width}.png', full=True)
            driver.execute_script("document.getElementById('results').scrollIntoView({behavior:'instant'})")
            screenshot(f'showcase-results-{width}.png')
            click('recorded-video')
            WebDriverWait(driver, 60).until(lambda d: d.execute_script('return document.getElementById("recorded-video").readyState>=2'))
            outcome = driver.execute_async_script('''const done=arguments[arguments.length-1],v=document.getElementById('recorded-video');
              v.muted=true;v.currentTime=0;v.play().then(()=>done({ok:true})).catch(e=>done({ok:false,error:e.name}));''')
            assert outcome['ok'], outcome
            time.sleep(2)
            video = driver.execute_script('''const v=document.getElementById('recorded-video');return {
              controls:v.controls, duration:v.duration,width:v.videoWidth,height:v.videoHeight,
              currentTime:v.currentTime,paused:v.paused,error:v.error?v.error.code:null,
              download:document.getElementById('video-download').href,
              release:document.getElementById('video-release').href};''')
            assert video['controls'] and 73 < video['duration'] < 74 and video['width'] == 1920 and video['height'] == 1080, video
            assert video['currentTime'] > .5 and not video['paused'] and video['error'] is None, video
            screenshot(f'video-playing-{width}.png')
            driver.execute_script('document.getElementById("recorded-video").pause()')
            assert driver.execute_script('return document.getElementById("recorded-video").paused')
            fullscreen = driver.execute_script('return document.fullscreenEnabled')
            if browser in ('edge', 'chrome'):
                assert fullscreen, 'Native video fullscreen must be available'
                driver.execute_script('''const v=document.getElementById('recorded-video');
                  v.addEventListener('click',()=>v.requestFullscreen(),{once:true});''')
                driver.find_element('id', 'recorded-video').click()
                WebDriverWait(driver, 10).until(lambda d: d.execute_script(
                    'return document.fullscreenElement===document.getElementById("recorded-video")'))
                screenshot(f'video-fullscreen-{width}.png')
                driver.execute_script('document.exitFullscreen()')
                WebDriverWait(driver, 10).until(lambda d: d.execute_script('return !document.fullscreenElement'))
                driver.execute_script('document.getElementById("recorded-video").pause()')
            report['viewports'].append({'width': width, **facts, 'zoom_and_navigation': 'passed'})
            report['video'].append({'viewport': width, **video, 'pause_verified': True,
                                    'fullscreen_verified': fullscreen, 'audio': 'Original recording has no audio track'})

        if browser in ('edge', 'chrome'):
            resize(390)
            driver.execute_cdp_cmd('Emulation.setScriptExecutionDisabled', {'value': True})
            try:
                driver.get(target)
                disabled = driver.execute_script('''const v=document.getElementById('recorded-video');return {
                  pageScriptRan:document.documentElement.classList.contains('js'),
                  controls:v.controls,source:v.querySelector('source').src,
                  download:document.getElementById('video-download').href,
                  release:document.getElementById('video-release').href,
                  videoVisible:v.getBoundingClientRect().height>100,
                  document:document.documentElement.scrollWidth,viewport:innerWidth};''')
                assert disabled['pageScriptRan'] is False and disabled['controls'], disabled
                assert disabled['source'] == disabled['download'] == VIDEO, disabled
                assert disabled['videoVisible'] and disabled['document'] <= disabled['viewport'], disabled
                assert driver.find_element('id', 'video-download').is_displayed()
                driver.execute_script("document.getElementById('recorded-video').scrollIntoView({block:'center',behavior:'instant'})")
                screenshot('showcase-no-javascript.png')
                report['javascript_disabled'] = {'status': 'passed', **disabled}
            finally:
                driver.execute_cdp_cmd('Emulation.setScriptExecutionDisabled', {'value': False})

        if not url and (folder / 'readme-preview.html').exists():
            for width in (1440, 390):
                resize(width)
                driver.get(target + 'readme-preview.html')
                images_ready()
                facts = driver.execute_script('''return {width:innerWidth,document:document.documentElement.scrollWidth,
                  heading:document.querySelector('h1').textContent,
                  brokenImages:[...document.images].filter(i=>!i.naturalWidth).map(i=>i.src)};''')
                assert facts['heading'] == 'ResumeAgent' and not facts['brokenImages'] and facts['document'] <= width, facts
                screenshot(f'readme-{width}.png')
                screenshot(f'readme-full-{width}.png', full=True)
                report['readme'][str(width)] = facts
    finally:
        if api:
            api.stop()
        server.shutdown()
        server.server_close()
        (output / 'browser-checks.json').write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding='utf-8')
    print(json.dumps(report, indent=2, ensure_ascii=False))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--folder', default='release-dist/showcase-job')
    parser.add_argument('--output', default='test-artifacts/job-showcase-v2/browser')
    parser.add_argument('--browser', default='edge', choices=['edge', 'chrome', 'firefox'])
    parser.add_argument('--driver-path')
    parser.add_argument('--url', help='Optional project Pages URL; does not publish')
    args = parser.parse_args()
    check(args.folder, args.output, args.browser, args.driver_path, args.url)
