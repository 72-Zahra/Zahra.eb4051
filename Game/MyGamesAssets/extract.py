
import os
import sys
import traceback

try:
    import brotli
    import UnityPy
except ImportError:
    print("کتابخونه‌ها نصب نیستن. این دستور رو بزن و دوباره اجرا کن:")
    print("    pip install brotli UnityPy")
    sys.exit(1)

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "output")
TMP = os.path.join(OUT, "_decompressed")
os.makedirs(TMP, exist_ok=True)


def safe(name):
    """اسم فایل امن (بدون کاراکتر ممنوعه)"""
    bad = '<>:"/\\|?*\n\r\t'
    return "".join("_" if c in bad else c for c in str(name)) or "unnamed"


def get_name(data, obj):
    name = getattr(data, "m_Name", None) or getattr(data, "name", None)
    return safe(name) + f"_{obj.path_id}"


# ---------- مرحله ۱: باز کردن فایل‌های .br ----------
to_scan = []
for fn in sorted(os.listdir(HERE)):
    full = os.path.join(HERE, fn)
    if not os.path.isfile(full) or fn == os.path.basename(__file__):
        continue
    low = fn.lower()
    if low.endswith(".br"):
        print(f"[br] باز کردن {fn} ...")
        try:
            with open(full, "rb") as f:
                raw = brotli.decompress(f.read())
        except Exception as e:
            print(f"   ✗ نشد (شاید Brotli نباشه یا رمزگذاری شده): {e}")
            continue
        out_name = fn[:-3] or "decompressed"
        out_path = os.path.join(TMP, out_name)
        with open(out_path, "wb") as f:
            f.write(raw)
        print(f"   ✓ ذخیره شد: {out_path}  ({len(raw):,} بایت)")
        to_scan.append(out_path)
    elif low.endswith(".bundle"):
        to_scan.append(full)

if not to_scan:
    print("هیچ فایل .br یا .bundle کنار اسکریپت پیدا نشد.")
    sys.exit(1)

# ---------- مرحله ۲: بیرون کشیدن assetها با UnityPy ----------
counts = {}
for path in to_scan:
    print(f"\n[unity] خوندن {os.path.basename(path)} ...")
    try:
        env = UnityPy.load(path)
    except Exception as e:
        print(f"   ✗ این فایل بندل یونیتی نیست یا رمزگذاری شده: {e}")
        continue

    for obj in env.objects:
        t = obj.type.name
        counts[t] = counts.get(t, 0) + 1
        try:
            if t in ("Texture2D", "Sprite"):
                data = obj.read()
                d = os.path.join(OUT, "images")
                os.makedirs(d, exist_ok=True)
                data.image.save(os.path.join(d, get_name(data, obj) + ".png"))

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
                with open(os.path.join(d, get_name(data, obj) + ".txt"), "wb") as f:
                    f.write(script)

            elif t == "Font":
                data = obj.read()
                d = os.path.join(OUT, "fonts")
                os.makedirs(d, exist_ok=True)
                if data.m_FontData:
                    with open(os.path.join(d, get_name(data, obj) + ".ttf"), "wb") as f:
                        f.write(bytes(data.m_FontData))
        except Exception:
            print(f"   ! مشکل در {t}:")
            traceback.print_exc(limit=1)

# ---------- گزارش ----------
print("\n===== تمام شد =====")
print("تعداد آبجکت‌های پیدا شده به تفکیک نوع:")
for k, v in sorted(counts.items(), key=lambda x: -x[1]):
    print(f"   {k}: {v}")
print(f"\nخروجی اینجاست: {OUT}")