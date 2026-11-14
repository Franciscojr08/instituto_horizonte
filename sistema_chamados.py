"""Sistema de protocolos simulado, persistido em JSON local (TK-10, RF-03, RF-05).

Reaproveitado da aula "pinecone" (chamados INC-xxxx). Agora com protocolos SOL-xxxx,
dados iniciais da Spec 3.2, validação de campos obrigatórios por tipo (Spec 3.4) e
escrita atômica (arquivo temporário + rename), para o JSON nunca ficar pela metade.
"""
import json
import os
import re
import unicodedata
from datetime import datetime
from pathlib import Path

from schemas import PADRAO_PROTOCOLO, Protocolo, normalizar_protocolo
from settings import ARQUIVO_PROTOCOLOS

PROTOCOLOS_INICIAIS: dict[str, dict] = {
    "SOL-1001": {
        "tipo": "declaracao_matricula",
        "descricao": "Declaração de matrícula não disponibilizada no portal",
        "turma": None, "justificativa": None,
        "status": "em_analise", "criado_em": "2026-11-03T10:15:00-03:00",
    },
    "SOL-1002": {
        "tipo": "suporte_tecnico",
        "descricao": "Erro de autenticação na biblioteca digital",
        "turma": None, "justificativa": None,
        "status": "resolvido", "criado_em": "2026-10-28T14:40:00-03:00",
    },
    "SOL-1003": {
        "tipo": "segunda_via_certificado",
        "descricao": "Segunda via do certificado do módulo 1",
        "turma": "6001", "justificativa": "Certificado original extraviado",
        "status": "aguardando_estudante", "criado_em": "2026-11-05T09:00:00-03:00",
    },
}

OBRIGATORIOS_POR_TIPO: dict[str, tuple[str, ...]] = {
    "segunda_via_certificado": ("turma", "justificativa"),  # ACAD-005
    "declaracao_matricula": (),                              # ACAD-001
    "suporte_tecnico": (),                                   # ACAD-007, ACAD-010
    "outro": (),
}
TAMANHO_MINIMO_DESCRICAO = 10

# Valores que não identificam nada e por isso contam como ausentes (Spec 3.4)
_GENERICOS = {
    "", "turma", "minha turma", "a minha turma", "da minha turma", "nossa turma", "a turma",
    "nao sei", "sei la", "nao informado", "nao informada", "nenhum", "nenhuma", "qualquer",
    "n/a", "na", "-", "?", "null", "none", "a definir", "desconhecida", "desconhecido",
}


def _simplificar(texto: str) -> str:
    sem_acento = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode()
    return re.sub(r"\s+", " ", sem_acento.lower().strip(" .!"))


def valor_ausente(valor: str | None) -> bool:
    return valor is None or _simplificar(valor) in _GENERICOS


def carregar_protocolos(caminho: Path = ARQUIVO_PROTOCOLOS) -> dict[str, dict]:
    if not caminho.exists():
        return {chave: dict(valor) for chave, valor in PROTOCOLOS_INICIAIS.items()}
    return json.loads(caminho.read_text(encoding="utf-8"))


def salvar_protocolos(protocolos: dict[str, dict], caminho: Path = ARQUIVO_PROTOCOLOS) -> None:
    caminho.parent.mkdir(parents=True, exist_ok=True)
    temporario = caminho.with_name(caminho.name + ".tmp")
    temporario.write_text(json.dumps(protocolos, indent=2, ensure_ascii=False), encoding="utf-8")
    os.replace(temporario, caminho)  # atômico no mesmo sistema de arquivos


def consultar_protocolo_local(protocolo: str, caminho: Path = ARQUIVO_PROTOCOLOS) -> dict:
    chave = normalizar_protocolo(protocolo)
    if not PADRAO_PROTOCOLO.match(chave):
        return {"resultado": "formato_invalido", "protocolo_informado": chave,
                "mensagem": "Use o formato SOL-0000, por exemplo SOL-1001."}
    registro = carregar_protocolos(caminho).get(chave)
    if registro is None:
        return {"resultado": "nao_encontrado", "protocolo_informado": chave}
    return {"resultado": "encontrado", "protocolo": Protocolo(id=chave, **registro).model_dump()}


def campos_faltando(tipo: str, descricao: str | None, turma: str | None, justificativa: str | None) -> list[str]:
    faltando = []
    if valor_ausente(descricao) or len((descricao or "").strip()) < TAMANHO_MINIMO_DESCRICAO:
        faltando.append("descricao")
    valores = {"turma": turma, "justificativa": justificativa}
    faltando += [campo for campo in OBRIGATORIOS_POR_TIPO[tipo] if valor_ausente(valores[campo])]
    return faltando


def _proximo_id(protocolos: dict[str, dict]) -> str:
    numeros = [int(chave[4:]) for chave in protocolos if PADRAO_PROTOCOLO.match(chave)]
    return f"SOL-{max([1000, *numeros]) + 1:04d}"


def registrar_solicitacao_local(
    tipo: str,
    descricao: str,
    turma: str | None = None,
    justificativa: str | None = None,
    caminho: Path = ARQUIVO_PROTOCOLOS,
) -> dict:
    """Registra e persiste; com dados faltando, não grava nada e devolve a lista (RF-05)."""
    if tipo not in OBRIGATORIOS_POR_TIPO:
        return {"resultado": "dados_pendentes", "faltando": ["tipo"],
                "mensagem": f"Tipo inválido. Opções: {', '.join(OBRIGATORIOS_POR_TIPO)}"}
    faltando = campos_faltando(tipo, descricao, turma, justificativa)
    if faltando:
        return {"resultado": "dados_pendentes", "tipo": tipo, "faltando": faltando,
                "mensagem": "Peça ao estudante os campos faltando; nada foi registrado."}

    protocolos = carregar_protocolos(caminho)
    novo = Protocolo(
        id=_proximo_id(protocolos), tipo=tipo, descricao=descricao.strip(),
        turma=None if valor_ausente(turma) else turma.strip(),
        justificativa=None if valor_ausente(justificativa) else justificativa.strip(),
        status="aberto", criado_em=datetime.now().astimezone().isoformat(timespec="seconds"),
    )
    protocolos[novo.id] = novo.model_dump(exclude={"id"})
    salvar_protocolos(protocolos, caminho)
    return {"resultado": "registrado", "protocolo": novo.model_dump()}
