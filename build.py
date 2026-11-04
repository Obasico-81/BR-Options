"""Gera index.html embutindo montador.js e o snapshot publicado (enxuto) a partir de snapshot.json.

O snapshot.json do repositório guarda até 12 pregões de cadeia (paridade, testes, modo ?teste=1 local). O app só
usa o pregão mais recente e os fechamentos: o publicado leva só isso, sem a cópia duplicada em "ativos" (o app a
refaz a partir de por_data). Com 12 pregões dos 11 ativos, ~1,3 MB viram ~0,15 MB.
"""
import json


def snapshot_publicado(caminho="snapshot.json"):
    s = json.load(open(caminho, encoding="utf-8"))
    return {"data": s["data"], "atualizado_em": s.get("atualizado_em"), "fechamentos": s["fechamentos"],
            "por_data": {s["data"]: s["por_data"][s["data"]]}}


if __name__ == "__main__":
    snap = json.dumps(snapshot_publicado(), ensure_ascii=False, separators=(",", ":"))
    t = open("template.html", encoding="utf-8").read()
    t = t.replace("/*MONTADOR*/", open("montador.js", encoding="utf-8").read()).replace("/*SNAPSHOT*/", snap)
    open("index.html", "w", encoding="utf-8").write(t); print(len(t.encode("utf-8")) // 1024, "KB")
