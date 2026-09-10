# src/indexing/build_index.py
import chromadb
from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction
from src.indexing.simple_chunking import build_nodes

CHROMA_PATH = "./chroma_db"
COLLECTION_NAME = "marches_publics"
# Multilingual model: all-MiniLM-L6-v2 is English-centric and performed poorly
# on French legal text (relevant articles ranked ~90th/236 on exclusion-related
# queries). This model is trained on 50+ languages including French.
# MiniLM-L12 (~470MB) over mpnet-base (~1GB) to fit free-tier deployment RAM.
EMBEDDING_MODEL = "paraphrase-multilingual-MiniLM-L12-v2"


def build_and_store_index():
    """
    Loads all chunks, computes their embeddings, and stores everything
    in a local ChromaDB collection ready for semantic search.

    This is a full rebuild, not an incremental update: the existing
    collection is dropped and recreated from scratch on every call (see
    the delete_collection() below), re-embedding every chunk every time.
    There is no logic here to add/update/remove individual documents
    without reprocessing the whole corpus.
    """
    print("Loading chunks...")
    nodes = build_nodes()
    print(f"{len(nodes)} chunks to index")

    print(f"Loading embedding model ({EMBEDDING_MODEL})...")
    # Attached to the collection so that collection.query(query_texts=...)
    # embeds queries with this same model later, in this script and in any
    # other script that does client.get_collection(COLLECTION_NAME).
    embedding_function = SentenceTransformerEmbeddingFunction(model_name=EMBEDDING_MODEL)

    print("Connecting to ChromaDB...")
    client = chromadb.PersistentClient(path=CHROMA_PATH)

    # Full rebuild every time (not incremental) — see docstring above.
    try:
        client.delete_collection(COLLECTION_NAME)
    except Exception:
        pass
    collection = client.create_collection(COLLECTION_NAME, embedding_function=embedding_function)

    print("Computing embeddings and storing chunks...")
    # Some source PDFs bundle several legal texts that each restart their own
    # article numbering (e.g. "Article premier", "Article 2"...), so the
    # content-derived article_id can collide across those texts. Track ids
    # actually used and disambiguate collisions with a counter suffix.
    seen_ids = {}
    batch_size = 32
    for i in range(0, len(nodes), batch_size):
        batch = nodes[i:i + batch_size]
        texts = [node.text for node in batch]
        embeddings = embedding_function(texts)

        ids = []
        metadatas = []
        for j, node in enumerate(batch):
            # Chroma requires a unique string id per entry
            base_id = node.metadata.get("article_id", f"chunk_{i + j}")
            chunk_part = node.metadata.get("chunk_part", "")
            unique_id = f"{base_id}_{chunk_part}" if chunk_part else base_id

            if unique_id in seen_ids:
                seen_ids[unique_id] += 1
                unique_id = f"{unique_id}_dup{seen_ids[unique_id]}"
            else:
                seen_ids[unique_id] = 0

            ids.append(unique_id)

            # Chroma metadata values must be str/int/float/bool, not None
            clean_metadata = {
                k: (v if v is not None else "")
                for k, v in node.metadata.items()
            }
            metadatas.append(clean_metadata)

        collection.add(
            ids=ids,
            embeddings=embeddings,
            documents=texts,
            metadatas=metadatas,
        )

        print(f"  Indexed {min(i + batch_size, len(nodes))}/{len(nodes)}")

    print(f"\nDone. Collection '{COLLECTION_NAME}' now contains {collection.count()} chunks.")
    return collection


if __name__ == "__main__":
    build_and_store_index()