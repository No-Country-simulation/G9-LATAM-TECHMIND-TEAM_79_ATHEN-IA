import json
import os
import chromadb
from chromadb.utils import embedding_functions

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
JSON_PATH = os.path.join(BASE_DIR, "Data", "cursos_dataset.json")
VECTOR_DB_DIR = os.path.join(BASE_DIR, "backend", "app", "data", "vector_db")

embedding_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
    model_name="paraphrase-multilingual-MiniLM-L12-v2"
)

client = chromadb.PersistentClient(path=VECTOR_DB_DIR)
collection = client.get_or_create_collection(
    name="athenex_courses",
    embedding_function=embedding_fn
)

def build_index():
    print(f"Cargando dataset desde {JSON_PATH}...")
    if not os.path.exists(JSON_PATH):
        print(f"❌ Error: No se encontró el archivo en {JSON_PATH}")
        return

    with open(JSON_PATH, "r", encoding="utf-8") as f:
        courses = json.load(f)

    documents = []
    metadatas = []
    ids = []

    print("Procesando datos e IDs únicos...")
    for idx, item in enumerate(courses):
        text_to_embed = item.get("full_text") or f"{item.get('clean_title', '')} {item.get('clean_skills', '')} {item.get('clean_intro', '')}"
        
        documents.append(text_to_embed)
        metadatas.append({
        # Usa las claves según tu dataset JSON (ej: Title, clean_title, etc.)
        "title": str(item.get("clean_title") or item.get("Title") or "Sin título"),
        "url": str(item.get("URL") or item.get("url") or ""),
        "site": str(item.get("clean_site") or item.get("Site") or "Desconocido"),
        "category": str(item.get("target_category") or item.get("Category") or "Otras Áreas"),
        "rating": str(item.get("Rating") or "N/A")
        })
        ids.append(f"course_{idx}")

    # Guardar por lotes
    batch_size = 500
    for i in range(0, len(documents), batch_size):
        collection.add(
            documents=documents[i:i+batch_size],
            metadatas=metadatas[i:i+batch_size],
            ids=ids[i:i+batch_size]
        )
        print(f"Indexados {i + len(documents[i:i+batch_size])} / {len(documents)} cursos...")

    print("¡Base vectorial generada exitosamente en backend/app/data/vector_db!")

if __name__ == "__main__":
    build_index()
