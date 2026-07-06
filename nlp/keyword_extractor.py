"""Keyword & phrase extraction with graceful degradation:
KeyBERT -> spaCy noun chunks -> TF-IDF -> RAKE-lite (always available)."""
import re
from collections import Counter, defaultdict

from utils.text_cleaner import STOPWORDS, clean_text, tokenize

_PHRASE_SPLIT = re.compile(r"[^A-Za-z0-9'&-]+")


def rake_phrases(text: str, top_n: int = 30, max_words: int = 4):
    """RAKE-style phrase extraction — dependency-free workhorse."""
    text = clean_text(text).lower()
    words = _PHRASE_SPLIT.split(text)
    phrases, current = [], []
    for w in words:
        if not w or w in STOPWORDS or w.isdigit():
            if 1 <= len(current) <= max_words:
                phrases.append(tuple(current))
            current = []
        else:
            current.append(w)
    if 1 <= len(current) <= max_words:
        phrases.append(tuple(current))

    freq, degree = Counter(), defaultdict(int)
    for phrase in phrases:
        for w in phrase:
            freq[w] += 1
            degree[w] += len(phrase) - 1
    scores = Counter()
    for phrase in set(phrases):
        scores[" ".join(phrase)] += sum((degree[w] + freq[w]) / freq[w] for w in phrase)
    for phrase in phrases:  # frequency bonus so repeated phrases rank up
        scores[" ".join(phrase)] += 0.4
    return [(p, round(s, 2)) for p, s in scores.most_common(top_n) if len(p) > 2]


def _tfidf_terms(texts, top_n=30):
    try:
        from sklearn.feature_extraction.text import TfidfVectorizer
    except Exception:
        counts = Counter()
        for t in texts:
            counts.update(tokenize(t, drop_stopwords=True))
        return [(w, float(c)) for w, c in counts.most_common(top_n)]
    vec = TfidfVectorizer(ngram_range=(1, 3), stop_words="english",
                          max_features=4000, min_df=1)
    matrix = vec.fit_transform(texts)
    scores = matrix.sum(axis=0).A1
    terms = vec.get_feature_names_out()
    ranked = sorted(zip(terms, scores), key=lambda x: -x[1])[:top_n]
    return [(t, round(float(s), 3)) for t, s in ranked]


def extract_keywords(texts, top_n: int = 30):
    """Best-available extractor. texts: str or list[str] -> [(keyword, score)]."""
    if isinstance(texts, str):
        texts = [texts]
    texts = [clean_text(t) for t in texts if clean_text(t)]
    if not texts:
        return []
    blob = "\n".join(texts)

    try:  # KeyBERT (optional, heavy)
        from keybert import KeyBERT
        model = _keybert_singleton()
        pairs = model.extract_keywords(blob, keyphrase_ngram_range=(1, 3),
                                       stop_words="english", top_n=top_n)
        if pairs:
            return [(k, round(float(s), 3)) for k, s in pairs]
    except Exception:
        pass

    try:  # spaCy noun chunks (optional)
        nlp = _spacy_singleton()
        if nlp is not None:
            doc = nlp(blob[:100000])
            counts = Counter(chunk.text.lower().strip() for chunk in doc.noun_chunks
                             if 2 < len(chunk.text) < 60)
            if counts:
                return [(k, float(v)) for k, v in counts.most_common(top_n)]
    except Exception:
        pass

    if len(texts) >= 3:
        return _tfidf_terms(texts, top_n)
    return rake_phrases(blob, top_n)


_KEYBERT = None
_SPACY = None


def _keybert_singleton():
    global _KEYBERT
    if _KEYBERT is None:
        from keybert import KeyBERT
        _KEYBERT = KeyBERT()
    return _KEYBERT


def _spacy_singleton():
    global _SPACY
    if _SPACY is None:
        try:
            import spacy
            _SPACY = spacy.load("en_core_web_sm")
        except Exception:
            _SPACY = False
    return _SPACY or None


def nlp_capabilities() -> dict:
    caps = {"rake": True, "tfidf": False, "spacy": False, "keybert": False,
            "sentence_transformers": False}
    try:
        import sklearn  # noqa: F401
        caps["tfidf"] = True
    except Exception:
        pass
    caps["spacy"] = _spacy_singleton() is not None
    try:
        import keybert  # noqa: F401
        caps["keybert"] = True
    except Exception:
        pass
    try:
        import sentence_transformers  # noqa: F401
        caps["sentence_transformers"] = True
    except Exception:
        pass
    return caps
