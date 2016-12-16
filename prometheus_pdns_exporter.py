#!/usr/bin/python3 -tt
"""Fetch PowerDNS metrics from the REST API and export Prometheus metrics"""

import argparse
import http.client
import json
import re
import sys
import urllib.parse
import wsgiref

import prometheus_client as promc

_HIST_SPLIT_RE = re.compile("(.*answers)([0-9-_]*)")

_GAUGES = set([
    "powerdns_cache_entries",
    "powerdns_concurrent_queries"
    "powerdns_failed_host_entries",
    "powerdns_fd_usage",
    "powerdns_negcache_entries",
    "powerdns_nsspeeds_entries",
    "powerdns_real_memory_usage",
    "powerdns_security_status",
    "powerdns_tcp_clients",
    "powerdns_throttle_entries"
])

def _filter(all_metrics):
    stats = set()
    for stat in all_metrics:
        stats.add((stat[0], "", stat[1]))
    return stats


def _fetch(host, port, url, key):
    metrics = []
    conn = http.client.HTTPConnection(host, port)
    conn.request("GET", url, headers={"X-API-Key": key})
    resp = conn.getresponse()
    if resp.status != 200:
        sys.stderr.write("HTTP Error response: %s\n" % (resp.status))
    else:
        jsondata = json.loads(resp.read().decode())
        for metric in jsondata:
            name = "powerdns_%s" % metric["name"].replace("-", "_")
            value = metric["value"]
            metrics.append((name, value))
    return metrics


class _NoLoggingWSGIRequestHandler(wsgiref.simple_server.WSGIRequestHandler):
    def log_message(self, fmt, *args):
        pass


class _CustomCollector(object):
    # pylint: disable=too-few-public-methods,no-self-use
    """A custom collector that fetches PowerDNS metrics"""

    def __init__(self, scheme="http", host="localhost", port=8082,
                 path="/api/v1/servers/localhost/statistics", api_key=""):
        # pylint: disable=too-many-arguments

        self.scheme = scheme
        self.host = host
        self.port = port
        self.path = path
        self.api_key = api_key

    def collect(self):
        """Collect metrics and yield entries"""
        url = "%s://%s:%s%s" % (self.scheme, self.host, self.port, self.path)
        rawmetrics = _fetch(self.host, self.port, url, self.api_key)
        stats = _filter(rawmetrics)
        for sname, bucket, svalue in stats:
            # pylint: disable=redefined-variable-type
            if sname in _GAUGES:
                metric = promc.core.GaugeMetricFamily(
                    sname, "Auto-generated stat from PowerDNS API",
                    labels=["le"])
            else:
                metric = promc.core.CounterMetricFamily(
                    sname, "Auto-generated stat from PowerDNS API",
                    labels=["le"])
            if bucket:
                metric.add_metric([bucket], float(svalue))
            else:
                metric.add_metric([], float(svalue))
            yield metric


def main():
    """Main program"""
    cmdp = argparse.ArgumentParser(
        description='Fetch PowerDNS metrics and export them for Prometheus')

    cmdp.add_argument('--url', '-u', default="http://localhost:8082"
                      "/api/v1/servers/localhost/statistics",
                      help="URL to connect to (default: %(default)s")

    cmdp.add_argument('--api_key', '-k', default="", help="PowerDNS API key")
    cmdp.add_argument('--api_key_file', '-f', default="",
                      help="File to read PowerDNS API key from")
    cmdp.add_argument('--listen_host', '-l', default="localhost",
                      help="Host to listen on")
    cmdp.add_argument('--listen_port', '-p', default=9911,
                      help="Port to listen on")

    args = cmdp.parse_args()

    if ((not args.api_key and not args.api_key_file) or
            (args.api_key and args.api_key_file)):
        sys.stderr.write(
            "You must provide exactly one of --api_key or --api_key_file.\n")
        sys.exit(-1)

    if args.api_key_file:
        try:
            with open(args.api_key_file) as fdesc:
                api_key = fdesc.read().strip()
        except Exception as exc:  # pylint: disable=broad-except
            sys.stderr.write("Could not load API key from %s: %s\n" %
                             (args.api_key_file, exc))
            sys.exit()
    else:
        api_key = args.api_key

    urlp_res = urllib.parse.urlparse(args.url)
    if not (urlp_res.scheme and urlp_res.hostname and
            urlp_res.port and urlp_res.path):
        sys.stderr.write("Could not parse '%s' as a URL. It must include "
                         "scheme (e.g. http://), hostname, port and path to "
                         "the metrics.\n" % (args.url))
        sys.exit(-1)

    metrics = _CustomCollector(urlp_res.scheme, urlp_res.hostname,
                               urlp_res.port, urlp_res.path, api_key)
    promc.core.REGISTRY.register(metrics)
    app = promc.make_wsgi_app()
    httpd = wsgiref.simple_server.make_server(
        args.listen_host, args.listen_port, app=app,
        handler_class=_NoLoggingWSGIRequestHandler)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass

if __name__ == "__main__":
    main()
