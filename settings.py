"""Configuração central do agente (TK-02).

Tudo vem do `.env` (modelo em `.env.example`). Os valores padrão apontam para os
serviços do `compose.yaml`, então o projeto roda mesmo sem `.env`.
Reaproveitado da aula "pinecone": saíram o Pinecone e os provedores em nuvem (RNF-01).
"""
import os
from pathlib import Path

from dotenv import load_dotenv

RAIZ = Path(__file__).resolve().parent
load_dotenv(RAIZ / ".env")


def _env(nome: str, padrao: str = "") -> str:
    return (os.getenv(nome) or padrao).strip()


def _int(nome: str, padrao: int, minimo: int, maximo: int) -> int:
    bruto = _env(nome, str(padrao))
    try:
        valor = int(bruto)
    except ValueError:
        raise ValueError(f"{nome} deve ser inteiro, recebido {bruto!r}") from None
    if not minimo <= valor <= maximo:
        raise ValueError(f"{nome} deve estar entre {minimo} e {maximo}, recebido {valor}")
    return valor


def _float(nome: str, padrao: float, minimo: float, maximo: float) -> float:
    bruto = _env(nome, str(padrao))
    try:
        valor = float(bruto)
    except ValueError:
        raise ValueError(f"{nome} deve ser número, recebido {bruto!r}") from None
    if not minimo <= valor <= maximo:
        raise ValueError(f"{nome} deve estar entre {minimo} e {maximo}, recebido {valor}")
    return valor


def _bool(nome: str, padrao: bool) -> bool:
    return _env(nome, "true" if padrao else "false").lower() in {"1", "true", "sim", "yes", "on"}


def _caminho(nome: str, padrao: Path) -> Path:
    bruto = _env(nome)
    if not bruto:
        return padrao
    caminho = Path(bruto)
    return caminho if caminho.is_absolute() else RAIZ / caminho


# --- LLM (todos locais, API compatível com OpenAI) ---------------------------------
PROVEDORES_LLM = {
    "llamacpp": {"base_url": "http://localhost:8091/v1", "modelo_padrao": "qwen3-30b"},
    "localai": {"base_url": "http://localhost:8080/v1", "modelo_padrao": "qwen3-4b"},
    "ollama": {"base_url": "http://localhost:11434/v1", "modelo_padrao": "qwen3:4b"},
}

LLM_PROVIDER = _env("LLM_PROVIDER", "llamacpp").lower()
if LLM_PROVIDER not in PROVEDORES_LLM:
    raise ValueError(f"LLM_PROVIDER desconhecido: {LLM_PROVIDER!r}. Opções: {', '.join(PROVEDORES_LLM)}")
_provedor = PROVEDORES_LLM[LLM_PROVIDER]
LLM_BASE_URL = _env("LLM_BASE_URL", _provedor["base_url"])
LLM_MODEL = _env("LLM_MODEL", _provedor["modelo_padrao"])
# Servidores locais não validam a chave; o cliente OpenAI só exige que exista.
LLM_API_KEY = _env("LLM_API_KEY", "local")
LLM_TIMEOUT = _int("LLM_TIMEOUT", 300, 10, 1800)  # segundos; CPU sem GPU é lenta
LLM_MAX_RETRIES = _int("LLM_MAX_RETRIES", 1, 0, 5)
# Modelos Qwen3 híbridos (ex.: qwen3-4b) "pensam" antes de responder; desligado por padrão.
LLM_DESATIVAR_RACIOCINIO = _bool("LLM_DESATIVAR_RACIOCINIO", True)

# --- Embeddings e banco vetorial -------------------------------------------------
EMBEDDING_BASE_URL = _env("EMBEDDING_BASE_URL", "http://localhost:8092/v1")
EMBEDDING_MODEL = _env("EMBEDDING_MODEL", "qwen3-embedding-0.6b")
EMBEDDING_DIMENSOES = _int("EMBEDDING_DIMENSOES", 1024, 8, 8192)
PG_DSN = _env("PG_DSN", "postgresql://horizonte:horizonte@localhost:5434/horizonte")

# --- Comportamento do agente -----------------------------------------------------
TOP_K = _int("TOP_K", 3, 1, 12)                    # RNF-03
SCORE_MINIMO = _float("SCORE_MINIMO", 0.55, 0.0, 1.0)  # RF-02 (calibrado no TK-08, ver sdd/05_validacao.md)
MAX_RODADAS = _int("MAX_RODADAS", 4, 1, 10)        # RNF-04

# --- Arquivos ---------------------------------------------------------------------
ARQUIVO_BASE = _caminho("ARQUIVO_BASE", RAIZ / "data" / "base_conhecimento_academica.json")
ARQUIVO_CENARIOS = _caminho("ARQUIVO_CENARIOS", RAIZ / "data" / "cenarios_de_teste_aluno.csv")
ARQUIVO_ESPERADO = _caminho("ARQUIVO_ESPERADO", RAIZ / "data" / "esperado_cenarios.json")
ARQUIVO_PROTOCOLOS = _caminho("ARQUIVO_PROTOCOLOS", RAIZ / "data" / "protocolos.json")
PASTA_LOGS = _caminho("PASTA_LOGS", RAIZ / "logs")
PASTA_RESULTADOS = _caminho("PASTA_RESULTADOS", RAIZ / "resultados")
