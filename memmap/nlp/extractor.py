"""
Entity and relation extraction using spaCy NLP models.
Tries pt_core_news_sm first, falls back to en_core_web_sm.
"""

from loguru import logger
import spacy
from spacy.language import Language

_nlp: Language | None = None
_model_name: str = ""


def load_model() -> tuple[Language, str]:
    """Load the best available spaCy model."""
    global _nlp, _model_name
    if _nlp is not None:
        return _nlp, _model_name

    for model in ("pt_core_news_sm", "en_core_web_sm"):
        try:
            _nlp = spacy.load(model)
            _model_name = model
            logger.info(f"Loaded spaCy model: {model}")
            return _nlp, _model_name
        except OSError:
            logger.warning(f"Model {model} not available, trying next...")

    raise RuntimeError(
        "No spaCy model available. Install en_core_web_sm: "
        "python -m spacy download en_core_web_sm"
    )


def extract_entities(text: str) -> list[dict]:
    """
    Extract named entities from text.

    Returns:
        List of dicts with keys: text, label, start, end
    """
    nlp, _ = load_model()
    doc = nlp(text)

    seen: set[str] = set()
    entities: list[dict] = []

    for ent in doc.ents:
        key = (ent.text.strip(), ent.label_)
        if key in seen:
            continue
        seen.add(key)
        entities.append(
            {
                "text": ent.text.strip(),
                "label": ent.label_,
                "start": ent.start_char,
                "end": ent.end_char,
            }
        )

    logger.debug(f"Extracted {len(entities)} entities from text of length {len(text)}")
    return entities


def extract_relations(text: str, entities: list[dict]) -> list[dict]:
    """
    Extract relations between entities by co-occurrence within the same sentence.

    Strategy: entities appearing in the same sentence are considered related.
    Returns list of dicts: {source, target, context}
    """
    nlp, _ = load_model()
    doc = nlp(text)

    relations: list[dict] = []
    seen_pairs: set[frozenset] = set()

    entity_texts = {e["text"] for e in entities}

    for sent in doc.sents:
        sent_text = sent.text
        # Find which entities appear in this sentence
        sent_entities = [
            e["text"]
            for e in entities
            if e["text"] in sent_text
        ]

        # Deduplicate while preserving order
        unique_sent_ents = list(dict.fromkeys(sent_entities))

        # Create pairs of co-occurring entities
        for i in range(len(unique_sent_ents)):
            for j in range(i + 1, len(unique_sent_ents)):
                src = unique_sent_ents[i]
                tgt = unique_sent_ents[j]

                pair = frozenset({src, tgt})
                if pair in seen_pairs:
                    continue
                seen_pairs.add(pair)

                # Trim context to 200 chars
                context = sent_text.strip()
                if len(context) > 200:
                    context = context[:197] + "..."

                relations.append(
                    {
                        "source": src,
                        "target": tgt,
                        "context": context,
                    }
                )

    logger.debug(f"Extracted {len(relations)} relations from {len(entities)} entities")
    return relations
