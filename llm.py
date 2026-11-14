"""Adaptadores de modelo (TK-03): o grafo e as Tools não sabem qual servidor está por trás.

Reaproveitado da aula "pinecone" (ChatOpenAI com base_url), agora apontando para o
llama.cpp local. Os embeddings usam o cliente OpenAI, como na aula "20260926".
"""
from functools import lru_cache

from langchain_openai import ChatOpenAI
from openai import OpenAI

from settings import (
    EMBEDDING_BASE_URL, LLM_API_KEY, LLM_BASE_URL, LLM_DESATIVAR_RACIOCINIO,
    LLM_MAX_RETRIES, LLM_MODEL, LLM_TIMEOUT,
)


def criar_modelo() -> ChatOpenAI:
    """LLM do agente. Temperatura 0 para respostas reproduzíveis nos testes."""
    kwargs = dict(
        model=LLM_MODEL,
        base_url=LLM_BASE_URL,
        api_key=LLM_API_KEY,
        temperature=0,
        timeout=LLM_TIMEOUT,
        max_retries=LLM_MAX_RETRIES,
    )
    if LLM_DESATIVAR_RACIOCINIO:
        # llama.cpp repassa ao template do Qwen3; modelos sem "thinking" ignoram.
        kwargs["extra_body"] = {"chat_template_kwargs": {"enable_thinking": False}}
    return ChatOpenAI(**kwargs)


@lru_cache(maxsize=1)
def criar_cliente_embeddings() -> OpenAI:
    """Cliente do servidor de embeddings (o mesmo na ingestão e na consulta, RNF-03)."""
    return OpenAI(base_url=EMBEDDING_BASE_URL, api_key="local", timeout=60, max_retries=2)
