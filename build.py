"""Gera app/index.html embutindo montador.js e snapshot.json."""
t = open("template.html").read()
t = t.replace("/*MONTADOR*/", open("montador.js").read()).replace("/*SNAPSHOT*/", open("snapshot.json").read())
open("index.html", "w").write(t); print(len(t)//1024, "KB")
