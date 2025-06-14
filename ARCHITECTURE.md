# Siphon Web Scraper - Technical Architecture

## Overview
Siphon is a sophisticated web crawling and file extraction tool built in Python. It supports both static and dynamic content scraping with advanced features like proxy rotation, multi-threading, and JavaScript-rendered page handling.

## System Architecture

### Core Components

#### 1. Main Application (`Siphon` class)
- **Purpose**: Primary orchestrator for web crawling operations
- **Key Features**:
  - Multi-threaded crawling
  - Proxy management integration
  - Dynamic/static scraping mode switching
  - File download management
  - URL filtering and validation

#### 2. Legacy WebScraper (`WebScraper` class)
- **Purpose**: Original scraping implementation (legacy)
- **Features**: Basic crawling with threading support
- **Status**: Maintained for compatibility

#### 3. Dynamic Scraping (`DynamicScraper` class)
- **Purpose**: Handle JavaScript-rendered content
- **Technology**: Playwright browser automation
- **Capabilities**:
  - Bot protection bypass
  - Interactive element detection
  - Blob/file download capture
  - Network monitoring

#### 4. Proxy Management (`ProxyManager` class)
- **Purpose**: Handle proxy rotation and failure detection
- **Features**:
  - Automatic proxy testing
  - Failed proxy removal
  - Thread-safe proxy assignment
  - Fallback to direct connection

#### 5. Rate Limiting (`RateLimiter` class)
- **Purpose**: Prevent server overload
- **Features**:
  - Adaptive delay adjustment
  - Response time monitoring
  - Status code-based throttling

#### 6. Robust Response Handling (`RobustResponse` class)
- **Purpose**: Handle various text encodings
- **Features**:
  - Multi-encoding detection
  - Fallback encoding strategies
  - Content-type analysis

## Technical Stack

### Core Dependencies
- **requests**: HTTP client library
- **BeautifulSoup4**: HTML parsing
- **playwright**: Browser automation (optional)
- **concurrent.futures**: Threading support
- **urllib.parse**: URL manipulation

### Optional Dependencies
- **selenium**: Alternative browser automation
- **chardet**: Character encoding detection

## Data Flow

```
URL Input → Siphon.crawl() → Worker Threads → URL Processing
    ↓
Static Scraping (requests + BeautifulSoup)
    ↓
Dynamic Scraping (Playwright) [if needed]
    ↓
Link Extraction & File Detection
    ↓
Download Processing → File Storage
```

## Threading Model

### Multi-threaded Architecture
- **Worker Threads**: Process URLs from shared queue
- **Thread Safety**: Locks for shared resources (visited URLs, queue, proxy assignments)
- **Load Balancing**: Round-robin proxy assignment per thread

### Synchronization Points
- `visited_lock`: Protects visited URL set
- `queue_lock`: Protects URL processing queue
- `proxy_lock`: Protects proxy manager state
- `files_lock`: Protects discovered files list

## Configuration System

### Command Line Interface
- Comprehensive argument parsing
- Support for proxy files/URLs
- Flexible file type filtering
- Dynamic scraping mode selection

### Runtime Configuration
- Adaptive rate limiting
- Proxy failure handling
- SSL verification control
- User agent rotation

## Error Handling Strategy

### Network Errors
- Automatic retry with exponential backoff
- Proxy failure detection and rotation
- Graceful degradation to direct connection

### Parsing Errors
- Robust encoding detection
- Fallback parsing strategies
- Content type validation

### Browser Automation Errors
- Playwright initialization failure handling
- Bot protection detection and bypass
- Timeout management

## Security Considerations

### Anti-Detection Measures
- User agent rotation
- Request timing variation
- Proxy rotation
- SSL verification options

### Bot Protection Handling
- Automatic detection of protection screens
- Multiple bypass strategies
- Graceful fallback mechanisms

## Performance Optimizations

### Caching
- Response caching with MD5 keys
- Visited URL tracking
- Duplicate download prevention

### Resource Management
- Streaming file downloads
- Memory-efficient content processing
- Automatic cleanup of browser resources

## Current Issue Analysis

### IndentationError at Line 2237
- **Location**: `fetch_url` method in `Siphon` class
- **Issue**: Missing indentation after `if` statement on line 2236
- **Impact**: Prevents application startup
- **Priority**: CRITICAL - blocks all functionality

### Root Cause
The error occurs in the `fetch_url` method where an `if` statement is not followed by properly indented code block, violating Python syntax requirements.

## Deployment Requirements

### System Requirements
- Python 3.7+
- Optional: Playwright browser binaries
- Network access for web crawling

### Installation Dependencies
```bash
pip install requests beautifulsoup4 lxml
# Optional for dynamic scraping:
pip install playwright
playwright install
```

## Extensibility Points

### Custom Parsers
- Plugin architecture for custom content parsing
- Configurable extraction rules

### Protocol Support
- HTTP/HTTPS with proxy support
- File:// URI handling for local content
- Blob: URI processing for dynamic content

## Monitoring and Logging

### Logging Strategy
- Thread-aware logging with unique IDs
- Configurable verbosity levels
- Progress tracking with statistics

### Performance Metrics
- URLs processed per second
- Download success rates
- Proxy performance statistics