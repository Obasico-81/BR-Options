"""Gera arquivos COTAHIST sintéticos (layout oficial de 245 posições) a partir do snapshot.json.

Escrito campo a campo, com o tamanho de cada campo da documentação da B3, sem reaproveitar o CAMPOS do
atualizador. Serve para testar a lógica do atualizador; NÃO prova que o layout está certo (isso só com arquivo real).
"""
import io, json, zipfile
from datetime import date, timedelta

# (nome, tamanho) na ordem do layout do registro tipo 01
LAYOUT = [("TIPREG", 2), ("DATA", 8), ("CODBDI", 2), ("CODNEG", 12), ("TPMERC", 3), ("NOMRES", 12), ("ESPECI", 10),
          ("PRAZOT", 3), ("MODREF", 4), ("PREABE", 13), ("PREMAX", 13), ("PREMIN", 13), ("PREMED", 13), ("PREULT", 13),
          ("PREOFC", 13), ("PREOFV", 13), ("TOTNEG", 5), ("QUATOT", 18), ("VOLTOT", 18), ("PREEXE", 13), ("INDOPC", 1),
          ("DATVEN", 8), ("FATCOT", 7), ("PTOEXE", 13), ("CODISI", 12), ("DISMES", 3)]
NUM = {"PREABE", "PREMAX", "PREMIN", "PREMED", "PREULT", "PREOFC", "PREOFV", "TOTNEG", "QUATOT", "VOLTOT", "PREEXE",
       "FATCOT", "PTOEXE", "DISMES"}
PAPEL = {"BOVA11": "BOVA11", "PETR4": "PETR4", "VALE3": "VALE3"}
isin = lambda nome: "BR" + nome[:4] + "ACNPR8"     # ISIN (CODISI) do papel à vista; a opção traz o ISIN do papel-objeto
isin_irmao = lambda nome: "BR" + nome[:4] + "ACNOR1"   # outro papel com o mesmo prefixo (como BBDC3 para BBDC4)


def registro(**v):
    out = []
    for nome, tam in LAYOUT:
        x = v.get(nome, 0 if nome in NUM else "")
        s = str(x).rjust(tam, "0") if nome in NUM else str(x).ljust(tam)
        assert len(s) == tam, (nome, s)
        out.append(s)
    ln = "".join(out)
    assert len(ln) == 245
    return ln


def c(p):  # preço em centavos, 13 dígitos (11)V99
    return int(round(p * 100))


def linhas_do_dia(dia, ativos, so_n_opcoes=None):
    d = dia.replace("-", "")
    d0 = date.fromisoformat(dia)
    ls = []
    for nome, a in ativos.items():
        ls.append(registro(TIPREG="01", DATA=d, CODBDI="02", CODNEG=PAPEL[nome], TPMERC="010", NOMRES=nome[:4],
                           ESPECI="ON", MODREF="R$", PREULT=c(a["S"]), PREOFC=c(a["S"] - .01), PREOFV=c(a["S"] + .01),
                           QUATOT=1000000, DATVEN="99991231", FATCOT=1, CODISI=isin(nome)))
        chain = a["chain"][:so_n_opcoes] if so_n_opcoes else a["chain"]
        for o in chain:
            venc = (d0 + timedelta(days=o["d"])).strftime("%Y%m%d")
            ls.append(registro(TIPREG="01", DATA=d, CODBDI="78" if o["t"] == "C" else "82", CODNEG=o["s"],
                               TPMERC="070" if o["t"] == "C" else "080", NOMRES=nome[:4], ESPECI="ON",
                               MODREF="R$", PREULT=c((o["b"] + o["a"]) / 2), PREOFC=c(o["b"]), PREOFV=c(o["a"]),
                               QUATOT=o["v"], PREEXE=c(o["k"]), INDOPC=0, DATVEN=venc, FATCOT=1, CODISI=isin(nome)))
        # ruído que o leitor tem de ignorar: opção vencida há 2 dias e opção sem oferta de compra
        # e opção líquida, com o mesmo prefixo, de outro papel-objeto (CODISI de outro ISIN)
        ls.append(registro(TIPREG="01", DATA=d, CODBDI="78", CODNEG=nome[:4] + "K777", TPMERC="070", NOMRES=nome[:4], ESPECI="ON",
                           MODREF="R$", PREOFC=c(1), PREOFV=c(1.05), QUATOT=100000, PREEXE=c(a["S"]),
                           DATVEN=(d0 + timedelta(days=30)).strftime("%Y%m%d"), FATCOT=1, CODISI=isin_irmao(nome)))
        ls.append(registro(TIPREG="01", DATA=d, CODBDI="78", CODNEG=nome[:4] + "X999", TPMERC="070", PREOFC=0,
                           PREOFV=c(1), PREEXE=c(a["S"]), DATVEN=(d0 + timedelta(days=30)).strftime("%Y%m%d")))
    return ls


def zip_do_dia(dia, ativos, so_n_opcoes=None):
    d = dia.replace("-", "")
    txt = [("00COTAHIST.%sBOVESPA %s" % (d[:4], d)).ljust(245)] + linhas_do_dia(dia, ativos, so_n_opcoes)
    txt.append(("99COTAHIST.%sBOVESPA %s%011d" % (d[:4], d, len(txt) + 1)).ljust(245))
    b = io.BytesIO()
    with zipfile.ZipFile(b, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("COTAHIST_D%s.TXT" % (d[6:8] + d[4:6] + d[:4]), ("\r\n".join(txt) + "\r\n").encode("latin-1"))
    return b.getvalue()


def ativos_deslocados(snap, base, dia, fator=1.0):
    """Mesma cadeia de `base` reapresentada em `dia` (vencimentos fixos; dias até o vencimento recalculados)."""
    d0, d1 = date.fromisoformat(base), date.fromisoformat(dia)
    out = {}
    for nome, a in snap["por_data"][base].items():
        ch = []
        for o in a["chain"]:
            nd = o["d"] - (d1 - d0).days
            if nd > 0:
                ch.append(dict(o, d=nd))
        out[nome] = dict(S=round(a["S"] * fator, 2), iv=a["iv"], chain=ch)
    return out


if __name__ == "__main__":
    import sys
    snap = json.load(open(sys.argv[1]))
    open(sys.argv[2], "wb").write(zip_do_dia(snap["data"], snap["por_data"][snap["data"]]))
