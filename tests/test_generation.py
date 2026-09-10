# test_generation.py
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import chromadb
from sentence_transformers import SentenceTransformer
from src.generation.llm_client import generate_answer

CHROMA_PATH = "./chroma_db"
COLLECTION_NAME = "marches_publics"
EMBEDDING_MODEL = "paraphrase-multilingual-MiniLM-L12-v2"


def retrieve(question, n_results=3):
    model = SentenceTransformer(EMBEDDING_MODEL)
    client = chromadb.PersistentClient(path=CHROMA_PATH)
    collection = client.get_collection(COLLECTION_NAME)

    query_embedding = model.encode([question]).tolist()
    results = collection.query(query_embeddings=query_embedding, n_results=n_results)

    chunks = []
    for i in range(len(results["documents"][0])):
        metadata = results["metadatas"][0][i]
        chunks.append({
            "text": results["documents"][0][i],
            "document": metadata.get("document", "N/A"),
            "document_type": metadata.get("document_type", "N/A"),
            "article": metadata.get("article", "N/A"),
        })
    return chunks


if __name__ == "__main__":
    question = "Quel est le délai de publication d'un avis d'appel d'offres ?"

    print(f"Question : {question}\n")
    chunks = retrieve(question)

    print("--- Contexte récupéré ---")
    for c in chunks:
        print(f"  {c['article']} ({c['document_type']})")

    print("\n--- Réponse générée (OpenAI) ---")
    answer = generate_answer(question, chunks)
    print(answer)