"""Bounded public-page text reading. No scripts, cookies, proxies or private networks."""
from html.parser import HTMLParser
import http.client
import ipaddress
import socket
import ssl
import time
from urllib.parse import quote, urljoin, urlsplit, urlunsplit

MAX_BYTES = 1_000_000


def public_target(url):
    try:
        parsed = urlsplit(url)
        port = parsed.port or (443 if parsed.scheme == 'https' else 80)
        host = (parsed.hostname or '').encode('idna').decode('ascii')
    except (ValueError, UnicodeError) as error:
        raise ValueError('Invalid public URL') from error
    if (len(url) > 2000 or parsed.scheme not in {'http', 'https'} or not host or parsed.username is not None
            or parsed.password is not None or port not in {80, 443}
            or any(ord(c) < 33 or c == '\\' for c in url)):
        raise ValueError('Use a public HTTP(S) URL without credentials, on port 80 or 443')
    try:
        addresses = socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)
    except OSError as error:
        raise ValueError('The public hostname could not be resolved') from error
    ips = list(dict.fromkeys(entry[4][0] for entry in addresses))
    if not ips or any(not ipaddress.ip_address(ip).is_global or ipaddress.ip_address(ip).is_multicast for ip in ips):
        raise ValueError('Private, local and reserved network addresses are not allowed')
    # Use this exact validated address for the socket, preventing DNS rebinding.
    return parsed, host, port, ips[0]


class TextPage(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts, self.title, self.links = [], [], []
        self.hidden = []
        self.in_title = False

    def handle_starttag(self, tag, attrs):
        if tag in {'script', 'style', 'noscript', 'template', 'svg'}:
            self.hidden.append(tag)
        if self.hidden:
            return
        self.in_title = tag == 'title' or self.in_title
        if tag in {'p', 'div', 'br', 'li', 'h1', 'h2', 'h3', 'tr', 'section'}:
            self.parts.append('\n')
        if tag == 'a' and len(self.links) < 40:
            href = dict(attrs).get('href', '')
            if href and len(href) <= 2000:
                self.links.append(href)

    def handle_endtag(self, tag):
        if self.hidden:
            if tag == self.hidden[-1]:
                self.hidden.pop()
            return
        if tag == 'title':
            self.in_title = False
        if tag in {'p', 'div', 'li', 'h1', 'h2', 'h3', 'tr', 'section'}:
            self.parts.append('\n')

    def handle_data(self, data):
        if not self.hidden:
            (self.title if self.in_title else self.parts).append(data)


def read_public_page(url):
    started = time.monotonic()
    for _ in range(4):
        if time.monotonic() - started > 20:
            raise ValueError('Page exceeded the reader time limit')
        parsed, host, port, address = public_target(url)
        connection = http.client.HTTPConnection(host, port, timeout=8)
        try:
            raw_socket = socket.create_connection((address, port), timeout=8)
            if parsed.scheme == 'https':
                try:
                    raw_socket = ssl.create_default_context().wrap_socket(raw_socket, server_hostname=host)
                except BaseException:
                    raw_socket.close()
                    raise
            connection.sock = raw_socket
            path = quote(urlunsplit(('', '', parsed.path or '/', parsed.query, '')), safe="/:?%&=;+,$@!~*'()-._")
            connection.request('GET', path, headers={'User-Agent':'Swarmojo-Reader/1.1',
                'Accept':'text/html,text/plain', 'Accept-Encoding':'identity', 'Connection':'close'})
            response = connection.getresponse()
            if response.status in {301, 302, 303, 307, 308}:
                location = response.getheader('Location')
                if not location:
                    raise ValueError('Redirect has no destination')
                url = urljoin(url, location)
                continue
            if response.status != 200:
                raise ValueError(f'Page returned HTTP {response.status}')
            kind = response.headers.get_content_type()
            if kind not in {'text/html', 'text/plain', 'application/xhtml+xml'}:
                raise ValueError('The reader supports HTML and plain text pages only')
            if response.getheader('Content-Encoding', 'identity').lower() != 'identity':
                raise ValueError('Compressed responses are not supported by this bounded reader')
            raw = bytearray()
            while True:
                if time.monotonic() - started > 20:
                    raise ValueError('Page exceeded the reader time limit')
                chunk = response.read1(min(65536, MAX_BYTES + 1 - len(raw)))
                if not chunk:
                    break
                raw.extend(chunk)
                if len(raw) > MAX_BYTES:
                    raise ValueError('Page exceeds the 1 MB reader limit')
            charset = response.headers.get_content_charset() or 'utf-8'
            try:
                decoded = raw.decode(charset, errors='replace')
            except LookupError:
                decoded = raw.decode('utf-8', errors='replace')
            page = TextPage()
            if kind == 'text/plain':
                page.parts = [decoded]
            else:
                page.feed(decoded)
            text = '\n'.join(' '.join(line.split()) for line in ''.join(page.parts).splitlines() if line.strip())
            links = []
            for href in page.links:
                try:
                    target = urljoin(url, href)
                    parsed_link = urlsplit(target)
                    if (len(target) <= 2000 and parsed_link.scheme in {'http', 'https'}
                            and parsed_link.hostname and not parsed_link.username and not parsed_link.password
                            and target not in links):
                        links.append(target)
                except ValueError:
                    continue
            return {'url':url, 'title':''.join(page.title).strip()[:300] or host,
                    'content':text[:20000], 'truncated':len(text) > 20000, 'links':links}
        except (OSError, http.client.HTTPException) as error:
            raise ValueError('Public page request failed or timed out') from error
        finally:
            connection.close()
    raise ValueError('Page exceeded the redirect limit')
