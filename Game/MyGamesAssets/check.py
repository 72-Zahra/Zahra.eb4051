import os
for fn in os.listdir("."):
    if fn.endswith((".br", ".bundle")):
        with open(fn, "rb") as f:
            head = f.read(96)
        print(fn, "-", os.path.getsize(fn), "bytes")
        print("  hex :", head.hex(" "))
        print("  text:", head.decode("latin1").encode("ascii", "replace").decode())
        print()