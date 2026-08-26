"""Tabelas oficiais embarcadas: CST e cClassTrib do IBS/CBS.

Dado, não código — vive em `regras/tabelas/`, versionado, com procedência e
sha256 conferido em teste. Ver `regras/tabelas/PROCEDENCIA.md`.

Duas regras de comportamento que não são negociáveis:

1. **Nunca acessa a rede.** Nem para atualizar, nem para conferir. A atualização
   é ato deliberado, por `scripts/baixar_tabelas.py`, com PR e nova procedência.
2. **Tabela ausente não vira erro.** Se o pacote foi instalado sem a tabela, a
   regra que dependeria dela não roda e diz que não pôde ser avaliada. Reprovar
   uma nota por defeito de instalação seria acusar errado — a falha mais cara
   que este projeto pode cometer (spec 05).
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

RAIZ_TABELAS = Path(__file__).resolve().parent / "regras" / "tabelas"
if not RAIZ_TABELAS.is_dir():  # repositório clonado, não instalado
    RAIZ_TABELAS = Path(__file__).resolve().parent.parent / "regras" / "tabelas"


class TabelaAusente(Exception):
    """A tabela não está embarcada. Quem chama decide o que fazer — nunca 'erro'."""


@dataclass(frozen=True)
class Classificacao:
    """Uma linha de cClassTrib, com os indicadores que as regras consultam."""

    codigo: str
    nome: str
    cst: str
    indicadores: dict[str, bool]
    reducao_ibs: float
    reducao_cbs: float
    desde: str | None
    ate: str | None

    def vale_para_modelo(self, modelo: str | None) -> bool | None:
        """A classificação é permitida no modelo 55 (NF-e) ou 65 (NFC-e)?

        Devolve None quando o modelo não é um dos dois — a regra não opina sobre
        documento que este projeto não valida.
        """
        chave = {"55": "IndNfe", "65": "IndNfce"}.get(modelo or "")
        return self.indicadores.get(chave) if chave else None


@dataclass(frozen=True)
class Cst:
    codigo: str
    nome: str
    indicadores: dict[str, bool]
    desde: str | None
    ate: str | None


@dataclass(frozen=True)
class TabelaCstClassTrib:
    versao: str
    fonte: str
    cst: dict[str, Cst]
    classificacoes: dict[str, Classificacao]

    def __len__(self) -> int:
        return len(self.classificacoes)


def _indicadores(bruto: dict) -> dict[str, bool]:
    return {c: v for c, v in bruto.items() if c.startswith("Ind") and isinstance(v, bool)}


@lru_cache(maxsize=1)
def cst_cclasstrib(raiz: Path | None = None) -> TabelaCstClassTrib:
    """Carrega a tabela embarcada. Levanta `TabelaAusente` se não houver."""
    caminho = (raiz or RAIZ_TABELAS) / "cst-cclasstrib.json"
    if not caminho.is_file():
        raise TabelaAusente(
            f"tabela oficial de CST/cClassTrib não encontrada em {caminho}. "
            "Reinstale o pacote ou rode scripts/baixar_tabelas.py."
        )
    bruto = json.loads(caminho.read_text(encoding="utf-8"))

    cst: dict[str, Cst] = {}
    classificacoes: dict[str, Classificacao] = {}
    for grupo in bruto["cst"]:
        cst[grupo["Cst"]] = Cst(
            codigo=grupo["Cst"],
            nome=grupo["NomeCst"],
            indicadores=_indicadores(grupo),
            desde=grupo.get("DthIniVig"),
            ate=grupo.get("DthFimVig"),
        )
        for linha in grupo["ClassificacoesTributarias"]:
            classificacoes[linha["CodClassTrib"]] = Classificacao(
                codigo=linha["CodClassTrib"],
                nome=linha["NomeClassTrib"],
                cst=linha["Cst"],
                indicadores=_indicadores(linha),
                reducao_ibs=float(linha.get("PercRedIbs") or 0),
                reducao_cbs=float(linha.get("PercRedCbs") or 0),
                desde=linha.get("DthIniVig"),
                ate=linha.get("DthFimVig"),
            )

    return TabelaCstClassTrib(
        versao=bruto.get("publicacao_declarada_pela_fonte") or "desconhecida",
        fonte=bruto.get("fonte", ""),
        cst=cst,
        classificacoes=classificacoes,
    )


def resumo() -> dict:
    """O que está embarcado. Quem depende disto precisa saber contra o quê valida."""
    try:
        tabela = cst_cclasstrib()
    except TabelaAusente as exc:
        return {"disponivel": False, "motivo": str(exc)}
    return {
        "disponivel": True,
        "tabela": "cst-cclasstrib",
        "publicacao_declarada_pela_fonte": tabela.versao,
        "fonte": tabela.fonte,
        "cst": len(tabela.cst),
        "cclasstrib": len(tabela.classificacoes),
    }
