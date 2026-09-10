# evaluate_retrieval.py
import chromadb
from sentence_transformers import SentenceTransformer

CHROMA_PATH = "./chroma_db"
COLLECTION_NAME = "marches_publics"
EMBEDDING_MODEL = "paraphrase-multilingual-MiniLM-L12-v2"

# Test set: each entry has a question and the article expected to appear
# in the top results. "document_type" narrows which corpus it belongs to,
# used only for readability in the report, not for filtering the search.
TEST_QUESTIONS = [
    {"question": "Quel est le délai de publication d'un avis d'appel d'offres ?", "expected_article": "Article 50", "document_type": "Décret"},
    {"question": "Quels sont les principes généraux de la passation des marchés publics ?", "expected_article": "Article premier", "document_type": "Décret"},
    {"question": "Comment sont définies les marchés à tranches conditionnelles ?", "expected_article": "Article 9", "document_type": "Décret"},
    {"question": "Dans quel délai le marché doit-il être approuvé après signature ?", "expected_article": "Article 143", "document_type": "Décret"},
    {"question": "Quelles sont les conditions de résiliation en cas d'incapacité civile du titulaire ?", "expected_article": "Article 30", "document_type": "CCAG-EMO"},
    {"question": "Qu'est-ce qu'un marché-cadre ?", "expected_article": "Article 7", "document_type": "Décret"},
    {"question": "Quel est le délai pour établir un décompte provisoire ?", "expected_article": "Article 41", "document_type": "CCAG"},
    {"question": "Comment est restituée la retenue de garantie ?", "expected_article": "Article 16", "document_type": "CCAG"},
    {"question": "Quelles assurances le titulaire doit-il souscrire ?", "expected_article": "Article 20", "document_type": "CCAG"},
    {"question": "Quelles sont les conditions de résiliation en cas de décès du titulaire ?", "expected_article": "Article 29", "document_type": "CCAG"},
    {"question": "Quel délai le maître d'ouvrage a-t-il pour vérifier les documents remis par le titulaire ?", "expected_article": "Article 47", "document_type": "CCAG"},
    {"question": "Que se passe-t-il si un fournisseur ne peut plus honorer son contrat pour raison de santé ?", "expected_article": "Article 30", "document_type": "CCAG-EMO"},
    {"question": "Est-ce que je peux céder mon marché à une autre entreprise ?", "expected_article": "Article 25", "document_type": "CCAG"},
    {"question": "Quelles pénalités en cas de retard dans l'exécution du contrat ?", "expected_article": "Article 42", "document_type": "CCAG"},
    {"question": "Quel est l'objectif de la révision des prix dans un marché public ?", "expected_article": "Article 2", "document_type": "Arrêté 3-205-14"},
    {"question": "Quel délai le maître d'ouvrage a-t-il pour effectuer les vérifications lors de la réception provisoire des travaux ?", "expected_article": "Article 73", "document_type": "CCAG-Travaux"},
    {"question": "Dans quel délai le maître d'ouvrage doit-il remettre à l'entrepreneur les pièces constitutives du marché ?", "expected_article": "Article 13", "document_type": "CCAG-Travaux"},
]


def retrieve(question, n_results=5):
    model = SentenceTransformer(EMBEDDING_MODEL)
    client = chromadb.PersistentClient(path=CHROMA_PATH)
    collection = client.get_collection(COLLECTION_NAME)

    query_embedding = model.encode([question]).tolist()
    results = collection.query(query_embeddings=query_embedding, n_results=n_results)

    articles = []
    for i in range(len(results["documents"][0])):
        metadata = results["metadatas"][0][i]
        articles.append(metadata.get("article", "N/A"))
    return articles


def run_evaluation():
    model = SentenceTransformer(EMBEDDING_MODEL)
    client = chromadb.PersistentClient(path=CHROMA_PATH)
    collection = client.get_collection(COLLECTION_NAME)

    top1_correct = 0
    top3_correct = 0
    total = len(TEST_QUESTIONS)

    print(f"Running evaluation on {total} questions...\n")

    for item in TEST_QUESTIONS:
        question = item["question"]
        expected = item["expected_article"]

        query_embedding = model.encode([question]).tolist()
        results = collection.query(query_embeddings=query_embedding, n_results=5)

        found_articles = [
            results["metadatas"][0][i].get("article", "N/A")
            for i in range(len(results["documents"][0]))
        ]

        is_top1 = found_articles[0] == expected
        is_top3 = expected in found_articles[:3]

        if is_top1:
            top1_correct += 1
        if is_top3:
            top3_correct += 1

        status = "OK (top1)" if is_top1 else ("OK (top3)" if is_top3 else "MISS")
        print(f"[{status}] {question}")
        print(f"   Attendu: {expected} | Trouvé: {found_articles[:3]}")
        print()

    print("=" * 60)
    print(f"Précision au rang 1 : {top1_correct}/{total} ({100 * top1_correct / total:.0f}%)")
    print(f"Précision au rang 3 : {top3_correct}/{total} ({100 * top3_correct / total:.0f}%)")


if __name__ == "__main__":
    run_evaluation()