# Siphon - Advanced Web Scraper with Dynamic Content Support

Siphon is a powerful web crawler and file downloader that can extract content from both static and dynamic websites. It's designed to discover and download files even when they're hidden behind JavaScript interactions, custom UI components, or dynamically generated content.

## Features

- **Static Scraping**: Traditional HTML parsing with BeautifulSoup
- **Dynamic Scraping**: Headless browser automation with Playwright
- **Hybrid Mode**: Automatically switches between static and dynamic as needed
- **Advanced Link Extraction**: Finds links in HTML attributes, JavaScript, and more
- **Interactive Element Detection**: Automatically finds and clicks download buttons
- **Network Traffic Monitoring**: Captures file downloads from XHR/fetch requests
- **Customizable Filters**: Target specific file types or URL patterns
- **Proxy Support**: Use proxies for distributed crawling

## Installation

### Basic Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/siphon.git
cd siphon

# Install basic dependencies
pip install -r requirements.txt
```

### Full Installation (with Dynamic Scraping)

```bash
# Install basic dependencies
pip install -r requirements.txt

# Install Playwright
playwright install
```

## Usage

### Basic Usage

```bash
# Download all PDF files from a website (static scraping)
python siphon.py https://example.com --filetype pdf,doc,docx

# Crawl a site and list all files without downloading (discovery mode)
python siphon.py https://example.com --crawl-only

# Download specific file types with depth 3
python siphon.py https://example.com --filetype md,mdc,pdf,doc --depth 3
```

### Dynamic Scraping

```bash
# Force dynamic scraping for JavaScript-heavy sites
python siphon.py https://example.com --dynamic always --filetype md,mdc

# Use dynamic scraping only when needed (auto mode)
python siphon.py https://example.com --dynamic auto --filetype md,mdc

# Run with visible browser (for debugging)
python siphon.py https://example.com --dynamic always --no-headless
```

### Advanced Options

```bash
# Click specific elements on the page
python siphon.py https://example.com --dynamic always --click-elements ".download-button,#export-pdf"

# Set custom headers and cookies
python siphon.py https://example.com --header "Referer:https://example.com" --cookie "session=abc123"

# Use a proxy
python siphon.py https://example.com --proxy "http://user:pass@proxy.example.com:8080"
```

## Dynamic Scraping Modes

Siphon supports three dynamic scraping modes:

1. **auto** (default): Starts with static scraping and switches to dynamic if needed
2. **always**: Always uses dynamic scraping with a headless browser
3. **never**: Only uses static scraping (fastest but may miss dynamic content)

## How It Works

### Static Scraping

The static scraper uses BeautifulSoup to parse HTML and extract links from:
- Standard `<a href>` tags
- Various attributes like `onclick`, `data-download`, etc.
- Inline JavaScript using regex patterns

### Dynamic Scraping

The dynamic scraper uses Playwright to:
1. Load the page in a headless browser
2. Wait for JavaScript to execute and render the page
3. Extract links from the rendered DOM
4. Monitor network requests for file downloads
5. Find and click elements that might trigger downloads
6. Extract URLs from executed JavaScript

### Auto Mode Logic

In auto mode, Siphon:
1. First tries static scraping
2. If no target files are found, switches to dynamic scraping
3. Combines results from both methods

## Requirements

- Python 3.7+
- BeautifulSoup4
- Requests
- Playwright (optional, for dynamic scraping)

## License

MIT

