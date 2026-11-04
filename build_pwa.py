"""Gera app/pwa/index.html (documento completo para instalar no celular) a partir de index.html."""
t = open("index.html", encoding="utf-8").read()
cab = '''<!doctype html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<meta name="theme-color" content="#1E1E20">
<meta name="mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-title" content="Opções">
<meta name="apple-mobile-web-app-status-bar-style" content="black">
<link rel="manifest" href="manifest.webmanifest">
<link rel="icon" href="icon-192.png">
<link rel="apple-touch-icon" href="apple-touch-icon.png">
'''
assert t.lstrip().startswith("<title>")
t = cab + t.replace('<main class="app"', '</head>\n<body>\n<main class="app"', 1)
t = t.rstrip() + '\n<script>if("serviceWorker" in navigator && location.protocol.startsWith("http")){ navigator.serviceWorker.register("sw.js").catch(function(){}); }</script>\n</body>\n</html>\n'
open("pwa/index.html", "w", encoding="utf-8").write(t); print(len(t)//1024, "KB")
# cópia publicada do snapshot: o app nativo baixa daqui os dados do dia (o código vai dentro do app)
import json; from build import snapshot_publicado, textos, fonte_css
json.dump(snapshot_publicado(), open("pwa/snapshot.json", "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
# termos de uso e política de privacidade como páginas do site (as lojas pedem os endereços)
PAGINA = """<!doctype html>
<html lang="pt-BR"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>%s · Montador de Opções</title>
<style>%s
:root{--bg:#1E1E20;--surface:#28282B;--ink:#EDEBE4;--muted:#A9A7A0;--line:#3C3C40;--accent:#F5C400;color-scheme:dark}
body{margin:0;background:var(--bg);color:var(--ink);font-family:'Figtree',system-ui,-apple-system,'Segoe UI',sans-serif;font-size:16px;line-height:1.55}
main{max-width:680px;margin:0 auto;padding:24px 16px 48px}h1{font-size:28px;margin:8px 0}h2{font-size:18px;margin:24px 0 6px}
.muted{color:var(--muted)}a{color:var(--accent)}ul{padding-left:20px}</style></head>
<body><main>%s</main></body></html>
"""
for k, titulo in (("termos", "Termos de uso"), ("privacidade", "Política de privacidade")):
    open(f"pwa/{k}.html", "w", encoding="utf-8").write(PAGINA % (titulo, fonte_css(), textos()[k]))
