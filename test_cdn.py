import urllib.request
urls = [
    "https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-mml-chtml.js",
    "https://fastly.jsdelivr.net/npm/mathjax@3/es5/tex-mml-chtml.js",
    "https://npm.elemecdn.com/mathjax@3.2.2/es5/tex-mml-chtml.js",
    "https://cdnjs.cloudflare.com/ajax/libs/mathjax/3.2.2/es5/tex-mml-chtml.min.js"
]

for u in urls:
    try:
        req = urllib.request.urlopen(u, timeout=5)
        print(f"OK: {u}  Size: {len(req.read())}")
    except Exception as e:
        print(f"FAILED {u}: {e}")
