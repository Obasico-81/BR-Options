"""Gera index.html embutindo montador.js e o snapshot publicado (enxuto) a partir de snapshot.json.

O snapshot.json do repositório guarda até 12 pregões de cadeia (paridade, testes, modo ?teste=1 local). O app só
usa o pregão mais recente e os fechamentos: o publicado leva só isso, sem a cópia duplicada em "ativos" (o app a
refaz a partir de por_data). Com 12 pregões dos 11 ativos, ~1,3 MB viram ~0,15 MB.
"""
import base64, json

# Figtree (variável, pesos 300-900), só o alfabeto latino: acentos do português e o sinal de menos (U+2212)
FONTE = ("@font-face{font-family:'Figtree';font-style:normal;font-display:swap;font-weight:300 900;"
         "src:url(data:font/woff2;base64,%s) format('woff2');unicode-range:U+0000-00FF,U+0131,U+0152-0153,U+02BB-02BC,"
         "U+02C6,U+02DA,U+02DC,U+0304,U+0308,U+0329,U+2000-206F,U+20AC,U+2122,U+2191,U+2193,U+2212,U+2215,U+FEFF,U+FFFD}")


def textos():
    """Termos de uso e política de privacidade (textos/*.html), com responsável e contato de textos/contato.json.
    Campo vazio aparece como "[a definir: ...]". Links externos abrem fora do app."""
    c = json.load(open("textos/contato.json", encoding="utf-8"))
    val = {"{{RESPONSAVEL}}": c.get("responsavel") or "[a definir: responsável]", "{{EMAIL}}": c.get("email") or "[a definir: e-mail de contato]"}
    out = {}
    for k in ("termos", "privacidade"):
        t = open(f"textos/{k}.html", encoding="utf-8").read().replace('<a href=', '<a target="_blank" rel="noopener" href=')
        for a, b in val.items():
            t = t.replace(a, b)
        out[k] = t
    return out


def fonte_css():
    return FONTE % base64.b64encode(open("fontes/figtree-latin-wght-normal.woff2", "rb").read()).decode()


PREG_MAXMIN = 160   # máximas e mínimas publicadas por papel: a tendência do minigráfico usa os últimos 150 pregões


def snapshot_publicado(caminho="snapshot.json"):
    s = json.load(open(caminho, encoding="utf-8"))
    p = {"data": s["data"], "atualizado_em": s.get("atualizado_em"), "fechamentos": s["fechamentos"],
         "por_data": {s["data"]: s["por_data"][s["data"]]}}
    if s.get("maxmin"):
        p["maxmin"] = {n: {d: v[d] for d in sorted(d for d in v if d <= s["data"])[-PREG_MAXMIN:]} for n, v in s["maxmin"].items()}
    return p


if __name__ == "__main__":
    snap = json.dumps(snapshot_publicado(), ensure_ascii=False, separators=(",", ":"))
    t = open("template.html", encoding="utf-8").read()
    t = t.replace("/*TEXTOS*/", json.dumps(textos(), ensure_ascii=False)).replace("/*FONTE*/", fonte_css()).replace("/*MONTADOR*/", open("montador.js", encoding="utf-8").read()).replace("/*SNAPSHOT*/", snap)
    open("index.html", "w", encoding="utf-8").write(t); print(len(t.encode("utf-8")) // 1024, "KB")
