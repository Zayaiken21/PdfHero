"""Text normalization, tokenizing, readability, and n-gram helpers. Dependency-free."""
import html
import re
from collections import Counter

STOPWORDS = set("""a about above after again against all am an and any are as at be because been
before being below between both but by can did do does doing down during each few for from further
had has have having he her here hers herself him himself his how i if in into is it its itself
just me more most my myself no nor not now of off on once only or other our ours ourselves out
over own same she should so some such than that the their theirs them themselves then there these
they this those through to too under until up very was we were what when where which while who
whom why will with you your yours yourself yourselves get got make made using use used via vs
""".split())

_WS = re.compile(r"\s+")
_TAG = re.compile(r"<[^>]+>")
_PUNCT_EDGE = re.compile(r"^[\W_]+|[\W_]+$")
_SENT_SPLIT = re.compile(r"(?<=[.!?])\s+(?=[A-Z0-9\"'])")
_WORD = re.compile(r"[A-Za-z][A-Za-z'&-]*|\d+")


def clean_text(text: str) -> str:
    if not text:
        return ""
    text = html.unescape(str(text))
    text = _TAG.sub(" ", text)
    return _WS.sub(" ", text).strip()


def normalize_keyword(kw: str) -> str:
    kw = clean_text(kw).lower()
    kw = _PUNCT_EDGE.sub("", kw)
    return _WS.sub(" ", kw).strip()


def slugify(text: str) -> str:
    text = normalize_keyword(text)
    return re.sub(r"[^a-z0-9]+", "-", text).strip("-") or "item"


def tokenize(text: str, drop_stopwords: bool = False):
    words = [w.lower() for w in _WORD.findall(text or "")]
    if drop_stopwords:
        words = [w for w in words if w not in STOPWORDS and len(w) > 1]
    return words


def split_sentences(text: str):
    text = clean_text(text)
    if not text:
        return []
    parts = _SENT_SPLIT.split(text)
    return [p.strip() for p in parts if len(p.strip()) > 15]


def _syllables(word: str) -> int:
    word = word.lower()
    groups = re.findall(r"[aeiouy]+", word)
    count = len(groups)
    if word.endswith("e") and count > 1:
        count -= 1
    return max(1, count)


def flesch_reading_ease(text: str) -> float:
    """Approximate Flesch score. 60-80 reads easily; clamps to [0, 100]."""
    sents = split_sentences(text) or [text]
    words = tokenize(text)
    if not words:
        return 0.0
    syl = sum(_syllables(w) for w in words)
    score = 206.835 - 1.015 * (len(words) / max(1, len(sents))) - 84.6 * (syl / len(words))
    return round(max(0.0, min(100.0, score)), 1)


def ngram_counts(texts, n: int = 2, top: int = 25, exclude_tokens=None):
    """Frequent word n-grams across a list of strings (stopwords removed)."""
    exclude = set(exclude_tokens or [])
    counter = Counter()
    for t in texts or []:
        toks = [w for w in tokenize(t, drop_stopwords=True) if w not in exclude]
        for i in range(len(toks) - n + 1):
            counter[" ".join(toks[i:i + n])] += 1
    return counter.most_common(top)


def truncate(text: str, limit: int) -> str:
    text = clean_text(text)
    if len(text) <= limit:
        return text
    cut = text[:limit].rsplit(" ", 1)[0]
    return cut + "…"
