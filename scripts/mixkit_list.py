"""List Mixkit SFX (id, title, duration) for category slugs: python mixkit_list.py wind radio ..."""
import re, sys, urllib.request
for slug in sys.argv[1:]:
    req = urllib.request.Request(f"https://mixkit.co/free-sound-effects/{slug}/", headers={"User-Agent": "Mozilla/5.0"})
    html = urllib.request.urlopen(req).read().decode("utf-8", "ignore")
    print("==", slug)
    for blk in html.split('data-controller="audio-player"')[1:]:
        i = re.search(r'item-id-value="(\d+)"', blk)
        t = re.search(r'item-grid-card__title">\s*(?:<[^>]+>\s*)*([^<]+?)\s*<', blk)
        d = re.search(r'(\d+:\d\d)', blk)
        if i:
            print(f"  {i.group(1):>5}  {d.group(1) if d else '?':>5}  {t.group(1) if t else '?'}")
