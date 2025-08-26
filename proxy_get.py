#!/usr/bin/env python3
# Part of the Siphon - Web Data Extraction Tool
import requests
import concurrent.futures
import time
import re
import signal
import threading
import argparse

PROXY_URLS = [ 
    # High-quality curated lists
    'https://raw.githubusercontent.com/proxifly/free-proxy-list/refs/heads/main/proxies/all/data.txt',
    'https://raw.githubusercontent.com/vakhov/fresh-proxy-list/refs/heads/master/proxylist.txt',
    'https://raw.githubusercontent.com/MuRongPIG/Proxy-Master/refs/heads/main/http_checked.txt',
    
    # Additional reliable sources
    'https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/http.txt',
    'https://raw.githubusercontent.com/ShiftyTR/Proxy-List/master/http.txt',
    'https://raw.githubusercontent.com/monosans/proxy-list/main/proxies/http.txt',
    'https://raw.githubusercontent.com/jetkai/proxy-list/main/online-proxies/txt/proxies-http.txt',
    'https://raw.githubusercontent.com/clarketm/proxy-list/master/proxy-list-raw.txt',
    'https://raw.githubusercontent.com/sunny9577/proxy-scraper/master/proxies.txt',
    'https://raw.githubusercontent.com/UserR3X/proxy-list/main/online/http.txt',
    
    # SOCKS proxies
    'https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/socks4.txt',
    'https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/socks5.txt',
    'https://raw.githubusercontent.com/monosans/proxy-list/main/proxies/socks4.txt',
    'https://raw.githubusercontent.com/monosans/proxy-list/main/proxies/socks5.txt',
    'https://raw.githubusercontent.com/jetkai/proxy-list/main/online-proxies/txt/proxies-socks4.txt',
    'https://raw.githubusercontent.com/jetkai/proxy-list/main/online-proxies/txt/proxies-socks5.txt',
]

MAX_WORKING_PROXIES = 50
shutdown_flag = threading.Event()

def handle_sigint(signum, frame):
    print("\n[!] Ctrl+C detected. Stopping proxy check and saving results...")
    shutdown_flag.set()

signal.signal(signal.SIGINT, handle_sigint)

def download_proxy_list(url):
    try:
        response = requests.get(url, timeout=10)
        lines = response.text.strip().split('\n')
        proxies = [line.strip() for line in lines if line.strip() and ':' in line]
        print(f"Downloaded {len(proxies)} proxies from {url}")
        return proxies
    except Exception as e:
        print(f"Failed to download from {url}: {e}")
        return []

def detect_proxy_type(proxy_line):
    """Detect proxy type from the proxy line"""
    proxy_line = proxy_line.lower().strip()
    if proxy_line.startswith('socks5://'):
        return 'socks5'
    elif proxy_line.startswith('socks4://'):
        return 'socks4' 
    elif proxy_line.startswith('https://'):
        return 'https'
    elif proxy_line.startswith('http://'):
        return 'http'
    elif proxy_line.startswith('socks://'):
        return 'socks5'  # Default socks to socks5
    else:
        # No prefix, assume HTTP
        return 'http'

def clean_proxy(proxy):
    """Clean and normalize proxy format"""
    proxy = proxy.strip()
    if not proxy:
        return None, None
        
    # Detect proxy type before cleaning
    proxy_type = detect_proxy_type(proxy)
    
    # Remove protocol prefixes
    proxy = re.sub(r'^https?://', '', proxy)
    proxy = re.sub(r'^socks[45]?://', '', proxy)
    proxy = re.sub(r'^socks://', '', proxy)
    proxy = re.sub(r'/.*$', '', proxy)
    
    # Validate format
    if ':' not in proxy:
        return None, None
    
    try:
        host, port = proxy.split(':', 1)
        port = int(port)
        if not (1 <= port <= 65535):
            return None, None
        if not host or len(host) < 3:
            return None, None
    except (ValueError, IndexError):
        return None, None
        
    return proxy, proxy_type

def test_proxy(proxy, timeout=3):
    """Enhanced proxy testing with multiple validation methods"""
    clean_result = clean_proxy(proxy)
    if not clean_result[0]:
        return None
    
    clean, proxy_type = clean_result
    
    try:
        start_time = time.time()
        
        # Configure proxy based on type
        if proxy_type in ['socks4', 'socks5']:
            proxies = {
                'http': f'{proxy_type}://{clean}',
                'https': f'{proxy_type}://{clean}'
            }
        else:
            proxies = {
                'http': f'http://{clean}',
                'https': f'http://{clean}'
            }
        
        # Test with multiple endpoints for better reliability
        test_urls = [
            'http://httpbin.org/ip',
            'http://icanhazip.com/',
            'http://ip-api.com/json/'
        ]
        
        for test_url in test_urls:
            try:
                response = requests.get(test_url, proxies=proxies, timeout=timeout)
                response_time = time.time() - start_time
                
                if response.status_code == 200 and len(response.text.strip()) > 5:
                    # Additional validation - check if we got a valid IP response
                    response_text = response.text.strip()
                    if ('.' in response_text and len(response_text) < 100) or 'ip' in response_text.lower():
                        print(f"{clean} [{proxy_type}] - Success {response_time:.3f}s")
                        return (clean, response_time, proxy_type)
                break
            except:
                continue
                
    except Exception as e:
        pass
    
    return None

def main():
    parser = argparse.ArgumentParser(description="Proxy checker with threading and timeout options.")
    parser.add_argument('--threads', type=int, default=5, help='Number of threads for proxy testing (default: 5)')
    args = parser.parse_args()
    all_proxies = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
        download_futures = [executor.submit(download_proxy_list, url) for url in PROXY_URLS]
        for future in concurrent.futures.as_completed(download_futures):
            proxies = future.result()
            all_proxies.extend(proxies)
    unique_proxies = list(set(all_proxies))
    print(f"Total unique proxies to test: {len(unique_proxies)}")
    working_proxies = []
    working_lock = threading.Lock()
    def test_and_collect(proxy):
        if shutdown_flag.is_set():
            return None
        result = test_proxy(proxy, timeout=3)
        if result:
            with working_lock:
                if len(working_proxies) < MAX_WORKING_PROXIES:
                    working_proxies.append(result)
        return result
    try:
        with concurrent.futures.ThreadPoolExecutor(max_workers=args.threads) as executor:
            futures = [executor.submit(test_and_collect, proxy) for proxy in unique_proxies]
            for future in concurrent.futures.as_completed(futures):
                if shutdown_flag.is_set():
                    break
                with working_lock:
                    if len(working_proxies) >= MAX_WORKING_PROXIES:
                        print(f"[+] Reached {MAX_WORKING_PROXIES} working proxies. Stopping early.")
                        shutdown_flag.set()
                        break
    except KeyboardInterrupt:
        print("\n[!] Interrupted by user. Saving found proxies...")
        shutdown_flag.set()
    working_proxies.sort(key=lambda x: x[1])  # Sort by response time
    top_n = working_proxies[:MAX_WORKING_PROXIES]
    
    # Save proxies with type information
    with open('proxies.txt', 'w') as f:
        for proxy_info in top_n:
            if len(proxy_info) >= 3:
                proxy, response_time, proxy_type = proxy_info[:3]
                f.write(f"{proxy}\n")
            else:
                proxy, response_time = proxy_info[:2]
                f.write(f"{proxy}\n")
    
    # Save detailed proxy info
    with open('proxies_detailed.txt', 'w') as f:
        f.write("# Format: proxy_address response_time(s) type\n")
        for proxy_info in top_n:
            if len(proxy_info) >= 3:
                proxy, response_time, proxy_type = proxy_info[:3]
                f.write(f"{proxy} {response_time:.3f}s {proxy_type}\n")
            else:
                proxy, response_time = proxy_info[:2]
                f.write(f"{proxy} {response_time:.3f}s http\n")
    
    print(f"Found {len(working_proxies)} working proxies, saved top {len(top_n)} to proxies.txt")
    print(f"Detailed info saved to proxies_detailed.txt")

if __name__ == "__main__":
    main()
