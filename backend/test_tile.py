import urllib.request
import math

lat, lon, z = 22.7196, 75.8577, 14
x = int((lon + 180.0) / 360.0 * (1 << z))
y = int((1.0 - math.log(math.tan(math.radians(lat)) + (1.0 / math.cos(math.radians(lat)))) / math.pi) / 2.0 * (1 << z))
url = f"https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}"
req = urllib.request.Request(url, headers={"User-Agent": "SatQueryAI/1.0"})
with urllib.request.urlopen(req, timeout=10) as resp:
    data = resp.read()
    print(f"SUCCESS: Fetched {len(data)} bytes from {url}")
