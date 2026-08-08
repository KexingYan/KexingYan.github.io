#!/usr/bin/env python3
"""Read-only, conservative post-deployment verification for kexingyan.com."""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from html.parser import HTMLParser
from typing import Mapping
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin, urlparse, urlunparse
from urllib.request import HTTPRedirectHandler, Request, build_opener
from xml.etree import ElementTree


USER_AGENT = "KexingYan-DeploymentVerifier/1.0 (+https://kexingyan.com/)"
MAX_REQUESTS = 20
MAX_BODY_BYTES = 2_500_000


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):  # noqa: ANN001
        return None


class MetadataParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.canonicals: list[str] = []
        self.properties: dict[str, list[str]] = {}
        self.urls: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = dict(attrs)
        if tag == "link" and "canonical" in (values.get("rel") or "").split():
            self.canonicals.append((values.get("href") or "").strip())
        if tag == "meta":
            prop = (values.get("property") or "").strip().lower()
            content = (values.get("content") or "").strip()
            if prop and content:
                self.properties.setdefault(prop, []).append(content)
                if prop in {"og:url", "og:image", "og:image:secure_url"}:
                    self.urls.append(content)
        for attribute in ("href", "src"):
            value = (values.get(attribute) or "").strip()
            if value:
                self.urls.append(value)


@dataclass
class Response:
    url: str
    status: int | None
    headers: Mapping[str, str]
    body: bytes
    network_error: str | None = None


@dataclass
class Result:
    status: str
    check: str
    detail: str


class Verifier:
    def __init__(self, base_url: str, timeout: float) -> None:
        self.base_url = normalize_base_url(base_url)
        self.timeout = timeout
        self.opener = build_opener(NoRedirect())
        self.request_count = 0
        self.cache: dict[str, Response] = {}
        self.results: list[Result] = []

    def add(self, status: str, check: str, detail: str) -> None:
        self.results.append(Result(status, check, detail))

    def fetch(self, path_or_url: str) -> Response:
        url = (
            path_or_url
            if urlparse(path_or_url).scheme
            else urljoin(f"{self.base_url}/", path_or_url.lstrip("/"))
        )
        if url in self.cache:
            return self.cache[url]
        if self.request_count >= MAX_REQUESTS:
            response = Response(url, None, {}, b"", "request budget exhausted")
            self.cache[url] = response
            return response
        last_error: str | None = None
        for attempt in range(2):
            if self.request_count >= MAX_REQUESTS:
                last_error = "request budget exhausted"
                break
            self.request_count += 1
            request = Request(
                url,
                headers={"User-Agent": USER_AGENT, "Accept": "*/*"},
                method="GET",
            )
            try:
                with self.opener.open(request, timeout=self.timeout) as opened:
                    body = opened.read(MAX_BODY_BYTES + 1)
                    response = Response(
                        url,
                        opened.status,
                        dict(opened.headers.items()),
                        body,
                    )
                    self.cache[url] = response
                    return response
            except HTTPError as exc:
                body = exc.read(MAX_BODY_BYTES + 1)
                response = Response(
                    url,
                    exc.code,
                    dict(exc.headers.items()),
                    body,
                )
                self.cache[url] = response
                return response
            except (URLError, TimeoutError, OSError) as exc:
                last_error = f"{type(exc).__name__}: {exc}"
                if attempt == 0 and self.request_count < MAX_REQUESTS:
                    continue
                break
        response = Response(url, None, {}, b"", last_error or "network failure")
        self.cache[url] = response
        return response

    def expect_response(
        self,
        label: str,
        response: Response,
        status: int,
        content_types: tuple[str, ...] = (),
    ) -> bool:
        if response.network_error:
            self.add("NOT CHECKED", label, response.network_error)
            return False
        if len(response.body) > MAX_BODY_BYTES:
            self.add("FAIL", label, "response exceeded the 2.5 MB safety limit")
            return False
        if response.status != status:
            note = ""
            if response.status in {403, 429}:
                note = "; one ordinary request does not establish crawler/WAF policy"
            self.add("FAIL", label, f"HTTP {response.status}, expected {status}{note}")
            return False
        content_type = header(response, "Content-Type").split(";", 1)[0].lower()
        if content_types and content_type not in content_types:
            self.add(
                "FAIL",
                label,
                f"Content-Type {content_type or '(missing)'}, expected {content_types}",
            )
            return False
        self.add("PASS", label, f"HTTP {status}; {content_type or 'type not asserted'}")
        return True

    def run(self) -> list[Result]:
        homepage = self.fetch("/")
        research = self.fetch("/research/microloan-quantity-size/")
        paper = self.fetch("/papers/the-quantity-and-size-of-microloans.pdf")
        robots = self.fetch("/robots.txt")
        sitemap = self.fetch("/sitemap.xml")
        llms = self.fetch("/llms.txt")
        unknown_path = "/a-definitely-nonexistent-deployment-test-path"
        unknown = self.fetch(unknown_path)

        home_ok = self.expect_response("homepage", homepage, 200, ("text/html",))
        research_ok = self.expect_response("research page", research, 200, ("text/html",))
        self.expect_response("paper PDF", paper, 200, ("application/pdf",))
        self.expect_response("robots.txt", robots, 200, ("text/plain",))
        sitemap_ok = self.expect_response(
            "sitemap.xml", sitemap, 200, ("application/xml", "text/xml")
        )
        self.expect_response("llms.txt", llms, 200, ("text/plain",))
        self.expect_response("unknown route is a real 404", unknown, 404, ("text/html",))

        expected_research = f"{self.base_url}/research/microloan-quantity-size/"
        for path in ("/papers", "/papers/"):
            response = self.fetch(path)
            label = f"redirect {path}"
            if response.network_error:
                self.add("NOT CHECKED", label, response.network_error)
                continue
            location = header(response, "Location")
            resolved = urljoin(response.url, location)
            if response.status == 301 and resolved == expected_research:
                self.add("PASS", label, f"301 -> {resolved}")
            else:
                self.add(
                    "FAIL",
                    label,
                    f"HTTP {response.status}; Location {location or '(missing)'}",
                )

        expected_pages = {
            "/": (homepage, f"{self.base_url}/", "Kexing Yan", home_ok),
            "/research/microloan-quantity-size/": (
                research,
                expected_research,
                "Student working paper",
                research_ok,
            ),
        }
        preview_urls: set[str] = set()
        for path, (response, expected_canonical, identity, usable) in expected_pages.items():
            if not usable:
                self.add("NOT CHECKED", f"HTML metadata {path}", "page unavailable")
                continue
            text = response.body.decode("utf-8", errors="replace")
            parser = MetadataParser()
            parser.feed(text)
            if parser.canonicals == [expected_canonical]:
                self.add("PASS", f"canonical {path}", expected_canonical)
            else:
                self.add("FAIL", f"canonical {path}", repr(parser.canonicals))
            if identity in text:
                self.add("PASS", f"identity text {path}", identity)
            else:
                self.add("FAIL", f"identity text {path}", f"missing {identity!r}")
            local_exposure = [
                value for value in parser.urls
                if "localhost" in value.lower() or "127.0.0.1" in value
            ]
            if local_exposure:
                self.add("FAIL", f"no local URLs {path}", repr(local_exposure))
            else:
                self.add("PASS", f"no local URLs {path}", "none found")
            images = parser.properties.get("og:image", [])
            if len(images) == 1:
                preview_urls.add(images[0])
            else:
                self.add("FAIL", f"Open Graph image {path}", repr(images))

        for preview_url in sorted(preview_urls):
            preview = self.fetch(preview_url)
            self.expect_response(
                f"Open Graph asset {preview_url}", preview, 200, ("image/png", "image/jpeg")
            )

        if sitemap_ok:
            try:
                root = ElementTree.fromstring(sitemap.body)
                namespace = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}
                locations = {
                    (node.text or "").strip()
                    for node in root.findall(".//sm:loc", namespace)
                }
                required = {
                    f"{self.base_url}/",
                    expected_research,
                    f"{self.base_url}/papers/the-quantity-and-size-of-microloans.pdf",
                }
                if required <= locations:
                    self.add("PASS", "sitemap required URLs", f"{len(locations)} URLs")
                else:
                    self.add("FAIL", "sitemap required URLs", repr(sorted(required - locations)))
            except ElementTree.ParseError as exc:
                self.add("FAIL", "sitemap XML parsing", str(exc))

        for path in (
            "/docs/deployment-readiness.md",
            "/scripts/site_dates.json",
            "/README.md",
        ):
            response = self.fetch(path)
            label = f"internal file is absent {path}"
            if response.network_error:
                self.add("NOT CHECKED", label, response.network_error)
            elif response.status != 404:
                self.add("FAIL", label, f"HTTP {response.status}, expected 404")
            else:
                self.add("PASS", label, "HTTP 404")

        for path in (
            "/assets/resume/Kexing-Yan-Resume-EN.pdf",
            "/assets/resume/Kexing-Yan-Resume-ZH.pdf",
        ):
            response = self.fetch(path)
            label = f"public résumé remains noindex {path}"
            if response.network_error:
                self.add("NOT CHECKED", label, response.network_error)
            elif response.status != 200:
                self.add("FAIL", label, f"HTTP {response.status}, expected 200")
            elif "noindex" not in header(response, "X-Robots-Tag").lower():
                self.add("FAIL", label, "X-Robots-Tag noindex missing")
            else:
                self.add("PASS", label, "HTTP 200; X-Robots-Tag includes noindex")

        hostname = urlparse(self.base_url).hostname
        if hostname == "kexingyan.com":
            www_url = f"https://www.kexingyan.com{unknown_path}"
            www = self.fetch(www_url)
            label = "www preserves unknown path"
            if www.network_error:
                self.add("NOT CHECKED", label, www.network_error)
            else:
                location = urljoin(www.url, header(www, "Location"))
                expected = f"https://kexingyan.com{unknown_path}"
                if www.status in {301, 308} and location == expected:
                    self.add("PASS", label, f"{www.status} -> {location}")
                else:
                    self.add(
                        "FAIL", label,
                        f"HTTP {www.status}; Location {header(www, 'Location') or '(missing)'}",
                    )
        else:
            self.add(
                "NOT CHECKED",
                "www preserves unknown path",
                "base host is not kexingyan.com",
            )
        return self.results


def header(response: Response, name: str) -> str:
    for key, value in response.headers.items():
        if key.lower() == name.lower():
            return value
    return ""


def normalize_base_url(value: str) -> str:
    parsed = urlparse(value.strip())
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError("base URL must be an absolute HTTP(S) URL")
    if parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise ValueError("base URL must not contain credentials, query, or fragment")
    path = parsed.path.rstrip("/")
    return urlunparse((parsed.scheme, parsed.netloc, path, "", "", ""))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("base_url", help="Deployment base URL, e.g. https://kexingyan.com/")
    parser.add_argument(
        "--timeout",
        type=float,
        default=10.0,
        help="Per-request timeout in seconds (default: 10)",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if not 1 <= args.timeout <= 30:
        print("ERROR: --timeout must be between 1 and 30 seconds", file=sys.stderr)
        return 2
    try:
        verifier = Verifier(args.base_url, args.timeout)
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    results = verifier.run()
    for result in results:
        print(f"{result.status:11} {result.check}: {result.detail}")
    print(f"\nRequests: {verifier.request_count}/{MAX_REQUESTS}")
    failures = [result for result in results if result.status == "FAIL"]
    not_checked = [result for result in results if result.status == "NOT CHECKED"]
    if failures:
        print(f"Deployment verification failed: {len(failures)} check(s) failed.")
        return 1
    if not_checked:
        print(
            "Deployment verification incomplete because network-dependent checks "
            f"could not run: {len(not_checked)} not checked."
        )
        return 2
    print("Deployment verification passed. This does not prove crawler or WAF compatibility.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
