#!/usr/bin/env python3
"""
HTTPing - A Python utility that mimics httping functionality
Measures HTTP response times and displays specified headers
"""

import argparse
import re
import sys
import time
import urllib.parse
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import requests
import socket


# ANSI color codes
class Colors:
    RED = '\033[91m'
    BRIGHT_RED = '\033[31m'
    YELLOW = '\033[93m'
    BRIGHT_YELLOW = '\033[33m'
    GREEN = '\033[92m'
    BRIGHT_GREEN = '\033[32m'
    CYAN = '\033[96m'
    BLUE = '\033[94m'
    MAGENTA = '\033[95m'
    RESET = '\033[0m'


class HTTPing:
    def __init__(self, site: str, headers: Optional[List[str]] = None, interval: float = 1.0, timeout: float = 5.0, quiet: bool = False, bell: bool = False, count: Optional[int] = None):
        self.site = site
        self.headers = headers or []
        self.interval = interval
        self.timeout = timeout
        self.quiet = quiet
        self.bell = bell
        self.count = count
        self.session = requests.Session()
        # Set custom User-Agent
        self.session.headers.update({'User-Agent': 'httping/mad'})
        # Track previous body length for change detection
        self.previous_body_length = None
        
    def parse_headers(self) -> List[re.Pattern]:
        """Parse header regex patterns from command line input"""
        patterns = []
        for header_pattern in self.headers:
            try:
                # Compile regex pattern for case-insensitive matching
                pattern = re.compile(header_pattern, re.IGNORECASE)
                patterns.append(pattern)
            except re.error as e:
                print(f"Error: Invalid regex pattern '{header_pattern}': {e}")
                sys.exit(1)
        return patterns
    
    def format_bytes(self, bytes_count: int) -> str:
        """Format bytes in human-readable format (B, KB, MB, GB, etc.)"""
        if bytes_count == 0:
            return "0B"
        
        units = ['B', 'KB', 'MB', 'GB', 'TB']
        size = float(bytes_count)
        unit_index = 0
        
        while size >= 1024 and unit_index < len(units) - 1:
            size /= 1024
            unit_index += 1
        
        if unit_index == 0:
            return f"{int(size)}{units[unit_index]}"
        else:
            return f"{size:.1f}{units[unit_index]}"
    
    def make_request(self) -> Tuple[int, float, float, Dict[str, str], int]:
        """Make HTTP request and return status, duration, headers, and body_length"""
        parsed_url = urllib.parse.urlparse(self.site)
        host = parsed_url.hostname
        port = parsed_url.port or (443 if parsed_url.scheme == 'https' else 80)
        
        
        # Measure full request duration
        start_time = time.time()
        try:
            response = self.session.get(self.site, timeout=self.timeout, allow_redirects=False)
            duration = (time.time() - start_time) * 1000  # Convert to milliseconds
            
            # Extract headers and body length
            headers = dict(response.headers)
            body_length = len(response.content)
            
            return response.status_code, duration, headers, body_length
        except Exception as e:
            duration = (time.time() - start_time) * 1000
            return -1, duration, {}, 0
    
    def filter_headers(self, headers: Dict[str, str], patterns: List[re.Pattern]) -> Dict[str, str]:
        """Filter headers based on regex patterns"""
        if not patterns:
            return {}
        
        filtered = {}
        for header_name, header_value in headers.items():
            for pattern in patterns:
                if pattern.search(header_name):
                    filtered[header_name] = header_value
                    break
        return filtered
    
    
    def get_status_color(self, status: int, body_length_change: float = 0.0) -> str:
        """Get color code based on HTTP status and body length change"""
        if status == -1:  # Timeout or connection error
            return Colors.RED
        elif status >= 400:  # Client/Server errors
            return Colors.RED
        elif 300 <= status <= 399:  # Redirects - always yellow
            return Colors.YELLOW
        elif body_length_change > 0.10:  # Large body length change (>10%)
            return Colors.YELLOW
        else:  # 200-299 Success - no color change
            return Colors.RESET
    
    def format_output(self, status: int, duration: float, 
                     filtered_headers: Dict[str, str], body_length: int, body_length_change: float = 0.0) -> str:
        """Format the output line with color coding"""
        # Format site (truncate if too long)
        site_display = self.site[:50] + "..." if len(self.site) > 50 else self.site
        
        # Format status
        status_str = str(status) if status != -1 else "ERROR"
        
        # Format times
        duration_str = f"{duration:.2f}ms"

        timestamp = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
        
        # Format headers
        header_parts = []
        for name, value in filtered_headers.items():
            header_parts.append(f"{name}: {value}")
        headers_str = ", ".join(header_parts) if header_parts else ""
        
        # Format output with site prefix for each value
        output_parts = [
            f"{status_str}",
            f"length={self.format_bytes(body_length)}",
            f"total={duration_str}"
        ]
        
        if headers_str:
            output_parts.append(headers_str)
        
        # Add message if large body length change
        if body_length_change > 0.10:
            change_percent = body_length_change * 100
            output_parts.append(f"large body length change (+{change_percent:.1f}%)")
        
        # Apply color coding
        color = self.get_status_color(status, body_length_change)
        output = f"{timestamp} {site_display}: {', '.join(output_parts)}"
        return f"{color}{output}{Colors.RESET}"
    
    def run_once(self) -> None:
        """Run a single HTTP ping"""
        patterns = self.parse_headers()
        status, duration, headers, body_length = self.make_request()
        
        # Calculate body length change percentage
        body_length_change = 0.0
        if self.previous_body_length is not None and self.previous_body_length > 0:
            change = abs(body_length - self.previous_body_length)
            body_length_change = change / self.previous_body_length
        
        filtered_headers = self.filter_headers(headers, patterns)
        
        output = self.format_output(status, duration, filtered_headers, body_length, body_length_change)
        print(output)
        
        # Print bell character on any failure or large body length change unless quiet mode is enabled
        if not self.quiet and (self.is_failure(status) or body_length_change > 0.10):
            print('\a', end='', flush=True)
        
        # Update previous body length for next iteration
        self.previous_body_length = body_length
    
    def is_failure(self, status: int) -> bool:
        """Check if status code represents a failure that should trigger bell"""
        return status >= 400  # Only HTTP errors 400+ (client and server errors)
    
    def run_verbose(self) -> None:
        """Run a single request and show all headers"""
        patterns = self.parse_headers()
        status, duration, headers, body_length = self.make_request()
        
        print(f"HTTPing {self.site}")
        print("-" * 80)
        
        # Format site (truncate if too long)
        site_display = self.site[:50] + "..." if len(self.site) > 50 else self.site
        
        # Format status
        status_str = str(status) if status != -1 else "ERROR"
        
        # Format times
        duration_str = f"{duration:.2f}ms"
        
        # Show basic info with color coding
        color = self.get_status_color(status)
        basic_info = f"{site_display}: {status_str}, length={self.format_bytes(body_length)}, request_time={duration_str}"
        print(f"{color}{basic_info}{Colors.RESET}")
        print()
        
        # Show all headers
        if headers:
            print("Headers:")
            for name, value in sorted(headers.items()):
                print(f"  {name}: {value}")
        else:
            print("No headers received")
    
    def run_continuous(self) -> None:
        """Run continuous HTTP pings at specified interval"""
        if self.count is not None:
            print(f"HTTPing {self.site} every {self.interval}s ({self.count} times)")
        else:
            print(f"HTTPing {self.site} every {self.interval}s (Ctrl+C to stop)")
        print("-" * 80)
        
        try:
            ping_count = 0
            while True:
                self.run_once()
                ping_count += 1
                if self.count is not None and ping_count >= self.count:
                    break
                time.sleep(self.interval)
        except KeyboardInterrupt:
            print("\nStopped.")


def main():
    parser = argparse.ArgumentParser(
        description="HTTPing - HTTP response time measurement tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s https://example.com
  %(prog)s https://example.com -d 0.5
  %(prog)s https://example.com -H "server,content-type"
  %(prog)s https://example.com -H "server" -H "content-type"
  %(prog)s https://example.com -v
  %(prog)s https://example.com -t 5.0
  %(prog)s https://example.com -d 0.1 -t 0.5
  %(prog)s https://example.com -q
        """
    )
    
    parser.add_argument(
        'site',
        help='URL to ping (e.g., https://example.com)'
    )
    
    parser.add_argument(
        '-i', '--interval',
        type=float,
        default=1.0,
        help='Interval between requests in seconds (default: 1.0)'
    )
    
    parser.add_argument(
        '-H', '--headers',
        action='append',
        help='Header names to display (regex patterns, comma-separated). Can be used multiple times.'
    )
    
    parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='Show all headers from a single request instead of continuous pinging'
    )
    
    parser.add_argument(
        '-t', '--timeout',
        type=float,
        default=5.0,
        help='Request timeout in seconds (default: 5.0)'
    )
    
    parser.add_argument(
        '-d', '--delay',
        type=float,
        default=1.0,
        help='Delay between requests in seconds (default: 1.0, use smaller values for faster pings)'
    )
    
    parser.add_argument(
        '-q', '--quiet',
        action='store_true',
        help='Disable bell alerts on failures'
    )

    parser.add_argument(
        '-b', '--bell',
        type=int,
        help='Reverse the behavior of the bell (bell on success)'
    )
    
    parser.add_argument(
        '-c', '--count',
        type=int,
        help='Stop after sending this many pings'
    )
    
    args = parser.parse_args()
    
    # Flatten headers if provided
    headers = []
    if args.headers:
        for header_group in args.headers:
            headers.extend([h.strip() for h in header_group.split(',')])
    
    # Validate site URL
    if not args.site.startswith(('http://', 'https://')):
        args.site = 'https://' + args.site
    
    # Create and run HTTPing instance
    httping = HTTPing(args.site, headers, args.delay, args.timeout, args.quiet, args.bell, args.count)
    
    if args.verbose:
        httping.run_verbose()
    else:
        httping.run_continuous()


if __name__ == '__main__':
    main()
