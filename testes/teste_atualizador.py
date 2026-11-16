"""Testa atualizar_dados.py contra um servidor local que imita o site da B3 (arquivos sintéticos).

Uso: python3 -I teste_atualizador.py /caminho/do/projeto
Cada cenário roda numa cópia do projeto; o snapshot.json do repositório não é tocado.
"""
import http.server, io, json, os, shutil, subprocess, sys, tempfile, threading, zipfile

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)
import gerar_cotahist as G

PROJ = os.path.abspath(sys.argv[1])
# Os cenários usam datas fixas do começo de 2026 e partem de uma cópia fixa do snapshot original (12 dias de
# cadeia até 30/12/2025, o dia do --validar), e não do snapshot.json que o workflow atualiza todo dia.
SNAP0 = json.load(open(os.path.join(AQUI, "snapshot_base.json")))
BASE = SNAP0["data"]                      # 2025-12-30
FIXTURE = json.dumps(SNAP0, separators=(",", ":")).encode()


class Servidor:
    def __init__(self):
        self.arquivos, self.modo, self.selic = {}, "normal", None   # selic: resposta do "Banco Central" (None: 404)
        dono = self

        class H(http.server.BaseHTTPRequestHandler):
            def do_GET(self):
                nome = self.path.split("?")[0].rsplit("/", 1)[-1]   # a consulta da Selic tem datas com barra
                if dono.modo == "403":
                    self.send_response(403); self.end_headers(); return
                if dono.modo == "html200":
                    corpo = b"<html><body>Arquivo nao encontrado</body></html>"
                    self.send_response(200); self.send_header("Content-Type", "text/html"); self.end_headers()
                    self.wfile.write(corpo); return
                if nome == "selic":
                    if dono.selic is None:
                        self.send_response(404); self.end_headers(); return
                    self.send_response(200); self.send_header("Content-Type", "application/json"); self.end_headers()
                    self.wfile.write(dono.selic); return
                if nome not in dono.arquivos:
                    self.send_response(404); self.end_headers(); return
                corpo = dono.arquivos[nome]
                self.send_response(200); self.send_header("Content-Length", str(len(corpo))); self.end_headers()
                self.wfile.write(corpo)

            def log_message(self, *a):
                pass

        self.httpd = http.server.ThreadingHTTPServer(("127.0.0.1", 0), H)
        threading.Thread(target=self.httpd.serve_forever, daemon=True).start()
        self.porta = self.httpd.server_address[1]

    def dia(self, iso, ativos, **kw):
        self.arquivos["COTAHIST_D%s.ZIP" % (iso[8:10] + iso[5:7] + iso[:4])] = G.zip_do_dia(iso, ativos, **kw)


SRV = Servidor()
WRAP = """import sys; sys.path.insert(0, {d!r}); import atualizar_dados as A
A.URL_DIA = "http://127.0.0.1:{p}/COTAHIST_D{{ddmmaaaa}}.ZIP"; A.URL_ANO = "http://127.0.0.1:{p}/COTAHIST_A{{aaaa}}.ZIP"
A.URL_SELIC = "http://127.0.0.1:{p}/selic?di={{di}}&df={{df}}"
sys.argv = ["atualizar_dados.py"] + {args!r}; A.main()
"""


def rodar(tmp, *args):
    env = dict(os.environ, NO_PROXY="127.0.0.1,localhost", no_proxy="127.0.0.1,localhost")
    r = subprocess.run([sys.executable, "-I", "-c", WRAP.format(d=tmp, p=SRV.porta, args=list(args))],
                       capture_output=True, text=True, env=env, timeout=120)
    return r.returncode, (r.stdout + r.stderr).strip()


def projeto():
    tmp = tempfile.mkdtemp(dir=os.path.join(AQUI, "tmp"))
    shutil.copy(os.path.join(PROJ, "atualizar_dados.py"), tmp)
    open(os.path.join(tmp, "snapshot.json"), "wb").write(FIXTURE)
    return tmp


def snap(tmp):
    return json.load(open(os.path.join(tmp, "snapshot.json")))


def bruto(tmp):
    return open(os.path.join(tmp, "snapshot.json"), "rb").read()


falhas = 0


def precos(tmp):
    pasta = os.path.join(tmp, "pwa", "precos")
    return {f[:-5]: json.load(open(os.path.join(pasta, f))) for f in sorted(os.listdir(pasta))} if os.path.isdir(pasta) else {}


def esperado_precos(ativos):
    """Séries que devem estar no arquivo do dia: compra > 0, venda >= compra, 5 a 100 dias (a cadeia sintética já
    tem compra > 0 e venda >= compra; as linhas de ruído sem compra ficam de fora)."""
    return {o["s"]: [o["b"], o["a"]] for a in ativos.values() for o in a["chain"] if 5 <= o["d"] <= 100}


def confere(nome, cond, saida):
    global falhas
    print(("OK    " if cond else "FALHA ") + nome)
    if not cond:
        falhas += 1
        print("      saída:", saida.replace("\n", "\n      "))


os.makedirs(os.path.join(AQUI, "tmp"), exist_ok=True)
orig = FIXTURE

# G. --validar com o dia do snapshot
t = projeto(); z = os.path.join(t, "COTAHIST_D30122025.ZIP")
open(z, "wb").write(G.zip_do_dia(BASE, SNAP0["por_data"][BASE]))
rc, out = rodar(t, "--validar", z)
confere("validar: IGUAL nos três papéis", rc == 0 and out.count("IGUAL") == 3 and "DIFERENTE" not in out, out)
print("      " + out.replace("\n", "\n      "))

# A. feriado: 01/01 e 31/12 sem arquivo; 30/12 já está no snapshot
t = projeto(); rc, out = rodar(t, "--data", "2026-01-01")
confere("feriado: nada a fazer, código 0, snapshot intacto", rc == 0 and "Nada a fazer" in out and bruto(t) == orig, out)

# B. dia perdido: o atualizador não rodou em 02/01; em 05/01 baixa os dois
SRV.arquivos.clear()
SRV.dia("2026-01-02", G.ativos_deslocados(SNAP0, BASE, "2026-01-02", 1.01))
SRV.dia("2026-01-05", G.ativos_deslocados(SNAP0, BASE, "2026-01-05", 1.02))
t = projeto(); rc, out = rodar(t, "--data", "2026-01-05"); s = snap(t)
ok = (rc == 0 and s["data"] == "2026-01-05" and all("2026-01-02" in s["fechamentos"][n] and "2026-01-05" in s["fechamentos"][n] for n in G.PAPEL)
      and "2026-01-02" not in s["por_data"] and len(s["por_data"]) == 12 and "recuperados de 1" in out and "buraco" not in out
      and abs(s["fechamentos"]["PETR4"]["2026-01-02"] - round(SNAP0["por_data"][BASE]["PETR4"]["S"] * 1.01, 2)) < 1e-9)
confere("dia perdido: recupera o fechamento de 02/01, cadeia de 05/01, mantém 12 dias de cadeia", ok, out)
mm_esp = lambda S: [round(S * 1.01, 2), round(S * 0.99, 2)]
ok = all(s.get("maxmin", {}).get(n, {}).get(d) == mm_esp(G.ativos_deslocados(SNAP0, BASE, d, f)[n]["S"])
         for n in SNAP0["por_data"][BASE] for d, f in (("2026-01-02", 1.01), ("2026-01-05", 1.02)))
confere("máxima e mínima do dia: grava a do pregão novo e a do recuperado", ok, json.dumps({n: s.get("maxmin", {}).get(n) for n in list(G.PAPEL)[:2]}))
print("      " + out.replace("\n", "\n      "))
pr = precos(t); e2, e5 = (esperado_precos(G.ativos_deslocados(SNAP0, BASE, d)) for d in ("2026-01-02", "2026-01-05"))
confere("preços diários: grava 02/01 (recuperado) e 05/01, com compra e venda de cada série",
        set(pr) == {"2026-01-02", "2026-01-05"} and pr["2026-01-02"]["op"] == e2 and pr["2026-01-05"]["op"] == e5 and len(e5) > 100, out)
antes = {f: os.path.getmtime(os.path.join(t, "pwa", "precos", f + ".json")) for f in pr}
rc, out = rodar(t, "--data", "2026-01-05")
confere("segunda execução no mesmo dia: nada a fazer", rc == 0 and "Nada a fazer" in out, out)
confere("preços diários: segunda execução não regrava nada",
        {f: os.path.getmtime(os.path.join(t, "pwa", "precos", f + ".json")) for f in precos(t)} == antes, out)

# F. buraco maior que a janela: avisa e grava o que achou
SRV.arquivos.clear()
SRV.dia("2026-01-19", G.ativos_deslocados(SNAP0, BASE, "2026-01-19"))
SRV.dia("2026-01-20", G.ativos_deslocados(SNAP0, BASE, "2026-01-20"))
t = projeto(); rc, out = rodar(t, "--data", "2026-01-20"); s = snap(t)
confere("buraco: grava 19 e 20/01 e avisa para rodar --ano", rc == 0 and s["data"] == "2026-01-20" and "buraco" in out and "--ano 2026" in out, out)

# C. B3 bloqueia (403 em tudo) e o snapshot está velho: falha visível, nada gravado
SRV.modo = "403"; t = projeto(); rc, out = rodar(t, "--data", "2026-01-20")
confere("bloqueio 403: código ≠ 0, nada gravado", rc != 0 and "Nenhum arquivo da B3" in out and bruto(t) == orig, out)

# D. B3 responde 200 com página HTML
SRV.modo = "html200"; t = projeto(); rc, out = rodar(t, "--data", "2026-01-01")
confere("HTML com 200 em feriado: tratado como sem arquivo, nada a fazer", rc == 0 and "Nada a fazer" in out and bruto(t) == orig, out)
rc, out = rodar(t, "--data", "2026-01-20")
confere("HTML com 200 e snapshot velho: código ≠ 0, nada gravado", rc != 0 and bruto(t) == orig, out)
SRV.modo = "normal"

# E. dia incompleto (10 opções por papel)
SRV.arquivos.clear(); SRV.dia("2026-01-02", G.ativos_deslocados(SNAP0, BASE, "2026-01-02"), so_n_opcoes=10)
t = projeto(); rc, out = rodar(t, "--data", "2026-01-02")
confere("dia incompleto: recusa, nada gravado (nem preços diários)", rc != 0 and "Dados incompletos" in out and bruto(t) == orig and not precos(t), out)

# preço diário que já existe não é sobrescrito
SRV.arquivos.clear(); SRV.dia("2026-01-02", G.ativos_deslocados(SNAP0, BASE, "2026-01-02"))
t = projeto(); os.makedirs(os.path.join(t, "pwa", "precos")); falso = {"data": "2026-01-02", "op": {"X": [1, 2]}}
json.dump(falso, open(os.path.join(t, "pwa", "precos", "2026-01-02.json"), "w"))
rc, out = rodar(t, "--data", "2026-01-02")
confere("preços diários: arquivo já existente não é sobrescrito", rc == 0 and precos(t)["2026-01-02"] == falso, out)

# I/J. papel novo (não obrigatório): fraco fica de fora só naquele dia; completo entra
G.PAPEL["ITUB4"] = "ITUB4"
def com_itub(dia, n_itub=None):
    at = G.ativos_deslocados(SNAP0, BASE, dia)
    ch = [dict(o, s="ITUB" + o["s"][4:]) for o in at["BOVA11"]["chain"]]
    at["ITUB4"] = dict(S=round(at["BOVA11"]["S"] / 4, 2), iv=at["BOVA11"]["iv"], chain=ch[:n_itub] if n_itub else ch)
    at["ITUB4"]["chain"] = [dict(o, k=round(o["k"] / 4, 2)) for o in at["ITUB4"]["chain"]]
    return at
SRV.arquivos.clear(); SRV.dia("2026-01-02", com_itub("2026-01-02", n_itub=10))
t = projeto(); rc, out = rodar(t, "--data", "2026-01-02"); s = snap(t); dia = s["por_data"].get("2026-01-02", {})
confere("papel novo com 10 opções: fica de fora, os 3 obrigatórios são gravados",
        rc == 0 and set(dia) == {"BOVA11", "PETR4", "VALE3"} and "ficaram de fora" in out and "ITUB4" in out, out)
SRV.arquivos.clear(); SRV.dia("2026-01-02", com_itub("2026-01-02"))
t = projeto(); rc, out = rodar(t, "--data", "2026-01-02"); s = snap(t); dia = s["por_data"].get("2026-01-02", {})
confere("papel novo completo: entra no dia", rc == 0 and "ITUB4" in dia and len(dia["ITUB4"]["chain"]) >= 20 and "ITUB4" in s["fechamentos"], out)

# H. sequência do workflow na primeira execução: --ano 2026 e depois sem argumento (hoje)
from datetime import date, timedelta
hoje = date.today()
dias = [d for d in (hoje - timedelta(days=i) for i in range(1, 6)) if d.weekday() < 5][:2]
b = io.BytesIO()
with zipfile.ZipFile(b, "w", zipfile.ZIP_DEFLATED) as zf:
    linhas = []
    for d in sorted(dias):
        linhas += G.linhas_do_dia(d.isoformat(), SNAP0["por_data"][BASE])
    zf.writestr("COTAHIST_A%d.TXT" % hoje.year, ("\r\n".join(linhas) + "\r\n").encode("latin-1"))
SRV.arquivos.clear(); SRV.arquivos["COTAHIST_A%d.ZIP" % hoje.year] = b.getvalue()
t = projeto(); rc1, out1 = rodar(t, "--ano", str(hoje.year)); rc2, out2 = rodar(t); s = snap(t)
ok = rc1 == 0 and rc2 == 0 and s["data"] == max(dias).isoformat() and all(d.isoformat() in s["fechamentos"]["VALE3"] for d in dias) and "Nada a fazer" in out2
confere("workflow: --ano e depois a execução diária", ok, out1 + "\n" + out2)
confere("--ano grava máxima e mínima de todos os pregões do arquivo",
        all(set(s.get("maxmin", {}).get(n, {})) >= {d.isoformat() for d in dias} for n in SNAP0["por_data"][BASE]), json.dumps(s.get("maxmin")))
confere("preços diários: --ano grava todos os pregões do arquivo", set(precos(t)) == {d.isoformat() for d in dias}
        and all(precos(t)[d.isoformat()]["op"] == esperado_precos({n: dict(a, chain=[dict(o) for o in a["chain"]]) for n, a in SNAP0["por_data"][BASE].items()}) for d in dias), out1)

# K. --ano refaz as cadeias que o snapshot já tem: uma opção de outro papel-objeto guardada antes sai da cadeia
b = io.BytesIO()
with zipfile.ZipFile(b, "w", zipfile.ZIP_DEFLATED) as zf:
    zf.writestr("COTAHIST_A2025.TXT", ("\r\n".join(G.linhas_do_dia(BASE, SNAP0["por_data"][BASE])) + "\r\n").encode("latin-1"))
SRV.arquivos.clear(); SRV.arquivos["COTAHIST_A2025.ZIP"] = b.getvalue()
t = projeto(); s0 = snap(t)
for n, a in s0["por_data"][BASE].items():
    a["chain"].append(dict(t="C", k=a["S"], b=1.0, a=1.05, v=100000, d=30, s=n[:4] + "K777"))
json.dump(s0, open(os.path.join(t, "snapshot.json"), "w"))
rc, out = rodar(t, "--ano", "2025"); s = snap(t)
chave = lambda ch: {(o["s"], o["t"], o["k"], o["b"], o["a"], o["d"]) for o in ch}
ok = rc == 0 and "cadeias refeitas: 1" in out and "descartadas" in out and all(
    chave(s["por_data"][BASE][n]["chain"]) == chave(SNAP0["por_data"][BASE][n]["chain"]) for n in SNAP0["por_data"][BASE])
confere("--ano refaz a cadeia guardada e tira a opção de outro papel-objeto", ok, out)

# S. Selic do dia (Banco Central): a volatilidade implícita é tirada com ela e ela fica no snapshot; sem o Banco Central,
# vale a última guardada; sem nenhuma, o juro padrão (e nada de Selic gravada)
import importlib.util
spec = importlib.util.spec_from_file_location("ad", os.path.join(PROJ, "atualizar_dados.py")); AD = importlib.util.module_from_spec(spec); spec.loader.exec_module(AD)
def iv_esperada(a, r):
    calls = sorted((o for o in a["chain"] if o["t"] == "C" and 25 <= o["d"] <= 70), key=lambda o: abs(o["k"] / a["S"] - 1))[:4]
    ivs = [v for v in (AD.iv_call((o["b"] + o["a"]) / 2, a["S"], o["k"], o["d"] / 365, r) for o in calls) if v]
    return round(AD.median(ivs), 4) if ivs else 0.30
SRV.arquivos.clear()
SRV.dia("2026-01-02", G.ativos_deslocados(SNAP0, BASE, "2026-01-02", 1.01)); SRV.dia("2026-01-05", G.ativos_deslocados(SNAP0, BASE, "2026-01-05", 1.02))
SRV.selic = json.dumps([{"data": "31/12/2025", "valor": "15.00"}, {"data": "02/01/2026", "valor": "14.25"}]).encode()
t = projeto(); rc, out = rodar(t, "--data", "2026-01-02"); s = snap(t); dia = s["por_data"].get("2026-01-02", {})
r1 = AD.juro_da_selic(14.25)
ok = (rc == 0 and s.get("selic", {}).get("2026-01-02") == 14.25 and dia and all(a["iv"] == iv_esperada(a, r1) for a in dia.values())
      and any(a["iv"] != iv_esperada(a, AD.R) for a in dia.values()))
confere("Selic do dia: guardada no snapshot e usada na volatilidade implícita", ok, out)
SRV.selic = None
rc, out = rodar(t, "--data", "2026-01-05"); s = snap(t); dia = s["por_data"].get("2026-01-05", {})
ok = rc == 0 and s["selic"].get("2026-01-05") == 14.25 and "última guardada" in out and dia and all(a["iv"] == iv_esperada(a, r1) for a in dia.values())
confere("Banco Central fora do ar: usa a última Selic guardada e avisa", ok, out)
t = projeto(); rc, out = rodar(t, "--data", "2026-01-02"); s = snap(t); dia = s["por_data"].get("2026-01-02", {})
ok = rc == 0 and "selic" not in s and "juro padrão" in out and dia and all(a["iv"] == iv_esperada(a, AD.R) for a in dia.values())
confere("sem Selic nenhuma: juro padrão, com aviso, e nada de Selic gravada", ok, out)

shutil.rmtree(os.path.join(AQUI, "tmp"), ignore_errors=True)
print("\n%s" % ("todos os cenários passaram" if not falhas else "%d cenário(s) falharam" % falhas))
sys.exit(1 if falhas else 0)
