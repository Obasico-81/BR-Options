"""Gera nativo/www/index.html (o que vai dentro do app de Android e iPhone, via Capacitor) a partir de index.html.

O código vai inteiro no app; os dados do dia vêm do site publicado (BASE). Ao abrir, o carregador baixa
BASE/snapshot.json (até 5 s), guarda a cópia no aparelho (IndexedDB) para abrir sem internet e só então roda a
interface; sem internet, vale a última cópia guardada; sem cópia, o snapshot embutido no build. O template escolhe
a mais nova entre a baixada e a embutida (window.SNAP_REMOTO), e os preços diários vêm de BASE/precos/.
Uso: python3 build.py && python3 build_nativo.py [--base URL] [--saida PASTA]
"""
import argparse, json, os

BASE_PADRAO = "https://obasico-81.github.io/BR-Options/"

ap = argparse.ArgumentParser()
ap.add_argument("--base", default=BASE_PADRAO, help="endereço do site publicado, terminado em /")
ap.add_argument("--saida", default=os.path.join("nativo", "www"))
a = ap.parse_args()
assert a.base.endswith("/"), "--base precisa terminar em /"

t = open("index.html", encoding="utf-8").read()
assert t.lstrip().startswith("<title>") and t.count("<script>") == 2 and t.count("</script>") == 2
# 1º script: montador (roda já); 2º: a interface, que só roda depois que o carregador tiver os dados
i = t.rindex("<script>"); f = t.rindex("</script>")
interface = t[i + len("<script>"):f]

CARREGADOR = """<script>
(function () {
  var BASE = window.BASE_DADOS = %s, feito = false;
  function iniciar(snap) {
    if (feito) return; feito = true;
    if (snap) window.SNAP_REMOTO = snap;
    var s = document.createElement("script"); s.textContent = document.getElementById("interface").textContent;
    document.body.appendChild(s);
  }
  function banco() { return new Promise(function (ok, erro) {
    var r = indexedDB.open("montador", 1);
    r.onupgradeneeded = function () { r.result.createObjectStore("dados"); };
    r.onsuccess = function () { ok(r.result); }; r.onerror = function () { erro(r.error); };
  }); }
  function guardada() { return banco().then(function (db) { return new Promise(function (ok) {
    var q = db.transaction("dados").objectStore("dados").get("snapshot");
    q.onsuccess = function () { ok(q.result || null); }; q.onerror = function () { ok(null); };
  }); }).catch(function () { return null; }); }
  function guardar(v) { return banco().then(function (db) { db.transaction("dados", "readwrite").objectStore("dados").put(v, "snapshot"); }).catch(function () {}); }
  function semRede() { guardada().then(iniciar); }
  var ctl = typeof AbortController === "function" ? new AbortController() : null;
  var prazo = setTimeout(function () { if (ctl) ctl.abort(); semRede(); }, 5000);
  fetch(BASE + "snapshot.json", { cache: "no-store", signal: ctl ? ctl.signal : undefined })
    .then(function (r) { return r.ok ? r.json() : null; })
    .then(function (s) { clearTimeout(prazo); if (s && s.data && s.ativos) { guardar(s); iniciar(s); } else semRede(); })
    .catch(function () { clearTimeout(prazo); semRede(); });
})();
</script>""" % json.dumps(a.base)

cab = """<!doctype html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<meta name="theme-color" content="#1E1E20">
"""
# topo abaixo da barra de status/entalhe (a barra de baixo já usa a área segura)
estilo = "<style>.app{padding-top:calc(16px + env(safe-area-inset-top))}</style>\n"
corpo = t[:i] + '<script type="text/x-montador" id="interface">' + interface + "</script>\n" + CARREGADOR + t[f + len("</script>"):]
assert corpo.count('<main class="app" id="app" aria-live="polite"></main>') == 1
corpo = corpo.replace('<main class="app" id="app" aria-live="polite"></main>',
                      '<main class="app" id="app" aria-live="polite"><p class="muted" style="margin-top:40vh;text-align:center">Carregando preços…</p></main>')
html = cab + corpo.replace('<main class="app"', estilo + "</head>\n<body>\n<main class=\"app\"", 1).rstrip() + "\n</body>\n</html>\n"
os.makedirs(a.saida, exist_ok=True)
open(os.path.join(a.saida, "index.html"), "w", encoding="utf-8").write(html)
print(len(html) // 1024, "KB ->", os.path.join(a.saida, "index.html"), "| dados de", a.base)
