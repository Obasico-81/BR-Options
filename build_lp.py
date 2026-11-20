"""Gera a página de divulgação (LP) a partir de lp/: copia os arquivos e põe o QR code do endereço da própria LP
(para quem abre no computador apontar a câmera do celular). Uso: python3 build_lp.py [--url URL] [--saida PASTA]"""
import argparse, os, shutil
import segno

ap = argparse.ArgumentParser()
ap.add_argument("--url", default="https://vaglio.com.br/", help="endereço público da LP (vai no QR code)")
ap.add_argument("--saida", default=os.path.join("pwa", "lp"))
a = ap.parse_args()

if os.path.isdir(a.saida):
    shutil.rmtree(a.saida)
shutil.copytree("lp", a.saida)
qr = segno.make(a.url, error="m").svg_inline(scale=4, border=1, dark="#111110")
p = os.path.join(a.saida, "index.html")
t = open(p, encoding="utf-8").read()
assert "<!--QR-->" in t
open(p, "w", encoding="utf-8").write(t.replace("<!--QR-->", qr, 1))
print("LP em", a.saida, "· QR para", a.url)
