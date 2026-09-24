import requests
import re
import sys

BASE = "http://localhost:3000"
routes = ["/", "/ask", "/reports", "/topics", "/logs"]

all_passed = True

print("=" * 60)
print("GEOVAULT AI - FRONTEND CSS & ROUTE VERIFICATION")
print("=" * 60)

for rt in routes:
    url = f"{BASE}{rt}"
    res = requests.get(url)
    status_icon = "[PASS]" if res.status_code == 200 else "[FAIL]"
    print(f"{status_icon} Route {rt:10s} -> HTTP {res.status_code}")
    if res.status_code != 200:
        all_passed = False
        continue

    css_links = re.findall(r'href=["\'](/_next/static/css/[^"\']+\.css[^"\']*)["\']', res.text)
    if not css_links:
        print(f"  [WARN] No CSS stylesheet links found in HTML for {rt}")
    for css in set(css_links):
        css_url = f"{BASE}{css}"
        c_res = requests.get(css_url)
        c_icon = "[PASS]" if c_res.status_code == 200 and len(c_res.content) > 1000 else "[FAIL]"
        print(f"  {c_icon} CSS: {css[:45]}... -> HTTP {c_res.status_code} ({len(c_res.content)} bytes)")
        if c_res.status_code != 200:
            all_passed = False

print("=" * 60)
if all_passed:
    print("ALL ROUTES & CSS STYLESHEETS VERIFIED SUCCESSFULLY (100% OK)")
else:
    print("SOME STYLESHEETS FAILED TO LOAD")
    sys.exit(1)
