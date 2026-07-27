# HTTPing

HTTP response time measurement tool similar to `ping` but for HTTP requests.

## Installation

```bash
# Using Nix
nix run github:cransom/httping# -- <options>
#or
nix profile add github:cransom/httping#
```

## Usage

```bash
httping <url> [options]
```

## Options

- `-d, --delay`: Delay between requests in seconds (default: 1.0)
- `-t, --timeout`: Request timeout in seconds (default: 5.0)
- `-c, --count`: Stop after N pings
- `-H, --headers`: Display specific headers (regex patterns, comma-separated)
- `-v, --verbose`: Show all headers from a single request
- `-q, --quiet`: Disable bell alerts on failures
- `--dns SERVER`: Re-resolve DNS on every request using the specified DNS server (e.g., 1.1.1.1). Shows the connected IP in output. Without this option, the system resolver (and connection pool) is used.

## Examples

```bash
httping https://example.com
httping https://example.com -c 5
httping https://example.com -d 0.5 -H "server,content-type"
httping https://example.com -v
httping https://example.com --dns 8.8.8.8
httping https://example.com --dns 1.1.1.1
```

## Output

Each ping shows:
- HTTP status code
- Response body length
- TCP connection time / total request time
- Selected headers (if specified)
- Color coding: red for errors, yellow for redirects/large body changes

