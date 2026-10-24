"""Extract translatable strings to a .ts file and compile .ts to .qm.

Qt's lrelease is not always installed, so this script writes the .qm format
itself (messages block plus hash table; enough for QTranslator lookups).

    python scripts/translations.py extract   # update i18n/species_data_sv.ts
    python scripts/translations.py compile   # write i18n/species_data_sv.qm
"""
import ast
import struct
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PACKAGE = ROOT / "species_data"
I18N = PACKAGE / "i18n"
TS = I18N / "species_data_sv.ts"
QM = I18N / "species_data_sv.qm"
CONTEXTS = {"dockwidget.py": "SpeciesDataDockWidget", "plugin.py": "SpeciesDataPlugin"}

MAGIC = bytes.fromhex("3cb86418caef9c95cd211cbf60a1bddd")


def extract_sources():
    found = {}
    for filename, context in CONTEXTS.items():
        tree = ast.parse((PACKAGE / filename).read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call) or not node.args:
                continue
            func = node.func
            name = func.id if isinstance(func, ast.Name) else getattr(func, "attr", "")
            first = node.args[0]
            is_text = isinstance(first, ast.Constant) and isinstance(first.value, str)
            if name in ("tr", "tr_noop") and is_text:
                found.setdefault(context, []).append(first.value)
    return found


def read_existing():
    existing = {}
    if TS.exists():
        for ctx in ET.parse(TS).getroot().iter("context"):
            for msg in ctx.iter("message"):
                existing[(ctx.findtext("name"), msg.findtext("source"))] = (
                    msg.findtext("translation") or ""
                )
    return existing


def extract():
    existing = read_existing()
    root = ET.Element("TS", version="2.1", language="sv_SE")
    for context, sources in sorted(extract_sources().items()):
        ctx = ET.SubElement(root, "context")
        ET.SubElement(ctx, "name").text = context
        for source in dict.fromkeys(sources):
            msg = ET.SubElement(ctx, "message")
            ET.SubElement(msg, "source").text = source
            translation = existing.get((context, source), "")
            node = ET.SubElement(msg, "translation")
            node.text = translation
            if not translation:
                node.set("type", "unfinished")
    ET.indent(root)
    TS.write_text(
        '<?xml version="1.0" encoding="utf-8"?>\n<!DOCTYPE TS>\n'
        + ET.tostring(root, encoding="unicode")
        + "\n",
        encoding="utf-8",
    )
    print(f"Wrote {TS}")


def elf_hash(data: bytes) -> int:
    h = 0
    for byte in data:
        h = ((h << 4) + byte) & 0xFFFFFFFF
        g = h & 0xF0000000
        if g:
            h ^= g >> 24
        h &= ~g & 0xFFFFFFFF
    return h


def compile_qm():
    messages = b""
    hashes = []
    for ctx in ET.parse(TS).getroot().iter("context"):
        context = ctx.findtext("name").encode("utf-8")
        for msg in ctx.iter("message"):
            translation = msg.find("translation")
            if translation is None or not translation.text or translation.get("type"):
                continue
            source = msg.findtext("source").encode("utf-8")
            hashes.append((elf_hash(source), len(messages)))
            text = translation.text.encode("utf-16-be")
            messages += b"\x03" + struct.pack(">I", len(text)) + text
            messages += b"\x06" + struct.pack(">I", len(source)) + source
            messages += b"\x07" + struct.pack(">I", len(context) + 1) + context + b"\x00"
            messages += b"\x08" + struct.pack(">I", 1) + b"\x00"
            messages += b"\x01"
    table = b"".join(struct.pack(">II", h, off) for h, off in sorted(hashes))
    out = MAGIC
    out += b"\x42" + struct.pack(">I", len(table)) + table
    out += b"\x69" + struct.pack(">I", len(messages)) + messages
    QM.write_bytes(out)
    print(f"Wrote {QM} ({len(hashes)} messages)")


if __name__ == "__main__":
    {"extract": extract, "compile": compile_qm}[sys.argv[1] if len(sys.argv) > 1 else "extract"]()
