"""Executa os 10 cenários oficiais (e os extras) com os serviços locais reais (TK-18, RF-08, RNF-08).

Cada execução fica numa pasta própria em `resultados/execucao_<data>/`:
  - resultados.json   estado final de cada caso (resposta, Tools, rodadas, correções, pré-classificação)
  - resultados.md     tabela pronta para o relatório
  - *.jsonl           log estruturado de todos os eventos
  - protocolos.json   base de protocolos usada (começa sempre dos dados iniciais da Spec)

A pré-classificação (passou/parcial/falhou) compara com `data/esperado_cenarios.json`;
a classificação final é revisada por pessoa no RELATORIO.md.

Uso:
  python executar_cenarios.py              # 10 cenários + extras
  python executar_cenarios.py --sem-extras
  python executar_cenarios.py --casos T04,T05,X01
"""
import argparse
import functools
import csv
import json
import os
import sys
import time
import unicodedata
from datetime import datetime
from pathlib import Path

RAIZ = Path(__file__).resolve().parent
print = functools.partial(print, flush=True)  # progresso visível mesmo com a saída redirecionada


def preparar_pasta() -> Path:
    pasta = RAIZ / "resultados" / f"execucao_{datetime.now():%Y%m%d-%H%M%S}"
    pasta.mkdir(parents=True)
    # Antes de importar o projeto: logs e protocolos desta execução ficam isolados na pasta
    os.environ["PASTA_LOGS"] = str(pasta)
    os.environ["ARQUIVO_PROTOCOLOS"] = str(pasta / "protocolos.json")
    return pasta


def _simples(texto: str) -> str:
    return unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode().lower()


def pre_classificar(esperado: dict, estado: dict, variacao_protocolos: int, log_texto: str) -> tuple[str, list[str]]:
    final = estado["resposta_final"]
    resposta = _simples(final["resposta"])
    tools = estado.get("tools_executadas", [])
    falhas, ressalvas = [], []

    if final["status"] not in esperado["status"]:
        falhas.append(f"status '{final['status']}' (esperado {esperado['status']})")
    if esperado.get("protocolo") and final.get("protocolo") != esperado["protocolo"]:
        falhas.append(f"protocolo {final.get('protocolo')} (esperado {esperado['protocolo']})")
    if esperado.get("motivo_termino") and estado.get("motivo_termino") != esperado["motivo_termino"]:
        falhas.append(f"término '{estado.get('motivo_termino')}' (esperado {esperado['motivo_termino']})")
    for proibido in esperado["resultados_proibidos"]:
        nome, resultado = proibido.split(":")
        if any(t["nome"] == nome and t["resultado"] == resultado for t in tools):
            falhas.append(f"resultado proibido: {proibido}")
    for termo in esperado["termos_proibidos"]:
        if _simples(termo) in resposta:
            falhas.append(f"termo proibido na resposta: {termo!r}")
    if variacao_protocolos != esperado["persistencia"]:
        falhas.append(f"protocolos variaram {variacao_protocolos:+d} (esperado {esperado['persistencia']:+d})")
    if esperado.get("segredo_no_log") and esperado["segredo_no_log"] in log_texto:
        falhas.append("segredo apareceu sem máscara no log")

    fontes = set(final["fontes"])
    faltando = set(esperado["fontes_obrigatorias"]) - fontes
    extras = fontes - set(esperado["fontes_obrigatorias"]) - set(esperado["fontes_aceitas"])
    if faltando:
        ressalvas.append(f"fontes faltando: {sorted(faltando)}")
    if extras:
        ressalvas.append(f"fontes extras: {sorted(extras)}")
    chamadas = {t["nome"] for t in tools}
    for nome in esperado["tools_obrigatorias"]:
        if nome not in chamadas:
            ressalvas.append(f"Tool não chamada: {nome}")
    for grupo in esperado["termos"]:
        if not any(_simples(termo) in resposta for termo in grupo):
            ressalvas.append(f"resposta sem nenhum de {grupo}")

    if falhas:
        return "falhou", falhas + ressalvas
    return ("parcial", ressalvas) if ressalvas else ("passou", [])


def main():
    parser = argparse.ArgumentParser(description="Executar os cenários de teste")
    parser.add_argument("--sem-extras", action="store_true")
    parser.add_argument("--casos", help="lista separada por vírgula, ex.: T04,T05,X01")
    args = parser.parse_args()

    pasta = preparar_pasta()
    from graph import criar_grafo, responder  # noqa: E402 (depois de configurar o ambiente)
    from observabilidade import RegistroExecucao, mascarar
    from settings import ARQUIVO_CENARIOS, ARQUIVO_ESPERADO, LLM_MODEL, MAX_RODADAS, SCORE_MINIMO, TOP_K
    from sistema_chamados import carregar_protocolos

    esperado = json.loads(ARQUIVO_ESPERADO.read_text(encoding="utf-8"))
    with open(ARQUIVO_CENARIOS, encoding="utf-8-sig", newline="") as arquivo:
        casos = [{"caso": l["caso"], "pergunta": l["pergunta"], "thread": l["caso"], **esperado["cenarios"][l["caso"]]}
                 for l in csv.DictReader(arquivo, delimiter=";")]
    if not args.sem_extras:
        casos += [{"thread": e["caso"], **e} for e in esperado["extras"]]
    if args.casos:
        escolhidos = {c.strip().upper() for c in args.casos.split(",")}
        casos = [c for c in casos if c["caso"] in escolhidos]

    registro = RegistroExecucao("cenarios", pasta)
    grafo = criar_grafo()
    print(f"Modelo: {LLM_MODEL} | Top-K: {TOP_K} | SCORE_MINIMO: {SCORE_MINIMO} | MAX_RODADAS: {MAX_RODADAS}")
    print(f"Saída: {pasta.relative_to(RAIZ)}\n")

    resultados = []
    for caso in casos:
        antes = len(carregar_protocolos())
        inicio = time.perf_counter()
        try:
            estado = responder(grafo, caso["pergunta"], caso["thread"], registro,
                               max_rodadas=caso.get("max_rodadas", MAX_RODADAS))
        except Exception as erro:  # registra e segue para o próximo caso
            registro.evento("erro_execucao", caso=caso["caso"], erro=f"{type(erro).__name__}: {erro}")
            estado = {"resposta_final": {"resposta": f"(exceção: {type(erro).__name__})", "status": "erro",
                                         "fontes": [], "protocolo": None},
                      "tools_executadas": [], "rodadas": 0, "correcoes": [], "motivo_termino": "excecao"}
        segundos = time.perf_counter() - inicio
        variacao = len(carregar_protocolos()) - antes
        classe, observacoes = pre_classificar(caso, estado, variacao, registro.caminho.read_text(encoding="utf-8"))
        final = estado["resposta_final"]
        resultados.append({
            "caso": caso["caso"], "pergunta": mascarar(caso["pergunta"]), "objetivo": caso.get("objetivo"),
            "pre_classificacao": classe, "observacoes": observacoes, "segundos": round(segundos, 1),
            "resposta": final, "rodadas": estado.get("rodadas"), "motivo_termino": estado.get("motivo_termino"),
            "tools": [{k: t[k] for k in ("nome", "args", "resultado", "protocolo", "fontes")}
                      for t in estado.get("tools_executadas", [])],
            "correcoes_validar": estado.get("correcoes", []), "variacao_protocolos": variacao,
        })
        icone = {"passou": "✅", "parcial": "⚠️", "falhou": "❌"}[classe]
        print(f"{icone} {caso['caso']} [{final['status']}] {segundos:.0f}s fontes={final['fontes']} "
              f"tools={[t['nome'] for t in estado.get('tools_executadas', [])]}")
        print(f"   {final['resposta'][:160]}")
        for obs in observacoes:
            print(f"   - {obs}")

    meta = {"data": datetime.now().astimezone().isoformat(timespec="seconds"), "modelo": LLM_MODEL,
            "top_k": TOP_K, "score_minimo": SCORE_MINIMO, "max_rodadas": MAX_RODADAS,
            "log": registro.caminho.name}
    (pasta / "resultados.json").write_text(
        json.dumps({"meta": meta, "resultados": resultados}, indent=2, ensure_ascii=False), encoding="utf-8")
    escrever_markdown(pasta / "resultados.md", meta, resultados)

    contagem = {c: sum(r["pre_classificacao"] == c for r in resultados) for c in ("passou", "parcial", "falhou")}
    print(f"\nPré-classificação: {contagem} | arquivos em {pasta.relative_to(RAIZ)}")


def escrever_markdown(caminho: Path, meta: dict, resultados: list[dict]) -> None:  # perguntas já mascaradas
    linhas = [
        f"# Execução dos cenários — {meta['data']}", "",
        f"Modelo `{meta['modelo']}` · Top-K {meta['top_k']} · SCORE_MINIMO {meta['score_minimo']} · "
        f"MAX_RODADAS {meta['max_rodadas']} · log `{meta['log']}`", "",
        "| Caso | Pré-classificação | Status | Fontes | Tools (resultado) | Rodadas | Tempo | Observações |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for r in resultados:
        tools = ", ".join(f"{t['nome']} ({t['resultado']})" for t in r["tools"]) or "—"
        obs = "; ".join(r["observacoes"] + [f"validar: {c}" for c in r["correcoes_validar"]]) or "—"
        linhas.append(
            f"| {r['caso']} | {r['pre_classificacao']} | {r['resposta']['status']} | "
            f"{', '.join(r['resposta']['fontes']) or '—'} | {tools} | {r['rodadas']} | {r['segundos']}s | "
            f"{obs.replace('|', '/')} |"
        )
    linhas += ["", "## Respostas", ""]
    for r in resultados:
        linhas += [f"**{r['caso']}** — {r['pergunta'].strip() or '(mensagem vazia)'}", "",
                   f"> {r['resposta']['resposta']}", ""]
    caminho.write_text("\n".join(linhas) + "\n", encoding="utf-8")


if __name__ == "__main__":
    sys.exit(main())
