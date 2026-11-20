"""Monta o site publicado no domínio vaglio.com.br a partir de pwa/ (gerado por build.py e build_pwa.py).

  site/app/               o app (cópia de pwa/)
  site/index.html         a raiz: na Fase 1, leva direto ao app; na Fase 2, as páginas de divulgação (lp/)
  site/404.html           endereço antigo sem /app/ (links e app instalado do tempo do github.io) vai para /app/
  site/snapshot.json      cópia dos dados do dia na raiz, para o APK antigo, que busca em <site>/snapshot.json
  site/precos/            idem, preços diários

O endereço antigo (obasico-81.github.io/BR-Options/...) é redirecionado pelo GitHub para vaglio.com.br/... sem o
/BR-Options: por isso os dados também ficam na raiz e o 404 manda o resto para /app/.
Uso: python3 build_site.py [--saida PASTA]
"""
import argparse, os, shutil

ap = argparse.ArgumentParser()
ap.add_argument("--saida", default="site")
a = ap.parse_args()

assert os.path.isfile(os.path.join("pwa", "index.html")), "gere o app antes: python3 build.py && python3 build_pwa.py"
if os.path.isdir(a.saida):
    shutil.rmtree(a.saida)
shutil.copytree("pwa", os.path.join(a.saida, "app"))
shutil.copy(os.path.join("pwa", "snapshot.json"), a.saida)
shutil.copytree(os.path.join("pwa", "precos"), os.path.join(a.saida, "precos"))

# Fase 1: a raiz leva ao app, mantendo ?teste=1 e afins
RAIZ = """<!doctype html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Vaglio</title>
<meta name="robots" content="noindex">
<link rel="canonical" href="https://vaglio.com.br/app/">
<meta http-equiv="refresh" content="0; url=app/">
<script>location.replace("app/" + location.search + location.hash);</script>
<style>body{margin:0;background:#1E1E20;color:#EDEBE4;font:17px system-ui,sans-serif;display:grid;place-items:center;min-height:100vh}a{color:#F5C400}</style>
</head>
<body><p><a href="app/">Abrir o Vaglio</a></p></body>
</html>
"""
# endereço sem /app/ (ex.: /termos.html, /?teste=1 vindo do github.io): o mesmo caminho dentro de /app/
NAO_ACHOU = """<!doctype html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Vaglio</title>
<meta name="robots" content="noindex">
<script>
(function () {
  var p = location.pathname;
  if (p.indexOf("/app/") !== 0) location.replace("/app" + (p.charAt(0) === "/" ? p : "/" + p) + location.search + location.hash);
})();
</script>
<style>body{margin:0;background:#1E1E20;color:#EDEBE4;font:17px system-ui,sans-serif;display:grid;place-items:center;min-height:100vh;text-align:center}a{color:#F5C400}</style>
</head>
<body><div><p>Página não encontrada.</p><p><a href="/app/">Abrir o Vaglio</a></p></div></body>
</html>
"""
open(os.path.join(a.saida, "index.html"), "w", encoding="utf-8").write(RAIZ)
open(os.path.join(a.saida, "404.html"), "w", encoding="utf-8").write(NAO_ACHOU)
print("site em", a.saida, "· app em /app/, raiz leva ao app, dados também na raiz")
