"""Semantic keyword clustering: sentence-transformers when available, TF-IDF otherwise."""
import math
from collections import Counter

from utils.text_cleaner import tokenize


def cluster_keywords(keywords, n_clusters: int = None):
    """Returns [{label, keywords, size}] sorted by size. Falls back to a
    shared-token grouping when scikit-learn is unavailable."""
    keywords = [k for k in dict.fromkeys(keywords or []) if k]
    if len(keywords) < 4:
        return [{"label": "All keywords", "keywords": keywords, "size": len(keywords)}]
    n_clusters = n_clusters or max(2, min(8, int(math.sqrt(len(keywords) / 2)) + 1))

    vectors = None
    try:
        from sentence_transformers import SentenceTransformer
        model = SentenceTransformer("all-MiniLM-L6-v2")
        vectors = model.encode(keywords)
    except Exception:
        try:
            from sklearn.feature_extraction.text import TfidfVectorizer
            vectors = TfidfVectorizer(analyzer="char_wb", ngram_range=(3, 4)).fit_transform(keywords)
        except Exception:
            vectors = None

    if vectors is not None:
        try:
            from sklearn.cluster import KMeans
            labels = KMeans(n_clusters=n_clusters, n_init=10, random_state=42).fit_predict(vectors)
            groups = {}
            for kw, lab in zip(keywords, labels):
                groups.setdefault(int(lab), []).append(kw)
            return _name_clusters(groups)
        except Exception:
            pass

    # Dependency-free fallback: group by most distinctive shared token
    global_counts = Counter(t for kw in keywords for t in set(tokenize(kw, drop_stopwords=True)))
    groups = {}
    for kw in keywords:
        tokens = tokenize(kw, drop_stopwords=True)
        anchor = max(tokens, key=lambda t: global_counts[t]) if tokens else "misc"
        groups.setdefault(anchor, []).append(kw)
    named = [{"label": label.title(), "keywords": kws, "size": len(kws)}
             for label, kws in groups.items()]
    named.sort(key=lambda g: -g["size"])
    return named[:12]


def _name_clusters(groups: dict):
    named = []
    for kws in groups.values():
        counts = Counter(t for kw in kws for t in tokenize(kw, drop_stopwords=True))
        top = [w for w, _ in counts.most_common(2)]
        named.append({"label": " ".join(top).title() or "Cluster",
                      "keywords": kws, "size": len(kws)})
    named.sort(key=lambda g: -g["size"])
    return named
