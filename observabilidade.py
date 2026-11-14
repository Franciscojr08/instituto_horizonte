"""Observabilidade e proteção de segredos (TK-13, RNF-06, RF-07).

- `mascarar()` esconde senhas, tokens e chaves antes de qualquer registro.
- `contem_credencial()` é usada pelas Tools para rejeitar argumentos com credenciais.
- `RegistroExecucao` grava um arquivo JSON Lines por sessão em `logs/`, um evento por linha.
"""
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any

from settings import PASTA_LOGS

MASCARA = "***"

# "senha: abc123", "token = xyz", "minha senha é abc123", "senha do portal é abc123",
# "código de autenticação 123456". Exige separador (: = é) para não mascarar frases comuns
# como "posso enviar minha senha para um colega?".
_ROTULADO = re.compile(
    r"(?i)\b(senha|password|passwd|token|api[_ -]?key|chave de api|c[oó]digo de autentica[cç][aã]o)"
    r"((?:\s+(?:do|da|de|no|na)\s+[\wÀ-ÿ]+){0,2}\s*(?:[:=]|\bé\b|\beh\b|\bis\b)\s*"
    r"|(?<=o)\s+(?=\d{4,}))"
    r"([^\s,;]{4,})"
)
# Formatos conhecidos de chaves de API
_CHAVE_CONHECIDA = re.compile(
    r"\b(sk-[A-Za-z0-9_-]{16,}|pcsk_[A-Za-z0-9_]{16,}|hf_[A-Za-z0-9]{16,}|gsk_[A-Za-z0-9]{16,}|AIza[0-9A-Za-z_-]{20,})\b"
)


def contem_credencial(texto: str) -> bool:
    return bool(_ROTULADO.search(texto) or _CHAVE_CONHECIDA.search(texto))


def mascarar(valor: Any) -> Any:
    """Mascara segredos em strings, inclusive dentro de dicts e listas."""
    if isinstance(valor, str):
        texto = _ROTULADO.sub(lambda m: f"{m.group(1)}{m.group(2)}{MASCARA}", valor)
        return _CHAVE_CONHECIDA.sub(MASCARA, texto)
    if isinstance(valor, dict):
        return {chave: mascarar(item) for chave, item in valor.items()}
    if isinstance(valor, (list, tuple)):
        return [mascarar(item) for item in valor]
    return valor


def resumir(texto: str, limite: int = 300) -> str:
    texto = " ".join(str(texto).split())
    return texto if len(texto) <= limite else texto[:limite] + "…"


class RegistroExecucao:
    """Log estruturado de uma sessão (CLI ou lote). Cada pergunta é uma `execucao`."""

    def __init__(self, rotulo: str = "sessao", pasta: Path = PASTA_LOGS):
        self.sessao = f"{datetime.now():%Y%m%d-%H%M%S}-{rotulo}"
        pasta.mkdir(parents=True, exist_ok=True)
        self.caminho = pasta / f"{self.sessao}.jsonl"
        self.execucao: str | None = None

    def iniciar_execucao(self, identificador: str) -> None:
        self.execucao = identificador

    def evento(self, tipo: str, **dados: Any) -> dict:
        registro = {
            "ts": datetime.now().astimezone().isoformat(timespec="milliseconds"),
            "sessao": self.sessao,
            "execucao": self.execucao,
            "evento": tipo,
            **mascarar(dados),
        }
        with self.caminho.open("a", encoding="utf-8") as arquivo:
            arquivo.write(json.dumps(registro, ensure_ascii=False, default=str) + "\n")
        return registro


class RegistroNulo(RegistroExecucao):
    """Usado quando ninguém pediu log (ex.: testes): não grava nada."""

    def __init__(self):
        self.sessao, self.caminho, self.execucao = "nulo", None, None

    def evento(self, tipo: str, **dados: Any) -> dict:
        return {"evento": tipo, **mascarar(dados)}
