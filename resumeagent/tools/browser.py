"""Selenium rendering and screenshots; one lock protects a shared browser."""
import os
from pathlib import Path
from threading import RLock
import time
from PIL import Image
from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from resumeagent.config import config as cfg


class Webserver:
    def __init__(self, save_file='saves/', preview_mode=False, *, web_type=None, driver_path=None):
        self.save_file = save_file
        self.preview_mode = preview_mode
        self.web_type = web_type or cfg.get('web_type', 'chrome')
        if self.web_type not in ('chrome', 'firefox', 'edge'):
            raise ValueError(f'Unsupported web browser type: {self.web_type}')
        self.driver_path = driver_path or os.environ.get('WEBDRIVER_PATH') or cfg.get('driver_path')
        self._driver = None
        self.preview_driver = None
        self._lock = RLock()

    @property
    def save_path(self):
        return self.save_file

    @save_path.setter
    def save_path(self, value):
        self.save_file = value

    @property
    def driver(self):
        with self._lock:
            if self._driver is None:
                self._driver = self._create_driver(headless=True)
            return self._driver

    def _create_driver(self, headless):
        if self.web_type == 'firefox':
            from selenium.webdriver.firefox.options import Options
            from selenium.webdriver.firefox.service import Service
            factory = webdriver.Firefox
        elif self.web_type == 'chrome':
            from selenium.webdriver.chrome.options import Options
            from selenium.webdriver.chrome.service import Service
            factory = webdriver.Chrome
        else:
            from selenium.webdriver.edge.options import Options
            from selenium.webdriver.edge.service import Service
            factory = webdriver.Edge
        options = Options()
        if headless:
            options.add_argument('-headless' if self.web_type == 'firefox' else '--headless=new')
        if self.web_type == 'firefox':
            options.set_preference('browser.download.folderList', 2)
            options.set_preference('browser.download.dir', str(Path(self.save_file).resolve()))
        else:
            options.add_argument('--start-maximized')
            options.add_experimental_option('prefs', {'download.default_directory': str(Path(self.save_file).resolve()), 'directory_upgrade': True, 'safebrowsing.enabled': True})
        # Explicit local path supports offline use; otherwise Selenium Manager resolves the driver.
        return factory(service=Service(executable_path=self.driver_path) if self.driver_path else Service(), options=options)

    def get_screenshot(self, local_html_path, save_path=None, is_local=True):
        with self._lock:
            save_path = Path(save_path or Path(self.save_file) / 'screenshot.png')
            save_path.parent.mkdir(parents=True, exist_ok=True)
            driver = self.driver
            url = Path(local_html_path).resolve().as_uri() if is_local else local_html_path
            driver.set_window_size(1440, 900)
            driver.get(url)
            try:
                driver.switch_to.alert.accept()
            except Exception:
                pass
            WebDriverWait(driver, 30).until(lambda d: d.execute_script('return document.readyState') == 'complete')
            # Preserve settling time for external styles, fonts and JS rendering.
            settling_time = float(cfg.get('render_wait', 5 if is_local else 15))
            time.sleep(settling_time)
            height = driver.execute_script('return Math.max(document.body.scrollHeight, document.documentElement.scrollHeight)')
            chrome_height = driver.execute_script('return Math.max(0, window.outerHeight - window.innerHeight)')
            driver.set_window_size(1440, max(900, height + chrome_height))
            # Full-page resizing exposes sections and triggers their entry
            # animations. Capture after those transitions, rather than midway.
            time.sleep(settling_time)
            if not driver.save_screenshot(str(save_path)):
                raise RuntimeError(f'Failed to save screenshot: {save_path}')
            with Image.open(save_path) as screenshot:
                if screenshot.height > 4096:
                    screenshot = screenshot.resize((screenshot.width // 2, screenshot.height // 2))
                screenshot.save(save_path)
            return str(save_path)

    def open_website(self, local_html_path):
        with self._lock:
            if self.preview_driver is None:
                self.preview_driver = self._create_driver(headless=False)
            self.preview_driver.get(Path(local_html_path).resolve().as_uri())

    def stop(self):
        with self._lock:
            for name in ('_driver', 'preview_driver'):
                driver = getattr(self, name)
                if driver is not None:
                    try:
                        driver.quit()
                    finally:
                        setattr(self, name, None)
