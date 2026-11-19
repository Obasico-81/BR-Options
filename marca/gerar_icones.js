// Gera os ícones e as telas de abertura do app (site, Android e iPhone) a partir do símbolo do Vaglio (marca/).
// Uso: node marca/gerar_icones.js   (precisa do Playwright; sobrescreve os PNGs nos caminhos abaixo, nos mesmos tamanhos)
const path = require("path"), fs = require("fs");
const RAIZ = path.join(__dirname, "..");
const FUNDO = "#111110", ABERTURA = "#1E1E20";   // ícone: cor da marca; abertura: a cor de fundo do app (sem piscar)
// símbolo em branco (o traço de cima mais apagado); em tamanho pequeno, o desenho do favicon (traço e barra mais grossos)
const SIMB = (p) => `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 120 120"><defs><clipPath id="c"><rect x="0" y="54" width="120" height="66"/></clipPath></defs>
  <path d="M24 22 L60 98 L96 22" fill="none" stroke="#fff" stroke-width="17" stroke-linecap="round" stroke-linejoin="round" opacity=".38"/>
  <g clip-path="url(#c)"><path d="M24 22 L60 98 L96 22" fill="none" stroke="#fff" stroke-width="17" stroke-linecap="round" stroke-linejoin="round"/></g>
  <rect x="6" y="50" width="108" height="4" rx="2" fill="#fff"/></svg>`;
const PEQ = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 120 120"><defs><clipPath id="c"><rect x="0" y="52" width="120" height="68"/></clipPath></defs>
  <g clip-path="url(#c)"><path d="M22 20 L60 100 L98 20" fill="none" stroke="#fff" stroke-width="21" stroke-linecap="round" stroke-linejoin="round"/></g>
  <rect x="8" y="44" width="104" height="8" rx="4" fill="#fff"/></svg>`;
// [arquivo, largura, altura, fração do lado menor ocupada pelo símbolo, fundo, forma]
const A = "nativo/android/app/src/main/res/", ALVOS = [
  ["pwa/icon-192.png", 192, 192, .64, FUNDO], ["pwa/icon-512.png", 512, 512, .64, FUNDO],
  ["pwa/icon-maskable-512.png", 512, 512, .50, FUNDO], ["pwa/apple-touch-icon.png", 180, 180, .64, FUNDO],
  ["nativo/ios/App/App/Assets.xcassets/AppIcon.appiconset/AppIcon-512@2x.png", 1024, 1024, .60, FUNDO],
  ...[["mdpi", 48, 108], ["hdpi", 72, 162], ["xhdpi", 96, 216], ["xxhdpi", 144, 324], ["xxxhdpi", 192, 432]].flatMap(([d, l, f]) => [
    [`${A}mipmap-${d}/ic_launcher.png`, l, l, .62, FUNDO, "quadrado"], [`${A}mipmap-${d}/ic_launcher_round.png`, l, l, .58, FUNDO, "redondo"],
    [`${A}mipmap-${d}/ic_launcher_foreground.png`, f, f, .40, "transparent"]]),   // ícone adaptável: área segura de 66 dp em 108 dp
  ...["drawable/", "drawable-land-hdpi/", "drawable-land-mdpi/", "drawable-land-xhdpi/", "drawable-land-xxhdpi/", "drawable-land-xxxhdpi/",
      "drawable-port-hdpi/", "drawable-port-mdpi/", "drawable-port-xhdpi/", "drawable-port-xxhdpi/", "drawable-port-xxxhdpi/"].map((d) => [`${A}${d}splash.png`, null, null, .22, ABERTURA]),
  ...["", "-1", "-2"].map((s) => [`nativo/ios/App/App/Assets.xcassets/Splash.imageset/splash-2732x2732${s}.png`, 2732, 2732, .16, ABERTURA]),
];
const tamanho = (f) => { const b = fs.readFileSync(f); return [b.readUInt32BE(16), b.readUInt32BE(20)]; };
(async () => {
  const { chromium } = require("playwright"); const b = await chromium.launch();
  for (let [arq, w, h, fr, fundo, forma] of ALVOS) {
    const f = path.join(RAIZ, arq); if (!w) [w, h] = tamanho(f);
    const lado = Math.round(Math.min(w, h) * fr), svg = lado < 40 ? PEQ : SIMB();
    const p = await b.newPage({ viewport: { width: w, height: h } });
    const raio = forma === "redondo" ? "50%" : forma === "quadrado" ? "22%" : "0";
    await p.setContent(`<html><body style="margin:0;width:${w}px;height:${h}px;background:transparent"><div style="width:${w}px;height:${h}px;background:${fundo};border-radius:${raio};display:flex;align-items:center;justify-content:center"><img style="width:${lado}px;height:${lado}px" src="data:image/svg+xml;base64,${Buffer.from(svg).toString("base64")}"></div></body></html>`);
    await p.waitForTimeout(50);
    await p.screenshot({ path: f, omitBackground: fundo === "transparent" || !!forma }); await p.close();
    console.log(`${w}x${h}`, arq);
  }
  await b.close();
})();
