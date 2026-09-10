# src/documents_registry.py
"""
Central registry of all documents to process.
Adding a new document means adding one entry here —
never touching the ingestion or parsing code itself.
"""

DOCUMENTS = [
    {
        "category": "01_Socle_Decret_Principal",
        "pdf_filename": "Decret_marches_publics_n_2_22_431_du_09_03_2023_Fr.pdf",
        "document_name": "Décret relatif aux marchés publics",
        "document_type": "Décret",
        "document_number": "2-22-431",
        "expected_max_articles": 170,
    },
    {
        "category": "02_Execution_Administrative_CCAG",
        "pdf_filename": "CCAG_EMO.pdf",
        "document_name": "CCAG applicable aux marchés de services d'études et de maîtrise d'œuvre",
        "document_type": "CCAG",
        "document_number": "2-01-2332",
        "expected_max_articles": 55,
    },
    {
        "category": "02_Execution_Administrative_CCAG",
        "pdf_filename": "CCAG_Travaux.pdf",  # adapte au nom exact de ton fichier
        "document_name": "CCAG applicable aux marchés de travaux",
        "document_type": "CCAG",
        "document_number": "2-14-394",
        "expected_max_articles": 60,  # à ajuster une fois qu'on connaîtra le vrai nombre
    },
    {
        "pdf_filename": "Arrete_3-205-14_Revision_Prix.pdf",
        "document_name": "Arrêté fixant les règles et conditions de révision des prix des marchés publics",
        "document_type": "Arrêté",
        "document_number": "3-205-14",
        "category": "04_Finances_et_Delais",
        "expected_max_articles": 15,
    },
]
