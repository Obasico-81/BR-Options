#!/usr/bin/env python3
"""Atualiza snapshot.json com o fechamento mais recente da B3 (arquivo COTAHIST diário).

Uso (na pasta do projeto):
  python3 atualizar_dados.py                    # baixa o pregão mais recente disponível
  python3 atualizar_dados.py --data 2026-11-03  # um dia específico
  python3 atualizar_dados.py --arquivo COTAHIST_D03112026.ZIP   # usa um arquivo já baixado
  python3 atualizar_dados.py --ano 2026         # preenche os fechamentos do ano inteiro (COTAHIST_A2026.ZIP)
  python3 atualizar_dados.py --validar COTAHIST_D30122025.ZIP   # confere o leitor contra o snapshot atual

Sem dependências além do Python 3.9+. Termina com código 0 quando não há arquivo novo (feriado/fim de semana).
Layout de posição fixa do COTAHIST (documentação oficial da B3): ver CAMPOS.
"""
import argparse, io, json, math, os, sys, time, urllib.error, urllib.request, zipfile
from datetime import date, datetime, timedelta, timezone
from statistics import median

# Papéis do app: nome -> (prefixo das opções, código do papel à vista)
ATIVOS = {"BOVA11": ("BOVA", "BOVA11"), "PETR4": ("PETR", "PETR4"), "VALE3": ("VALE", "VALE3")}
URL_DIA = "https://bvmf.bmfbovespa.com.br/InstDados/SerHist/COTAHIST_D{ddmmaaaa}.ZIP"
URL_ANO = "https://bvmf.bmfbovespa.com.br/InstDados/SerHist/COTAHIST_A{aaaa}.ZIP"
SNAPSHOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "snapshot.json")
DIAS_DE_CADEIA = 12          # quantos pregões completos (com cadeia de opções) ficam no snapshot
R = 0.11                     # juro livre de risco usado na volatilidade implícita (igual ao backtest)

# (início 1-based, fim inclusive)
CAMPOS = dict(tipreg=(1, 2), data=(3, 10), codneg=(13, 24), tpmerc=(25, 27),
              preult=(109, 121), preofc=(122, 134), preofv=(135, 147), quatot=(153, 170),
              preexe=(189, 201), datven=(203, 210))


def campo(ln, nome):
    a, b = CAMPOS[nome]
    return ln[a - 1:b].strip()


def preco(txt):
    return int(txt) / 100 if txt else 0.0


def iso(aaaammdd):
    return f"{aaaammdd[:4]}-{aaaammdd[4:6]}-{aaaammdd[6:8]}"


# ---------- volatilidade implícita (Black-Scholes, call) ----------
def _ncdf(x):
    return 0.5 * (1 + math.erf(x / math.sqrt(2)))


def bs_call(S, K, T, vol, r=R):
    d1 = (math.log(S / K) + (r + 0.5 * vol * vol) * T) / (vol * math.sqrt(T))
    return S * _ncdf(d1) - K * math.exp(-r * T) * _ncdf(d1 - vol * math.sqrt(T))


def iv_call(p, S, K, T, r=R):
    if p <= max(S - K * math.exp(-r * T), 0) + 1e-6:
        return None
    lo, hi = 0.05, 2.0
    if bs_call(S, K, T, hi) < p:
        return None
    for _ in range(50):
        m = (lo + hi) / 2
        lo, hi = (m, hi) if bs_call(S, K, T, m) < p else (lo, m)
    return (lo + hi) / 2


# ---------- leitura do COTAHIST ----------
def linhas_do_zip(origem):
    """origem: caminho ou bytes de um .zip com um único .TXT (latin-1)."""
    z = zipfile.ZipFile(io.BytesIO(origem) if isinstance(origem, (bytes, bytearray)) else origem)
    with z.open(z.namelist()[0]) as f:
        for b in f:
            yield b.decode("latin-1")


def ler(linhas, so_data=None, opc_desde=None):
    """Devolve (fechamentos, opcoes): fechamentos[nome][data] = último preço; opcoes[data][nome] = lista de linhas."""
    prefixos = {pref: nome for nome, (pref, _) in ATIVOS.items()}
    papeis = {pap: nome for nome, (_, pap) in ATIVOS.items()}
    fech, opc = {n: {} for n in ATIVOS}, {}
    for ln in linhas:
        if len(ln) < 210 or campo(ln, "tipreg") != "01":
            continue
        d = campo(ln, "data")
        if so_data and d != so_data:
            continue
        cod, tp = campo(ln, "codneg"), campo(ln, "tpmerc")
        if tp == "010" and cod in papeis:
            p = preco(campo(ln, "preult"))
            if p > 0:
                fech[papeis[cod]][iso(d)] = p
        elif tp in ("070", "080") and cod[:4] in prefixos and (not opc_desde or iso(d) >= opc_desde):
            opc.setdefault(iso(d), {}).setdefault(prefixos[cod[:4]], []).append(dict(
                t="C" if tp == "070" else "P", k=preco(campo(ln, "preexe")), b=preco(campo(ln, "preofc")),
                a=preco(campo(ln, "preofv")), v=int(campo(ln, "quatot") or 0), venc=iso(campo(ln, "datven")), s=cod))
    return fech, opc


def montar_dia(dia, S, linhas):
    """Cadeia filtrada (mesmas regras do exportar_snapshot.py) e volatilidade implícita de um papel num dia."""
    d0 = date.fromisoformat(dia)
    cadeia = []
    for o in linhas:
        dias = (date.fromisoformat(o["venc"]) - d0).days
        if o["b"] > 0 and o["a"] >= o["b"] and 5 <= dias <= 100 and o["k"] > 0:
            cadeia.append(dict(t=o["t"], k=o["k"], b=o["b"], a=o["a"], v=o["v"], d=dias, s=o["s"]))
    calls = sorted((o for o in cadeia if o["t"] == "C" and 25 <= o["d"] <= 70), key=lambda o: abs(o["k"] / S - 1))[:4]
    ivs = [v for v in (iv_call((o["b"] + o["a"]) / 2, S, o["k"], o["d"] / 365) for o in calls) if v]
    iv = median(ivs) if ivs else 0.30
    return dict(S=S, iv=round(iv, 4), chain=cadeia)


# ---------- rede ----------
def baixar(url, tentativas=3):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (compatible; opcoes-app-atualizador)"})
    for i in range(tentativas):
        try:
            with urllib.request.urlopen(req, timeout=120) as r:
                dados = r.read()
            # Página de erro com código 200 (HTML no lugar do .ZIP) conta como arquivo inexistente.
            return dados if dados[:2] == b"PK" else None
        except urllib.error.HTTPError as e:
            if e.code in (403, 404):
                return None          # arquivo ainda não existe (feriado, fim de semana ou antes da publicação)
            err = e
        except Exception as e:
            err = e
        time.sleep(5 * (i + 1))
    raise SystemExit(f"Falha ao baixar {url}: {err}")


def dias_candidatos(a_partir_de):
    d = a_partir_de
    for _ in range(7):
        if d.weekday() < 5:
            yield d
        d -= timedelta(days=1)


# ---------- snapshot ----------
def carregar():
    with open(SNAPSHOT, encoding="utf-8") as f:
        return json.load(f)


def gravar(snap):
    por = snap["por_data"]
    for d in sorted(por)[:-DIAS_DE_CADEIA]:
        del por[d]
    snap["data"] = max(por)
    snap["ativos"] = por[snap["data"]]
    snap["atualizado_em"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    tmp = SNAPSHOT + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(snap, f, separators=(",", ":"))
    os.replace(tmp, SNAPSHOT)


def incorporar(snap, fech, opc, dia_cadeia=None):
    """Soma fechamentos e, se pedido, a cadeia completa de um dia. Devolve resumo."""
    for nome, serie in fech.items():
        snap["fechamentos"].setdefault(nome, {}).update(serie)
    if dia_cadeia:
        por = {}
        for nome in ATIVOS:
            S = fech[nome].get(dia_cadeia)
            linhas = opc.get(dia_cadeia, {}).get(nome, [])
            if S and linhas:
                p = montar_dia(dia_cadeia, S, linhas)
                if len(p["chain"]) >= 20:          # menos que isso indica arquivo incompleto ou formato diferente
                    por[nome] = p
        if len(por) < len(ATIVOS):
            faltam = sorted(set(ATIVOS) - set(por))
            raise SystemExit(f"Dados incompletos em {dia_cadeia}: sem preço ou opções para {faltam}. Nada foi gravado.")
        snap["por_data"][dia_cadeia] = por
        return {n: (p["S"], p["iv"], len(p["chain"])) for n, p in por.items()}
    return {}


def comparar_com_snapshot(snap, dia, fech, opc):
    ref = snap["por_data"].get(dia)
    if not ref:
        print(f"O snapshot atual não tem o dia {dia} para comparar."); return 1
    ruim = 0
    for nome in ATIVOS:
        S = fech[nome].get(dia); novo = montar_dia(dia, S, opc.get(dia, {}).get(nome, [])) if S else None
        if not novo:
            print(f"{nome}: sem dados no arquivo"); ruim += 1; continue
        a = {(o["s"], o["t"], o["k"]): (o["b"], o["a"], o["d"]) for o in ref[nome]["chain"]}
        b = {(o["s"], o["t"], o["k"]): (o["b"], o["a"], o["d"]) for o in novo["chain"]}
        igual = a == b and abs(ref[nome]["S"] - novo["S"]) < 0.005
        print(f"{nome}: preço {novo['S']} (snapshot {ref[nome]['S']}), opções {len(b)} (snapshot {len(a)}), "
              f"iv {novo['iv']} (snapshot {ref[nome]['iv']}) -> {'IGUAL' if igual else 'DIFERENTE'}")
        if not igual:
            ruim += 1
            so_a, so_b = set(a) - set(b), set(b) - set(a)
            print(f"   só no snapshot: {len(so_a)} | só no arquivo: {len(so_b)} | valores diferentes: {sum(1 for k in set(a) & set(b) if a[k] != b[k])}")
    return ruim


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--data"); ap.add_argument("--arquivo"); ap.add_argument("--ano", type=int); ap.add_argument("--validar")
    a = ap.parse_args()
    snap = carregar()

    if a.validar:
        fech, opc = ler(linhas_do_zip(a.validar))
        dia = max(opc) if opc else max(max(s) for s in fech.values())
        sys.exit(1 if comparar_com_snapshot(snap, dia, fech, opc) else 0)

    if a.ano:
        dados = baixar(URL_ANO.format(aaaa=a.ano))
        if dados is None:
            raise SystemExit("Arquivo anual não encontrado.")
        fech, opc = ler(linhas_do_zip(dados), opc_desde=(date.today() - timedelta(days=20)).isoformat())
        ultimo = max(max(s) for s in fech.values())
        resumo = incorporar(snap, fech, opc, ultimo if ultimo in opc else None)
        gravar(snap); print(f"Fechamentos de {a.ano} incorporados. Último dia: {ultimo}", resumo); return

    if a.arquivo:
        origem, dia = a.arquivo, None
        fech, opc = ler(linhas_do_zip(origem))
    else:
        alvo = date.fromisoformat(a.data) if a.data else datetime.now(timezone(timedelta(hours=-3))).date()
        # Do pregão mais novo para trás, até achar um dia que o snapshot já tem. Baixa todos os que faltam:
        # a cadeia vem do mais novo; os outros completam os fechamentos (o Desempenho usa o fechamento do vencimento).
        ja = set(snap["por_data"]).union(*(set(s) for s in snap["fechamentos"].values()))
        achados, coberto = [], False
        for d in dias_candidatos(alvo):
            if d.isoformat() in ja:
                coberto = True; break
            dados = baixar(URL_DIA.format(ddmmaaaa=d.strftime("%d%m%Y")))
            if dados is not None:
                achados.append((d, ler(linhas_do_zip(dados))))
        if not achados:
            if coberto:
                print(f"Nenhum pregão novo depois de {max(ja)}. Nada a fazer."); return
            # Uma semana inteira sem arquivo não acontece na B3: é URL errada, bloqueio ou formato novo.
            raise SystemExit(f"Nenhum arquivo da B3 nos 7 dias até {alvo} e o snapshot para em {max(ja)}. "
                             "Conferir a URL em URL_DIA ou se a B3 bloqueou o acesso. Nada foi gravado.")
        fech, opc = achados[0][1]
        for _, (f, _o) in achados[1:]:
            for n in ATIVOS:
                fech[n].update(f[n])
        if len(achados) > 1:
            print(f"Fechamentos recuperados de {len(achados) - 1} pregão(s) que tinham ficado para trás.")
        if not coberto:
            print(f"Aviso: ficou um buraco nos fechamentos entre {max(ja)} e {achados[-1][0]}. "
                  f"Para preencher: python atualizar_dados.py --ano {alvo.year}")
    dia = max(opc) if opc else None
    if not dia:
        raise SystemExit("O arquivo não tem opções dos papéis do app.")
    resumo = incorporar(snap, fech, opc, dia)
    gravar(snap)
    print(f"Snapshot atualizado para {dia}:", resumo)


if __name__ == "__main__":
    main()
