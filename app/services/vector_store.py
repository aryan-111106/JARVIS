import json
import os
from typing import List

import faiss
import numpy as np
from sentence_transformers import SentenceTransformer

from config import CHATS_DIR, LEARNING_DIR, VECTOR_STORE_DIR

INDEX_PATH = os.path.join(VECTOR_STORE_DIR, "faiss.index")
CHUNKS_PATH = os.path.join(VECTOR_STORE_DIR, "chunks.json")
META_PATH = os.path.join(VECTOR_STORE_DIR, "meta.json")


class VectorStore:
    """FAISS + sentence-transformers; persisted under database/vector_store/."""

    def __init__(self) -> None:
        print("Loading embedding model...")
        self.model = SentenceTransformer("all-MiniLM-L6-v2")
        self.dimension = self.model.get_sentence_embedding_dimension()
        self.index = faiss.IndexFlatL2(self.dimension)
        self.chunks: List[str] = []
        self._load_or_build()

    def _load_or_build(self) -> None:
        if os.path.exists(INDEX_PATH) and os.path.exists(CHUNKS_PATH):
            try:
                with open(META_PATH, "r", encoding="utf-8") as f:
                    meta = json.load(f)
                if meta.get("dimension") != self.dimension:
                    raise ValueError("dimension mismatch")
                self.index = faiss.read_index(INDEX_PATH)
                with open(CHUNKS_PATH, "r", encoding="utf-8") as f:
                    self.chunks = json.load(f)
                print(f"Loaded vector store: {len(self.chunks)} chunks.")
                return
            except Exception as e:
                print(f"Vector store load failed, rebuilding: {e}")

        texts = self._collect_all_texts()
        if texts:
            embeddings = self.model.encode(texts)
            self.index.add(np.array(embeddings).astype("float32"))
            self.chunks = texts
            print(f"Indexed {len(texts)} memories into JARVIS Brain.")
        self._persist()

    def _collect_all_texts(self) -> List[str]:
        texts: List[str] = []
        if os.path.exists(LEARNING_DIR):
            for file in os.listdir(LEARNING_DIR):
                if file.endswith(".txt"):
                    try:
                        with open(
                            os.path.join(LEARNING_DIR, file), "r", encoding="utf-8"
                        ) as f:
                            content = f.read()
                            lines = [
                                line.strip()
                                for line in content.split("\n")
                                if len(line.strip()) > 3
                            ]
                            texts.extend(lines)
                    except Exception as e:
                        print(f"Error reading learning data {file}: {e}")

        if os.path.exists(CHATS_DIR):
            for file in os.listdir(CHATS_DIR):
                if file.endswith(".json"):
                    try:
                        with open(
                            os.path.join(CHATS_DIR, file), "r", encoding="utf-8"
                        ) as f:
                            chat = json.load(f)
                            for msg in chat.get("messages", []):
                                texts.append(f"{msg['role']}: {msg['content']}")
                    except Exception:
                        pass
        return texts

    def _persist(self) -> None:
        try:
            if len(self.chunks) == 0:
                return
            faiss.write_index(self.index, INDEX_PATH)
            with open(CHUNKS_PATH, "w", encoding="utf-8") as f:
                json.dump(self.chunks, f)
            with open(META_PATH, "w", encoding="utf-8") as f:
                json.dump({"dimension": self.dimension}, f)
        except Exception as e:
            print(f"Vector store persist error: {e}")

    def add_memory(self, role: str, content: str) -> None:
        text = f"{role}: {content}"
        embedding = self.model.encode([text])
        self.index.add(np.array(embedding).astype("float32"))
        self.chunks.append(text)
        self._persist()

    def search(self, query: str, k: int = 5) -> str:
        if not self.chunks:
            return ""
        query_vector = self.model.encode([query]).astype("float32")
        distances, indices = self.index.search(query_vector, min(k, len(self.chunks)))
        results = [self.chunks[i] for i in indices[0] if i < len(self.chunks)]
        return "\n".join(results)

    def rebuild_from_disk(self) -> None:
        """Delete persisted files and rebuild from learning_data + chats_data."""
        for p in (INDEX_PATH, CHUNKS_PATH, META_PATH):
            if os.path.exists(p):
                os.remove(p)
        self.index = faiss.IndexFlatL2(self.dimension)
        self.chunks = []
        texts = self._collect_all_texts()
        if texts:
            embeddings = self.model.encode(texts)
            self.index.add(np.array(embeddings).astype("float32"))
            self.chunks = texts
        self._persist()
        print(f"Rebuilt vector store: {len(self.chunks)} chunks.")


vector_store = VectorStore()
