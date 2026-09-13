"""Convert a hand-written post from the old HTML format into Markdown.

Usage: python tools/html2md.py travel-blog/posts/lycian-way/lycian-way.html

Pulls the title and lead paragraph out into front matter, converts headings and
paragraphs to Markdown, and leaves <figure> blocks as raw HTML (Markdown has no
figure/figcaption syntax, and Markdown files may contain HTML).
"""

import html
import re
import sys
from pathlib import Path

MAIN = re.compile(r"<main\b[^>]*>(.*?)</main>", re.S | re.I)
H1 = re.compile(r"<h1\b[^>]*>(.*?)</h1>", re.S | re.I)
LEAD = re.compile(r"<p\b[^>]*class=['\"][^'\"]*\blead\b[^'\"]*['\"][^>]*>(.*?)</p>", re.S | re.I)
FIGURE = re.compile(r"<figure\b.*?</figure>", re.S | re.I)
HEADING = re.compile(r"<(h[2-6])\b[^>]*>(.*?)</\1>", re.S | re.I)
QUOTE = re.compile(r"<blockquote\b[^>]*>(.*?)</blockquote>", re.S | re.I)
PARA_TAG = re.compile(r"</?p\b[^>]*>", re.I)
ITALIC = re.compile(r"</?(?:i|em)\b[^>]*>", re.I)
BOLD = re.compile(r"</?(?:b|strong)\b[^>]*>", re.I)
OPENS = re.compile(r"<(?:i|em)\b[^>]*>", re.I)
CLOSES = re.compile(r"</(?:i|em)\s*>", re.I)
BOLD_OPENS = re.compile(r"<(?:b|strong)\b[^>]*>", re.I)
BOLD_CLOSES = re.compile(r"</(?:b|strong)\s*>", re.I)
# Anything still carrying a tag after conversion is something we don't handle.
LEFTOVER = re.compile(r"<(?!/?(?:figure|img|figcaption|i|em|b|strong)\b)[a-zA-Z][^>]*>")


def clean(text):
    """Collapse whitespace, convert inline formatting, unescape entities."""
    # Escape asterisks already in the prose (censored swearing) before adding
    # our own, or Markdown reads them as emphasis and swallows them.
    text = text.replace("*", r"\*")
    # Markdown emphasis cannot span a paragraph break, and one story italicises
    # several paragraphs at once. Convert only pairs that open and close inside
    # this block; leave the rest as HTML, which Markdown passes through intact.
    if len(OPENS.findall(text)) == len(CLOSES.findall(text)):
        text = ITALIC.sub("*", text)
    if len(BOLD_OPENS.findall(text)) == len(BOLD_CLOSES.findall(text)):
        text = BOLD.sub("**", text)
    return html.unescape(re.sub(r"\s+", " ", text)).strip()


def convert(source):
    body = MAIN.search(source)
    if not body:
        raise SystemExit("no <main> element found")
    body = body.group(1)

    title = H1.search(body)
    title = clean(title.group(1)) if title else ""

    lead = LEAD.search(body)
    lead_text = clean(lead.group(1)) if lead else ""

    # Drop the title and lead; they become front matter and the layout renders them.
    if lead:
        body = body[: lead.start()] + body[lead.end() :]
    body = H1.sub("", body, count=1)

    # Protect figures from block conversion, restore them verbatim afterwards.
    figures = []

    def stash(match):
        figures.append(match.group(0).strip())
        # Blank lines each side so the figure splits out as its own block.
        return f"\n\n\x00FIGURE{len(figures) - 1}\x00\n\n"

    body = FIGURE.sub(stash, body)

    # Several posts have unbalanced <p> tags, leaving prose outside any element.
    # So rather than matching tagged blocks, convert the block-level elements to
    # their Markdown form and then split on blank lines: any run of text becomes
    # a paragraph whether or not it was ever wrapped in a <p>.
    body = QUOTE.sub(lambda m: f"\n\n> {clean(m.group(1))}\n\n", body)
    body = HEADING.sub(
        lambda m: f"\n\n{'#' * int(m.group(1)[1])} {clean(m.group(2))}\n\n", body
    )
    body = PARA_TAG.sub("\n\n", body)

    ordered = []
    for block in re.split(r"\n\s*\n", body):
        block = clean(block)
        if not block:
            continue
        if re.fullmatch(r"#{1,6}", block):  # an empty <h3></h3> in the source
            continue
        placeholder = re.fullmatch(r"\x00FIGURE(\d+)\x00", block)
        ordered.append(figures[int(placeholder.group(1))] if placeholder else block)

    # layout and permalink come from the directory data file (posts.json).
    front = ["---", f'title: "{title}"']
    if lead_text:
        front.append(f'lead: "{lead_text.replace(chr(34), chr(39))}"')
    front += ["---", ""]
    return "\n".join(front) + "\n\n".join(ordered) + "\n"


def words(markup):
    """Visible words in a fragment of markup, for comparing before and after.

    Punctuation-only tokens are dropped: removing a tag such as <i> leaves a
    space before the following comma, which would otherwise count as a word.
    """
    text = html.unescape(re.sub(r"<[^>]+>", " ", markup))
    return [w for w in text.split() if re.search(r"\w", w)]


def check(source, markdown):
    """Return a list of warnings about anything lost or not understood."""
    warnings = []

    before = words(MAIN.search(source).group(1))

    # Compare prose only: front matter holds the title and lead, which in the
    # original were an <h1> and a <p class="lead"> inside <main>.
    front, _, body = markdown.partition("\n---\n")
    quoted = re.findall(r'^(?:title|lead): "(.*)"$', front, re.M)
    after = words(" ".join(quoted)) + [
        w for w in words(body) if not re.fullmatch(r"#{1,6}|>", w)
    ]
    # <i>per se</i> becomes *per se*, so the markers attach to adjacent words.
    # Strip them before counting, or every italic looks like a lost word.
    after = [w for w in (w.strip("*") for w in after) if w]
    if len(before) != len(after):
        warnings.append(f"word count {len(before)} -> {len(after)}")

    for tag in sorted(set(LEFTOVER.findall(markdown))):
        warnings.append(f"unhandled markup: {tag}")

    for name in ("figure", "h2", "h3", "blockquote"):
        expected = len(re.findall(rf"<{name}\b", source, re.I))
        if name == "figure":
            actual = len(re.findall(r"<figure\b", markdown, re.I))
        elif name == "blockquote":
            actual = len([l for l in markdown.splitlines() if l.startswith("> ")])
        else:
            actual = len([l for l in markdown.splitlines() if l.startswith("#" * int(name[1]) + " ")])
        if expected != actual:
            warnings.append(f"{name}: {expected} -> {actual}")

    return warnings


if __name__ == "__main__":
    failures = 0
    for argument in sys.argv[1:]:
        path = Path(argument)
        source = path.read_text(encoding="utf-8")
        markdown = convert(source)
        warnings = check(source, markdown)
        path.with_suffix(".md").write_text(markdown, encoding="utf-8")
        status = "OK " if not warnings else "WARN"
        print(f"{status} {path}")
        for warning in warnings:
            failures += 1
            print(f"       - {warning}")
    print(f"\n{failures} warning(s)")
