# src/retrieval/hybrid_search.py
import re

import chromadb
from rank_bm25 import BM25Okapi
from sentence_transformers import SentenceTransformer

CHROMA_PATH = "./chroma_db"
COLLECTION_NAME = "marches_publics"
EMBEDDING_MODEL = "paraphrase-multilingual-MiniLM-L12-v2"

# Reciprocal Rank Fusion constant. k=60 is the standard value from the
# original RRF paper (Cormack et al.) and needs no tuning for this corpus size.
RRF_K = 60

# How many candidates each individual ranking (dense, BM25) contributes
# to the fusion pool before RRF picks the final n_results.
FUSION_POOL_SIZE = 20


def _tokenize(text):
    return re.findall(r"\w+", text.lower())


def build_bm25_index(collection):
    """
    Builds a BM25 index over every chunk currently stored in the given
    ChromaDB collection, reusing the same ids/documents/metadatas as the
    dense index so rankings can be fused by id afterwards.
    """
    data = collection.get(include=["documents", "metadatas"])
    ids = data["ids"]
    documents = data["documents"]
    metadatas = data["metadatas"]

    tokenized_corpus = [_tokenize(doc) for doc in documents]
    bm25 = BM25Okapi(tokenized_corpus)

    return bm25, ids, documents, metadatas


def hybrid_retrieve_with_resources(question, model, collection, bm25_index, n_results=3):
    """
    Same as hybrid_retrieve(), but takes an already-loaded embedding
    model, ChromaDB collection and BM25 index instead of loading them —
    for callers (like the Streamlit app) that cache those resources
    themselves and want to reuse them across calls.

    a) dense search via the collection's embedding index
    b) BM25 keyword search over the same chunks
    c) fuses both rankings with Reciprocal Rank Fusion (RRF, k=60) — RRF
       only uses each ranking's positions, so the very different score
       scales of cosine distance and BM25 never need to be normalized
       against each other
    d) returns the top n_results fused chunks
    """
    bm25, ids, documents, metadatas = bm25_index
    pool_size = min(FUSION_POOL_SIZE, len(ids))

    # a) dense ranking
    query_embedding = model.encode([question]).tolist()
    dense_results = collection.query(query_embeddings=query_embedding, n_results=pool_size)
    dense_ranking = dense_results["ids"][0]

    # b) BM25 ranking
    tokenized_query = _tokenize(question)
    bm25_scores = bm25.get_scores(tokenized_query)
    bm25_order = sorted(range(len(ids)), key=lambda i: bm25_scores[i], reverse=True)
    bm25_ranking = [ids[i] for i in bm25_order[:pool_size]]

    # c) Reciprocal Rank Fusion
    rrf_scores = {}
    for ranking in (dense_ranking, bm25_ranking):
        for rank, doc_id in enumerate(ranking, start=1):
            rrf_scores[doc_id] = rrf_scores.get(doc_id, 0) + 1 / (RRF_K + rank)

    fused_ids = sorted(rrf_scores, key=rrf_scores.get, reverse=True)[:n_results]

    # d) build the result chunks, same shape as retrieve()
    id_to_index = {doc_id: i for i, doc_id in enumerate(ids)}
    chunks = []
    for doc_id in fused_ids:
        idx = id_to_index[doc_id]
        metadata = metadatas[idx]
        chunks.append({
            "text": documents[idx],
            "document": metadata.get("document", "N/A"),
            "document_type": metadata.get("document_type", "N/A"),
            "article": metadata.get("article", "N/A"),
        })
    return chunks


def hybrid_retrieve(question, n_results=3):
    """
    Retrieves the n_results chunks most relevant to the question by
    combining dense (embedding) search and BM25 keyword search. Loads
    its own model/collection/BM25 index on every call — self-contained,
    for one-off use (e.g. the evaluation script).
    """
    model = SentenceTransformer(EMBEDDING_MODEL)
    client = chromadb.PersistentClient(path=CHROMA_PATH)
    collection = client.get_collection(COLLECTION_NAME)
    bm25_index = build_bm25_index(collection)

    return hybrid_retrieve_with_resources(question, model, collection, bm25_index, n_results)
