"""
extract2.py
-----------
۱) فایل‌های UnityWebData (مثل game.data.br که قبلاً باز شده) رو به فایل‌های جدا تقسیم می‌کنه
۲) نسخه‌ی یونیتی بازی رو پیدا می‌کنه
۳) فایل‌های .bundle رو با اون نسخه می‌خونه و عکس/صدا/متن/فونت بیرون می‌کشه

اجرا:  python extract2.py   (کنار فایل‌ها)
"""

import os
import re
import struct
import sys
import traceback

try:
    import brotli
    import UnityPy
except ImportError:
    print("اول این رو بزن:  pip install brotli UnityPy")
    sys.exit(1)

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "output")
WEBDATA_DIR = os.path.join(OUT, "webdata")
os.makedirs(WEBDATA_DIR, exist_ok=True)

MAGIC = b"UnityWebData1.0\x00"
VERSION_RE = re.compile(rb"\d{4}\.\d+\.\d+[fpab]\d+|[5-9]\.\d+\.\d+[fpab]\d+|6000\.\d+\.\d+[fpab]\d+")
# اگه نسخه پیدا نشد، به ترتیب اینا رو امتحان می‌کنیم
CANDIDATES = [
    "2022.3.62f1", "2021.3.45f1", "2020.3.49f1", "2019.4.40f1",
    "2023.2.20f1", "6000.0.40f1", "2018.4.36f1", "2017.4.40f1",
]


def safe(name):
    bad = '<>:"/\\|?*\n\r\t'
    return "".join("_" if c in bad else c for c in str(name)) or "unnamed"


def read_maybe_brotli(path):
    """فایل رو می‌خونه؛ اگه Brotli بود باز می‌کنه، وگرنه همون‌طور برمی‌گردونه."""
    with open(path, "rb") as f:
        raw = f.read()
    if raw.startswith(MAGIC) or raw.startswith(b"UnityFS"):
        return raw
    try:
        return brotli.decompress(raw)
    except Exception:
        return raw


def parse_webdata(data):
    """UnityWebData1.0 → لیست (name, bytes)"""
    head_len = struct.unpack_from("<I", data, 16)[0]
    pos = 20
    files = []
    while pos < head_len:
        off, size, nlen = struct.unpack_from("<III", data, pos)
        pos += 12
        name = data[pos:pos + nlen].decode("utf-8", "replace")
        pos += nlen
        files.append((name, data[off:off + size]))
    return files


def find_version(blobs):
    """از اول فایل‌های سریال‌شده‌ی یونیتی دنبال رشته‌ی نسخه می‌گرده."""
    for name, blob in blobs:
        m = VERSION_RE.search(blob[:600])
        if m:
            return m.group(0).decode()
    return None


# ---------- مرحله ۱: UnityWebData ----------
bundles = []
detected_version = None
for fn in sorted(os.listdir(HERE)):
    full = os.path.join(HERE, fn)
    if not os.path.isfile(full) or fn.endswith(".py"):
        continue
    low = fn.lower()
    if not low.endswith((".br", ".data", ".bundle", ".unity3d")):
        continue

    data = read_maybe_brotli(full)

    if data.startswith(MAGIC):
        print(f"[webdata] {fn}: آرشیو UnityWebData پیدا شد")
        files = parse_webdata(data)
        for name, blob in files:
            out_path = os.path.join(WEBDATA_DIR, safe(name))
            with open(out_path, "wb") as f:
                f.write(blob)
            print(f"   {name}  ({len(blob):,} بایت)")
        v = find_version(files)
        if v:
            detected_version = v
            print(f"   ✓ نسخه‌ی یونیتی پیدا شد: {v}")
        # اگه توش بندل یا آرشیو یونیتی بود، اونا رو هم بعداً می‌خونیم
        for name, blob in files:
            if blob.startswith(b"UnityFS"):
                bundles.append(os.path.join(WEBDATA_DIR, safe(name)))
    elif data.startswith(b"UnityFS"):
        if full not in bundles:
            bundles.append(full)
    else:
        print(f"[؟] {fn}: فرمت ناشناخته، رد شد")

if detected_version is None:
    print("\nنسخه‌ی یونیتی توی آرشیو پیدا نشد؛ چند نسخه‌ی رایج رو امتحان می‌کنم.")

# ---------- مرحله ۲: بیرون کشیدن assetها ----------
counts = {}
skipped_sprites = [0]
import warnings
warnings.filterwarnings("ignore")


def export_env(env):
    for obj in env.objects:
        t = obj.type.name
        counts[t] = counts.get(t, 0) + 1
        try:
            if t in ("Texture2D", "Sprite"):
                data = obj.read()
                d = os.path.join(OUT, "images")
                os.makedirs(d, exist_ok=True)
                nm = safe(getattr(data, "m_Name", None) or getattr(data, "name", "") ) + f"_{obj.path_id}"
                data.image.save(os.path.join(d, nm + ".png"))
            elif t == "AudioClip":
                data = obj.read()
                d = os.path.join(OUT, "audio")
                os.makedirs(d, exist_ok=True)
                for sname, sdata in data.samples.items():
                    with open(os.path.join(d, safe(sname)), "wb") as f:
                        f.write(sdata)
            elif t == "TextAsset":
                data = obj.read()
                d = os.path.join(OUT, "text")
                os.makedirs(d, exist_ok=True)
                script = data.m_Script
                if isinstance(script, str):
                    script = script.encode("utf-8", "surrogateescape")
                nm = safe(getattr(data, "m_Name", "") ) + f"_{obj.path_id}"
                with open(os.path.join(d, nm + ".txt"), "wb") as f:
                    f.write(script)
            elif t == "Font":
                data = obj.read()
                d = os.path.join(OUT, "fonts")
                os.makedirs(d, exist_ok=True)
                if data.m_FontData:
                    nm = safe(getattr(data, "m_Name", "") ) + f"_{obj.path_id}"
                    with open(os.path.join(d, nm + ".ttf"), "wb") as f:
                        f.write(bytes(data.m_FontData))
        except Exception as e:
            if t == "Sprite":
                skipped_sprites[0] += 1
                continue
            print(f"   ! مشکل در {t}: {str(e)[:100]}")


for path in bundles:
    print(f"\n[unity] خوندن {os.path.basename(path)} ...")
    versions = ([detected_version] if detected_version else []) + CANDIDATES
    env = None
    for ver in versions:
        try:
            UnityPy.config.FALLBACK_UNITY_VERSION = ver
            env = UnityPy.load(path)
            # مطمئن شیم واقعاً چیزی خونده می‌شه
            objs = list(env.objects)
            if objs:
                objs[0].read()
            print(f"   ✓ با نسخه‌ی {ver} باز شد ({len(objs)} آبجکت)")
            break
        except Exception as e:
            print(f"   - نسخه‌ی {ver} جواب نداد: {str(e)[:80]}")
            env = None
    if env is None:
        print("   ✗ با هیچ نسخه‌ای باز نشد.")
        continue
    export_env(env)

# ---------- گزارش ----------
print("\n===== تمام شد =====")
if counts:
    print("آبجکت‌های پیدا شده:")
    for k, v in sorted(counts.items(), key=lambda x: -x[1]):
        print(f"   {k}: {v}")
if skipped_sprites[0]:
    print(f"\n{skipped_sprites[0]} تا Sprite رد شد (عکسشون جای دیگه‌ایه، مشکلی نیست).")
print(f"\nخروجی اینجاست: {OUT}")
