#!/usr/bin/env python3
"""Atualiza snapshot.json com o fechamento mais recente da B3 (arquivo COTAHIST diário).

Uso (na pasta do projeto):
  python3 atualizar_dados.py                    # baixa o pregão mais recente disponível
  python3 atualizar_dados.py --data 2026-11-03  # um dia específico
  python3 atualizar_dados.py --arquivo COTAHIST_D03112026.ZIP   # usa um arquivo já baixado
  python3 atualizar_dados.py --ano 2026         # fechamentos do ano inteiro e refaz as cadeias que o snapshot tem (COTAHIST_A2026.ZIP)
  python3 atualizar_dados.py --validar COTAHIST_D30122025.ZIP   # confere o leitor contra o snapshot atual

Sem dependências além do Python 3.9+. Termina com código 0 quando não há arquivo novo (feriado/fim de semana).
Layout de posição fixa do COTAHIST (documentação oficial da B3): ver CAMPOS.
"""
import argparse, io, json, math, os, sys, time, urllib.error, urllib.request, zipfile
from datetime import date, datetime, timedelta, timezone
from statistics import median

# Papéis do app: nome -> (prefixo das opções, código do papel à vista)
ATIVOS = {"BOVA11": ("BOVA", "BOVA11"), "PETR4": ("PETR", "PETR4"), "VALE3": ("VALE", "VALE3"),
          # incluídos em 02/11/2026: montam em >= 60% dos pregões com o corte do app (pesquisa/liquidez.py)
          "BBDC4": ("BBDC", "BBDC4"), "BBAS3": ("BBAS", "BBAS3"), "MGLU3": ("MGLU", "MGLU3"),
          "ITUB4": ("ITUB", "ITUB4"), "B3SA3": ("B3SA", "B3SA3")}
# Retirados em 06/11/2026: WEGE3, USIM5 e PRIO3. Com as quatro operações do Início e o perfil padrão (risco R$ 500,
# capital R$ 12.000), em qualquer vencimento, montavam em menos de 60% dos pregões em 2025 e 2026 (pesquisa/disponibilidade.py,
# pesquisa/RESULTADO_DISPONIBILIDADE.md). Os fechamentos já gravados ficam no snapshot (operações antigas nesses papéis).
# Se um destes vier sem preço ou com menos de 20 opções, o arquivo do dia está com problema: nada é gravado.
# Os demais ficam de fora só naquele dia (o app não os lista), com aviso.
OBRIGATORIOS = ("BOVA11", "PETR4", "VALE3")
URL_DIA = "https://bvmf.bmfbovespa.com.br/InstDados/SerHist/COTAHIST_D{ddmmaaaa}.ZIP"
URL_ANO = "https://bvmf.bmfbovespa.com.br/InstDados/SerHist/COTAHIST_A{aaaa}.ZIP"
SNAPSHOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "snapshot.json")
# Preços diários das opções (melhor compra e venda no fechamento), um arquivo por pregão, publicado com o app:
# o app marca as operações simuladas dia a dia (valor hoje e regras de saída). Arquivo novo por dia, nunca regravado.
PRECOS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "pwa", "precos")
DIAS_DE_CADEIA = 12          # quantos pregões completos (com cadeia de opções) ficam no snapshot
R = 0.11                     # juro livre de risco usado na volatilidade implícita (igual ao backtest)

# (início 1-based, fim inclusive)
CAMPOS = dict(tipreg=(1, 2), data=(3, 10), codneg=(13, 24), tpmerc=(25, 27),
              premax=(70, 82), premin=(83, 95), preult=(109, 121), preofc=(122, 134), preofv=(135, 147), quatot=(153, 170),
              preexe=(189, 201), datven=(203, 210), codisi=(231, 242))


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
    """Devolve (fechamentos, opcoes, maxmin): fechamentos[nome][data] = último preço; opcoes[data][nome] = lista de
    linhas; maxmin[nome][data] = [máxima, mínima] do papel no dia (a tendência do minigráfico usa no ADX).
    A opção entra pelo prefixo do código E pelo papel-objeto: o CODISI da opção é o ISIN do papel à vista, e um prefixo
    serve a mais de um papel (BBDC: BBDC3 e BBDC4; PETR: PETR3 e PETR4; ITUB: ITUB3 e ITUB4). Só ficam as do papel do app."""
    prefixos = {pref: nome for nome, (pref, _) in ATIVOS.items()}
    papeis = {pap: nome for nome, (_, pap) in ATIVOS.items()}
    fech, opc, isin, mm = {n: {} for n in ATIVOS}, {}, {n: set() for n in ATIVOS}, {n: {} for n in ATIVOS}
    for ln in linhas:
        if len(ln) < 210 or campo(ln, "tipreg") != "01":
            continue
        d = campo(ln, "data")
        if so_data and d != so_data:
            continue
        cod, tp = campo(ln, "codneg"), campo(ln, "tpmerc")
        if tp == "010" and cod in papeis:
            isin[papeis[cod]].add(campo(ln, "codisi"))
            p = preco(campo(ln, "preult"))
            if p > 0:
                fech[papeis[cod]][iso(d)] = p
                h, lo = preco(campo(ln, "premax")), preco(campo(ln, "premin"))
                if h >= p >= lo > 0:
                    mm[papeis[cod]][iso(d)] = [h, lo]
        elif tp in ("070", "080") and cod[:4] in prefixos and (not opc_desde or iso(d) >= opc_desde):
            b, a = preco(campo(ln, "preofc")), preco(campo(ln, "preofv"))
            if not (b > 0 and a >= b):
                continue
            opc.setdefault(iso(d), {}).setdefault(prefixos[cod[:4]], []).append(dict(
                t="C" if tp == "070" else "P", k=preco(campo(ln, "preexe")), b=b,
                a=a, v=int(campo(ln, "quatot") or 0), venc=iso(campo(ln, "datven")), s=cod, isin=campo(ln, "codisi")))
    fora = {}
    for por in opc.values():
        for nome, lst in por.items():
            por[nome] = [o for o in lst if o.pop("isin") in isin[nome]]
            if len(por[nome]) < len(lst):
                fora[nome] = fora.get(nome, 0) + len(lst) - len(por[nome])
    if fora:
        print("Opções de outro papel com o mesmo prefixo, descartadas:", ", ".join(f"{n} {q}" for n, q in sorted(fora.items())))
    return fech, opc, mm


def gravar_precos(opc, dias):
    """Grava pwa/precos/AAAA-MM-DD.json de cada dia pedido: {"data", "op": {símbolo: [compra, venda]}} das séries dos
    papéis do app com compra > 0, venda >= compra e 5 a 100 dias (as mesmas que podem entrar na cadeia). Não regrava
    um dia que já existe. Devolve quantos arquivos foram criados."""
    os.makedirs(PRECOS, exist_ok=True); novos = 0
    for dia in sorted(dias):
        arq = os.path.join(PRECOS, f"{dia}.json")
        if os.path.exists(arq) or dia not in opc:
            continue
        d0 = date.fromisoformat(dia); op = {}
        for linhas in opc[dia].values():
            for o in linhas:
                if o["b"] > 0 and o["a"] >= o["b"] and 5 <= (date.fromisoformat(o["venc"]) - d0).days <= 100:
                    op[o["s"]] = [o["b"], o["a"]]
        if op:
            with open(arq + ".tmp", "w", encoding="utf-8") as f:
                json.dump({"data": dia, "op": dict(sorted(op.items()))}, f, separators=(",", ":"))
            os.replace(arq + ".tmp", arq); novos += 1
    return novos


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


def incorporar(snap, fech, opc, dia_cadeia=None, mm=None):
    """Soma fechamentos (e máximas/mínimas) e, se pedido, a cadeia completa de um dia. Devolve resumo."""
    for nome, serie in fech.items():
        snap["fechamentos"].setdefault(nome, {}).update(serie)
    for nome, serie in (mm or {}).items():
        if serie:
            snap.setdefault("maxmin", {}).setdefault(nome, {}).update(serie)
    if dia_cadeia:
        por = {}
        for nome in ATIVOS:
            S = fech[nome].get(dia_cadeia)
            linhas = opc.get(dia_cadeia, {}).get(nome, [])
            if S and linhas:
                p = montar_dia(dia_cadeia, S, linhas)
                if len(p["chain"]) >= 20:          # menos que isso indica arquivo incompleto ou formato diferente
                    por[nome] = p
        faltam = [n for n in OBRIGATORIOS if n not in por]
        if faltam:
            raise SystemExit(f"Dados incompletos em {dia_cadeia}: sem preço ou opções para {faltam}. Nada foi gravado.")
        fora = sorted(set(ATIVOS) - set(por))
        if fora:
            print(f"Aviso: {fora} ficaram de fora em {dia_cadeia} (sem preço ou menos de 20 opções); os demais foram gravados.")
        snap["por_data"][dia_cadeia] = por
        return {n: (p["S"], p["iv"], len(p["chain"])) for n, p in por.items()}
    return {}


def comparar_com_snapshot(snap, dia, fech, opc):
    ref = snap["por_data"].get(dia)
    if not ref:
        print(f"O snapshot atual não tem o dia {dia} para comparar."); return 1
    ruim = 0
    for nome in [n for n in ATIVOS if n in ref]:      # só os papéis que o snapshot de referência tem
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
        fech, opc, _ = ler(linhas_do_zip(a.validar))
        dia = max(opc) if opc else max(max(s) for s in fech.values() if s)
        sys.exit(1 if comparar_com_snapshot(snap, dia, fech, opc) else 0)

    if a.ano:
        dados = baixar(URL_ANO.format(aaaa=a.ano))
        if dados is None:
            raise SystemExit("Arquivo anual não encontrado.")
        fech, opc, mm = ler(linhas_do_zip(dados))
        ultimo = max(max(s) for s in fech.values() if s)
        recente = ultimo in opc and ultimo >= (date.today() - timedelta(days=20)).isoformat()
        # refaz também as cadeias dos pregões que o snapshot já tem e que estão no arquivo (vale para correções do leitor)
        refazer = sorted(d for d in snap["por_data"] if d in opc and d != ultimo) + ([ultimo] if ultimo in opc and (recente or ultimo in snap["por_data"]) else [])
        resumo = incorporar(snap, fech, opc, None, mm)
        for d in refazer:
            resumo = incorporar(snap, fech, opc, d)
        gravar(snap); novos = gravar_precos(opc, opc.keys())
        print(f"Fechamentos de {a.ano} incorporados. Último dia: {ultimo}", resumo, f"| cadeias refeitas: {len(refazer)}",
              f"| preços diários: {novos} dia(s) novo(s)"); return

    if a.arquivo:
        origem, dia = a.arquivo, None
        fech, opc, mm = ler(linhas_do_zip(origem))
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
        fech, opc, mm = achados[0][1]
        for _, (f, o2, mm2) in achados[1:]:
            for n in ATIVOS:
                fech[n].update(f[n]); mm[n].update(mm2[n])
            for d2, v in o2.items():          # opções dos pregões recuperados: só para os preços diários
                opc.setdefault(d2, v)          # (a cadeia continua sendo a do pregão mais novo, max(opc))
        if len(achados) > 1:
            print(f"Fechamentos recuperados de {len(achados) - 1} pregão(s) que tinham ficado para trás.")
        if not coberto:
            print(f"Aviso: ficou um buraco nos fechamentos entre {max(ja)} e {achados[-1][0]}. "
                  f"Para preencher: python atualizar_dados.py --ano {alvo.year}")
    dia = max(opc) if opc else None
    if not dia:
        raise SystemExit("O arquivo não tem opções dos papéis do app.")
    resumo = incorporar(snap, fech, opc, dia, mm)
    gravar(snap); novos = gravar_precos(opc, opc.keys())
    print(f"Snapshot atualizado para {dia}:", resumo, f"| preços diários: {novos} dia(s) novo(s)")


if __name__ == "__main__":
    main()
