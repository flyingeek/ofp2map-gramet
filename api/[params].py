from flask import Flask, Response
from flask_cors import CORS
from urllib.parse import urlsplit
import re
import time
import requests

app = Flask(__name__)


@app.after_request
def add_headers(response):
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add("Access-Control-Allow-Headers", "X-Requested-With")


# cors = CORS(app, resources={r"/api/*": {"origins": "*"}})


def fetch_image(url):
    url_object = urlsplit(url)
    try:
        r = requests.get(url, timeout=6)
    except requests.exceptions.Timeout:
        return Response("ogimet gramet TimeOut", status=408)
    data = r.text
    if data:
        m = re.search(r'<img src="([^"]+/gramet_[^"]+)"', data)
        if m:
            img_src = "{url.scheme}://{url.netloc}{path}".format(
                url=url_object, path=m.group(1))
            cookies = dict(ogimet_serverid=r.cookies['ogimet_serverid'])
            try:
                response = requests.get(img_src, cookies=cookies, timeout=2)
            except requests.exceptions.Timeout:
                return Response("ogimet fetch image TimeOut", status=504)
            content_type=response.headers.get('content-type')
            mimetype, _, _ = content_type.partition(';')
            if response.status_code != 200:
                return Response('ogimet returns with status %s' % response.status_code, status=response.status_code)
            if not mimetype.startswith("image/"):
                return Response('gramet is not an image', status=406)
            return Response(
                response.content,
                content_type=content_type,
                mimetype=mimetype,
                status=response.status_code)
    return Response("gramet not found", status=404)


@app.route('/api/<int:hini>-<int:tref>-<int:hfin>-<int:fl>-<wmo>__<name>')
def proxy_gramet(hini, tref, hfin, fl, wmo, name):
    now_ts = int(time.time())
    tref = max(now_ts, int(tref))
    OGIMET_URL = "http://www.ogimet.com/display_gramet.php?" \
                 "lang=en&hini={hini}&tref={tref}&hfin={hfin}&fl={fl}" \
                 "&hl=3000&aero=yes&wmo={wmo}&submit=submit"
    url = OGIMET_URL.format(hini=hini, tref=tref, hfin=hfin, fl=fl, wmo=wmo)
    # app.logger.info('proxying %s', url)
    response = fetch_image(url)
    return response


@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def catch_all(path):
    return Response("not a gramet request", status=400)