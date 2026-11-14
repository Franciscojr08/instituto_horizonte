"""Contratos tipados (TK-09): resposta do agente, argumentos das Tools e protocolo.

Spec 3.2, 3.3 e 3.5. `RespostaAgente` é o contrato final e verifica as invariantes que não
dependem do contexto; as que dependem (fontes recuperadas, Tools executadas) são aplicadas
pelo nó `validar` do grafo antes de construir a resposta.
"""
import re
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from observabilidade import contem_credencial

PADRAO_FONTE = re.compile(r"^ACAD-\d{3}$")
PADRAO_PROTOCOLO = re.compile(r"^SOL-\d{4}$")

StatusResposta = Literal[
    "respondido", "abstencao", "recusado", "protocolo_consultado",
    "solicitacao_registrada", "dados_pendentes", "erro",
]
StatusProtocolo = Literal["aberto", "em_analise", "aguardando_estudante", "resolvido", "cancelado"]
TipoSolicitacao = Literal["segunda_via_certificado", "declaracao_matricula", "suporte_tecnico", "outro"]


def normalizar_protocolo(valor: str) -> str:
    return valor.strip().upper()


# --- Resposta final do agente (Spec 3.5) ----------------------------------------------

class RespostaAgente(BaseModel):
    """Contrato da resposta entregue ao estudante."""

    model_config = ConfigDict(extra="forbid")

    resposta: str = Field(min_length=1, description="Texto para o estudante, em português")
    status: StatusResposta
    fontes: list[str] = Field(default_factory=list, description="IDs ACAD-xxx usados na resposta")
    protocolo: str | None = Field(default=None, description="SOL-xxxx consultado ou registrado")

    @field_validator("resposta")
    @classmethod
    def _resposta_nao_vazia(cls, valor: str) -> str:
        valor = valor.strip()
        if not valor:
            raise ValueError("a resposta não pode ser vazia")
        return valor

    @field_validator("fontes")
    @classmethod
    def _fontes_validas(cls, fontes: list[str]) -> list[str]:
        normalizadas = []
        for fonte in fontes:
            fonte = fonte.strip().upper()
            if not PADRAO_FONTE.match(fonte):
                raise ValueError(f"fonte inválida: {fonte!r} (esperado ACAD-xxx)")
            if fonte not in normalizadas:
                normalizadas.append(fonte)
        return normalizadas

    @field_validator("protocolo")
    @classmethod
    def _protocolo_valido(cls, valor: str | None) -> str | None:
        if valor is None or not valor.strip():
            return None
        valor = normalizar_protocolo(valor)
        if not PADRAO_PROTOCOLO.match(valor):
            raise ValueError(f"protocolo inválido: {valor!r} (esperado SOL-xxxx)")
        return valor

    @model_validator(mode="after")
    def _invariantes(self) -> "RespostaAgente":
        if self.status == "respondido" and not self.fontes:
            raise ValueError("status 'respondido' exige ao menos uma fonte")
        if self.status == "abstencao" and self.fontes:
            raise ValueError("status 'abstencao' não pode citar fontes")
        if self.status in {"protocolo_consultado", "solicitacao_registrada"} and not self.protocolo:
            raise ValueError(f"status '{self.status}' exige o número do protocolo")
        return self


class RespostaBruta(BaseModel):
    """Leitura tolerante do JSON produzido pelo LLM, antes das correções do nó `validar`."""

    model_config = ConfigDict(extra="ignore")

    resposta: str = ""
    status: str = ""
    fontes: list[str] = Field(default_factory=list)
    protocolo: str | None = None

    @field_validator("fontes", mode="before")
    @classmethod
    def _lista(cls, valor):
        if valor is None:
            return []
        if isinstance(valor, str):
            return [valor]
        return [str(item) for item in valor]

    @field_validator("protocolo", mode="before")
    @classmethod
    def _texto(cls, valor):
        return None if valor in (None, "", "null") else str(valor)


# --- Argumentos das Tools (Spec 3.3) ------------------------------------------------

def _sem_credencial(valor: str | None) -> str | None:
    if valor is not None and contem_credencial(valor):
        raise ValueError("o texto parece conter senha, token ou chave; não envie credenciais")
    return valor


class ArgsBuscarNormas(BaseModel):
    pergunta: str = Field(
        min_length=3, max_length=500,
        description="Dúvida do estudante reescrita como consulta objetiva às normas acadêmicas",
    )
    categoria: str | None = Field(
        default=None,
        description="Opcional; normalmente deixe vazio. Só use se tiver certeza, com um destes valores: "
                    "documentos, certificacao, avaliacao, calendario, seguranca, servicos (biblioteca), "
                    "matricula, financeiro, suporte (plataforma de aulas), atendimento (ouvidoria), integridade.",
    )

    @field_validator("pergunta")
    @classmethod
    def _pergunta(cls, valor: str) -> str:
        return _sem_credencial(valor.strip())

    @field_validator("categoria")
    @classmethod
    def _categoria(cls, valor: str | None) -> str | None:
        from rag_utils import categorias_da_base  # import tardio: evita ciclo e acesso ao disco na carga

        if valor is None or not valor.strip():
            return None
        valor = valor.strip().lower()
        if valor not in categorias_da_base():
            raise ValueError(f"categoria desconhecida: {valor!r}; opções: {sorted(categorias_da_base())}")
        return valor


class ArgsConsultarProtocolo(BaseModel):
    protocolo: str = Field(description="Número do protocolo no formato SOL-0000, por exemplo SOL-1001")

    @field_validator("protocolo")
    @classmethod
    def _protocolo(cls, valor: str) -> str:
        return normalizar_protocolo(valor)


class ArgsRegistrarSolicitacao(BaseModel):
    tipo: TipoSolicitacao = Field(
        description="segunda_via_certificado | declaracao_matricula | suporte_tecnico | outro"
    )
    descricao: str = Field(
        max_length=1000, description="O que o estudante pediu, com as palavras dele (sem credenciais)"
    )
    turma: str | None = Field(
        default=None, description="Identificação da turma informada pelo estudante. Não invente."
    )
    justificativa: str | None = Field(
        default=None, max_length=1000, description="Motivo informado pelo estudante. Não invente."
    )

    @field_validator("descricao", "turma", "justificativa")
    @classmethod
    def _texto(cls, valor: str | None) -> str | None:
        return _sem_credencial(valor.strip() if isinstance(valor, str) else valor)


# --- Protocolo persistido (Spec 3.2) -------------------------------------------------

class Protocolo(BaseModel):
    id: str
    tipo: TipoSolicitacao
    descricao: str
    turma: str | None = None
    justificativa: str | None = None
    status: StatusProtocolo
    criado_em: str

    @field_validator("id")
    @classmethod
    def _id(cls, valor: str) -> str:
        valor = normalizar_protocolo(valor)
        if not PADRAO_PROTOCOLO.match(valor):
            raise ValueError(f"protocolo inválido: {valor!r}")
        return valor
