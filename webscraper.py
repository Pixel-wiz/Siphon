#!/usr/bin/env python3
import os
import sys
if sys.platform.startswith('win'):
    os.environ['PYTHONIOENCODING'] = 'utf-8'

import requests
from bs4 import BeautifulSoup
import re
import argparse
import urllib.parse
import time
import random
import json
import csv
import logging
import os
from collections import deque
from datetime import datetime
import hashlib
from concurrent.futures import ThreadPoolExecutor, as_completed
import warnings
import threading
import signal
import mimetypes

def print_logo():
    logo = """
     ╔═╗╦╔═╗╦ ╦╔═╗╔╗╔
     ╚═╗║╠═╝╠═╣║ ║║║║  Web Data Extraction Tool
     ╚═╝╩╩  ╩ ╩╚═╝╝╚╝  
     
     ░░░▒▒▒▓▓▓███████████▶ DRAINING THE WEB ▶███████████▓▓▓▒▒▒░░░

     Siphon - Web Data Extraction Tool
     """
    print(logo)

warnings.filterwarnings("ignore", category=requests.packages.urllib3.exceptions.InsecureRequestWarning)

shutdown_flag = threading.Event()

def signal_handler(sig, frame):
    
    print("\n\n⚠️  Shutdown signal received! Stopping threads...")
    shutdown_flag.set()
    
signal.signal(signal.SIGINT, signal_handler)

USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.1 Safari/605.1.15',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Edge/91.0.864.59',
    'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:89.0) Gecko/20100101 Firefox/89.0',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36 Edg/91.0.864.59'
]

API_PATTERNS = [
    r'/api/v\d+',
    r'/api/[\w-]+',
    r'/v\d+/[\w-]+',
    r'/rest/[\w-]+',
    r'/services/[\w-]+',
    r'/webapi/[\w-]+',
    r'/web-api/[\w-]+',
    r'/ajax/[\w-]+',
    r'/json/[\w-]+',
    r'/data/[\w-]+',
    r'/endpoints/[\w-]+',
    
    r'/graphql',
    r'/gql',
    r'/query',
    
    r'wss?://[\w.-]+(?:/[\w.-]+)*',
    r'/ws(?:/|$)',
    r'/websocket',
    r'/socket\.io',
    
    r'/auth(?:/|$)',
    r'/authenticate',
    r'/oauth',
    r'/token',
    r'/login',
    r'/logout',
    r'/register',
    r'/user(?:s)?(?:/|$)',
    r'/account(?:s)?(?:/|$)',
    r'/profile(?:s)?(?:/|$)',
    r'/search',
    r'/query',
    r'/get[\w-]*',
    r'/post[\w-]*',
    r'/update[\w-]*',
    r'/delete[\w-]*',
    r'/create[\w-]*',
    r'/list[\w-]*',
    r'/fetch[\w-]*',
    
    r'/swagger',
    r'/api-docs',
    r'/docs/api',
    r'/documentation/api',
    r'/openapi',
    r'/redoc',
    r'/rapidoc',
    
    r'\.json(?:\?|$)',
    r'\.xml(?:\?|$)',
    r'\.csv(?:\?|$)',
]

API_KEY_PATTERNS = [
    r'api[_-]?key["\']?\s*[:=]\s*["\']?([a-zA-Z0-9\-_]{20,})',
    r'apikey["\']?\s*[:=]\s*["\']?([a-zA-Z0-9\-_]{20,})',
    r'access[_-]?token["\']?\s*[:=]\s*["\']?([a-zA-Z0-9\-_]{20,})',
    r'auth[_-]?token["\']?\s*[:=]\s*["\']?([a-zA-Z0-9\-_]{20,})',
    r'bearer["\']?\s*[:=]\s*["\']?([a-zA-Z0-9\-_]{20,})',
    r'token["\']?\s*[:=]\s*["\']?([a-zA-Z0-9\-_]{20,})',
    r'secret[_-]?key["\']?\s*[:=]\s*["\']?([a-zA-Z0-9\-_]{20,})',
    r'client[_-]?id["\']?\s*[:=]\s*["\']?([a-zA-Z0-9\-_]{20,})',
    r'client[_-]?secret["\']?\s*[:=]\s*["\']?([a-zA-Z0-9\-_]{20,})',
    r'private[_-]?key["\']?\s*[:=]\s*["\']?([a-zA-Z0-9\-_]{20,})',
    r'["\']Authorization["\']\s*:\s*["\']Bearer\s+([a-zA-Z0-9\-_.]+)',
    r'["\']X-API-Key["\']\s*:\s*["\']([a-zA-Z0-9\-_]+)',
    r'["\']X-Auth-Token["\']\s*:\s*["\']([a-zA-Z0-9\-_]+)',
    r'openai[_-]?key["\']?\s*[:=]\s*["\']?(sk-[a-zA-Z0-9]{48,56})',
    r'google[_-]?key["\']?\s*[:=]\s*["\']?(AIza[a-zA-Z0-9\-_]{30,40})',
    r'anthropic[_-]?key["\']?\s*[:=]\s*["\']?(sk-ant-[a-zA-Z0-9\-_]{90,100})',
    r'aws[_-]?key["\']?\s*[:=]\s*["\']?(AKIA[a-zA-Z0-9]{16,20})',
    r'azure[_-]?key["\']?\s*[:=]\s*["\']?([a-zA-Z0-9\-_]{32,})',
    r'stripe[_-]?key["\']?\s*[:=]\s*["\']?([sp]k_[a-zA-Z0-9]{24,40})',
    r'twilio[_-]?key["\']?\s*[:=]\s*["\']?(SK[a-zA-Z0-9]{32})',
    r'github[_-]?token["\']?\s*[:=]\s*["\']?(gh[po]_[a-zA-Z0-9]{36,40})',
    r'slack[_-]?token["\']?\s*[:=]\s*["\']?(xox[bp]-[a-zA-Z0-9\-]{40,100})',
    r'sendgrid[_-]?key["\']?\s*[:=]\s*["\']?(SG\.[a-zA-Z0-9\-_.]{60,70})',
]

DUMP_ALL_EXTENSIONS = [
    'pdf', 'doc', 'docx', 'xls', 'xlsx', 'ppt', 'pptx', 'odt', 'ods', 'odp', 'rtf', 'txt', 'csv', 'env',
    
    'jpg', 'jpeg', 'png', 'gif', 'bmp', 'svg', 'webp', 'ico', 'tiff', 'tif',
    
    'mp4', 'avi', 'mov', 'wmv', 'flv', 'webm', 'mkv', 'mpg', 'mpeg',
    
    'mp3', 'wav', 'flac', 'aac', 'ogg', 'wma', 'm4a',
    
    'zip', 'rar', '7z', 'tar', 'gz', 'bz2', 'xz',
    
    'js', 'css', 'json', 'xml', 'yaml', 'yml', 'ini', 'conf', 'config', 'env',
    'py', 'php', 'java', 'cpp', 'c', 'h', 'cs', 'rb', 'go', 'rs', 'swift',
    
    'sql', 'db', 'sqlite', 'mdb',
    
    'log', 'bak', 'backup', 'old', 'temp', 'tmp', 'cache',
    
    'html', 'htm', 'php', 'asp', 'aspx', 'jsp', 'do', 'action'
]

class RobustResponse:

    def __init__(self, raw_content, original_response, url):
        self.raw_content = raw_content
        self.url = url
        self.status_code = original_response.status_code
        self.headers = original_response.headers
        self._encoding = None
        self._text = None
        
    def _detect_encoding(self):
        
        if self._encoding:
            return self._encoding
            
        content = self.raw_content
        content_type = self.headers.get('content-type', '').lower()
        
        if 'charset=' in content_type:
            try:
                charset = content_type.split('charset=')[1].split(';')[0].strip().strip('"\'')
                content.decode(charset)
                self._encoding = charset
                return charset
            except:
                pass
        
        if b'text/html' in content_type.encode() or not content_type:
            meta_charset = re.search(rb'<meta[^>]+charset=["\']?([^"\'>\\s]+)', content[:4096], re.IGNORECASE)
            if meta_charset:
                try:
                    charset = meta_charset.group(1).decode('ascii')
                    content.decode(charset)
                    self._encoding = charset
                    return charset
                except:
                    pass
            
            meta_http = re.search(rb'<meta[^>]+http-equiv=["\']?content-type["\']?[^>]+content=["\']?[^;"\']*charset=([^;"\'\\s]+)', content[:4096], re.IGNORECASE)
            if meta_http:
                try:
                    charset = meta_http.group(1).decode('ascii')
                    content.decode(charset)
                    self._encoding = charset
                    return charset
                except:
                    pass
        
        try:
            import chardet
            sample_size = min(len(content), 65536)
            detected = chardet.detect(content[:sample_size])
            if detected and detected.get('confidence', 0) > 0.75:
                try:
                    content.decode(detected['encoding'])
                    self._encoding = detected['encoding']
                    return detected['encoding']
                except:
                    pass
        except ImportError:
            pass
        
        encodings = [
            'utf-8', 'utf-8-sig',
            'cp1252', 'windows-1252',
            'iso-8859-1', 'latin-1',
            'cp1251', 'windows-1251',
            'cp1250', 'windows-1250',
            'iso-8859-2',
            'iso-8859-15',
            'gb2312', 'gbk', 'gb18030',
            'big5', 'cp950',
            'shift_jis', 'cp932',
            'euc-jp', 'iso-2022-jp',
            'euc-kr', 'cp949',
            'iso-8859-5',
            'iso-8859-7',
            'iso-8859-8',
            'iso-8859-9',
            'utf-16', 'utf-16le', 'utf-16be',
            'utf-32', 'utf-32le', 'utf-32be',
            'ascii',
        ]
        
        for encoding in encodings:
            try:
                content.decode(encoding)
                self._encoding = encoding
                return encoding
            except:
                continue
        
        self._encoding = 'utf-8'
        return 'utf-8'
    
    @property
    def encoding(self):
        return self._detect_encoding()
    
    @encoding.setter
    def encoding(self, value):
        self._encoding = value
        self._text = None
    
    @property
    def content(self):
        return self.raw_content
    
    @property 
    def text(self):
        
        if self._text is not None:
            return self._text
            
        encoding = self.encoding
        content = self.raw_content
        
        try:
            self._text = content.decode(encoding)
            return self._text
        except:
            pass
        
        for error_mode in ['ignore', 'replace', 'backslashreplace']:
            try:
                self._text = content.decode(encoding, errors=error_mode)
                return self._text
            except:
                continue
        
        for fallback_encoding in ['utf-8', 'latin-1', 'cp1252']:
            for error_mode in ['ignore', 'replace']:
                try:
                    self._text = content.decode(fallback_encoding, errors=error_mode)
                    return self._text
                except:
                    continue
        
        self._text = content.decode('utf-8', errors='replace')
        return self._text

class ProxyManager:
    
    def __init__(self, proxy_list, test_url='http://httpbin.org/ip'):
        self.proxies = []
        self.original_proxy_count = 0
        self.test_url = test_url
        self.proxy_counters = {}
        self.proxy_lock = threading.Lock()
        self.failed_proxies = set()
        self.use_direct = False
        self.proxy_attempts = {}
        if proxy_list:
            self.load_proxies(proxy_list)
    
    def load_proxies(self, proxy_list):
        
        if len(proxy_list) == 1:
            proxy_source = proxy_list[0]
            if proxy_source.startswith('http'):
                try:
                    response = requests.get(proxy_source, timeout=10)
                    proxy_lines = response.text.strip().split('\n')
                    self.proxies = [self._format_proxy(p.strip()) for p in proxy_lines if p.strip()]
                except Exception as e:
                    logging.error(f"Failed to download proxy list: {e}")
                    self.proxies = []
            else:
                try:
                    with open(proxy_source, 'r') as f:
                        proxy_lines = f.read().strip().split('\n')
                    self.proxies = [self._format_proxy(p.strip()) for p in proxy_lines if p.strip()]
                except Exception as e:
                    logging.error(f"Failed to read proxy file {proxy_source}: {e}")
                    self.proxies = [self._format_proxy(proxy_source)]
        else:
            self.proxies = [self._format_proxy(p) for p in proxy_list]
        
        self.original_proxy_count = len(self.proxies)
    
    def _format_proxy(self, proxy_string):
        
        if '://' not in proxy_string:
            proxy_string = f'http://{proxy_string}'
        return {
            'http': proxy_string,
            'https': proxy_string
        }
    
    def test_proxies(self, max_workers=10):
        
        logging.info(f"Testing {len(self.proxies)} proxies...")
        working_proxies = []
        
        def test_proxy(proxy):
            try:
                start_time = time.time()
                response = requests.get(self.test_url, proxies=proxy, timeout=5)
                response_time = time.time() - start_time
                if response.status_code == 200:
                    return (proxy, response_time)
            except:
                pass
            return None
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = [executor.submit(test_proxy, proxy) for proxy in self.proxies]
            for future in as_completed(futures):
                result = future.result()
                if result:
                    working_proxies.append(result)
        
        working_proxies.sort(key=lambda x: x[1])
        self.proxies = [p[0] for p in working_proxies]
        self.original_proxy_count = len(self.proxies)
        logging.info(f"Found {len(self.proxies)} working proxies")
    
    def get_proxy(self, thread_id, url=None):
        
        if self.use_direct or not self.proxies:
            return None
            
        with self.proxy_lock:
            if self.failed_proxies:
                active_proxies = [p for p in self.proxies if str(p) not in self.failed_proxies]
                if not active_proxies:
                    if len(self.failed_proxies) >= self.original_proxy_count:
                        logging.warning(f"All {self.original_proxy_count} proxies have failed, switching to direct connection")
                        self.use_direct = True
                        return None
                    else:
                        active_proxies = self.proxies
                self.proxies = active_proxies
            
            if thread_id not in self.proxy_counters:
                self.proxy_counters[thread_id] = {
                    'proxy_index': 0,
                    'request_count': 0,
                    'rotation_threshold': random.randint(1, 5)
                }
            
            counter = self.proxy_counters[thread_id]
            
            if url:
                if url not in self.proxy_attempts:
                    self.proxy_attempts[url] = set()
                
                for i in range(len(self.proxies)):
                    proxy_str = str(self.proxies[i])
                    if proxy_str not in self.proxy_attempts[url] and proxy_str not in self.failed_proxies:
                        self.proxy_attempts[url].add(proxy_str)
                        return self.proxies[i]
            
            counter['request_count'] += 1
            
            if counter['request_count'] >= counter['rotation_threshold']:
                counter['proxy_index'] = (counter['proxy_index'] + 1) % len(self.proxies)
                counter['request_count'] = 0
                counter['rotation_threshold'] = random.randint(1, 5)
            
            if counter['proxy_index'] >= len(self.proxies):
                counter['proxy_index'] = 0
            
            return self.proxies[counter['proxy_index']]
    
    def mark_proxy_failed(self, proxy):
        
        with self.proxy_lock:
            proxy_str = str(proxy)
            if proxy_str not in self.failed_proxies:
                self.failed_proxies.add(proxy_str)
                logging.info(f"Proxy marked as failed: {proxy.get('http', '').replace('http://', '').split(':')[0]} ({len(self.failed_proxies)}/{self.original_proxy_count} failed)")
    
    def all_proxies_failed(self):
        
        with self.proxy_lock:
            return len(self.failed_proxies) >= self.original_proxy_count
    
    def get_untried_proxy_for_url(self, url):
        
        with self.proxy_lock:
            if url not in self.proxy_attempts:
                self.proxy_attempts[url] = set()
            
            for proxy in self.proxies:
                proxy_str = str(proxy)
                if proxy_str not in self.proxy_attempts[url] and proxy_str not in self.failed_proxies:
                    self.proxy_attempts[url].add(proxy_str)
                    return proxy
            
            return None

class RateLimiter:
    
    def __init__(self, initial_delay=1.0):
        self.delay = initial_delay
        self.min_delay = 0.1
        self.max_delay = 10.0
        self.last_request_time = 0
        self.response_times = deque(maxlen=10)
    
    def wait(self):
        
        elapsed = time.time() - self.last_request_time
        if elapsed < self.delay:
            time.sleep(self.delay - elapsed)
        self.last_request_time = time.time()
    
    def adjust(self, response_time, status_code):
        
        self.response_times.append(response_time)
        
        if status_code == 429:
            self.delay = min(self.delay * 2, self.max_delay)
        elif status_code >= 500:
            self.delay = min(self.delay * 1.5, self.max_delay)
        elif len(self.response_times) == self.response_times.maxlen:
            avg_response_time = sum(self.response_times) / len(self.response_times)
            if avg_response_time < 0.5:
                self.delay = max(self.delay * 0.9, self.min_delay)
            elif avg_response_time > 2.0:
                self.delay = min(self.delay * 1.1, self.max_delay)

class WebScraper:
    def __init__(self, start_url, domain=None, depth=3, proxies=None, filetypes=None, 
                 keywords=None, output_dir='output', clean_data=True, use_selenium=False,
                 max_threads=3, dump_all=False, find_apis=False, crawl_only=False, test_proxies=False):
        self.start_url = start_url
        parsed_start = urllib.parse.urlparse(start_url)
        self.domain = domain or parsed_start.netloc
        self.base_path = parsed_start.path.rstrip('/')
        self.depth = depth
        self.filetypes = filetypes or []
        self.keywords = keywords or []
        self.output_dir = output_dir
        self.clean_data = clean_data
        self.use_selenium = use_selenium
        self.max_threads = max_threads
        self.dump_all = dump_all
        self.find_apis = find_apis
        self.crawl_only = crawl_only
        
        self.discovered_files = []
        self.files_lock = threading.Lock()
        
        if self.dump_all:
            self.filetypes = list(set(self.filetypes + DUMP_ALL_EXTENSIONS))
            if not self.crawl_only:
                logging.info(f"Dump all mode: Will download {len(self.filetypes)} file types")
            else:
                logging.info(f"Crawl-only dump all mode: Will list {len(self.filetypes)} file types")
        
        self.visited = set()
        self.visited_lock = threading.Lock()
        self.url_queue = deque([(self.start_url, 0)])
        self.queue_lock = threading.Lock()
        self.active_workers = 0
        self.workers_lock = threading.Lock()
        self.all_workers_started = threading.Event()
        
        self.discovered_apis = set()
        self.api_keys_found = set()
        self.api_lock = threading.Lock()
        
        self.proxy_manager = ProxyManager(proxies or [])
        self.rate_limiter = RateLimiter()
        self.cache = {}
        self.session = requests.Session()
        
        self.thread_counter = 0
        self.thread_ids = {}
        self.thread_id_lock = threading.Lock()
        
        os.makedirs(output_dir, exist_ok=True)
        
        parsed_start = urllib.parse.urlparse(self.start_url)
        safe_domain = parsed_start.netloc.replace(':', '_').replace('/', '_')
        safe_path = parsed_start.path.strip('/').replace('/', '_') if parsed_start.path.strip('/') else ''
        
        if safe_path:
            folder_name = f"{safe_domain}_{safe_path}"
        else:
            folder_name = safe_domain
            
        self.domain_dir = os.path.join(output_dir, folder_name)
        os.makedirs(self.domain_dir, exist_ok=True)
        os.makedirs(os.path.join(self.domain_dir, 'downloads'), exist_ok=True)
        
        class ThreadFormatter(logging.Formatter):
            def __init__(self, fmt, scraper_instance):
                super().__init__(fmt)
                self.scraper = scraper_instance
                
            def format(self, record):
                thread_name = threading.current_thread().name
                
                with self.scraper.thread_id_lock:
                    if thread_name not in self.scraper.thread_ids:
                        if thread_name == 'MainThread':
                            self.scraper.thread_ids[thread_name] = 0
                        else:
                            self.scraper.thread_counter += 1
                            self.scraper.thread_ids[thread_name] = self.scraper.thread_counter
                    
                    thread_id = f"[{self.scraper.thread_ids[thread_name]}]"
                
                record.thread_id = thread_id
                return super().format(record)
        
        file_formatter = ThreadFormatter('%(asctime)s %(thread_id)s - %(levelname)s - %(message)s', self)
        console_formatter = ThreadFormatter('%(thread_id)s %(levelname)s: %(message)s', self)
        
        logging.getLogger().handlers.clear()
        
        file_handler = logging.FileHandler(os.path.join(self.domain_dir, 'scraper.log'), encoding='utf-8')
        file_handler.setFormatter(file_formatter)
        
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(console_formatter)
        console_handler.stream = open(sys.stdout.fileno(), 'w', encoding='utf-8', closefd=False)
        
        logging.basicConfig(
            level=logging.INFO,
            handlers=[file_handler, console_handler]
        )
        
        if use_selenium:
            self._init_selenium()

        if self.proxy_manager.proxies and test_proxies:
            self.proxy_manager.test_proxies()
            if self.proxy_manager.proxies:
                logging.info(f"Using {len(self.proxy_manager.proxies)} working proxies out of {self.proxy_manager.original_proxy_count} total")
    
    def _init_selenium(self):
        
        try:
            from selenium import webdriver
            from selenium.webdriver.chrome.options import Options
            
            self.chrome_options = Options()
            self.chrome_options.add_argument('--headless')
            self.chrome_options.add_argument('--no-sandbox')
            self.chrome_options.add_argument('--disable-dev-shm-usage')
            self.chrome_options.add_experimental_option('excludeSwitches', ['enable-logging'])
            
            self.chrome_options.add_argument(f'user-agent={random.choice(USER_AGENTS)}')
            
            self.driver = webdriver.Chrome(options=self.chrome_options)
            logging.info("Selenium WebDriver initialized")
        except Exception as e:
            logging.warning(f"Failed to initialize Selenium: {e}")
            self.use_selenium = False

    def get_random_headers(self):
        
        return {
            'User-Agent': random.choice(USER_AGENTS),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Cache-Control': 'max-age=0',
            'DNT': '1',
            'Pragma': 'no-cache'
        }
    
    def make_request(self, url, retries=3):
        
        thread_name = threading.current_thread().name
        with self.thread_id_lock:
            thread_id = str(self.thread_ids.get(thread_name, 0))
              
        cache_key = hashlib.md5(url.encode()).hexdigest()
        
        for attempt in range(retries):
            if shutdown_flag.is_set():
                return None
                
            try:
                cache_key = hashlib.md5(url.encode()).hexdigest()
                if cache_key in self.cache:
                    logging.debug(f"Cache hit for {url}")
                    return self.cache[cache_key]
                
                self.rate_limiter.wait()
                
                if self.use_selenium and hasattr(self, 'driver'):
                    return self._selenium_request(url)
                
                proxy = self.proxy_manager.get_proxy(thread_id, url)
                proxy_info = ""
                if proxy:
                    proxy_host = proxy.get('http', 'direct').replace('http://', '').split(':')[0]
                    proxy_info = f" via {proxy_host}"
                
                headers = self.get_random_headers()
                
                start_time = time.time()
                response = self.session.get(
                    url, 
                    headers=headers, 
                    proxies=proxy,
                    timeout=(5, 15),
                    verify=False,
                    allow_redirects=True
                )
                response_time = time.time() - start_time
                
                if response.status_code == 200:
                    raw_content = b''
                    for chunk in response.iter_content(chunk_size=8192):
                        raw_content += chunk
                    
                    robust_response = RobustResponse(raw_content, response, url)
                    
                    self.rate_limiter.adjust(response_time, response.status_code)
                    
                    self.cache[cache_key] = robust_response
                    return robust_response
                else:
                    logging.warning(f"HTTP {response.status_code} for {url}{proxy_info}")
                    if proxy and attempt < retries - 1:
                        with self.proxy_manager.proxy_lock:
                            if thread_id in self.proxy_manager.proxy_counters:
                                self.proxy_manager.proxy_counters[thread_id]['request_count'] = 0
                    
            except Exception as e:
                error_msg = str(e)
                proxy_errors = ['ProxyError', 'ConnectionError', 'ConnectTimeout', 'ReadTimeout', 
                               'HTTPSConnectionPool', 'HTTPConnectionPool', 'Connection refused',
                               'timed out', 'Name or service not known', 'BadStatusLine', 'Connection aborted']
                
                is_proxy_error = any(err in error_msg for err in proxy_errors)
                
                if is_proxy_error and proxy:
                    logging.warning(f"Proxy error for {url}{proxy_info}: {error_msg}")
                    if hasattr(self.proxy_manager, 'mark_proxy_failed'):
                        self.proxy_manager.mark_proxy_failed(proxy)
                    with self.proxy_manager.proxy_lock:
                        if thread_id in self.proxy_manager.proxy_counters:
                            self.proxy_manager.proxy_counters[thread_id]['request_count'] = 0
                else:
                    logging.error(f"Request failed for {url}{proxy_info}: {e}")
                
                if attempt < retries - 1:
                    sleep_time = min(2 ** attempt, 5)
                    time.sleep(sleep_time)
        
        untried_proxy = self.proxy_manager.get_untried_proxy_for_url(url)
        if untried_proxy:
            proxy_host = untried_proxy.get('http', 'direct').replace('http://', '').split(':')[0]
            logging.info(f"Trying untried proxy {proxy_host} for {url}")
            try:
                headers = self.get_random_headers()
                start_time = time.time()
                response = self.session.get(
                    url, 
                    headers=headers, 
                    proxies=untried_proxy,
                    timeout=(5, 15),
                    verify=False,
                    allow_redirects=True
                )
                response_time = time.time() - start_time
                
                if response.status_code == 200:
                    raw_content = b''
                    for chunk in response.iter_content(chunk_size=8192):
                        raw_content += chunk
                    
                    robust_response = RobustResponse(raw_content, response, url)
                    self.rate_limiter.adjust(response_time, response.status_code)
                    self.cache[cache_key] = robust_response
                    return robust_response
                else:
                    logging.warning(f"HTTP {response.status_code} for {url} via {proxy_host}")
                    
            except Exception as e:
                logging.error(f"Untried proxy {proxy_host} failed for {url}: {e}")
                self.proxy_manager.mark_proxy_failed(untried_proxy)
        
        if self.proxy_manager.all_proxies_failed():
            logging.info(f"All {self.proxy_manager.original_proxy_count} proxies have been tried and failed for {url}, using direct connection...")
            try:
                headers = self.get_random_headers()
                start_time = time.time()
                response = self.session.get(
                    url, 
                    headers=headers, 
                    proxies=None,
                    timeout=(5, 15),
                    verify=False,
                    allow_redirects=True
                )
                response_time = time.time() - start_time
                
                if response.status_code == 200:
                    raw_content = b''
                    for chunk in response.iter_content(chunk_size=8192):
                        raw_content += chunk
                    
                    robust_response = RobustResponse(raw_content, response, url)
                    self.rate_limiter.adjust(response_time, response.status_code)
                    self.cache[cache_key] = robust_response
                    return robust_response
                else:
                    logging.warning(f"Direct connection HTTP {response.status_code} for {url}")
                    
            except Exception as e:
                logging.error(f"Direct connection failed for {url}: {e}")
        else:
            remaining = self.proxy_manager.original_proxy_count - len(self.proxy_manager.failed_proxies)
            logging.info(f"Not using direct connection yet - {remaining} proxies still available")
        
        logging.error(f"Failed to fetch {url} after {retries} attempts and direct fallback. Last error: {error_msg if 'error_msg' in locals() else 'Unknown'}")
        return None
    
    def _selenium_request(self, url):
        
        try:
            self.driver.get(url)
            time.sleep(2)
            
            class SeleniumResponse:
                def __init__(self, content, url):
                    self.content = content.encode('utf-8')
                    self.text = content
                    self.url = url
                    self.status_code = 200
            
            return SeleniumResponse(self.driver.page_source, url)
        except Exception as e:
            logging.error(f"Selenium request failed for {url}: {e}")
            return None
    
    def is_valid_url(self, url, base_url):
        
        if not url:
            return False
        
        url = urllib.parse.urljoin(base_url, url)
        parsed = urllib.parse.urlparse(url)
        
        skip_patterns = [r'javascript:', r'mailto:', r'tel:', r'#']
        
        if not self.dump_all and not any(url.lower().endswith(f'.{ft}') for ft in (self.filetypes or [])):
            skip_patterns.extend([r'\.(css|js)$', r'\.(jpg|jpeg|png|gif|bmp|svg|webp)$'])
        
        if any(re.search(pattern, url, re.I) for pattern in skip_patterns):
            return False
        
        if self.domain and parsed.netloc != self.domain:
            return False
        
        if self.base_path and not self.dump_all:
            if not parsed.path.startswith(self.base_path):
                if self.filetypes:
                    path_lower = parsed.path.lower()
                    if any(path_lower.endswith(f'.{ft}') for ft in self.filetypes):
                        return True
                return False
        
        if url in self.visited:
            return False
        
        if not self.dump_all and self.filetypes:
            path = parsed.path.lower()
            if path and '.' in path:
                ext = path.split('.')[-1]
                if ext not in self.filetypes:
                    return False
        
        return True
    
    def extract_links(self, soup, base_url):
        
        links = set()
        
        for tag in soup.find_all(['a', 'link']):
            href = tag.get('href')
            if href:
                full_url = urllib.parse.urljoin(base_url, href)
                if self.is_valid_url(full_url, base_url):
                    links.add(full_url)
        
        for tag in soup.find_all(srcset=True):
            srcset = tag.get('srcset', '')
            for src in srcset.split(','):
                src_url = src.strip().split()[0]
                full_url = urllib.parse.urljoin(base_url, src_url)
                if self.is_valid_url(full_url, base_url):
                    links.add(full_url)
        
        if self.dump_all or (self.filetypes and any(ft in ['jpg', 'jpeg', 'png', 'gif', 'bmp', 'svg', 'webp'] for ft in self.filetypes)):
            for img in soup.find_all('img'):
                src = img.get('src') or img.get('data-src') or img.get('data-lazy-src')
                if src:
                    full_url = urllib.parse.urljoin(base_url, src)
                    if self.is_valid_url(full_url, base_url):
                        links.add(full_url)
                        
            for element in soup.find_all(style=True):
                style = element.get('style', '')
                import re
                bg_urls = re.findall(r'background-image:\s*url\(["\']?([^"\')]+)["\']?\)', style)
                for bg_url in bg_urls:
                    full_url = urllib.parse.urljoin(base_url, bg_url)
                    if self.is_valid_url(full_url, base_url):
                        links.add(full_url)
        
        if self.dump_all:
            for script in soup.find_all('script', src=True):
                src = script.get('src')
                full_url = urllib.parse.urljoin(base_url, src)
                if self.is_valid_url(full_url, base_url):
                    links.add(full_url)
            
            for link in soup.find_all('link', rel='stylesheet'):
                href = link.get('href')
                if href:
                    full_url = urllib.parse.urljoin(base_url, href)
                    if self.is_valid_url(full_url, base_url):
                        links.add(full_url)
        
        for attr in ['data-href', 'data-url', 'data-link']:
            for tag in soup.find_all(attrs={attr: True}):
                url = tag.get(attr)
                if url:
                    full_url = urllib.parse.urljoin(base_url, url)
                    if self.is_valid_url(full_url, base_url):
                        links.add(full_url)
        
        return list(links)
    
    def extract_keywords(self, text):
        
        if not self.keywords:
            return []
        
        extracted = []
        for keyword in self.keywords:
            try:
                pattern = re.compile(keyword, re.IGNORECASE)
                matches = pattern.findall(text)
                extracted.extend(matches)
            except:
                if keyword.lower() in text.lower():
                    extracted.append(keyword)
        
        return list(set(extracted))
    
        
    def find_api_endpoints(self, text, url):
        
        found_apis = []
        
        for pattern in API_PATTERNS:
            try:
                matches = re.findall(pattern, text, re.IGNORECASE)
                for match in matches:
                    if match.startswith('/'):
                        api_url = urllib.parse.urljoin(url, match)
                    elif match.startswith('http'):
                        api_url = match
                    else:
                        api_url = urllib.parse.urljoin(url, '/' + match)
                    
                    with self.api_lock:
                        if api_url not in self.discovered_apis:
                            self.discovered_apis.add(api_url)
                            found_apis.append(api_url)
                            logging.info(f"[API] Found endpoint: {api_url}")
            except:
                pass
        
        for pattern in API_KEY_PATTERNS:
            try:
                matches = re.findall(pattern, text, re.IGNORECASE)
                for match in matches:
                    key_value = match if isinstance(match, str) else match[0]
                    if len(key_value) >= 20:
                        with self.api_lock:
                            if key_value not in self.api_keys_found:
                                self.api_keys_found.add(key_value)
                                logging.info(f"[KEY] Found potential API key/token: {key_value[:10]}...")
            except:
                pass
        
        return found_apis
    
    def clean_text(self, text):
        
        if not self.clean_data:
            return text
        
        text = re.sub(r'<script.*?</script>', '', text, flags=re.DOTALL)
        text = re.sub(r'<style.*?</style>', '', text, flags=re.DOTALL)
        
        text = re.sub(r'<[^>]+>', ' ', text)
        
        text = BeautifulSoup(text, 'html.parser').get_text()
        
        text = re.sub(r'\s+', ' ', text)
        
        text = re.sub(r'[^\w\s\-.,!?;:\'\"()]', '', text)
        
        text = text.strip()
        
        return text
    
    def extract_structured_data(self, soup):
        
        structured = {}
        
        json_lds = soup.find_all('script', type='application/ld+json')
        if json_lds:
            structured['json_ld'] = []
            for json_ld in json_lds:
                try:
                    data = json.loads(json_ld.string)
                    structured['json_ld'].append(data)
                except:
                    pass
        
        og_tags = {}
        for meta in soup.find_all('meta', property=re.compile(r'^og:')):
            og_tags[meta.get('property')] = meta.get('content')
        if og_tags:
            structured['open_graph'] = og_tags
        
        twitter_tags = {}
        for meta in soup.find_all('meta', attrs={'name': re.compile(r'^twitter:')}):
            twitter_tags[meta.get('name')] = meta.get('content')
        if twitter_tags:
            structured['twitter_card'] = twitter_tags
        
        return structured
    
    def scrape_page(self, url):
        
        parsed_start = urllib.parse.urlparse(self.start_url)
        base_url = f"{parsed_start.scheme}://{parsed_start.netloc}{parsed_start.path.rstrip('/')}"
        
        if url.startswith(base_url):
            display_url = url[len(base_url):] or '/'
        else:
            display_url = url.replace(f'{parsed_start.scheme}://{parsed_start.netloc}', '') or '/'
        
        response = self.make_request(url)
        if not response:
            return None
        
        content_type = response.headers.get('content-type', '').lower()
        is_binary = any(t in content_type for t in ['image/', 'application/pdf', 'application/zip', 
                                                   'video/', 'audio/', 'application/octet-stream'])
        
        should_process = False
        if self.dump_all:
            should_process = True
        elif self.filetypes:
            url_lower = url.lower()
            should_process = any(url_lower.endswith(f'.{ft}') for ft in self.filetypes)
        
        if is_binary:
            if should_process:
                if self.crawl_only:
                    file_info = {
                        'url': url,
                        'path': urllib.parse.urlparse(url).path,
                        'content_type': content_type,
                        'size': len(response.content),
                        'timestamp': datetime.now().isoformat()
                    }
                    with self.files_lock:
                        self.discovered_files.append(file_info)
                    logging.info(f"Found file: {display_url} ({content_type}, {len(response.content)} bytes)")
                else:
                    self._save_file(url, response.content)
                    logging.info(f"Downloaded: {display_url}")
            return {
                'url': url,
                'timestamp': datetime.now().isoformat(),
                'type': 'binary',
                'content_type': content_type,
                'size': len(response.content),
                'links': []
            }
        
        logging.info(f"Scraping: {display_url}")
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        raw_text = response.text if hasattr(response, 'text') else ''
        
        api_endpoints = []
        if self.find_apis:
            api_endpoints = self.find_api_endpoints(raw_text, url)
            
            for script in soup.find_all('script', src=True):
                script_url = urllib.parse.urljoin(url, script.get('src'))
                script_response = self.make_request(script_url)
                if script_response:
                    self.find_api_endpoints(script_response.text, script_url)
        
        for script in soup(["script", "style"]):
            script.decompose()
        
        data = {
            'url': url,
            'timestamp': datetime.now().isoformat(),
            'title': soup.title.string if soup.title else '',
            'text': self.clean_text(soup.get_text()),
            'keywords': [],
            'links': [],
            'metadata': {},
            'structured_data': {},
            'headers': {}
        }
        
        if api_endpoints:
            data['api_endpoints'] = api_endpoints
        
        for i in range(1, 7):
            headers = soup.find_all(f'h{i}')
            if headers:
                data['headers'][f'h{i}'] = [h.get_text().strip() for h in headers]
        
        if self.keywords:
            data['keywords'] = self.extract_keywords(data['text'])
        
        for meta in soup.find_all('meta'):
            name = meta.get('name') or meta.get('property')
            content = meta.get('content')
            if name and content:
                data['metadata'][name] = content
        
        data['structured_data'] = self.extract_structured_data(soup)
        
        data['links'] = self.extract_links(soup, url)
        
        if should_process and not self.crawl_only:
            self._save_file(url, response.content)
        elif should_process and self.crawl_only:
            file_info = {
                'url': url,
                'path': urllib.parse.urlparse(url).path,
                'content_type': content_type,
                'size': len(response.content),
                'timestamp': datetime.now().isoformat(),
                'title': data.get('title', ''),
                'type': 'html'
            }
            with self.files_lock:
                self.discovered_files.append(file_info)
        
        return data
    
    def _save_file(self, url, content):
        
        try:
            parsed_url = urllib.parse.urlparse(url)
            path_parts = parsed_url.path.strip('/').split('/')
            
            if len(path_parts) > 1:
                subdir = os.path.join(self.domain_dir, 'downloads', *path_parts[:-1])
                os.makedirs(subdir, exist_ok=True)
                filename = path_parts[-1]
            else:
                subdir = os.path.join(self.domain_dir, 'downloads')
                filename = path_parts[0] if path_parts else 'index.html'
            
            if not filename:
                filename = 'index.html'
            
            if '.' not in filename:
                content_type = mimetypes.guess_type(url)[0]
                if content_type:
                    ext = mimetypes.guess_extension(content_type)
                    if ext:
                        filename += ext
                else:
                    filename += '.html'
            
            filepath = os.path.join(subdir, filename)
            
            base, ext = os.path.splitext(filepath)
            counter = 1
            while os.path.exists(filepath):
                filepath = f"{base}_{counter}{ext}"
                counter += 1
            
            with open(filepath, 'wb') as f:
                f.write(content)
            
            logging.info(f"Saved file: {os.path.relpath(filepath, self.domain_dir)}")
        except Exception as e:
            logging.error(f"Failed to save file {url}: {e}")
    
    def save_data(self, data, format='json'):
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        if format == 'json':
            filename = os.path.join(self.domain_dir, f'scraped_data_{timestamp}.json')
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        
        elif format == 'csv':
            filename = os.path.join(self.domain_dir, f'scraped_data_{timestamp}.csv')
            with open(filename, 'w', newline='', encoding='utf-8') as f:
                if data:
                    flattened = []
                    for item in data:
                        if 'type' in item:
                            flat_item = {
                                'url': item['url'],
                                'timestamp': item['timestamp'],
                                'type': item.get('type', 'html'),
                                'size': item.get('size', 0)
                            }
                        else:
                            flat_item = {
                                'url': item['url'],
                                'timestamp': item['timestamp'],
                                'title': item.get('title', ''),
                                'text': item.get('text', '')[:1000],
                                'keywords': ', '.join(item.get('keywords', [])),
                                'num_links': len(item.get('links', [])),
                                'api_endpoints': ', '.join(item.get('api_endpoints', []))
                            }
                        flattened.append(flat_item)
                    
                    writer = csv.DictWriter(f, fieldnames=flattened[0].keys())
                    writer.writeheader()
                    writer.writerows(flattened)
        
        if self.find_apis and (self.discovered_apis or self.api_keys_found):
            api_filename = os.path.join(self.domain_dir, f'api_discoveries_{timestamp}.json')
            api_data = {
                'discovered_endpoints': list(self.discovered_apis),
                'potential_api_keys': list(self.api_keys_found),
                'total_endpoints': len(self.discovered_apis),
                'total_keys': len(self.api_keys_found)
            }
            with open(api_filename, 'w', encoding='utf-8') as f:
                json.dump(api_data, f, indent=2, ensure_ascii=False)
            logging.info(f"API discoveries saved to {os.path.basename(api_filename)}")
        
        if self.crawl_only and self.discovered_files:
            files_filename = os.path.join(self.domain_dir, f'discovered_files_{timestamp}.json')
            files_data = {
                'discovered_files': self.discovered_files,
                'total_files': len(self.discovered_files),
                'file_types': {},
                'total_size': 0
            }
            
            for file_info in self.discovered_files:
                content_type = file_info.get('content_type', 'unknown')
                if content_type not in files_data['file_types']:
                    files_data['file_types'][content_type] = 0
                files_data['file_types'][content_type] += 1
                files_data['total_size'] += file_info.get('size', 0)
            
            with open(files_filename, 'w', encoding='utf-8') as f:
                json.dump(files_data, f, indent=2, ensure_ascii=False)
            logging.info(f"Discovered files list saved to {os.path.basename(files_filename)}")
        
        logging.info(f"Data saved to {os.path.basename(filename)}")
        return filename
    
    def get_next_url(self):
        
        with self.queue_lock:
            if self.url_queue:
                return self.url_queue.popleft()
            return None
    
    def add_urls_to_queue(self, urls, current_depth):
        
        with self.queue_lock:
            for url in urls:
                with self.visited_lock:
                    if url not in self.visited and current_depth < self.depth:
                        self.url_queue.append((url, current_depth + 1))
    
    def mark_visited(self, url):
        
        with self.visited_lock:
            if url in self.visited:
                return True
            self.visited.add(url)
            return False
    
    def worker_thread(self):
        
        scraped_data = []
        thread_name = threading.current_thread().name
        
        logging.info(f"Worker thread {thread_name} started")
        
        with self.workers_lock:
            self.active_workers += 1
        
        consecutive_empty = 0
        max_empty = 20
        
        while not shutdown_flag.is_set():
            url_info = self.get_next_url()
            if url_info is None:
                with self.workers_lock:
                    with self.queue_lock:
                        if len(self.url_queue) == 0 and self.all_workers_started.is_set():
                            consecutive_empty += 1
                            if consecutive_empty >= max_empty:
                                logging.debug(f"Worker {thread_name} found no work after {max_empty} attempts, exiting")
                                break
                        else:
                            consecutive_empty = 0
                
                time.sleep(0.1)
                continue
            
            consecutive_empty = 0
            current_url, current_depth = url_info
            
            if self.mark_visited(current_url):
                logging.debug(f"Worker {thread_name}: {current_url} already visited")
                continue
            
            if current_depth > self.depth:
                logging.debug(f"Worker {thread_name}: {current_url} exceeds depth {self.depth}")
                continue
            
            data = self.scrape_page(current_url)
            if data:
                scraped_data.append(data)
                
                if current_depth < self.depth and 'links' in data:
                    self.add_urls_to_queue(data['links'], current_depth)
            else:
                logging.warning(f"Failed to scrape {current_url}")
        
        with self.workers_lock:
            self.active_workers -= 1
        
        logging.info(f"Worker thread {thread_name} finished with {len(scraped_data)} pages")
        return scraped_data
    
    def crawl(self):
        
        all_data = []
        
        logging.info(f"Starting {'crawl-only' if self.crawl_only else 'crawl'} with {self.max_threads} threads")
        if self.crawl_only:
            logging.info("[CRAWL-ONLY MODE] Listing files without downloading!")
        if self.dump_all:
            action = "Listing" if self.crawl_only else "Downloading"
            logging.info(f"[DUMP ALL MODE] {action} everything possible!")
        if self.find_apis:
            logging.info("[API DISCOVERY MODE] Searching for API endpoints and keys!")
        
        try:
            with ThreadPoolExecutor(max_workers=self.max_threads) as executor:
                futures = [executor.submit(self.worker_thread) for _ in range(self.max_threads)]
                
                time.sleep(0.5)
                self.all_workers_started.set()
                
                last_queue_size = -1
                last_visited_count = -1
                no_progress_count = 0
                
                while not shutdown_flag.is_set():
                    time.sleep(2)
                    
                    with self.workers_lock:
                        active = self.active_workers
                    with self.queue_lock:
                        queue_size = len(self.url_queue)
                    with self.visited_lock:
                        visited_count = len(self.visited)
                    
                    if visited_count != last_visited_count:
                        proxy_status = ""
                        if self.proxy_manager.original_proxy_count > 0:
                            failed_count = len(self.proxy_manager.failed_proxies)
                            working_count = self.proxy_manager.original_proxy_count - failed_count
                            proxy_status = f", Proxies: {working_count}/{self.proxy_manager.original_proxy_count} working"
                        
                        api_status = ""
                        if self.find_apis:
                            api_status = f", APIs found: {len(self.discovered_apis)}"
                        
                        files_status = ""
                        if self.crawl_only and self.discovered_files:
                            files_status = f", Files found: {len(self.discovered_files)}"
                        
                        logging.info(f"Progress: {visited_count} pages visited, {queue_size} URLs queued, {active} active workers{proxy_status}{api_status}{files_status}")
                        last_visited_count = visited_count
                        no_progress_count = 0
                    else:
                        no_progress_count += 1
                    
                    if all(future.done() for future in futures):
                        logging.info("All worker threads have completed")
                        break
                    
                    if no_progress_count > 10 and queue_size == 0 and active == 0:
                        logging.info("No progress detected, stopping crawl")
                        break
                
                if shutdown_flag.is_set():
                    logging.info("Cancelling remaining work...")
                    for future in futures:
                        future.cancel()
                
                for i, future in enumerate(futures):
                    try:
                        thread_data = future.result(timeout=5)
                        if thread_data:
                            all_data.extend(thread_data)
                            logging.info(f"Collected {len(thread_data)} pages from thread {i}")
                        else:
                            logging.debug(f"Thread {i} returned no data")
                    except Exception as e:
                        logging.error(f"Thread {i} error: {e}")
        
        except KeyboardInterrupt:
            logging.info("Crawl interrupted by user")
            shutdown_flag.set()
        
        if self.use_selenium and hasattr(self, 'driver'):
            self.driver.quit()
        
        return all_data

def main():
    parser = argparse.ArgumentParser(
        description="Professional web scraper with proxy support, multithreading, and advanced features."
    )
    
    parser.add_argument("url", help="The URL to start the crawl from")
    
    parser.add_argument("--domain", help="The domain to limit the crawl to (default: start URL domain)")
    parser.add_argument("--depth", type=int, default=3, help="The maximum depth of the crawl (default: 3)")
    
    parser.add_argument("--proxies", nargs="+", help="List of proxies or URL to proxy list")
    parser.add_argument("--test-proxies", action="store_true", help="Test and select best proxies before scraping")
        
    parser.add_argument("--threads", type=int, default=3, help="Number of threads for crawling (default: 3)")
    
    parser.add_argument("--filetype", nargs="+", help="File extensions to filter by (e.g., html pdf doc jpg png)")
    parser.add_argument("--keywords", nargs="+", help="Keywords or regex patterns to extract")
    
    parser.add_argument("--dump-all", action="store_true", help="Download EVERYTHING - all file types, scripts, styles, etc.")
    parser.add_argument("--crawl-only", action="store_true", help="Crawl and list files without downloading them (discovery mode)")
    parser.add_argument("--find-apis", action="store_true", help="Search for API endpoints, keys, and tokens")
                
    parser.add_argument("--output-dir", default="output", help="Output directory for data and logs (default: output)")
    parser.add_argument("--format", choices=['json', 'csv'], default='json', help="Output format (default: json)")
    parser.add_argument("--raw", action="store_true", help="Don't clean scraped data")
    
    parser.add_argument("--selenium", action="store_true", help="Use Selenium for JavaScript-heavy sites")
        
    args = parser.parse_args()
    
    print_logo()

    if args.crawl_only:
        print("[+] CRAWL-ONLY MODE - Will list files without downloading!")
    if args.dump_all:
        action = "list" if args.crawl_only else "download"
        print(f"[+] DUMP ALL MODE - Will {action} EVERYTHING possible!")
    if args.find_apis:
        print("[+] API DISCOVERY MODE - Will search for API endpoints!")
    
    scraper = WebScraper(
        start_url=args.url,
        domain=args.domain,
        depth=args.depth,
        proxies=args.proxies,
        filetypes=args.filetype,
        keywords=args.keywords,
        output_dir=args.output_dir,
        clean_data=not args.raw,
        use_selenium=args.selenium,
        max_threads=args.threads,
        dump_all=args.dump_all,
        find_apis=args.find_apis,
        crawl_only=args.crawl_only,
        test_proxies=args.test_proxies
    )

    start_time = time.time()
    logging.info(f"Starting crawl from {args.url}")
    print("Press Ctrl+C to stop gracefully at any time.")
    print("="*60 + "\n")
    
    try:
        data = scraper.crawl()
        
        if data:
            filename = scraper.save_data(data, format=args.format)
            elapsed = time.time() - start_time
            
            html_pages = sum(1 for item in data if item.get('type') != 'binary')
            binary_files = sum(1 for item in data if item.get('type') == 'binary')
            
            print(f"\n{'Crawl-only scan' if args.crawl_only else 'Crawl'} complete!")
            print(f"HTML pages scraped: {html_pages}")
            if binary_files > 0:
                action = "found" if args.crawl_only else "downloaded"
                print(f"Binary files {action}: {binary_files}")
            print(f"Total items processed: {len(data)}")
            
            if args.crawl_only and scraper.discovered_files:
                print(f"\n[FILES DISCOVERED]")
                print(f"Total files found: {len(scraper.discovered_files)}")
                
                file_types = {}
                total_size = 0
                for file_info in scraper.discovered_files:
                    content_type = file_info.get('content_type', 'unknown')
                    if content_type not in file_types:
                        file_types[content_type] = {'count': 0, 'size': 0}
                    file_types[content_type]['count'] += 1
                    file_size = file_info.get('size', 0)
                    file_types[content_type]['size'] += file_size
                    total_size += file_size
                
                print(f"Total size: {total_size:,} bytes ({total_size/1024/1024:.2f} MB)")
                print("\nFile types found:")
                for content_type, info in sorted(file_types.items(), key=lambda x: x[1]['count'], reverse=True):
                    size_mb = info['size'] / 1024 / 1024
                    print(f"  {content_type}: {info['count']} files ({size_mb:.2f} MB)")
                
                print("\nSample discovered files:")
                for file_info in scraper.discovered_files[:10]:
                    size_mb = file_info.get('size', 0) / 1024 / 1024
                    print(f"  {file_info['path']} ({file_info.get('content_type', 'unknown')}, {size_mb:.2f} MB)")
                if len(scraper.discovered_files) > 10:
                    print(f"  ... and {len(scraper.discovered_files) - 10} more files")
            
            print(f"\nTime elapsed: {elapsed:.2f} seconds")
            print(f"Data saved to: {os.path.basename(filename)}")
            if args.crawl_only and scraper.discovered_files:
                print(f"Files list saved to: discovered_files_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
            
            if args.find_apis:
                print(f"\n[API Discovery Results]")
                print(f"Endpoints found: {len(scraper.discovered_apis)}")
                print(f"Potential API keys/tokens: {len(scraper.api_keys_found)}")
                if scraper.discovered_apis:
                    print("\nSample endpoints found:")
                    for api in list(scraper.discovered_apis)[:5]:
                        print(f"  - {api}")
                    if len(scraper.discovered_apis) > 5:
                        print(f"  ... and {len(scraper.discovered_apis) - 5} more")
            
                        
            if args.keywords:
                keyword_counts = {}
                for page in data:
                    for keyword in page.get('keywords', []):
                        keyword_counts[keyword] = keyword_counts.get(keyword, 0) + 1
                
                if keyword_counts:
                    print("\nKeyword occurrences:")
                    for keyword, count in sorted(keyword_counts.items(), key=lambda x: x[1], reverse=True):
                        print(f"  {keyword}: {count}")
        else:
            logging.warning("No data was scraped.")
            print("\nℹ️  Note: This may happen if the site blocks requests or has no content matching your criteria.")
    
    except KeyboardInterrupt:
        logging.info("Crawl interrupted by user")
        print("\n✅ Gracefully stopped. Any scraped data has been saved.")
    except Exception as e:
        logging.error(f"Crawl failed: {e}")
        raise

if __name__ == "__main__":
    main()
