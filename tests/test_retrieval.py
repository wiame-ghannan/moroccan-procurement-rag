import chromadb

# Connexion à ta base persistante (adapte le path si besoin)
client = chromadb.PersistentClient(path="./chroma_db")  # ou le path que tu utilises
collection = client.get_collection("marches_publics")

# Questions de test représentatives de ton domaine
questions = [
    "seuil de passation en appel d'offres",
    "délai de publication d'un avis d'appel d'offres",
    "conditions d'exclusion d'un soumissionnaire",
]

for q in questions:
    print(f"\n{'='*60}")
    print(f"QUESTION: {q}")
    print('='*60)
    
    results = collection.query(
        query_texts=[q],
        n_results=3
    )
    
    for i, (doc, metadata, distance) in enumerate(zip(
        results['documents'][0],
        results['metadatas'][0],
        results['distances'][0]
    )):
        document = metadata.get('document', 'N/A')
        document_type = metadata.get('document_type')
        source = f"{document} ({document_type})" if document_type else document

        print(f"\n--- Résultat {i+1} (distance: {distance:.3f}) ---")
        print(f"Source: {source}")
        print(f"Article: {metadata.get('article', 'N/A')}")
        print(f"Texte: {doc[:200]}...")  # Affiche les 200 premiers caractères