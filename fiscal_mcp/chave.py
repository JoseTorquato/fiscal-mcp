"""Chave de acesso de documento fiscal eletrônico.

44 dígitos que codificam quem emitiu, quando, o quê e um dígito verificador:

    cUF   AAMM    CNPJ         mod serie nNF       tpEmis cNF      cDV
    43    2608    12345678000195 55 001   000001234 1     12345678 9
    └2┘   └─4─┘   └───14────┘   └2┘└─3─┘ └───9───┘ └1┘   └──8──┘  └1┘

O dígito verificador usa módulo 11 com pesos 2 a 9 cíclicos, da direita para a
esquerda — o mesmo algoritmo em toda a família de documentos fiscais.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

# Códigos de UF do IBGE, usados nos dois primeiros dígitos da chave.
UFS = {
    "11": "RO", "12": "AC", "13": "AM", "14": "RR", "15": "PA", "16": "AP",
    "17": "TO", "21": "MA", "22": "PI", "23": "CE", "24": "RN", "25": "PB",
    "26": "PE", "27": "AL", "28": "SE", "29": "BA", "31": "MG", "32": "ES",
    "33": "RJ", "35": "SP", "41": "PR", "42": "SC", "43": "RS", "50": "MS",
    "51": "MT", "52": "GO", "53": "DF",
}

MODELOS = {"55": "NF-e", "65": "NFC-e", "57": "CT-e", "58": "MDF-e"}

TAMANHO = 44


def calcula_dv(chave43: str) -> int:
    """Dígito verificador dos 43 primeiros dígitos, por módulo 11.

    Pesos 2..9 ciclicamente, da direita para a esquerda. Resto 0 ou 1 → DV 0.
    """
    if len(chave43) != 43 or not chave43.isdigit():
        raise ValueError("esperados exatamente 43 dígitos")
    soma = 0
    peso = 2
    for digito in reversed(chave43):
        soma += int(digito) * peso
        peso = 2 if peso == 9 else peso + 1
    resto = soma % 11
    return 0 if resto < 2 else 11 - resto


@dataclass(frozen=True)
class Chave:
    """Chave decomposta. `valida` diz se o dígito verificador confere."""

    valor: str
    cuf: str
    ano: str
    mes: str
    cnpj: str
    modelo: str
    serie: str
    numero: str
    tipo_emissao: str
    codigo_numerico: str
    dv: str

    @property
    def uf(self) -> str | None:
        return UFS.get(self.cuf)

    @property
    def documento(self) -> str | None:
        return MODELOS.get(self.modelo)

    @property
    def dv_esperado(self) -> int:
        return calcula_dv(self.valor[:43])

    @property
    def valida(self) -> bool:
        return int(self.dv) == self.dv_esperado

    def resumo(self) -> dict:
        return {
            "chave": self.valor,
            "uf": self.uf,
            "codigo_uf": self.cuf,
            "emissao": f"{self.mes}/20{self.ano}",
            "cnpj_emitente": self.cnpj,
            "documento": self.documento,
            "modelo": self.modelo,
            "serie": int(self.serie),
            "numero": int(self.numero),
            "dv_confere": self.valida,
        }


def limpa(texto: str) -> str:
    """Tira tudo que não for dígito. Chave costuma vir com espaço ou vindo do DANFE."""
    return re.sub(r"\D", "", texto or "")


def decompoe(texto: str) -> Chave:
    """Decompõe a chave. Levanta ValueError se o formato estiver errado."""
    v = limpa(texto)
    if len(v) != TAMANHO:
        raise ValueError(f"a chave tem {len(v)} dígitos, esperados {TAMANHO}")
    return Chave(
        valor=v,
        cuf=v[0:2], ano=v[2:4], mes=v[4:6], cnpj=v[6:20], modelo=v[20:22],
        serie=v[22:25], numero=v[25:34], tipo_emissao=v[34:35],
        codigo_numerico=v[35:43], dv=v[43:44],
    )


def analisa(texto: str) -> dict:
    """Analisa a chave e devolve o resumo com os problemas encontrados.

    Nunca levanta exceção: devolve `ok: false` com o motivo, porque quem
    consome é um agente que precisa decidir o que fazer.
    """
    v = limpa(texto)
    if not v:
        return {"ok": False, "erro": "nenhum dígito encontrado no texto informado"}
    if len(v) != TAMANHO:
        return {
            "ok": False,
            "erro": f"a chave tem {len(v)} dígitos, esperados {TAMANHO}",
            "acao": "Confira se a chave foi copiada por inteiro. No DANFE ela aparece "
                    "em grupos de 4 dígitos.",
        }

    chave = decompoe(v)
    problemas = []
    if not chave.valida:
        problemas.append({
            "campo": "cDV",
            "problema": f"dígito verificador é {chave.dv}, esperado {chave.dv_esperado}",
            "acao": "A chave está incorreta ou foi transcrita com erro. Não use para consulta.",
        })
    if chave.uf is None:
        problemas.append({
            "campo": "cUF",
            "problema": f"código de UF '{chave.cuf}' não existe",
            "acao": "Os dois primeiros dígitos precisam ser um código de UF do IBGE.",
        })
    if chave.documento is None:
        problemas.append({
            "campo": "mod",
            "problema": f"modelo '{chave.modelo}' desconhecido",
            "acao": "55 é NF-e, 65 é NFC-e.",
        })
    if not 1 <= int(chave.mes) <= 12:
        problemas.append({
            "campo": "AAMM",
            "problema": f"mês '{chave.mes}' inválido",
            "acao": "Posições 5 e 6 são o mês de emissão, de 01 a 12.",
        })

    return {"ok": not problemas, **chave.resumo(), "problemas": problemas}
