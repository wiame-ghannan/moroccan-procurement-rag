# src/indexing/backfill_source_metadata.py
"""
One-off migration: adds the "source" metadata field to chunks that were
indexed before parse_legal_text() started emitting it. Only touches
metadata (no re-embedding, no re-parsing).
"""
import chromadb

CHROMA_PATH = "./chroma_db"
COLLECTION_NAME = "marches_publics"


def backfill_source():
    client = chromadb.PersistentClient(path=CHROMA_PATH)
    collection = client.get_collection(COLLECTION_NAME)

    existing = collection.get(include=["metadatas"])
    ids = existing["ids"]
    metadatas = existing["metadatas"]

    updated_metadatas = []
    missing_number = []
    for chunk_id, metadata in zip(ids, metadatas):
        document_type = metadata.get("document_type", "")
        document_number = metadata.get("document_number", "")
        document_name = metadata.get("document", "")

        if document_number:
            source = f"{document_type} n° {document_number}".strip()
        else:
            source = document_name
            missing_number.append(chunk_id)

        new_metadata = dict(metadata)
        new_metadata["source"] = source
        updated_metadatas.append(new_metadata)

    collection.update(ids=ids, metadatas=updated_metadatas)

    print(f"{len(ids)} chunks mis à jour avec le champ 'source'.")
    if missing_number:
        print(f"ATTENTION - {len(missing_number)} chunks sans document_number, "
              f"'source' repli sur le nom du document: {missing_number[:5]}...")

    sample = collection.get(limit=3, include=["metadatas"])
    print("\nAperçu après mise à jour:")
    for m in sample["metadatas"]:
        print(f"  source={m.get('source')!r}  article={m.get('article')!r}")


if __name__ == "__main__":
    backfill_source()
