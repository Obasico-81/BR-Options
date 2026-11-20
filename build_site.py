"""Monta o site publicado no domínio vaglio.com.br a partir de pwa/ (gerado por build.py e build_pwa.py).

  site/app/               o app (cópia de pwa/)
  site/index.html         a raiz: a página institucional (lp/index.html); quem chega com parâmetro do app
                          (?teste=1, ?assinatura=ok…) ou pelo app instalado do tempo do github.io vai para /app/
  site/bolsa-brasileira/  a página da campanha (lp/bolsa-brasileira/)
  site/instalar/          como instalar no Android, no iPhone e no computador (lp/instalar/), com o QR do endereço
  site/img, fontes        imagens e fonte das páginas (lp/)
  site/404.html           endereço antigo sem /app/ (links e app instalado do tempo do github.io) vai para /app/
  site/snapshot.json      cópia dos dados do dia na raiz, para o APK antigo, que busca em <site>/snapshot.json
  site/precos/            idem, preços diários

O endereço antigo (obasico-81.github.io/BR-Options/...) é redirecionado pelo GitHub para vaglio.com.br/... sem o
/BR-Options: por isso os dados também ficam na raiz e o 404 manda o resto para /app/.
Uso: python3 build_site.py [--saida PASTA] [--url https://vaglio.com.br/]  (precisa de segno, para o QR)
"""
import argparse, os, shutil, subprocess, sys, tempfile

ap = argparse.ArgumentParser()
ap.add_argument("--saida", default="site")
ap.add_argument("--url", default="https://vaglio.com.br/", help="endereço público do site (QR das páginas)")
a = ap.parse_args()

assert os.path.isfile(os.path.join("pwa", "index.html")), "gere o app antes: python3 build.py && python3 build_pwa.py"
if os.path.isdir(a.saida):
    shutil.rmtree(a.saida)
shutil.copytree("pwa", os.path.join(a.saida, "app"))
shutil.copy(os.path.join("pwa", "snapshot.json"), a.saida)
shutil.copytree(os.path.join("pwa", "precos"), os.path.join(a.saida, "precos"))

# a raiz: quem chega com parâmetro do app (?teste=1, ?assinatura=ok, ?aovivo=sim…) ou pelo app instalado (do tempo do
# github.io, que o GitHub redireciona para a raiz do domínio) vai para /app/. Parâmetros de campanha (utm_*, fbclid…) ficam.
ENCAMINHA = """<script>(function () {
  var k = location.search.slice(1).split("&").filter(Boolean).map(function (x) { return decodeURIComponent(x.split("=")[0]); });
  var doApp = k.some(function (x) { return !/^(utm_|fbclid$|gclid$|gbraid$|wbraid$|msclkid$|ttclid$)/.test(x); });
  var instalado = (window.matchMedia && matchMedia("(display-mode: standalone)").matches) || navigator.standalone === true;
  if (doApp || instalado) location.replace("app/" + location.search + location.hash);
})();</script>"""
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
# as páginas de divulgação (lp/), com o QR de cada endereço, na raiz do site
with tempfile.TemporaryDirectory() as tmp:
    subprocess.run([sys.executable, "build_lp.py", "--url", a.url, "--saida", os.path.join(tmp, "lp")], check=True)
    for nome in os.listdir(os.path.join(tmp, "lp")):
        assert not os.path.exists(os.path.join(a.saida, nome)), "lp/ não pode ter " + nome + " (já é do site)"
    shutil.copytree(os.path.join(tmp, "lp"), a.saida, dirs_exist_ok=True)
raiz = os.path.join(a.saida, "index.html"); t = open(raiz, encoding="utf-8").read()
assert t.count('<meta charset="utf-8">') == 1
open(raiz, "w", encoding="utf-8").write(t.replace('<meta charset="utf-8">', '<meta charset="utf-8">\n' + ENCAMINHA, 1))
open(os.path.join(a.saida, "404.html"), "w", encoding="utf-8").write(NAO_ACHOU)
print("site em", a.saida, "· institucional na raiz, campanha em /bolsa-brasileira/, /instalar/, app em /app/, dados também na raiz")
