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
import tempfile
import pathlib
import base64
import shutil
import queue

# New imports for dynamic scraping
try:
    from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False

def print_logo():
    logo = """
     ╔═╗╦╔═╗╦ ╦╔═╗╔╗╔
     ╚═╗║╠═╝╠═╣║ ║║║║  Web Data Extraction Tool
     ╚═╝╩╩  ╩ ╩╚═╝╝╚╝  
     
     ░░░▒▒▒▓▓▓███████████▶ DRAINING THE WEB ▶███████████▓▓▓▒▒▒░░░
     """
    print(logo)

warnings.filterwarnings("ignore", category=requests.packages.urllib3.exceptions.InsecureRequestWarning)

# Global variables
shutdown_flag = threading.Event()
siphon_instance = None

def signal_handler(sig, frame):
    """Handle Ctrl+C gracefully"""
    global siphon_instance
    print("\n\nReceived interrupt signal. Shutting down gracefully...")
    shutdown_flag.set()
    if siphon_instance:
        try:
            siphon_instance.close()
        except:
            pass
    print("Shutdown complete.")
    # Force exit if hanging
    import os
    os._exit(0)

# Register the signal handler
signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

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
        self.test_url = test_url
        self.proxies = []
        self.failed_proxies = set()
        self.proxy_lock = threading.Lock()
        self.thread_assignments = {}
        self.current_proxy_index = 0
        self.all_failed_warned = False
        self.original_proxy_count = 0
        
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
        """Get a working proxy for the given thread and URL"""
        with self.proxy_lock:
            if not self.proxies:
                # Only show warning if we actually had proxies configured initially
                if not self.all_failed_warned and self.original_proxy_count > 0:
                    print(f"WARNING: All {self.original_proxy_count} proxies have failed, switching to direct connection")
                    self.all_failed_warned = True
                return None
            
            # Try to get an untried proxy for this URL first
            if url:
                untried_proxy = self.get_untried_proxy_for_url(url)
                if untried_proxy:
                    self.thread_assignments[thread_id] = untried_proxy
                    return untried_proxy
            
            # Round-robin assignment if no specific URL or no untried proxy
            if thread_id not in self.thread_assignments or self.thread_assignments[thread_id] not in self.proxies:
                if self.proxies:
                    # Assign next available proxy
                    self.current_proxy_index = (self.current_proxy_index) % len(self.proxies)
                    assigned_proxy = self.proxies[self.current_proxy_index]
                    self.thread_assignments[thread_id] = assigned_proxy
                    self.current_proxy_index += 1
                    return assigned_proxy
                else:
                    return None
            
            return self.thread_assignments[thread_id]

    def mark_proxy_failed(self, proxy):
        """Mark a proxy as failed and remove it from the active list"""
        with self.proxy_lock:
            if proxy in self.proxies:
                self.proxies.remove(proxy)
                self.failed_proxies.add(proxy)
                
                # Clean up thread assignments using this proxy
                threads_to_reassign = [tid for tid, p in self.thread_assignments.items() if p == proxy]
                for tid in threads_to_reassign:
                    del self.thread_assignments[tid]
                
                remaining = len(self.proxies)
                print(f"Proxy failed, {remaining} remaining out of {self.original_proxy_count}")
                
                if remaining == 0 and not self.all_failed_warned and self.original_proxy_count > 0:
                    print(f"WARNING: All {self.original_proxy_count} proxies have failed, switching to direct connection")
                    self.all_failed_warned = True

    def all_proxies_failed(self):
        """Check if all proxies have failed"""
        return len(self.proxies) == 0
    
    def get_untried_proxy_for_url(self, url):
        """Get an untried proxy for a specific URL"""
        with self.proxy_lock:
            # Simple round-robin for now - more sophisticated logic can be added later
            if self.proxies:
                return self.proxies[self.current_proxy_index % len(self.proxies)]
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
        """Extract links from BeautifulSoup object."""
        links = set()
        if not soup:
            return links
        
        for a_tag in soup.find_all('a', href=True):
            href = a_tag['href']
            try:
                absolute_url = urllib.parse.urljoin(base_url, href)
                absolute_url = urllib.parse.urldefrag(absolute_url)[0]
                links.add(absolute_url)
            except Exception as e:
                logging.debug(f"Could not process link {href}: {e}")
                continue
        return links
    
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

# DynamicScraper class for handling JavaScript-rendered pages
class DynamicScraper:
    def __init__(self, headless=True, timeout=30000, user_agent=None):
        self.headless = headless
        self.timeout = timeout
        self.user_agent = user_agent
        self.playwright = None
        self.browser = None
        self.page = None

    def start(self):
        if self.browser: 
            return
        try:
            logging.debug("Starting Playwright context...")
            self.playwright = sync_playwright().start()
            
            logging.debug("Launching Chromium browser...")
            # Add timeout and better error handling for browser launch
            self.browser = self.playwright.chromium.launch(
                headless=self.headless,
                timeout=30000  # 30 second timeout for browser launch
            )
            
            logging.debug("Creating new page...")
            self.page = self.browser.new_page(user_agent=self.user_agent)
            
            # Set page timeout
            self.page.set_default_timeout(self.timeout)
            
            logging.debug("Playwright browser started successfully")
            
        except Exception as e:
            logging.error(f"Failed to start Playwright browser: {e}")
            # Clean up on failure
            if self.browser:
                try:
                    self.browser.close()
                except:
                    pass
            if self.playwright:
                try:
                    self.playwright.stop()
                except:
                    pass
            self.browser = None
            self.playwright = None
            self.page = None
            raise # Re-raise exception to be handled by Siphon

    def stop(self):
        if self.browser:
            self.browser.close()
        if self.playwright:
            self.playwright.stop()
        self.browser = None
        self.playwright = None
        self.page = None

    def navigate(self, url, wait_until="domcontentloaded", timeout=None):
        if not self.page:
            logging.error("Navigate called but page is not available.")
            return False
        try:
            self.page.goto(url, wait_until=wait_until, timeout=timeout or self.timeout)
            # A brief wait can help with pages that load content after DOM is ready
            self.page.wait_for_timeout(1000) 
            return True
        except PlaywrightTimeoutError:
            logging.warning(f"Timeout while navigating to {url}")
            return False
        except Exception as e:
            logging.error(f"An unexpected error occurred during navigation to {url}: {e}")
            return False

    def extract_links(self, base_url):
        if not self.page: return set()
        
        try:
            # Using page.eval_on_selector_all is efficient for grabbing hrefs
            hrefs = self.page.eval_on_selector_all("a[href]", "elements => elements.map(el => el.href)")
            
            # Resolve all URLs and add to a set for uniqueness
            links = set()
            for href in hrefs:
                try:
                    absolute_url = urllib.parse.urljoin(base_url, href.strip())
                    absolute_url = urllib.parse.urldefrag(absolute_url)[0]
                    if absolute_url.startswith(('http', 'https')):
                        links.add(absolute_url)
                except Exception:
                    continue # Ignore malformed hrefs
            return links
        except Exception as e:
            logging.error(f"Failed to extract links dynamically from {base_url}: {e}")
            return set()

    def find_and_click_downloads(self, download_extensions=None, keywords=None, delay=1.0):
        """
        Find and interact with download elements using multiple robust strategies.
        Uses modern Playwright locator methods with comprehensive fallbacks.
        """
        if not self.page:
            logging.warning("No page available for download detection")
            return []

        discovered_downloads = []
        keywords = keywords or ['download', 'save', 'export', 'get', 'fetch']
        # Only use provided extensions, don't fall back to defaults
        download_extensions = download_extensions or []
        
        logging.info(f"Starting download detection with extensions: {download_extensions}")
        
        # Strategy 1: Modern Playwright locator methods (preferred)
        try:
            elements_found = 0
            
            # Find elements by text content (case-insensitive)
            for keyword in keywords:
                try:
                    # Use getByText for exact and partial matches
                    text_elements = self.page.get_by_text(keyword, exact=False).all()
                    for element in text_elements:
                        if element.is_visible():
                            elements_found += 1
                            href = element.get_attribute('href')
                            if href:
                                absolute_url = urllib.parse.urljoin(self.page.url, href)
                                discovered_downloads.append(absolute_url)
                                logging.info(f"Found download via text '{keyword}': {absolute_url}")
                except Exception as e:
                    logging.debug(f"Text search for '{keyword}' failed: {e}")
                    
            # Find elements by role (buttons, links)
            try:
                # Look for download buttons
                buttons = self.page.get_by_role("button").all()
                for button in buttons:
                    if button.is_visible():
                        text_content = button.text_content() or ""
                        if any(kw.lower() in text_content.lower() for kw in keywords):
                            elements_found += 1
                            # Try to click and capture download
                            try:
                                with self.page.expect_download(timeout=5000) as download_info:
                                    button.click(timeout=3000)
                                download = download_info.value
                                temp_file_path = os.path.join(tempfile.gettempdir(), download.suggested_filename)
                                download.save_as(temp_file_path)
                                file_uri = pathlib.Path(temp_file_path).as_uri()
                                discovered_downloads.append(file_uri)
                                logging.info(f"Captured download from button: {download.suggested_filename}")
                            except Exception as e:
                                logging.debug(f"Button click failed: {e}")
                                
                # Look for download links
                links = self.page.get_by_role("link").all()
                for link in links:
                    if link.is_visible():
                        href = link.get_attribute('href')
                        if href:
                            absolute_url = urllib.parse.urljoin(self.page.url, href)
                            # Check if it's a direct file link
                            if any(absolute_url.lower().endswith(f'.{ext.lower()}') for ext in download_extensions):
                                elements_found += 1
                                discovered_downloads.append(absolute_url)
                                logging.info(f"Found direct file link: {absolute_url}")
                            # Check if link text suggests download
                            elif any(kw.lower() in (link.text_content() or "").lower() for kw in keywords):
                                elements_found += 1
                                discovered_downloads.append(absolute_url)
                                logging.info(f"Found download link by text: {absolute_url}")
                                
            except Exception as e:
                logging.debug(f"Role-based search failed: {e}")
                
            logging.info(f"Strategy 1 (Modern locators) found {elements_found} elements")
            
        except Exception as e:
            logging.warning(f"Modern locator strategy failed: {e}")

        # Strategy 2: CSS selectors with proper syntax (fallback)
        try:
            elements_found = 0
            
            # Build valid CSS selectors
            css_selectors = [
                "[download]",  # Elements with download attribute
                "[onclick*='download']",  # Elements with download in onclick
                "a:has-text(\"download\")",  # Links containing "download" text
                "button:has-text(\"download\")",  # Buttons containing "download" text
                "a:has-text(\"save\")",  # Links containing "save" text
                "button:has-text(\"save\")",  # Buttons containing "save" text
                "a:has-text(\"export\")",  # Links containing "export" text
                "button:has-text(\"export\")",  # Buttons containing "export" text
            ]

            # Add file extension selectors
            for ext in download_extensions:
                css_selectors.append(f"a[href$='.{ext.lower()}']")
                css_selectors.append(f"a[href*='.{ext.lower()}']")

            # Query elements using valid CSS selectors
            for selector in css_selectors:
                try:
                    elements = self.page.query_selector_all(selector)
                    for element in elements:
                        if element.is_visible():
                            elements_found += 1
                            href = element.get_attribute('href')
                            if href:
                                absolute_url = urllib.parse.urljoin(self.page.url, href)
                                if absolute_url not in discovered_downloads:
                                    discovered_downloads.append(absolute_url)
                                    logging.info(f"Found via CSS '{selector}': {absolute_url}")
                except Exception as e:
                    logging.debug(f"CSS selector '{selector}' failed: {e}")
                    
            logging.info(f"Strategy 2 (CSS selectors) found {elements_found} additional elements")
            
        except Exception as e:
            logging.warning(f"CSS selector strategy failed: {e}")

        # Strategy 3: JavaScript blob detection (for dynamic content)
        try:
            elements_found = 0
            
            # Look for elements with Alpine.js @click or onclick containing blob operations
            js_elements = self.page.query_selector_all("[onclick], [x-on\\:click]")
            for element in js_elements:
                try:
                    onclick_attr = (element.get_attribute('onclick') or 
                                  element.get_attribute('@click') or 
                                  element.get_attribute('x-on:click') or "")
                    
                    if 'blob' in onclick_attr.lower() or 'download' in onclick_attr.lower():
                        elements_found += 1
                        blob_info = self.extract_blob_info(element)
                        if blob_info and blob_info not in discovered_downloads:
                            discovered_downloads.append(blob_info)
                            logging.info(f"Found blob download: {blob_info}")
                        else:
                            # Try clicking to trigger download
                            try:
                                with self.page.expect_download(timeout=3000) as download_info:
                                    element.click(timeout=2000)
                                download = download_info.value
                                temp_file_path = os.path.join(tempfile.gettempdir(), download.suggested_filename)
                                download.save_as(temp_file_path)
                                file_uri = pathlib.Path(temp_file_path).as_uri()
                                if file_uri not in discovered_downloads:
                                    discovered_downloads.append(file_uri)
                                    logging.info(f"Captured JS-triggered download: {download.suggested_filename}")
                            except Exception as e:
                                logging.debug(f"JS element click failed: {e}")
                                
                except Exception as e:
                    logging.debug(f"JS element processing failed: {e}")
                    
            logging.info(f"Strategy 3 (JS/Blob detection) found {elements_found} additional elements")
            
        except Exception as e:
            logging.warning(f"JavaScript detection strategy failed: {e}")

        # Strategy 4: XPath fallback (most robust but slower)
        try:
            elements_found = 0
            
            xpath_selectors = [
                "//a[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'download')]",
                "//button[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'download')]",
                "//a[contains(translate(@href, 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'download')]",
                "//a[@download]",
                "//button[@download]",
            ]
            
            # Add XPath for file extensions
            for ext in download_extensions:
                xpath_selectors.append(f"//a[contains(@href, '.{ext.lower()}')]")
                
            for xpath in xpath_selectors:
                try:
                    elements = self.page.query_selector_all(f"xpath={xpath}")
                    for element in elements:
                        if element.is_visible():
                            elements_found += 1
                            href = element.get_attribute('href')
                            if href:
                                absolute_url = urllib.parse.urljoin(self.page.url, href)
                                if absolute_url not in discovered_downloads:
                                    discovered_downloads.append(absolute_url)
                                    logging.info(f"Found via XPath: {absolute_url}")
                except Exception as e:
                    logging.debug(f"XPath '{xpath}' failed: {e}")
                    
            logging.info(f"Strategy 4 (XPath fallback) found {elements_found} additional elements")
            
        except Exception as e:
            logging.warning(f"XPath strategy failed: {e}")

        # Remove duplicates while preserving order
        unique_downloads = []
        seen = set()
        for url in discovered_downloads:
            if url not in seen:
                unique_downloads.append(url)
                seen.add(url)
                
        logging.info(f"Total unique downloads found: {len(unique_downloads)}")
        
        # Add delay between operations if specified
        if delay > 0:
            time.sleep(delay)
            
        return unique_downloads

    def extract_blob_info(self, element):
        """
        Extracts filename and content from a JS blob download with multiple strategies.
        Handles various JavaScript patterns for dynamic content generation.
        """
        try:
            # Get all possible JavaScript attributes
            js_code = (element.get_attribute('@click') or 
                      element.get_attribute('onclick') or 
                      element.get_attribute('x-on:click') or 
                      element.get_attribute('data-action') or "")
            
            if not js_code:
                logging.debug("No JavaScript code found in element")
                return None
                
            logging.debug(f"Analyzing JS code: {js_code[:200]}...")
            
            # Strategy 1: Extract filename from download attribute
            filename = None
            filename_patterns = [
                r"download\s*=\s*['\"]([^'\"]+)['\"]",  # download="filename.ext"
                r"\.download\s*=\s*['\"]([^'\"]+)['\"]",  # a.download="filename.ext"
                r"setAttribute\s*\(\s*['\"]download['\"],\s*['\"]([^'\"]+)['\"]",  # setAttribute("download", "filename.ext")
                r"filename['\"]?\s*[:=]\s*['\"]([^'\"]+)['\"]",  # filename: "filename.ext"
            ]
            
            for pattern in filename_patterns:
                match = re.search(pattern, js_code, re.IGNORECASE)
                if match:
                    filename = match.group(1)
                    logging.debug(f"Extracted filename: {filename}")
                    break
                    
            if not filename:
                # Fallback: try to get filename from nearby elements
                try:
                    # Look for filename in element text or nearby elements
                    element_text = element.text_content() or ""
                    if '.' in element_text:
                        # Extract potential filename from text
                        words = element_text.split()
                        for word in words:
                            if '.' in word and len(word.split('.')[-1]) <= 5:  # Reasonable extension length
                                filename = word.strip('.,!?;:')
                                break
                except Exception as e:
                    logging.debug(f"Failed to extract filename from text: {e}")
                    
            if not filename:
                filename = "downloaded_file.txt"  # Default filename
                
            # Strategy 2: Extract content from various sources
            content = None
            
            # Method 1: Look for content in nearby code elements
            try:
                # Try different XPath patterns to find code content
                code_selectors = [
                    "xpath=./preceding-sibling::*//code",
                    "xpath=./following-sibling::*//code", 
                    "xpath=./ancestor::*[1]//code",
                    "xpath=./ancestor::*[2]//code",
                    "xpath=.//code",
                ]
                
                for selector in code_selectors:
                    try:
                        code_element = element.query_selector(selector)
                        if code_element:
                            content = code_element.inner_text()
                            if content and content.strip():
                                logging.debug(f"Found content in code element: {len(content)} characters")
                                break
                    except Exception as e:
                        logging.debug(f"Code selector '{selector}' failed: {e}")
                        
            except Exception as e:
                logging.debug(f"Code element search failed: {e}")
                
            # Method 2: Look for content in pre elements
            if not content:
                try:
                    pre_selectors = [
                        "xpath=./preceding-sibling::*//pre",
                        "xpath=./following-sibling::*//pre",
                        "xpath=./ancestor::*[1]//pre",
                        "xpath=./ancestor::*[2]//pre",
                    ]
                    
                    for selector in pre_selectors:
                        try:
                            pre_element = element.query_selector(selector)
                            if pre_element:
                                content = pre_element.inner_text()
                                if content and content.strip():
                                    logging.debug(f"Found content in pre element: {len(content)} characters")
                                    break
                        except Exception as e:
                            logging.debug(f"Pre selector '{selector}' failed: {e}")
                            
                except Exception as e:
                    logging.debug(f"Pre element search failed: {e}")
                    
            # Method 3: Extract content from JavaScript variables
            if not content:
                try:
                    # Look for content in JavaScript variables
                    content_patterns = [
                        r"textContent\s*[=:]\s*['\"]([^'\"]+)['\"]",
                        r"innerText\s*[=:]\s*['\"]([^'\"]+)['\"]",
                        r"content\s*[=:]\s*['\"]([^'\"]+)['\"]",
                        r"data\s*[=:]\s*['\"]([^'\"]+)['\"]",
                    ]
                    
                    for pattern in content_patterns:
                        match = re.search(pattern, js_code, re.IGNORECASE | re.DOTALL)
                        if match:
                            content = match.group(1)
                            logging.debug(f"Extracted content from JS: {len(content)} characters")
                            break
                            
                except Exception as e:
                    logging.debug(f"JS content extraction failed: {e}")
                    
            # Method 4: Try to execute JavaScript to get content
            if not content:
                try:
                    # Try to evaluate JavaScript to get the content
                    # This is more complex and site-specific, so we'll use a simple approach
                    if '$refs.' in js_code:
                        # Alpine.js pattern - try to find the referenced element
                        ref_match = re.search(r'\$refs\.(\w+)', js_code)
                        if ref_match:
                            ref_name = ref_match.group(1)
                            try:
                                ref_element = self.page.query_selector(f"[x-ref='{ref_name}']")
                                if ref_element:
                                    content = ref_element.inner_text()
                                    logging.debug(f"Found content via Alpine.js ref: {len(content)} characters")
                            except Exception as e:
                                logging.debug(f"Alpine.js ref extraction failed: {e}")
                                
                except Exception as e:
                    logging.debug(f"JavaScript execution failed: {e}")
                    
            # Fallback content
            if not content:
                content = f"# {filename}\n\nContent extracted from {self.page.url}\n\nGenerated by Siphon web scraper"
                logging.debug("Using fallback content")
                
            # Create blob URI
            try:
                encoded_content = base64.b64encode(content.encode('utf-8')).decode('utf-8')
                blob_uri = f"blob:{filename}:{encoded_content}"
                logging.info(f"Successfully created blob URI for '{filename}' ({len(content)} chars)")
                return blob_uri
                
            except Exception as e:
                logging.error(f"Failed to create blob URI: {e}")
                return None
                
        except Exception as e:
            logging.error(f"Error extracting blob info: {e}")
            return None

    # ... other DynamicScraper methods like monitor_network can remain ...

class Siphon:
    def __init__(self, base_url=None, output_dir="output", max_depth=1, delay=0, max_urls=None,
                 timeout=10, user_agent=None, verify_ssl=True, headers=None, cookies=None, auth=None,
                 proxy=None, # proxy here is a single string or dict, ProxyManager expects a list
                 crawl_only=False, download_extensions=None, exclude_extensions=None,
                 exclude_urls=None, include_urls=None, custom_parser=None,
                 dynamic_mode="auto", test_proxies_on_start=False, max_threads=3, verbose=False): # Added test_proxies_on_start, max_threads, and verbose

        self.base_url = base_url
        if not base_url:
            raise ValueError("base_url must be provided to Siphon.")
            
        parsed_start = urllib.parse.urlparse(base_url)
        self.domain = parsed_start.netloc
        self.output_dir = output_dir
        self.max_depth = max_depth
        self.delay = delay
        self.max_urls = max_urls
        self.timeout = timeout
        self.user_agent = user_agent or random.choice(USER_AGENTS) # Use global USER_AGENTS
        self.verify_ssl = verify_ssl
        self.headers = headers or {}
        self.request_headers = headers or {}
        self.request_cookies = cookies or {}
        self.auth = auth
        self.crawl_only = crawl_only
        
        # Ensure extensions are lists of non-empty strings
        self.download_extensions = [ext.strip() for ext in download_extensions if ext.strip()] if isinstance(download_extensions, list) else ([ext.strip() for ext in download_extensions.split(',') if ext.strip()] if download_extensions else [])
        self.exclude_extensions = [ext.strip() for ext in exclude_extensions if ext.strip()] if isinstance(exclude_extensions, list) else ([ext.strip() for ext in exclude_extensions.split(',') if ext.strip()] if exclude_extensions else [])
        
        self.exclude_urls = [pat.strip() for pat in exclude_urls if pat.strip()] if isinstance(exclude_urls, list) else ([pat.strip() for pat in exclude_urls.split(',') if pat.strip()] if exclude_urls else [])
        self.include_urls = [pat.strip() for pat in include_urls if pat.strip()] if isinstance(include_urls, list) else ([pat.strip() for pat in include_urls.split(',') if pat.strip()] if include_urls else [])
        
        self.custom_parser = custom_parser

        self.visited_urls = set()
        self.discovered_files = set()
        self.downloaded_files = set()

        self.session = requests.Session()
        if self.request_headers:
            self.session.headers.update(self.request_headers)
        if self.request_cookies:
            self.session.cookies.update(self.request_cookies)
        if self.auth:
            self.session.auth = self.auth

        proxy_list_arg = []
        if isinstance(proxy, str) and proxy.strip():
            proxy_list_arg = [proxy.strip()]
        elif isinstance(proxy, dict):
            proxy_url = proxy.get('https', proxy.get('http'))
            if proxy_url and proxy_url.strip():
                proxy_list_arg = [proxy_url.strip()]
        elif isinstance(proxy, list):
            proxy_list_arg = [p.strip() for p in proxy if p.strip()]

        self.proxy_manager = ProxyManager(proxy_list_arg)
        
        # Automatically disable SSL verification when using proxies to avoid certificate issues
        if self.proxy_manager.proxies and self.verify_ssl:
            logging.info("Proxies detected - disabling SSL verification to avoid certificate chain issues")
            self.verify_ssl = False
            
        # Don't test proxies upfront - they'll be tested on-demand in get_proxy()
        if self.proxy_manager.proxies:
            logging.info(f"Loaded {len(self.proxy_manager.proxies)} proxies (will test on-demand)")
        else:
            logging.info("No proxies loaded, using direct connection")

        self.rate_limiter = RateLimiter(initial_delay=self.delay if self.delay > 0 else 0.25)
        self.cache = {}

        # Threading attributes
        self.max_threads = max_threads
        self.url_queue = queue.Queue()
        self.queue_lock = threading.Lock()
        self.visited_lock = threading.Lock()
        self.thread_counter = 0 # For assigning sequential thread IDs
        self.thread_ids = {}
        self.thread_id_lock = threading.Lock()

        safe_domain_name = parsed_start.netloc.replace(':', '_').replace('/', '_')
        safe_path_segment = parsed_start.path.strip('/').replace('/', '_') if parsed_start.path.strip('/') else ''
        
        # Ensure the folder name is valid for filesystems
        folder_name_base = f"{safe_domain_name}_{safe_path_segment}" if safe_path_segment else safe_domain_name
        folder_name = "".join(c if c.isalnum() or c in ['_', '-'] else '_' for c in folder_name_base)
        folder_name = folder_name.strip('_') # Avoid leading/trailing underscores

        if not folder_name: # Fallback if everything was stripped
            folder_name = "siphon_download"
            
        self.domain_dir = os.path.join(self.output_dir, folder_name)
        os.makedirs(self.domain_dir, exist_ok=True)
        self.downloads_subdir = os.path.join(self.domain_dir, 'downloads')
        os.makedirs(self.downloads_subdir, exist_ok=True)
        
        # Dynamic scraping settings
        self.dynamic_mode = dynamic_mode
        self.dynamic_scraper = None
        self.verbose = verbose
        
        # Don't initialize dynamic scraper immediately to avoid hanging
        # It will be initialized when first needed
        # if self.dynamic_mode == "always" and PLAYWRIGHT_AVAILABLE:
        #     self.init_dynamic_scraper()

    def init_dynamic_scraper(self):
        """Initialize the dynamic scraper if not already initialized"""
        if self.dynamic_scraper is None and PLAYWRIGHT_AVAILABLE:
            try:
                logging.info("Initializing dynamic scraper (Playwright browser)...")
                self.dynamic_scraper = DynamicScraper(
                    headless=True, 
                    timeout=min(self.timeout * 1000, 30000),  # Cap at 30 seconds
                    user_agent=self.user_agent
                )
                logging.info("Starting Playwright browser...")
                self.dynamic_scraper.start()
                logging.info("Dynamic scraper initialized successfully")
                return True
            except Exception as e:
                logging.error(f"Failed to initialize dynamic scraper: {str(e)}")
                logging.warning("Falling back to static scraping only")
                self.dynamic_scraper = None
                return False
        return self.dynamic_scraper is not None
        
    def close_dynamic_scraper(self):
        """Close the dynamic scraper if it's open"""
        if self.dynamic_scraper:
            try:
                self.dynamic_scraper.stop()
            except:
                pass
            self.dynamic_scraper = None
            
    def should_use_dynamic_scraping(self, url, static_links=None):
        """Determine if dynamic scraping should be used for this URL"""
        if self.dynamic_mode == "always":
            return True
        elif self.dynamic_mode == "never":
            return False
            
        # In auto mode, check if static scraping found any target files
        if static_links is not None:
            target_files = self.filter_target_files(static_links)
            if target_files:
                return False  # Static scraping found target files
                
        # Check URL for indicators of dynamic content
        dynamic_indicators = [
            "react", "vue", "angular", "spa", "single-page", 
            "javascript", "js", "ajax", "dynamic"
        ]
        
        url_lower = url.lower()
        for indicator in dynamic_indicators:
            if indicator in url_lower:
                return True
                
        return False  # Default to static scraping
        
    def dynamic_scrape(self, url):
        """Perform dynamic scraping on a URL, with corrected arguments and error handling."""
        if not self.init_dynamic_scraper() or not self.dynamic_scraper:
            logging.warning("Dynamic scraper not available or failed to initialize.")
            return set()

        all_links = set()
        try:
            if not self.dynamic_scraper.navigate(url):
                logging.warning(f"Dynamic navigation to {url} failed.")
                return set()
            
            # Extract links from the fully rendered page
            try:
                rendered_links = self.dynamic_scraper.extract_links(url)
                all_links.update(rendered_links)
                logging.info(f"Dynamically found {len(rendered_links)} links on: {url}")
            except Exception as e:
                logging.error(f"Error dynamically extracting links from {url}: {e}")

            # Find and click elements that might trigger downloads
            try:
                discovered_downloads = self.dynamic_scraper.find_and_click_downloads(self.download_extensions)
                if discovered_downloads:
                    all_links.update(discovered_downloads)
                    logging.info(f"Found {len(discovered_downloads)} downloads via dynamic interaction")
            except Exception as e:
                logging.error(f"Error dynamically clicking download elements on {url}: {e}")
            
            return all_links
            
        except Exception as e:
            logging.critical(f"A major, unrecoverable error occurred during dynamic scraping for {url}: {e}")
            self.close_dynamic_scraper() # Attempt to clean up
            return set()
    
    def crawl(self, url=None, depth=0):
        """
        Crawl a URL and its links up to max_depth using multiple threads.
        
        Parameters:
        -----------
        url : str
            The URL to crawl.
        depth : int
            The current depth of crawling (ignored in threaded version).
        """
        if url is None:
            url = self.base_url
            
        # Initialize the queue with the starting URL
        self.url_queue.put((url, 0))
        
        # Start worker threads
        with ThreadPoolExecutor(max_workers=self.max_threads) as executor:
            futures = [executor.submit(self.worker_thread) for _ in range(self.max_threads)]
            
            # Wait for all threads to complete
            for future in as_completed(futures):
                try:
                    future.result()
                except Exception as e:
                    logging.error(f"Worker thread error: {e}")
    
    def worker_thread(self):
        """Worker thread that processes URLs from the queue."""
        # Assign sequential thread ID
        with self.thread_id_lock:
            current_thread_ident = threading.get_ident()
            if current_thread_ident not in self.thread_ids:
                self.thread_counter += 1
                self.thread_ids[current_thread_ident] = self.thread_counter
            thread_id = self.thread_ids[current_thread_ident]
        
        while not shutdown_flag.is_set():
            try:
                # Get next URL from queue with timeout
                url_info = self.url_queue.get(timeout=1.0)
                url, depth = url_info
            except queue.Empty:
                # Check if there are any other threads still working
                if self.url_queue.empty():
                    break
                continue
            
            # Check if we got a valid URL
            if not url_info:
                try:
                    self.url_queue.task_done()
                except ValueError:
                    pass
                continue
            
            try:
                # Check if we should process this URL
                with self.visited_lock:
                    if url in self.visited_urls:
                        self.url_queue.task_done()
                        continue
                    
                    if self.max_urls is not None and len(self.visited_urls) >= self.max_urls:
                        self.url_queue.task_done()
                        continue
                        
                    if depth > self.max_depth:
                        self.url_queue.task_done()
                        continue
                        
                    if not self.should_crawl_url(url):
                        self.url_queue.task_done()
                        continue
                        
                    self.visited_urls.add(url)
                
                # Only show progress for files that match our criteria or when downloading
                should_download = self.should_download_file(url)
                
                # Show progress for all URLs when verbose
                if self.verbose or should_download:
                    print(f"[{thread_id}] Crawling: {url}")
                
                # Try static scraping first (always enabled now for better threading)
                static_links = set()
                html_content = None
                html_content = self.fetch_url(url)
                if html_content:
                    soup = self.parse_html(html_content)
                    static_links = self.extract_links(soup, url)
                    if self.verbose:
                        print(f"    -> Found {len(static_links)} links")
                
                # Use dynamic scraping only when necessary and single-threaded
                dynamic_links = set()
                use_dynamic = (self.max_threads == 1 and 
                              self.should_use_dynamic_scraping(url, static_links))
                
                if use_dynamic:
                    if should_download:
                        print(f"[{thread_id}] {url} -> Dynamic mode")
                    dynamic_links = self.dynamic_scrape(url)
                    
                # Combine links from both methods
                links = list(static_links.union(dynamic_links))
                
                # Process the links
                files_downloaded = 0
                potential_files = []
                new_crawl_urls = 0
                
                for link in links:
                    if shutdown_flag.is_set():
                        break
                        
                    if self.should_download_file(link):
                        potential_files.append(link)
                        if self.verbose:
                            print(f"    -> Downloading: {link}")
                        self.download_file(link)
                        files_downloaded += 1
                    elif self.should_crawl_url(link) and depth < self.max_depth:
                        # Add to queue for processing by worker threads
                        self.url_queue.put((link, depth + 1))
                        new_crawl_urls += 1
                
                # Show summary - only show meaningful progress
                if files_downloaded > 0:
                    print(f"    -> Downloaded {files_downloaded} file(s)")
                elif self.verbose:
                    if new_crawl_urls > 0:
                        print(f"    -> Added {new_crawl_urls} URLs to crawl queue")
                    if len(potential_files) > 0:
                        print(f"    -> Found {len(potential_files)} potential files but none matched criteria")
                
                if self.delay > 0:
                    time.sleep(self.delay)
                    
            except Exception as e:
                if self.verbose:
                    print(f"    ERROR: {str(e)}")
                logging.error(f"Error processing {url}: {str(e)}")
            finally:
                # Always call task_done() exactly once per item
                self.url_queue.task_done()
    
    def __enter__(self):
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close_dynamic_scraper()
        
    def close(self):
        """Clean up resources"""
        self.close_dynamic_scraper()

    def should_crawl_url(self, url):
        """
        Determine if a URL should be crawled based on various criteria.
        """
        if not url:
            return False
        if url in self.visited_urls:
            return False
        try:
            parsed_url = urllib.parse.urlparse(url)
            if parsed_url.netloc and parsed_url.netloc != self.domain:
                return False
        except:
            return False
        if self.exclude_urls:
            for pattern in self.exclude_urls:
                if pattern in url:
                    return False
        if self.include_urls:
            for pattern in self.include_urls:
                if pattern in url:
                    return True
            return False
        # Allow crawling of downloadable files - we need to crawl them to download them
        return True

    def should_download_file(self, url):
        """
        Determine if a URL points to a file that should be downloaded.
        """
        if not url:
            return False
        if self.crawl_only:
            return False
            
        # For playbooks.com, treat rule pages as downloadable content
        if 'playbooks.com/rules/' in url and not url.endswith('/'):
            return True
            
        # Check file:/// URLs from dynamic scraper (they're captured downloads)
        if url.startswith('file:///'):
            try:
                parsed_url = urllib.parse.urlparse(url)
                path = parsed_url.path
                ext = os.path.splitext(path)[1].lower().lstrip('.')
                # Treat .mdc files as .md files for compatibility
                if ext == 'mdc':
                    ext = 'md'
                if ext and self.download_extensions:
                    return ext in self.download_extensions
                return True  # If no extension filtering, download it
            except:
                return True
            
        # Check blob: URLs from dynamic scraper
        if url.startswith('blob:'):
            try:
                # Extract filename from blob URL format: blob:filename:base64content
                parts = url.split(':', 2)
                if len(parts) >= 2:
                    filename = parts[1]
                    ext = os.path.splitext(filename)[1].lower().lstrip('.')
                    # Treat .mdc files as .md files for compatibility
                    if ext == 'mdc':
                        ext = 'md'
                    if ext and self.download_extensions:
                        return ext in self.download_extensions
                return True  # If no extension filtering, download it
            except:
                return True
            
        try:
            parsed_url = urllib.parse.urlparse(url)
            path = parsed_url.path
            ext = os.path.splitext(path)[1].lower().lstrip('.')
            # Treat .mdc files as .md files for compatibility
            if ext == 'mdc':
                ext = 'md'
        except:
            return False
        if not ext:
            return False
        if self.exclude_extensions and ext in self.exclude_extensions:
            return False
        if self.download_extensions:
            return ext in self.download_extensions
        return False

    def fetch_url(self, url, max_retries=3):
        """
        Fetch content from a URL with retries and error handling.
        """
        last_exception = None
        
        for attempt in range(max_retries):
            try:
                proxy_to_use = None
                if self.proxy_manager and hasattr(self.proxy_manager, 'get_proxy'):
                    try:
                        proxy_to_use = self.proxy_manager.get_proxy(threading.get_ident(), url)
                    except Exception as e_proxy:
                        logging.warning(f"Failed to get proxy for {url}: {e_proxy}")

                # Set headers including user agent
                headers = {
                    'User-Agent': self.user_agent
                }
                if self.headers:
                    headers.update(self.headers)
                
                response = self.session.get(
                    url,
                    timeout=(self.timeout, self.timeout),  # (connect_timeout, read_timeout)
                    verify=self.verify_ssl,
                    proxies=proxy_to_use,
                    headers=headers
                )
                response.raise_for_status()
                # Use RobustResponse for better encoding detection
                return RobustResponse(response.content, response, url).text
                
            except requests.exceptions.HTTPError as e_http:
                last_exception = e_http
                # Log 4xx client errors as warnings, not critical errors
                if 400 <= e_http.response.status_code < 500:
                    if self.verbose:
                        logging.warning(f"Client error {e_http.response.status_code} fetching {url}: {e_http.response.reason}")
                    else:
                        logging.warning(f"Client error {e_http.response.status_code} fetching {url}: {e_http.response.reason}")
                else:
                    if self.verbose:
                        logging.error(f"HTTP server error {e_http.response.status_code} fetching {url}: {e_http.response.reason}")
                    else:
                        logging.error(f"HTTP server error {e_http.response.status_code} fetching {url}: {e_http.response.reason}")
                if self.proxy_manager and hasattr(self.proxy_manager, 'mark_proxy_failed') and proxy_to_use:
                    self.proxy_manager.mark_proxy_failed(proxy_to_use)
                break  # Don't retry HTTP errors
                
            except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as e_conn:
                last_exception = e_conn
                if self.proxy_manager and hasattr(self.proxy_manager, 'mark_proxy_failed') and proxy_to_use:
                    self.proxy_manager.mark_proxy_failed(proxy_to_use)
                if attempt < max_retries - 1:
                    if self.verbose:
                        logging.warning(f"Connection error fetching {url} (attempt {attempt + 1}/{max_retries}): {e_conn}")
                    else:
                        logging.warning(f"Connection error fetching {url} (attempt {attempt + 1}/{max_retries}): Connection failed")
                    time.sleep(0.5)  # Shorter delay for faster proxy rotation
                    continue
                else:
                    if self.verbose:
                        logging.error(f"Connection error fetching {url} (final attempt): {e_conn}")
                    else:
                        logging.error(f"Connection error fetching {url} (final attempt): Connection failed")
                        
            except requests.exceptions.RequestException as e_req:
                last_exception = e_req
                if self.verbose:
                    logging.error(f"Request error fetching {url}: {e_req}")
                else:
                    logging.error(f"Request error fetching {url}: Request failed")
                if self.proxy_manager and hasattr(self.proxy_manager, 'mark_proxy_failed') and proxy_to_use:
                    self.proxy_manager.mark_proxy_failed(proxy_to_use)
                break  # Don't retry other request exceptions
                
            except Exception as e_gen:
                last_exception = e_gen
                if self.verbose:
                    logging.error(f"General error fetching {url}: {e_gen}")
                else:
                    logging.error(f"General error fetching {url}: Unexpected error")
                break  # Don't retry general exceptions
                
        return None

    def parse_html(self, html_content):
        """
        Parse HTML content using BeautifulSoup.
        """
        if not html_content:
            return None
        try:
            return BeautifulSoup(html_content, 'html.parser')
        except Exception as e:
            logging.error(f"Error parsing HTML: {str(e)}")
            return None

    def extract_links(self, soup, base_url):
        """
        Extract and resolve links from a BeautifulSoup soup object.
        """
        links = set()
        if not soup or not base_url:
            return links
        for a_tag in soup.find_all('a', href=True):
            href = a_tag['href']
            if href: # Ensure href is not None or empty
                try:
                    # urljoin handles absolute and relative URLs correctly
                    absolute_url = urllib.parse.urljoin(base_url, href.strip())
                    # Remove fragment
                    absolute_url = urllib.parse.urldefrag(absolute_url)[0]
                    if absolute_url.startswith(('http://', 'https://')): # Ensure it's a valid web URL
                        links.add(absolute_url)
                except Exception as e:
                    logging.debug(f"Could not process or resolve link '{href}' from base '{base_url}': {e}")
        return links

    def extract_main_content(self, soup, url):
        """
        Extract the main content from a HTML page and convert to markdown-like format.
        """
        # For playbooks.com rule pages, look for the main content area
        if 'playbooks.com/rules/' in url:
            # Try to find the main content container
            content_selectors = [
                'main',
                '[role="main"]', 
                '.main-content',
                '.content',
                'article',
                '.rule-content',
                '.markdown-body'
            ]
            
            content_elem = None
            for selector in content_selectors:
                content_elem = soup.select_one(selector)
                if content_elem:
                    break
            
            if not content_elem:
                # Fallback to body content, excluding nav/header/footer
                content_elem = soup.select_one('body')
                if content_elem:
                    # Remove navigation, header, footer elements
                    for unwanted in content_elem.select('nav, header, footer, .navbar, .nav, .header, .footer, script, style'):
                        unwanted.decompose()
            
            if content_elem:
                # Extract text content with basic formatting
                text_content = ""
                title = soup.select_one('title')
                if title:
                    text_content += f"# {title.get_text().strip()}\n\n"
                
                # Extract meta description
                meta_desc = soup.select_one('meta[name="description"]')
                if meta_desc:
                    text_content += f"{meta_desc.get('content', '').strip()}\n\n"
                
                # Process content elements
                for elem in content_elem.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'p', 'pre', 'code', 'ul', 'ol', 'li']):
                    tag_name = elem.name
                    text = elem.get_text().strip()
                    
                    if not text:
                        continue
                    
                    if tag_name.startswith('h'):
                        level = int(tag_name[1])
                        text_content += f"{'#' * level} {text}\n\n"
                    elif tag_name == 'p':
                        text_content += f"{text}\n\n"
                    elif tag_name in ['pre', 'code']:
                        text_content += f"```\n{text}\n```\n\n"
                    elif tag_name in ['ul', 'ol']:
                        continue  # Process individual list items
                    elif tag_name == 'li':
                        text_content += f"- {text}\n"
                
                return text_content.strip()
        
        return None

    def download_file(self, url):
        """
        Download a file from a URL, with robust filename handling.
        """
        if url in self.downloaded_files:
            logging.debug(f"File already downloaded: {url}")
            return
        
        # Handle playbooks.com rule pages by extracting content as markdown
        if 'playbooks.com/rules/' in url and not url.endswith('/'):
            try:
                # Get the HTML content
                html_content = self.fetch_url(url)
                if html_content:
                    soup = self.parse_html(html_content)
                    markdown_content = self.extract_main_content(soup, url)
                    
                    if markdown_content:
                        # Generate filename from URL
                        parsed_url = urllib.parse.urlparse(url)
                        rule_name = parsed_url.path.split('/')[-1] or "rule"
                        filename = f"{rule_name}.md"
                        
                        # Sanitize filename
                        safe_filename = "".join(c for c in filename if c.isalnum() or c in ['.', '_', '-']).strip()
                        if not safe_filename:
                            safe_filename = "rule.md"
                        
                        # Ensure downloads_subdir exists
                        os.makedirs(self.downloads_subdir, exist_ok=True)
                        
                        file_path = os.path.join(self.downloads_subdir, safe_filename)
                        
                        with open(file_path, 'w', encoding='utf-8') as f:
                            f.write(markdown_content)
                        
                        print(f"    + {safe_filename}")
                        logging.info(f"SUCCESS: Saved rule content to {file_path}")
                        self.downloaded_files.add(url)
                        self.discovered_files.add(url)
                        return
                    else:
                        logging.warning(f"Could not extract content from {url}")
            except Exception as e:
                logging.error(f"Error processing rule page {url}: {e}")
                # Fall through to normal file download logic

        # Handle blob URIs from dynamic scraper
        if url.startswith('blob:'):
            try:
                _, filename, b64_content = url.split(':', 2)
                content = base64.b64decode(b64_content)
                
                # Convert .mdc extension to .md
                if filename.endswith('.mdc'):
                    filename = filename[:-4] + '.md'
                
                # Sanitize filename
                safe_filename = "".join(c for c in filename if c.isalnum() or c in ['.', '_', '-']).strip()
                if not safe_filename:
                    safe_filename = "downloaded_file.md"

                file_path = os.path.join(self.downloads_subdir, safe_filename)
                
                with open(file_path, 'wb') as f:
                    f.write(content)
                
                print(f"    + {safe_filename}")
                logging.info(f"SUCCESS: Saved blob content to {file_path}")
                self.downloaded_files.add(url) # Use blob URI as the unique identifier
                self.discovered_files.add(url)
                return
            except Exception as e:
                logging.error(f"Failed to download from blob URI {url}: {e}")
                return

        # Handle file URIs from captured downloads
        if url.startswith('file:///'):
            try:
                parsed_url = urllib.parse.urlparse(url)
                local_path = parsed_url.path
                
                # Convert Windows path format
                if local_path.startswith('/') and ':' in local_path:
                    local_path = local_path[1:]  # Remove leading slash for Windows paths
                
                # Get filename from path
                filename = os.path.basename(local_path)
                
                # Convert .mdc extension to .md
                if filename.endswith('.mdc'):
                    filename = filename[:-4] + '.md'
                
                # Sanitize filename
                safe_filename = "".join(c for c in filename if c.isalnum() or c in ['.', '_', '-']).strip()
                if not safe_filename:
                    safe_filename = "downloaded_file.md"

                # Copy the file to our downloads directory
                file_path = os.path.join(self.downloads_subdir, safe_filename)
                
                if os.path.exists(local_path):
                    with open(local_path, 'rb') as src, open(file_path, 'wb') as dst:
                        dst.write(src.read())
                    print(f"    + {safe_filename}")
                    logging.info(f"SUCCESS: Copied file from {local_path} to {file_path}")
                else:
                    logging.warning(f"Local file not found: {local_path}")
                    return
                
                self.downloaded_files.add(url)
                self.discovered_files.add(url)
                return
            except Exception as e:
                logging.error(f"Failed to download from file URI {url}: {e}")
                return

        # Handle regular HTTP/HTTPS URLs
        try:
            proxy_to_use = None
            if self.proxy_manager and hasattr(self.proxy_manager, 'get_proxy'):
                try:
                    proxy_to_use = self.proxy_manager.get_proxy(threading.get_ident(), url)
                except Exception as e_proxy:
                    logging.warning(f"Failed to get proxy for {url}: {e_proxy}")

            response = self.session.get(
                url,
                timeout=(self.timeout, self.timeout),
                verify=self.verify_ssl,
                proxies=proxy_to_use,
                stream=True
            )
            response.raise_for_status()

            # Get filename from URL or headers
            filename = None
            content_disposition = response.headers.get('content-disposition', '')
            if 'filename=' in content_disposition:
                filename = content_disposition.split('filename=')[1].strip('"\'')
            
            if not filename:
                parsed_url = urllib.parse.urlparse(url)
                filename = os.path.basename(parsed_url.path) or "downloaded_file"
                if not os.path.splitext(filename)[1]:
                    # Try to guess extension from content-type
                    content_type = response.headers.get('content-type', '').lower()
                    if 'markdown' in content_type or 'text/plain' in content_type:
                        filename += '.md'
                    else:
                        filename += '.bin'

            # Convert .mdc extension to .md
            if filename.endswith('.mdc'):
                filename = filename[:-4] + '.md'
            
            # Sanitize filename
            filename = "".join(c for c in filename if c.isalnum() or c in ['.', '_', '-']).strip()
            if len(filename) > 200:
                filename = filename[:200] # Limit length
            if not filename: # If sanitization results in empty filename
                 filename = f"siphon_dl_{len(self.downloaded_files)}_sanitized.md"

            filepath = os.path.join(self.downloads_subdir, filename)
            
            # Ensure downloads_subdir exists
            os.makedirs(self.downloads_subdir, exist_ok=True)

            with open(filepath, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk: 
                        f.write(chunk)
            
            print(f"    + {filename}")
            self.downloaded_files.add(url)
            self.discovered_files.add(url) 
            logging.info(f"Successfully downloaded: {filepath} (from {url})")

        except requests.exceptions.HTTPError as e_http:
            logging.error(f"HTTP error {e_http.response.status_code} downloading {url}: {e_http.response.reason}")
            if self.proxy_manager and hasattr(self.proxy_manager, 'mark_proxy_failed') and proxy_to_use:
                self.proxy_manager.mark_proxy_failed(proxy_to_use)
        except requests.exceptions.RequestException as e_req: 
            logging.error(f"Request error downloading {url}: {e_req}")
            if self.proxy_manager and hasattr(self.proxy_manager, 'mark_proxy_failed') and proxy_to_use:
                self.proxy_manager.mark_proxy_failed(proxy_to_use)
        except Exception as e_gen:
            logging.error(f"General error downloading {url}: {e_gen}")
            # import traceback; logging.debug(traceback.format_exc()) # For detailed debug

    def filter_target_files(self, links):
        """Filter a list of links to find ones that match download criteria."""
        if not links:
            return []
        
        target_files = []
        for link in links:
            if self.should_download_file(link):
                target_files.append(link)
        return target_files

def main():
    global siphon_instance
    parser = argparse.ArgumentParser(
        description="Siphon - A web crawler and file downloader",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    parser.add_argument("url", help="The URL to start crawling from")
    parser.add_argument("-o", "--output", help="Output directory", default="output")
    parser.add_argument("-d", "--depth", help="Maximum crawl depth", type=int, default=3)
    parser.add_argument("--delay", help="Delay between requests in seconds", type=float, default=0)
    parser.add_argument("--max-urls", help="Maximum number of URLs to crawl", type=int)
    parser.add_argument("--timeout", help="Request timeout in seconds", type=int, default=10)
    parser.add_argument("--user-agent", help="User agent string")
    parser.add_argument("--no-verify-ssl", help="Disable SSL certificate verification", action="store_true")
    parser.add_argument("--header", help="Add custom header (format: key:value)", action="append")
    parser.add_argument("--cookie", help="Add cookie (format: key=value)", action="append")
    parser.add_argument("--auth", help="Basic auth credentials (format: username:password)")
    parser.add_argument("--proxy", help="Proxy URL (format: protocol://host:port)")
    parser.add_argument("--crawl-only", help="Only crawl, don't download files", action="store_true")
    parser.add_argument("--filetype", help="File extensions to download (comma-separated)", default="pdf,doc,docx,xls,xlsx,ppt,pptx,zip,rar,tar,gz,7z,mp3,mp4,avi,mkv,jpg,jpeg,png,gif,svg")
    parser.add_argument("--exclude", help="File extensions to exclude (comma-separated)")
    parser.add_argument("--exclude-url", help="URL patterns to exclude (comma-separated)")
    parser.add_argument("--include-url", help="URL patterns to include (comma-separated)")
    parser.add_argument("--verbose", help="Enable verbose logging", action="store_true")
    parser.add_argument("--quiet", help="Disable logging", action="store_true")
    parser.add_argument("--version", help="Show version and exit", action="store_true")
    
    # New dynamic scraping options
    parser.add_argument("--dynamic", help="Dynamic scraping mode", choices=["auto", "always", "never"], default="auto")
    parser.add_argument("--headless", help="Run browser in headless mode", action="store_true", default=True)
    parser.add_argument("--no-headless", help="Run browser in visible mode", action="store_false", dest="headless")
    parser.add_argument("--browser-timeout", help="Browser timeout in seconds", type=int, default=30)
    parser.add_argument("--click-elements", help="CSS selectors for elements to click (comma-separated)")
    parser.add_argument("--test-proxies", help="Test proxies on startup before crawling", action="store_true")
    parser.add_argument("--threads", help="Number of worker threads", type=int, default=5)
    
    args = parser.parse_args()
    
    if args.version:
        print(f"Siphon v{__version__}")
        return
        
    # Configure logging
    log_level = logging.WARNING
    if args.verbose:
        log_level = logging.INFO
    if args.quiet:
        log_level = logging.ERROR
        
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    
    # Print logo
    if not args.quiet:
        print_logo()
        
    # Parse headers
    headers = {}
    if args.header:
        for header in args.header:
            key, value = header.split(":", 1)
            headers[key.strip()] = value.strip()
            
    # Parse cookies
    cookies = {}
    if args.cookie:
        for cookie in args.cookie:
            key, value = cookie.split("=", 1)
            cookies[key.strip()] = value.strip()
            
    # Parse auth
    auth = None
    if args.auth:
        username, password = args.auth.split(":", 1)
        auth = (username, password)
        
    # Parse proxy - can be a single proxy URL or a file path
    proxy = None
    if args.proxy:
        # Check if it's a file path
        if os.path.isfile(args.proxy):
            proxy = args.proxy  # Pass the file path directly
        else:
            # Treat as a single proxy URL
            proxy = {"http": args.proxy, "https": args.proxy}
        
    # Parse file extensions
    download_extensions = args.filetype.split(",") if args.filetype else None
    exclude_extensions = args.exclude.split(",") if args.exclude else None
    
    # Parse URL patterns
    exclude_urls = args.exclude_url.split(",") if args.exclude_url else None
    include_urls = args.include_url.split(",") if args.include_url else None
    
    # Parse click elements
    click_elements = args.click_elements.split(",") if args.click_elements else None
    
    # Check if Playwright is available for dynamic scraping
    if args.dynamic != "never" and not PLAYWRIGHT_AVAILABLE:
        logging.warning("Playwright not available. Dynamic scraping will be disabled.")
        logging.warning("Install with: pip install playwright && playwright install")
        args.dynamic = "never"
        
    # Create output directory if it doesn't exist
    os.makedirs(args.output, exist_ok=True)
    
    # Create Siphon instance
    siphon_instance = Siphon(
        base_url=args.url,
        output_dir=args.output,
        max_depth=args.depth,
        delay=args.delay,
        max_urls=args.max_urls,
        timeout=args.timeout,
        user_agent=args.user_agent,
        verify_ssl=not args.no_verify_ssl,
        headers=headers,
        cookies=cookies,
        auth=auth,
        proxy=proxy,
        crawl_only=args.crawl_only,
        download_extensions=download_extensions,
        exclude_extensions=exclude_extensions,
        exclude_urls=exclude_urls,
        include_urls=include_urls,
        dynamic_mode=args.dynamic,
        test_proxies_on_start=args.test_proxies,
        max_threads=args.threads,
        verbose=args.verbose
    )
    
    try:
        # Start crawling
        siphon_instance.crawl()
        
        # Print summary
        if not args.quiet:
            print("\n" + "="*60)
            print("CRAWL SUMMARY")
            print("="*60)
            print(f"URLs visited: {len(siphon_instance.visited_urls)}")
            print(f"Files discovered: {len(siphon_instance.discovered_files)}")
            print(f"Files downloaded: {len(siphon_instance.downloaded_files)}")
            if siphon_instance.downloaded_files:
                print(f"Output directory: {siphon_instance.output_dir}")
            print("="*60)
            
    except KeyboardInterrupt:
        logging.warning("Crawl interrupted by user")
    finally:
        siphon_instance.close()
        
if __name__ == "__main__":
    main()
