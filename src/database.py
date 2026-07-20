import os
import json
import sqlite3

# ChromaDB SQLite Version Check / Workaround
# If SQLite is older than 3.35.0, check if pysqlite3 is available to patch it
if sqlite3.sqlite_version_info < (3, 35, 0):
    try:
        __import__('pysqlite3')
        import sys
        sys.modules['sqlite3'] = sys.modules.pop('pysqlite3')
        print("[INFO]: SQLite version was outdated. Successfully patched using pysqlite3-binary.")
    except ImportError:
        print("[WARNING]: SQLite version is older than 3.35.0, and pysqlite3-binary is not installed. ChromaDB may fail to load.")

import chromadb
from chromadb.utils import embedding_functions
from src.config import DB_PERSIST_PATH, FACTS_JSON_PATH

def get_chroma_client():
    """Initializes and returns a persistent ChromaDB client saving to disk."""
    os.makedirs(DB_PERSIST_PATH, exist_ok=True)
    return chromadb.PersistentClient(path=DB_PERSIST_PATH)

def get_embedding_function():
    """Returns the default embedding function for vectorizing text."""
    # ChromaDB's default uses sentence-transformers (all-MiniLM-L6-v2)
    return embedding_functions.DefaultEmbeddingFunction()

def setup_and_populate_db(json_file_path=FACTS_JSON_PATH):
    """
    Reads the offline JSON facts, creates a collection, and populates it.
    This runs on startup to make sure facts are vectorized.
    """
    client = get_chroma_client()
    embedding_fn = get_embedding_function()

    # Get or create the sports facts collection
    collection = client.get_or_create_collection(
        name="sports_history",
        embedding_function=embedding_fn
    )

    # Check if database is already populated
    if collection.count() > 0:
        print(f"[INFO]: Database already populated with {collection.count()} facts.")
        return collection

    # Check if raw data file exists
    if not os.path.exists(json_file_path):
        print(f"[WARNING]: Raw fact data file not found at {json_file_path}. Initializing empty collection.")
        return collection

    try:
        with open(json_file_path, "r", encoding="utf-8") as f:
            facts_list = json.load(f)
    except Exception as e:
        print(f"[ERROR]: Failed to parse JSON data file: {e}")
        return collection

    documents = []
    metadata_list = []
    ids = []

    for idx, item in enumerate(facts_list):
        if "fact" in item and "sport" in item:
            documents.append(item["fact"])
            metadata_list.append({"sport": item["sport"]})
            ids.append(f"fact_{idx}")

    if documents:
        collection.add(
            documents=documents,
            metadatas=metadata_list,
            ids=ids
        )
        print(f"[INFO]: Successfully vectorized and stored {len(documents)} facts.")
    
    return collection

def query_historic_facts(sport, query_text, n_results=2):
    """
    Queries ChromaDB for historic documents relating to a sport.
    Filters database elements to match the selected sport category using metadata.
    """
    client = get_chroma_client()
    embedding_fn = get_embedding_function()
    collection = client.get_or_create_collection(
        name="sports_history",
        embedding_function=embedding_fn
    )

    if collection.count() == 0:
        return []

    try:
        # Query with metadata filtering so we only get facts for the chosen sport
        results = collection.query(
            query_texts=[query_text],
            n_results=n_results,
            where={"sport": sport}
        )
        # Return matched documents list (or empty list if none found)
        docs = results.get("documents", [[]])
        if docs and len(docs) > 0:
            return docs[0]
    except Exception as e:
        print(f"[ERROR]: Query to vector database failed: {e}")
    
    return []

def add_custom_fact(sport, fact_text):
    """
    Adds a custom fact dynamically to ChromaDB.
    """
    client = get_chroma_client()
    embedding_fn = get_embedding_function()
    collection = client.get_or_create_collection(
        name="sports_history",
        embedding_function=embedding_fn
    )

    # Generate a unique ID based on existing count
    new_id = f"fact_custom_{collection.count() + 1}"
    
    collection.add(
        documents=[fact_text],
        metadatas=[{"sport": sport}],
        ids=[new_id]
    )
    print(f"[INFO]: Added custom fact to DB: [{sport}] {fact_text[:50]}...")
    return new_id

def get_all_facts():
    """
    Retrieves all documents and metadatas currently in the database.
    """
    client = get_chroma_client()
    embedding_fn = get_embedding_function()
    collection = client.get_or_create_collection(
        name="sports_history",
        embedding_function=embedding_fn
    )
    
    data = collection.get()
    facts = []
    if data and "documents" in data:
        for idx in range(len(data["documents"])):
            facts.append({
                "id": data["ids"][idx],
                "sport": data["metadatas"][idx]["sport"] if data["metadatas"] else "Unknown",
                "fact": data["documents"][idx]
            })
    return facts
