import os 
import uuid
import json
import sys
import logfire

from qdrant_client import QdrantClient
from qdrant_client.http import models

from app.config import settings
from app.services.retrieval.embeddings import get_embedding_dim, embed_texts
from app.ingestion.chunking.splitter import chunk_text

logfire.configure(service_name="rag-ingestion")

PROCESSED_DATA_DIR = "processed_data"

qdrant_client = QdrantClient(
    url=settings.QDRANT_URL,
    api_key=settings.QDRANT_API_KEY
)


def save_processed_locally(data: dict, source_type: str, filename: str) -> str:
    folder = os.path.join(PROCESSED_DATA_DIR, source_type)
    os.makedirs(folder, exist_ok=True)
    destination = os.path.join(folder, f"{filename}.json")
    with open(destination, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return destination


def process_file(file_path: str, filename: str, source_type: str):
    with logfire.span("Processing File", file=filename, source=source_type):
        try:
            extension = filename.lower().rsplit(".", 1)[-1]
            if extension == "pdf":
                from app.ingestion.loaders.pdf import parse_pdf
                full_text = parse_pdf(file_path)
            elif extension in ("html", "htm"):
                from app.ingestion.loaders.html import parse_html
                full_text = parse_html(file_path)
            elif extension == "txt":
                from app.ingestion.loaders.text import parse_text
                full_text = parse_text(file_path)
            elif extension in ("docx", "pptx"):
                from app.ingestion.loaders.office import parse_office
                full_text = parse_office(file_path)
            else:
                logfire.warning(f"Skipping the Unsupported type {filename}")
                return

            if not full_text or not full_text.strip():
                logfire.warning(f"No text extracted from {filename} - skipping")
                return 

            chunks = chunk_text(full_text)
            if not chunks:
                return

            processed_data = {
                "filename": filename,
                "source_type": source_type,
                "chunks": chunks
            }
            local_path = save_processed_locally(processed_data, source_type, filename)
            logfire.info(f"Saving Processed Data Locally -> {local_path}")

            with logfire.span("Vectorising and Indexing"):
                embeddings = embed_texts(chunks)
                points = [
                    models.PointStruct(
                        id = str(uuid.uuid4()),
                        vector=vector,
                        payload={
                            "text": chunk,
                            "source": filename,
                            "source_type": source_type,
                        },
                    )
                    for chunk, vector in zip(chunks, embeddings)
                ]

                qdrant_client.upsert(
                    collection_name=settings.QDRANT_COLLECTION,
                    points=points,
                )
                logfire.info(f"Indexed {len(points)} points in qdrant from {filename}")

        except Exception as e:
            logfire.error(f"Failed to process {filename}: {e}")


def process_directory(dir_path: str, source_type: str):
    with logfire.span("Processing Directory", path=dir_path, source=source_type):
        files = [f for f in os.listdir(dir_path) if os.path.isfile(os.path.join(dir_path, f))]
        logfire.info(f"Found {len(files)} files in {dir_path}")
        for filename in files:
            process_file(os.path.join(dir_path, filename), filename, source_type)


def run_universal_ingestion(base_dir: str, explicit_source_type: str = None, wipe: bool = False):
    with logfire.span("Universl Ingestion strated", base_directory=base_dir):
        if wipe:
            with logfire.span("Wiping Collection"):
                if qdrant_client.collection_exists(settings.QDRANT_COLLECTION):
                    qdrant_client.delete_collection(settings.QDRANT_COLLECTION)
                    logfire.info(f"Collection {settings.QDRANT_COLLECTION} deleted")

        if not qdrant_client.collection_exists(settings.QDRANT_COLLECTION):
            dimensions = get_embedding_dim()
            qdrant_client.create_collection(
                collection_name=settings.QDRANT_COLLECTION,
                vectors_config=models.VectorParams(
                    size=dimensions,
                    distance=models.Distance.COSINE,
                ),
            )
            logfire.info(
                f"Created Collection: {settings.QDRANT_COLLECTION}"
                f"{dimensions}-dimension, Cosine"
            )

        subdirs = [d for d in os.listdir(base_dir) if os.path.isdir(os.path.join(base_dir, d))]

        if not subdirs:
            if explicit_source_type:
                source_type = explicit_source_type
            else:
                base_name = os.path.basename(os.path.normpath(base_dir)).lower()
                source_type = ("true" if "true" in base_name else "noisy" if "noisy" in base_name else "general")
            logfire.info(f"No sub folder found processing '{base_dir}' as '{source_type}' ")
            process_directory(base_dir, source_type)
        else:
            for subdir in subdirs:
                source_type = ("true" if "true" in subdir.lower() else "noisy" if "noisy" in subdir.lower() else subdir)
                process_directory(os.path.join(base_dir, subdir), source_type)


if __name__=="__main__":
    wipe_required = "--wipe" in sys.argv
    clean_args = [a for a in sys.argv if a != "--wipe"]

    target_dir = clean_args[1] if len(clean_args) > 1 else "DATA"
    explicit_type = clean_args[2] if len(clean_args) > 2 else None

    if not os.path.exists(target_dir):
        print(f"Error {target_dir} does not exist")
        sys.exit(1)

    run_universal_ingestion(target_dir, explicit_type, wipe_required)
    logfire.info("Ingestion job Completed")