import urllib.request

ports = [3000, 5173, 5174, 5175]
for port in ports:
    try:
        url = f"http://localhost:{port}/"
        resp = urllib.request.urlopen(url, timeout=5)
        print(f"Port {port}: HTTP {resp.status} OK")
    except Exception as e:
        print(f"Port {port}: Error {e}")
