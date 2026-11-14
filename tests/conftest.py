"""Configuração dos testes: rodam sem LLM, sem embeddings e sem pgvector (RNF-08).

As variáveis são definidas ANTES de importar o projeto, porque `settings.py` lê o
ambiente na importação. Cada teste começa com os protocolos iniciais da Spec.
"""
import os
import sys
import tempfile
from pathlib import Path

_TEMP = Path(tempfile.mkdtemp(prefix="horizonte-testes-"))
os.environ["ARQUIVO_PROTOCOLOS"] = str(_TEMP / "protocolos.json")
os.environ["PASTA_LOGS"] = str(_TEMP / "logs")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest  # noqa: E402

from rag_utils import Evidencia  # noqa: E402

ARQUIVO_PROTOCOLOS = Path(os.environ["ARQUIVO_PROTOCOLOS"])


@pytest.fixture(autouse=True)
def protocolos_limpos():
    ARQUIVO_PROTOCOLOS.unlink(missing_ok=True)
    yield ARQUIVO_PROTOCOLOS
    ARQUIVO_PROTOCOLOS.unlink(missing_ok=True)


def evidencia(fonte: str, score: float = 0.8) -> Evidencia:
    return Evidencia(fonte=fonte, titulo=f"Título {fonte}", categoria="documentos",
                     trecho=f"Conteúdo da norma {fonte}.", score=score)


@pytest.fixture
def busca_falsa(monkeypatch):
    """Substitui a busca no pgvector. Uso: busca_falsa(["ACAD-001"]) ou busca_falsa(erro=True)."""
    from rag_utils import ErroRecuperacao

    def configurar(fontes: list[str] | None = None, erro: bool = False):
        def falsa(pergunta, top_k=3, categoria=None, score_minimo=0.55):
            if erro:
                raise ErroRecuperacao("banco vetorial indisponível")
            return [evidencia(f) for f in (fontes or [])]
        monkeypatch.setattr("tool_agente.buscar_contexto", falsa)
    return configurar
