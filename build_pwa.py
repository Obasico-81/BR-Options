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
import shutil; shutil.copyfile("snapshot.json", "pwa/snapshot.json")
