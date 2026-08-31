import time 
import logfire
from flashrank import Ranker, RerankRequest

_ranker = None

def _get_ranker() -> Ranker:
    """
    Initializes the FlashRank engine lazily. 
    FlashRank uses a local ONNX model (ms-marco-MiniLM-L-6-v2) for ultra-fast reranking.
    """
    global _ranker
    if _ranker is None:
        logfire.info("Initializing Flashrank model (TinyBERT) locally...")
        try:
            _ranker = Ranker(cache_dir="/tmp/flashrank")
        except Exception as e:
            _ranker = Ranker()
    return _ranker


def rank_documents(query: str, documents: list[str], top_no: int = 5) -> list[str]:
    """
    Refines retrieval results by re-scoring documents against the query semantically.
    
    Why FlashRank? 
    Standard vector search (Cosine Similarity) is fast but mathematically "fuzzy."
    FlashRank uses a Cross-Encoder approach which is much more precise but usually slow.
    FlashRank solves this by using highly optimized, quantized ONNX models locally.
    """

    if not documents:
        return []
    
    start_time = time.time()
    logfire.info(f"[Reranker] sending {len(documents)} doc to Reranker Cross-Encoding...")

    try:
        ranker = _get_ranker()

        passages = [ {"id": i, "text": doc} for i, doc in enumerate(documents) ]

        request = RerankRequest(query=query, passages=passages)
        results = ranker.rerank(request)

        ranked_docs = []
        for res in results[:top_no]:
            ranked_docs.append(res["text"])

        duration = time.time() - start_time
        top_score = results[0]["score"] if results else "N/A"
        logfire.info(f"[Reranker] reranking in {duration:.2f}s and Top Semantic score: {top_score}")

        return ranked_docs
    except Exception as e:
        logfire.error(f"[Rerank] Failed: {e}")
        return documents[:top_no]