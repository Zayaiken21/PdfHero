"""Rank sentences for title/description mining: relevance, uniqueness, buyer intent,
readability, and commercial fit — with an explainable per-sentence breakdown."""
from utils.text_cleaner import flesch_reading_ease, split_sentences, tokenize

from nlp.intent_classifier import TRANSACTIONAL, COMMERCIAL

ACTION_WORDS = TRANSACTIONAL | COMMERCIAL | {"organize", "plan", "track", "save", "print"}


def _centrality_scores(sentences):
    try:
        from sklearn.feature_extraction.text import TfidfVectorizer
        from sklearn.metrics.pairwise import cosine_similarity
        matrix = TfidfVectorizer(stop_words="english").fit_transform(sentences)
        sims = cosine_similarity(matrix)
        return [float(row.sum() - 1) / max(1, len(sentences) - 1) for row in sims]
    except Exception:
        token_sets = [set(tokenize(s, drop_stopwords=True)) for s in sentences]
        scores = []
        for i, ts in enumerate(token_sets):
            overlap = sum(len(ts & other) / (len(ts | other) or 1)
                          for j, other in enumerate(token_sets) if j != i)
            scores.append(overlap / max(1, len(sentences) - 1))
        return scores


def rank_sentences(text, target_keyword: str = "", top_n: int = 12):
    sentences = split_sentences(text) if isinstance(text, str) else list(text or [])
    sentences = [s for s in sentences if 25 <= len(s) <= 320][:200]
    if not sentences:
        return []
    centrality = _centrality_scores(sentences)
    kw_tokens = set(tokenize(target_keyword, drop_stopwords=True))

    ranked = []
    for sent, central in zip(sentences, centrality):
        tokens = set(tokenize(sent, drop_stopwords=True))
        kw_density = len(tokens & kw_tokens) / len(kw_tokens) if kw_tokens else 0.0
        buyer = min(1.0, 0.25 * len(tokens & ACTION_WORDS))
        readability = flesch_reading_ease(sent) / 100.0
        length_fit = 1.0 if 40 <= len(sent) <= 180 else 0.55
        uniqueness = 1.0 - min(0.6, central * 0.5)  # too central often = boilerplate
        score = (0.26 * central + 0.22 * kw_density + 0.20 * buyer +
                 0.14 * readability + 0.10 * length_fit + 0.08 * uniqueness)
        ranked.append({
            "sentence": sent,
            "score": round(score * 100, 1),
            "title_potential": len(sent) <= 80 and (kw_density > 0 or buyer > 0),
            "description_potential": 60 <= len(sent) <= 240,
            "breakdown": {"relevance": round(central, 2), "keyword_fit": round(kw_density, 2),
                          "buyer_intent": round(buyer, 2), "readability": round(readability, 2)},
        })
    ranked.sort(key=lambda r: -r["score"])

    deduped, seen = [], []
    for item in ranked:
        sig = set(tokenize(item["sentence"], drop_stopwords=True))
        if any(len(sig & s) / (len(sig | s) or 1) > 0.8 for s in seen):
            continue
        seen.append(sig)
        deduped.append(item)
        if len(deduped) >= top_n:
            break
    return deduped
