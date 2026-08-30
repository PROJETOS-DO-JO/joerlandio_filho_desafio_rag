"""
Etapas 3-4 do fluxo: transformar chunks em embeddings e permitir a busca
por similaridade, com persistência do índice em disco (extensão opcional).

Modelo escolhido: sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2
  - Público, gratuito, não exige API key.
  - Multilíngue: funciona bem para perguntas em português sobre documentação
    em inglês (caso deste desafio).
  - Limite de 128 tokens por texto, compatível com os chunks de ~60-90 palavras
    adotados aqui.

A similaridade usada é a cosseno. Como os embeddings são normalizados
(normalize_embeddings=True), o produto escalar entre dois vetores já é
equivalente à similaridade cosseno, então basta multiplicar as matrizes.
"""
import json
from pathlib import Path

import numpy as np

MODEL_NAME = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"


class RAGIndex:
    def __init__(self, model_name: str = MODEL_NAME):
        self.model_name = model_name
        self._model = None
        self.chunks = []  # metadados + texto de cada chunk (lista alinhada com embeddings)
        self.embeddings = None  # np.ndarray (n_chunks, dim), normalizado

    @property
    def model(self):
        # Import tardio: evita carregar sentence-transformers/torch quando não é necessário
        # (ex.: mensagens de erro rápidas para corpus vazio).
        if self._model is None:
            from sentence_transformers import SentenceTransformer

            print(f"[indexer] Carregando modelo de embeddings: {self.model_name}")
            self._model = SentenceTransformer(self.model_name)
        return self._model

    def build(self, chunks):
        if not chunks:
            raise ValueError(
                "Nenhum chunk para indexar: o corpus está vazio (nenhum documento "
                "válido foi encontrado). Verifique a pasta docs/ do repositório."
            )
        self.chunks = chunks
        texts = [c["text"] for c in chunks]
        embeddings = self.model.encode(
            texts,
            batch_size=32,
            show_progress_bar=True,
            normalize_embeddings=True,
        )
        self.embeddings = np.asarray(embeddings, dtype="float32")

    def save(self, out_dir):
        if self.embeddings is None or not self.chunks:
            raise ValueError("Não há índice construído para salvar. Rode build() antes.")
        out_dir = Path(out_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        np.savez_compressed(out_dir / "embeddings.npz", embeddings=self.embeddings)
        with open(out_dir / "metadata.json", "w", encoding="utf-8") as f:
            json.dump(
                {"model_name": self.model_name, "chunks": self.chunks},
                f,
                ensure_ascii=False,
                indent=2,
            )
        print(f"[indexer] Índice salvo em {out_dir} ({len(self.chunks)} chunks).")

    @classmethod
    def load(cls, out_dir):
        out_dir = Path(out_dir)
        emb_path = out_dir / "embeddings.npz"
        meta_path = out_dir / "metadata.json"
        if not emb_path.exists() or not meta_path.exists():
            raise FileNotFoundError(
                f"Índice não encontrado em {out_dir}. Rode 'python build_index.py' primeiro."
            )
        data = np.load(emb_path)
        with open(meta_path, "r", encoding="utf-8") as f:
            meta = json.load(f)

        index = cls(model_name=meta.get("model_name", MODEL_NAME))
        index.embeddings = data["embeddings"]
        index.chunks = meta["chunks"]
        return index

    def search(self, query, top_k: int = 3):
        """Busca por similaridade. Levanta ValueError com mensagem clara em casos inválidos
        em vez de falhar silenciosamente (pergunta vazia, corpus vazio, top_k inválido)."""
        if query is None or not str(query).strip():
            raise ValueError("A pergunta está vazia. Digite uma pergunta antes de buscar.")

        if not self.chunks or self.embeddings is None or len(self.chunks) == 0:
            raise ValueError(
                "O índice está vazio (corpus sem documentos). Rode 'python build_index.py' "
                "com uma pasta docs/ válida antes de consultar."
            )

        if not isinstance(top_k, int) or isinstance(top_k, bool) or top_k <= 0:
            raise ValueError(
                f"top_k inválido: {top_k!r}. Use um número inteiro positivo (ex.: 3, 4 ou 5)."
            )

        n = len(self.chunks)
        effective_top_k = min(top_k, n)

        query_emb = self.model.encode([str(query)], normalize_embeddings=True)[0].astype("float32")
        scores = self.embeddings @ query_emb  # cosine similarity (vetores normalizados)
        ranked_idx = np.argsort(-scores)[:effective_top_k]

        results = []
        for rank, idx in enumerate(ranked_idx, start=1):
            c = self.chunks[int(idx)]
            results.append(
                {
                    "rank": rank,
                    "score": float(scores[idx]),
                    "text": c["text"],
                    "source_file": c["source_file"],
                    "title": c["title"],
                    "section": c["section"],
                    "chunk_id": c["chunk_id"],
                }
            )
        return results
