"""Read-only capture for Xbox cloud-play session negotiation hosts.

Only TLS connections whose SNI contains gssv-play and ends in xboxlive.com are
decrypted. Every other XboxPcApp connection passes through untouched. Logs
exclude headers, tokens, query values, and bodies; the local gitignored flow
file is analyzed later with credential-safe tooling.
"""

from urllib.parse import urlsplit

from mitmproxy import ctx, http, tls


def is_cloud_play_host(host: str) -> bool:
    normalized = host.lower().rstrip(".")
    return "gssv-play" in normalized and normalized.endswith(".xboxlive.com")


class XboxCloudSessionCapture:
    def tls_clienthello(self, data: tls.ClientHelloData) -> None:
        sni = (data.client_hello.sni or "").lower()
        if not is_cloud_play_host(sni):
            data.ignore_connection = True

    def request(self, flow: http.HTTPFlow) -> None:
        host = flow.request.pretty_host.lower()
        if not is_cloud_play_host(host):
            return
        parts = urlsplit(flow.request.pretty_url)
        ctx.log.alert(
            f"[xbx-cloud-request] host={host} method={flow.request.method} "
            f"path={parts.path} query_keys={sorted(flow.request.query.keys())} "
            f"body_bytes={len(flow.request.raw_content or b'')}"
        )

    def response(self, flow: http.HTTPFlow) -> None:
        host = flow.request.pretty_host.lower()
        if not is_cloud_play_host(host):
            return
        content_type = flow.response.headers.get("content-type", "")
        ctx.log.alert(
            f"[xbx-cloud-response] host={host} "
            f"status={flow.response.status_code} "
            f"content_type={content_type!r} "
            f"body_bytes={len(flow.response.raw_content or b'')}"
        )


addons = [XboxCloudSessionCapture()]
