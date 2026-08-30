"""
Interface web — EXTRA, fora do escopo obrigatório do desafio (não vale
pontos na correção; feita só depois de tudo que é obrigatório estar pronto).

Roda 100% local: abre um servidor Flask na sua própria máquina e consulta o
MESMO índice já construído por build_index.py (nenhuma lógica de busca é
duplicada — este arquivo só chama RAGIndex.search() e generate_answer(),
exatamente como query.py faz no terminal).

Uso:
    python app.py
    (depois abra http://127.0.0.1:5000 no navegador)
"""
import sys
from pathlib import Path

from flask import Flask, jsonify, render_template, request

sys.path.insert(0, str(Path(__file__).resolve().parent))

from src.indexer import RAGIndex
from src.render import render_chunk_html

BASE_DIR = Path(__file__).resolve().parent
INDEX_DIR = BASE_DIR / "index"

app = Flask(__name__)
_index = None


def get_index():
    global _index
    if _index is None:
        _index = RAGIndex.load(INDEX_DIR)
    return _index


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/api/search", methods=["POST"])
def api_search():
    data = request.get_json(silent=True) or {}
    question = data.get("question", "")
    top_k = data.get("top_k", 3)
    generate = bool(data.get("generate", False))

    try:
        top_k = int(top_k)
    except (TypeError, ValueError):
        pass  # deixa o RAGIndex.search validar e devolver a mensagem certa

    try:
        index = get_index()
        results = index.search(question, top_k=top_k)
    except (ValueError, FileNotFoundError) as e:
        return jsonify({"error": str(e)}), 400

    for r in results:
        r["text_html"] = render_chunk_html(r["text"])

    answer = None
    if generate:
        from src.generate import generate_answer

        answer = generate_answer(question, results)

    return jsonify({"results": results, "answer": answer})


if __name__ == "__main__":
    print("Carregando índice e modelo de embeddings (pode levar alguns segundos)...")
    idx = get_index()
    _ = idx.model  # força o carregamento do modelo agora, não na primeira pergunta
    print("\nPronto! Abra no navegador: http://127.0.0.1:5000\n")
    app.run(debug=False, port=5000)
