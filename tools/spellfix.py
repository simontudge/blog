"""Apply the spelling corrections in tools/corrections.json to the posts.

  python tools/spellfix.py --dry-run    show every change with context
  python tools/spellfix.py              write the changes

Only prose is touched: anything inside an HTML tag is skipped, so image
filenames and src attributes cannot be rewritten by a correction that happens
to match them.
"""

import json
import re
import sys
from pathlib import Path

# Regions that must never be rewritten: HTML tags, and anything path-like in
# the front matter. A post about Kyrgyzstan lives in a directory spelled
# "krygistan", so correcting the word would otherwise break its image path.
SKIP = re.compile(
    r"<[^>]*>"
    r"|^(?:thumbnail|permalink|layout|tags|order|collection):.*$"
    r"|\S*/\S*"
    r"|\S+\.(?:jpg|jpeg|png|webp|gif|html|css|md)\b",
    re.M | re.I,
)


def load():
    raw = json.loads(Path("tools/corrections.json").read_text())
    return {k: v for k, v in raw.items() if not k.startswith("_")}


def match_case(original, replacement):
    """Carry the original's capitalisation over to the replacement."""
    if original.isupper() and len(original) > 1:
        return replacement.upper()
    if original[0].isupper():
        return replacement[0].upper() + replacement[1:]
    return replacement


def fix(text, table, log, path):
    pattern = re.compile(
        r"\b(" + "|".join(sorted(map(re.escape, table), key=len, reverse=True)) + r")\b",
        re.I,
    )

    def replacer(segment):
        """Offsets inside the callback are relative to the segment, so the
        context has to be read from that same segment."""

        def replace(m):
            word = m.group(0)
            new = match_case(word, table[word.lower()])
            if new == word:
                return word
            start = max(0, m.start() - 55)
            end = min(len(segment), m.end() + 55)
            log.append((path, word, new, " ".join(segment[start:end].split())))
            return new

        return replace

    # Rebuild the document, skipping the contents of HTML tags entirely.
    out = []
    last = 0
    for tag in SKIP.finditer(text):
        segment = text[last : tag.start()]
        out.append(pattern.sub(replacer(segment), segment))
        out.append(tag.group(0))
        last = tag.end()
    segment = text[last:]
    out.append(pattern.sub(replacer(segment), segment))
    return "".join(out)


if __name__ == "__main__":
    dry = "--dry-run" in sys.argv
    table = load()
    log = []
    changed = 0
    for path in sorted(Path(".").glob("*/posts/*/*.md")):
        text = path.read_text(encoding="utf-8")
        new = fix(text, table, log, str(path))
        if new != text:
            changed += 1
            if not dry:
                path.write_text(new, encoding="utf-8")

    for path, old, new, ctx in log:
        print(f"{old} -> {new}\n    {path}\n    ...{ctx}...")
    verb = "would change" if dry else "changed"
    print(f"\n{len(log)} corrections across {changed} files ({verb})")
