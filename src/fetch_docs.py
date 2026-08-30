"""
Etapa 1 do fluxo: obter a base documental.

Clona (ou reaproveita) o repositório oficial do HTTPX e fixa o commit exigido
pelo desafio, depois localiza recursivamente os arquivos .md dentro de docs/.
"""
import subprocess
from pathlib import Path

REPO_URL = "https://github.com/encode/httpx.git"
PINNED_COMMIT = "b5addb64f0161ff6bfe94c124ef76f6a1fba5254"


def _run_git(args, cwd=None):
    return subprocess.run(
        ["git", *args], cwd=cwd, capture_output=True, text=True, check=True
    )


def ensure_httpx_repo(target_dir: Path) -> Path:
    """Garante que target_dir contenha o repositório httpx no commit fixado.

    Se a pasta já existir e já estiver no commit certo, não faz nada (idempotente).
    Se existir mas estiver em outro commit, tenta corrigir com fetch + checkout.
    Se não existir, clona do zero.
    """
    target_dir = Path(target_dir)

    if target_dir.exists() and (target_dir / ".git").exists():
        current = _run_git(["rev-parse", "HEAD"], cwd=target_dir).stdout.strip()
        if current == PINNED_COMMIT:
            print(f"[fetch_docs] Repositório já presente em {target_dir} no commit correto.")
            return target_dir
        print(
            f"[fetch_docs] Repositório existe mas está no commit {current[:10]}; "
            f"ajustando para {PINNED_COMMIT[:10]}..."
        )
        _run_git(["fetch", "--all"], cwd=target_dir)
        _run_git(["checkout", PINNED_COMMIT], cwd=target_dir)
        return target_dir

    print(f"[fetch_docs] Clonando {REPO_URL} em {target_dir} ...")
    _run_git(["clone", REPO_URL, str(target_dir)])
    _run_git(["checkout", PINNED_COMMIT], cwd=target_dir)
    print(f"[fetch_docs] Checkout concluído no commit {PINNED_COMMIT}.")
    return target_dir


def find_markdown_files(docs_dir: Path):
    """Busca recursiva por *.md dentro de docs_dir. Lança erro claro se a pasta não existir."""
    docs_dir = Path(docs_dir)
    if not docs_dir.exists():
        raise FileNotFoundError(
            f"Pasta de documentação não encontrada: {docs_dir}. "
            "Confirme se o clone/checkout do repositório funcionou."
        )
    files = sorted(docs_dir.rglob("*.md"))
    return files
