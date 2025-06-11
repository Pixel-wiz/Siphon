# WebScraper - Professional Web Scraping Tool

A powerful, multi-threaded web scraper with proxy support, advanced content discovery, and robust encoding handling.

## Features

- **Multi-threaded crawling** with configurable depth
- **Unlimited proxy support** with automatic rotation and failover
- **Built-in proxy checker** for testing and validating proxy lists
- **Advanced content discovery** (APIs, files)
- **Multiple output formats** (JSON, CSV)
- **Selenium support** for JavaScript-heavy sites
- **Comprehensive logging** with thread identification

## Installation

```bash
pip install -r requirements.txt
```

For Selenium support (optional):
- Install Chrome/Chromium browser
- Download ChromeDriver from https://chromedriver.chromium.org/

## Proxy Checker

Test and validate proxy lists from multiple sources:

```bash
python proxy_get.py
```

The proxy checker will:
- Download proxy lists from 3 built-in sources
- Test all proxies concurrently with 3-second timeout
- Show real-time progress: `<ipaddress> - Success <responsetime>s`
- Save top 50 fastest working proxies to `proxies.txt`
- Handle various proxy formats gracefully (strips protocols, paths, etc.)

## Web Scraper Usage

Basic usage:
```bash
python webscraper.py https://example.com
```

With tested proxies:
```bash
python webscraper.py https://example.com --proxies proxies.txt
```

## Command Line Options

### Basic Options
- `url` - The URL to start crawling from (required)
- `--domain` - Limit crawl to specific domain (default: start URL domain)
- `--depth` - Maximum crawl depth (default: 3)
- `--threads` - Number of threads for crawling (default: 3)

### Proxy Options
- `--proxies` - List of proxies or URL to proxy list
- `--test-proxies` - Test and select best proxies before scraping

### Content Filtering
- `--filetype` - File extensions to filter by (e.g., html pdf doc)
- `--keywords` - Keywords or regex patterns to extract

### Discovery Modes
- `--dump-all` - Download all file types
- `--crawl-only` - List files without downloading
- `--find-apis` - Search for API endpoints and keys

### Output Options
- `--output-dir` - Output directory (default: output)
- `--format` - Output format: json or csv (default: json)
- `--raw` - Don't clean scraped data

### Advanced Options
- `--selenium` - Use Selenium for JavaScript-heavy sites

## Examples

### Test Proxies First
```bash
python proxy_get.py
python webscraper.py https://example.com --proxies proxies.txt
```

### Basic Web Scraping
```bash
python webscraper.py https://example.com --depth 2
```

### Download Specific File Types
```bash
python webscraper.py https://example.com --filetype pdf doc xlsx
```

### Find APIs and Keys
```bash
python webscraper.py https://example.com --find-apis --depth 3
```

### Crawl-Only Mode (Discovery)
```bash
python webscraper.py https://example.com --crawl-only --dump-all
```

### JavaScript-Heavy Sites
```bash
python webscraper.py https://example.com --selenium --threads 1
```

## Output Structure

The scraper creates a domain-specific folder in the output directory containing:

- `scraper.log` - Detailed crawl log
- `scraped_data_[timestamp].json` - Main scraped data
- `downloads/` - Downloaded files (when not in crawl-only mode)
- `api_discoveries_[timestamp].json` - Found API endpoints (with --find-apis)
- `discovered_files_[timestamp].json` - File list (with --crawl-only)


### Encoding Issues
The scraper handles encoding automatically, but if issues persist:
- Check the log file for specific encoding errors
- Use `--raw` flag to get unprocessed data

### Memory Issues with Large Crawls
- Reduce `--depth` parameter
- Lower `--threads` count
- Use `--crawl-only` for discovery before downloading

## Legal Notice

This tool is for authorized use only. Users are responsible for:
- Obtaining proper authorization before use
- Complying with all applicable laws and regulations
- Respecting website terms of service

