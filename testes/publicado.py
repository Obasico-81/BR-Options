"""Snapshot publicado (build.snapshot_publicado): com vários pregões no snapshot do repositório, o app e o site
recebem só o mais recente, sem a cópia em "ativos", com todos os fechamentos. Usa testes/snapshot_base.json
(12 pregões). Uso: python3 testes/publicado.py"""
import json, os, sys
RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); sys.path.insert(0, RAIZ)
from build import snapshot_publicado
base = os.path.join(RAIZ, "testes", "snapshot_base.json")
s, p = json.load(open(base)), snapshot_publicado(base)
falhas = 0
def confere(nome, ok):
    global falhas
    print(("OK    " if ok else "FALHA ") + nome); falhas += 0 if ok else 1
confere(f"o repositório tem vários pregões ({len(s['por_data'])})", len(s["por_data"]) > 1)
confere("publicado: só o pregão mais recente", list(p["por_data"]) == [s["data"]] and p["data"] == s["data"])
confere("publicado: a cadeia do dia é a mesma", p["por_data"][s["data"]] == s["ativos"])
confere("publicado: sem a cópia em 'ativos'", "ativos" not in p)
confere("publicado: todos os fechamentos", p["fechamentos"] == s["fechamentos"])
t0, t1 = len(json.dumps(s, separators=(",", ":"))), len(json.dumps(p, separators=(",", ":")))
confere(f"publicado menor: {t0 // 1024} KB -> {t1 // 1024} KB", t1 < t0 / 3)
print("\ntodos os casos passaram" if not falhas else f"\n{falhas} caso(s) falharam"); sys.exit(1 if falhas else 0)
