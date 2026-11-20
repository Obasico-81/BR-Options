"""Gera as páginas de divulgação a partir de lp/: copia os arquivos e põe em cada página o QR code do próprio endereço
(para quem abre no computador apontar a câmera do celular). lp/index.html: institucional (raiz do site);
lp/bolsa-brasileira/: a da campanha. Uso: python3 build_lp.py [--url URL] [--saida PASTA]"""
import argparse, os, shutil
import segno

ap = argparse.ArgumentParser()
ap.add_argument("--url", default="https://vaglio.com.br/", help="endereço público do site; cada página leva o QR do próprio endereço")
ap.add_argument("--saida", default=os.path.join("pwa", "lp"))
a = ap.parse_args()

if os.path.isdir(a.saida):
    shutil.rmtree(a.saida)
shutil.copytree("lp", a.saida)
# cada página (lp/index.html, a institucional; lp/bolsa-brasileira/index.html, a da campanha) leva o QR do seu endereço
for raiz, _, arqs in os.walk(a.saida):
    if "index.html" not in arqs:
        continue
    p = os.path.join(raiz, "index.html"); t = open(p, encoding="utf-8").read()
    if "<!--QR-->" not in t:
        continue
    rel = os.path.relpath(raiz, a.saida).replace(os.sep, "/")
    url = a.url + ("" if rel == "." else rel + "/")
    qr = segno.make(url, error="m").svg_inline(scale=4, border=1, dark="#111110")
    open(p, "w", encoding="utf-8").write(t.replace("<!--QR-->", qr, 1))
    print("página", p, "· QR para", url)
