from flask import Flask, Response
from urllib.parse import urlsplit
from hashlib import sha1
import re
import time
import requests

app = Flask(__name__)


def fetch_image(url, etag_src):
    url_object = urlsplit(url)
    try:
        r = requests.get(url, timeout=6)
    except requests.exceptions.Timeout:
        return Response("ogimet gramet TimeOut", status="408 ogimet gramet TimeOut")
    data = r.text
    if data:
        if data.find('No grib data available') >=0 :
            return Response('no grib data', status="503 no grib data")
        if data.find('Sorry, OGIMET is overloaded. Try again in few minutes')>=0 :
            return Response('OGIMET is overloaded', status="404 OGIMET is overloaded")
        m = re.search(r'gramet_lee_rutind: Error, no se han encontrado datos de (.+)', data)
        if m:
            return Response(m.group(1), status="409 " + m.group(1) + " unknown wmo") # wmo non reconnu
        m = re.search(r'<img src="([^"]+/gramet_[^"]+)"', data)
        if m:
            img_src = "{url.scheme}://{url.netloc}{path}".format(
                url=url_object, path=m.group(1))
            ogimet_serverid = r.cookies.get('ogimet_serverid', None)
            try:
                if ogimet_serverid:
                    response = requests.get(img_src, cookies=dict(ogimet_serverid=ogimet_serverid), timeout=2)
                else:
                    response = requests.get(img_src, timeout=2)
            except requests.exceptions.Timeout:
                return Response("ogimet fetch image TimeOut", status="504 ogimet fetch image TimeOut")
            content_type=response.headers.get('content-type')
            mimetype, _, _ = content_type.partition(';')
            if response.status_code != 200:
                return Response('ogimet returns with status %s' % response.status_code, status=response.status_code)
            if not mimetype.startswith("image/"):
                return Response('gramet is not an image', status="406 gramet is not an image")
            proxy_response = Response(
                response.content,
                content_type=content_type,
                mimetype=mimetype,
                status=response.status_code)
            etag = sha1(etag_src.encode('utf-8')).hexdigest()
            proxy_response.headers.add('X-ETag', etag)
            proxy_response.set_etag(etag, True)
            return proxy_response
    return Response("gramet not found", status="404 gramet not found")


@app.route('/api/<int:hini>-<int:tref>-<int:hfin>-<int:fl>-<wmo>__<name>')
def proxy_gramet(hini, tref, hfin, fl, wmo, name):
    now_ts = int(time.time())
    tref = int(tref)
    tref_hours = tref / 3600.0
    if (tref_hours - int(tref_hours)) > 0.5:
        tref = (int(tref_hours) + 1) * 3600
    tref = max(now_ts, tref)
    OGIMET_URL = "http://www.ogimet.com/display_gramet.php?" \
                 "lang=en&hini={hini}&tref={tref}&hfin={hfin}&fl={fl}" \
                 "&hl=3000&aero=yes&wmo={wmo}&submit=submit"
    url = OGIMET_URL.format(hini=hini, tref=tref, hfin=hfin, fl=fl, wmo=wmo)
    etag_src = "{hini}&tref={tref}&hfin={hfin}&fl={fl}&wmo={wmo}".format(hini=hini, tref=int(tref / 3600.0), hfin=hfin, fl=fl, wmo=wmo)
    response = fetch_image(url, etag_src)

    # add CORS headers
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add("Access-Control-Allow-Headers", "X-Requested-With")
    response.headers.add("Access-Control-Expose-Headers", "ETag, X-ETag, X-ofp2map-status")
    print(name)
    if (response.status_code != 200):
        print(response.status)
        response.headers.add('X-ofp2map-status', response.status)
    return response


@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def catch_all(path):
    return Response("not a gramet request", status="400 not a gramet request")
