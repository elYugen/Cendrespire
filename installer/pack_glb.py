"""Prépare des modèles glTF pour le jeu (outil de développement, lancé à la main).

- Personnages .glb : ne garde que les animations listées (les packs en contiennent souvent des dizaines),
  puis réécrit un .glb compact ne contenant que les données encore utilisées.
- Objets .gltf (+ .bin, + texture .png à côté) : les rassemble en un seul .glb, texture incluse.

Usage :
  python installer/pack_glb.py char <entrée.glb> <sortie.glb> Anim1 Anim2 ...
  python installer/pack_glb.py prop <entrée.gltf> <sortie.glb>
"""
import json
import os
import struct
import sys


def read_glb(path):
    data = open(path, "rb").read()
    jlen = struct.unpack("<I", data[12:16])[0]
    g = json.loads(data[20:20 + jlen])
    off = 20 + jlen
    blen = struct.unpack("<I", data[off:off + 4])[0]
    return g, data[off + 8:off + 8 + blen]


def read_gltf(path):
    """.gltf à fichiers séparés : un seul tampon binaire, images externes intégrées à la suite."""
    folder = os.path.dirname(path)
    g = json.load(open(path, encoding="utf-8"))
    assert len(g["buffers"]) == 1, "un seul tampon attendu"
    binary = bytearray(open(os.path.join(folder, g["buffers"][0]["uri"]), "rb").read())
    for im in g.get("images", []):
        if "uri" in im:
            raw = open(os.path.join(folder, im.pop("uri")), "rb").read()
            while len(binary) % 4:
                binary.append(0)
            g["bufferViews"].append({"buffer": 0, "byteOffset": len(binary), "byteLength": len(raw)})
            binary += raw
            im["bufferView"] = len(g["bufferViews"]) - 1
            im["mimeType"] = "image/png"
    g["buffers"][0].pop("uri", None)
    return g, bytes(binary)


def repack(g, binary):
    """Ne garde que les accesseurs et vues encore référencés, et reconstruit le tampon binaire."""
    used_acc = set()
    for m in g.get("meshes", []):
        for p in m["primitives"]:
            used_acc |= set(p["attributes"].values())
            if "indices" in p:
                used_acc.add(p["indices"])
            for t in p.get("targets", []):
                used_acc |= set(t.values())
    for s in g.get("skins", []):
        if "inverseBindMatrices" in s:
            used_acc.add(s["inverseBindMatrices"])
    for a in g.get("animations", []):
        for smp in a["samplers"]:
            used_acc |= {smp["input"], smp["output"]}
    acc_map = {old: new for new, old in enumerate(sorted(used_acc))}
    accessors = [g["accessors"][old] for old in sorted(used_acc)]
    used_views = {a["bufferView"] for a in accessors if "bufferView" in a}
    used_views |= {im["bufferView"] for im in g.get("images", []) if "bufferView" in im}
    view_map, views, out = {}, [], bytearray()
    for old in sorted(used_views):
        v = dict(g["bufferViews"][old])
        start = v.get("byteOffset", 0)
        chunk = binary[start:start + v["byteLength"]]
        while len(out) % 4:
            out.append(0)
        v["byteOffset"] = len(out)
        v["buffer"] = 0
        out += chunk
        view_map[old] = len(views)
        views.append(v)
    for a in accessors:
        if "bufferView" in a:
            a["bufferView"] = view_map[a["bufferView"]]
    for im in g.get("images", []):
        if "bufferView" in im:
            im["bufferView"] = view_map[im["bufferView"]]
    for m in g.get("meshes", []):
        for p in m["primitives"]:
            p["attributes"] = {k: acc_map[v] for k, v in p["attributes"].items()}
            if "indices" in p:
                p["indices"] = acc_map[p["indices"]]
            p["targets"] = [{k: acc_map[v] for k, v in t.items()} for t in p.get("targets", [])] or None
            if p["targets"] is None:
                del p["targets"]
    for s in g.get("skins", []):
        if "inverseBindMatrices" in s:
            s["inverseBindMatrices"] = acc_map[s["inverseBindMatrices"]]
    for a in g.get("animations", []):
        for smp in a["samplers"]:
            smp["input"], smp["output"] = acc_map[smp["input"]], acc_map[smp["output"]]
    g["accessors"], g["bufferViews"] = accessors, views
    g["buffers"] = [{"byteLength": len(out)}]
    return g, bytes(out)


def write_glb(path, g, binary):
    js = json.dumps(g, separators=(",", ":")).encode("utf-8")
    js += b" " * (-len(js) % 4)
    binary += b"\0" * (-len(binary) % 4)
    total = 12 + 8 + len(js) + 8 + len(binary)
    with open(path, "wb") as f:
        f.write(struct.pack("<4sII", b"glTF", 2, total))
        f.write(struct.pack("<I4s", len(js), b"JSON") + js)
        f.write(struct.pack("<I4s", len(binary), b"BIN\0") + binary)


def main(argv):
    kind, src, dst = argv[:3]
    if kind == "char":
        keep = set(argv[3:])
        g, binary = read_glb(src)
        missing = keep - {a["name"] for a in g.get("animations", [])}
        if missing:
            raise SystemExit(f"animations absentes : {sorted(missing)}")
        g["animations"] = [a for a in g.get("animations", []) if a["name"] in keep]
    else:
        g, binary = read_gltf(src)
    g, binary = repack(g, binary)
    write_glb(dst, g, binary)
    print(f"{os.path.basename(dst)} : {os.path.getsize(dst) / 1024:.0f} Ko")


if __name__ == "__main__":
    main(sys.argv[1:])
