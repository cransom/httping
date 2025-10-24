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
from typing import Dict, List, Optional, Tuple
import requests
import socket


class HTTPing:
    def __init__(self, site: str, headers: Optional[List[str]] = None, interval: float = 1.0):
        self.site = site
        self.headers = headers or []
        self.interval = interval
        self.session = requests.Session()
        
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
    
    def measure_tcp_connect_time(self, host: str, port: int) -> float:
        """Measure TCP connection time"""
        start_time = time.time()
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(10)  # 10 second timeout
            sock.connect((host, port))
            sock.close()
            return (time.time() - start_time) * 1000  # Convert to milliseconds
        except Exception:
            return -1  # Connection failed
    
    def make_request(self) -> Tuple[int, float, float, Dict[str, str], int]:
        """Make HTTP request and return status, tcp_time, duration, headers, and body_length"""
        parsed_url = urllib.parse.urlparse(self.site)
        host = parsed_url.hostname
        port = parsed_url.port or (443 if parsed_url.scheme == 'https' else 80)
        
        # Measure TCP connection time
        tcp_time = self.measure_tcp_connect_time(host, port)
        
        # Measure full request duration
        start_time = time.time()
        try:
            response = self.session.get(self.site, timeout=10, allow_redirects=False)
            duration = (time.time() - start_time) * 1000  # Convert to milliseconds
            
            # Extract headers and body length
            headers = dict(response.headers)
            body_length = len(response.content)
            
            return response.status_code, tcp_time, duration, headers, body_length
        except Exception as e:
            duration = (time.time() - start_time) * 1000
            return -1, tcp_time, duration, {}, 0
    
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
    
    def format_output(self, status: int, tcp_time: float, duration: float, 
                     filtered_headers: Dict[str, str], body_length: int) -> str:
        """Format the output line"""
        # Format site (truncate if too long)
        site_display = self.site[:50] + "..." if len(self.site) > 50 else self.site
        
        # Format status
        status_str = str(status) if status != -1 else "ERROR"
        
        # Format times
        tcp_str = f"{tcp_time:.2f}ms" if tcp_time != -1 else "FAIL"
        duration_str = f"{duration:.2f}ms"
        
        # Format headers
        header_parts = []
        for name, value in filtered_headers.items():
            header_parts.append(f"{name}: {value}")
        headers_str = ", ".join(header_parts) if header_parts else ""
        
        # Format output with site prefix for each value
        output_parts = [
            f"{status_str}",
            f"length={self.format_bytes(body_length)}",
            f"tcp_time={tcp_str}",
            f"request_time={duration_str}"
        ]
        
        if headers_str:
            output_parts.append(headers_str)
        
        return f"{site_display}: {', '.join(output_parts)}"
    
    def run_once(self) -> None:
        """Run a single HTTP ping"""
        patterns = self.parse_headers()
        status, tcp_time, duration, headers, body_length = self.make_request()
        filtered_headers = self.filter_headers(headers, patterns)
        
        output = self.format_output(status, tcp_time, duration, filtered_headers, body_length)
        print(output)
    
    def run_continuous(self) -> None:
        """Run continuous HTTP pings at specified interval"""
        print(f"HTTPing {self.site} every {self.interval}s (Ctrl+C to stop)")
        print("-" * 80)
        
        try:
            while True:
                self.run_once()
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
  %(prog)s https://example.com -i 2.5
  %(prog)s https://example.com -H "server,content-type"
  %(prog)s https://example.com -H "server" -H "content-type"
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
    httping = HTTPing(args.site, headers, args.interval)
    httping.run_continuous()


if __name__ == '__main__':
    main()
