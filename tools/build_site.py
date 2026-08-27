"""Render the four landing pages from one template so they cannot drift."""
import html
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from site_content import CONTENT, DOWNLOAD, LANGS, LANG_NAMES, REPO, RELEASES, SITE, VERSION

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOCS = os.path.join(ROOT, "docs")

CSS = """
:root{--grape:#4a4076;--grape-deep:#342c58;--grape-soft:#655a9e;--cream:#fff6e8;
--sunny:#ffc94a;--mint:#5fe0b0;--ink:#2e2650;--muted:#6b6390;--card:#ffffff}
*{box-sizing:border-box}
html{scroll-behavior:smooth}
body{margin:0;background:var(--cream);color:var(--ink);
font:16px/1.65 -apple-system,BlinkMacSystemFont,"Segoe UI",Inter,system-ui,sans-serif;
-webkit-font-smoothing:antialiased}
a{color:var(--grape);text-decoration:none}
img{max-width:100%;height:auto}
a:hover{text-decoration:underline}
.wrap{max-width:1040px;margin:0 auto;padding:0 24px}
nav{display:flex;align-items:center;justify-content:space-between;gap:16px;
padding:20px 0;flex-wrap:wrap}
.brand{display:flex;align-items:center;gap:12px;font-weight:800;font-size:20px;color:var(--cream)}
.brand img{width:40px;height:40px;border-radius:11px}
.langs{display:flex;gap:6px;flex-wrap:wrap}
.langs a,.langs span{font-size:13px;padding:6px 12px;border-radius:999px;
background:rgba(255,246,232,.14);color:var(--cream)}
.langs span{background:var(--sunny);color:var(--ink);font-weight:700}
.langs a:hover{background:rgba(255,246,232,.28);text-decoration:none}
header{background:var(--grape);background:linear-gradient(170deg,#5a4f92 0%,#4a4076 55%,#3b3363 100%);
color:var(--cream);padding-bottom:64px}
.hero{display:grid;grid-template-columns:1.05fr .95fr;gap:48px;align-items:center;padding:36px 0 0}
.hero h1{font-size:42px;line-height:1.12;margin:18px 0 14px;letter-spacing:-.5px}
.hero p{font-size:18px;color:rgba(255,246,232,.86);margin:0 0 28px;max-width:36em}
.hero-logo{width:96px;height:96px;border-radius:26px;box-shadow:0 12px 32px rgba(0,0,0,.28)}
.cta{display:flex;gap:14px;align-items:center;flex-wrap:wrap}
.btn{display:inline-block;background:var(--sunny);color:var(--ink);font-weight:800;
padding:15px 28px;border-radius:14px;font-size:17px;box-shadow:0 8px 20px rgba(0,0,0,.22)}
.btn:hover{background:#ffd77a;text-decoration:none}
.btn-ghost{color:var(--cream);border:2px solid rgba(255,246,232,.4);padding:13px 24px;
border-radius:14px;font-weight:700}
.btn-ghost:hover{background:rgba(255,246,232,.12);text-decoration:none}
.sub{font-size:14px;color:rgba(255,246,232,.7);margin-top:14px}
.hero-art img{width:100%;max-width:420px;display:block;margin:0 auto;
filter:drop-shadow(0 18px 38px rgba(0,0,0,.32))}
main{padding:64px 0 0}
section{margin-bottom:64px}
h2{font-size:28px;margin:0 0 20px;letter-spacing:-.3px}
h3{font-size:17px;margin:0 0 6px}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:20px}
.card{background:var(--card);border-radius:18px;padding:22px 24px;
box-shadow:0 2px 10px rgba(46,38,80,.07)}
.card p{margin:0;color:var(--muted);font-size:15px}
.prose{max-width:62ch;color:#4a4270}
.steps{counter-reset:s;display:grid;gap:16px}
.step{background:var(--card);border-radius:18px;padding:20px 24px 20px 66px;position:relative;
box-shadow:0 2px 10px rgba(46,38,80,.07)}
.step:before{counter-increment:s;content:counter(s);position:absolute;left:20px;top:20px;
width:32px;height:32px;border-radius:50%;background:var(--mint);color:var(--ink);
font-weight:800;display:grid;place-items:center}
table{width:100%;border-collapse:collapse;background:var(--card);border-radius:18px;
overflow:hidden;box-shadow:0 2px 10px rgba(46,38,80,.07)}
td{padding:13px 22px;border-bottom:1px solid #efeaf7}
tr:last-child td{border-bottom:none}
td:last-child{text-align:right}
kbd{background:var(--grape);color:var(--cream);border-radius:7px;padding:3px 10px;
font:600 13px ui-monospace,SFMono-Regular,Menlo,monospace}
.note{font-size:14px;color:var(--muted);margin-top:14px}
.shot{width:100%;border-radius:16px;box-shadow:0 8px 28px rgba(46,38,80,.16);display:block}
ul.plain{list-style:none;padding:0;margin:0;display:grid;gap:10px}
ul.plain li{background:var(--card);border-radius:12px;padding:12px 18px;
box-shadow:0 2px 8px rgba(46,38,80,.06);color:#4a4270}
.safe{background:var(--grape-deep);color:var(--cream);border-radius:20px;padding:32px 34px}
.safe h2{color:var(--cream)}
.safe p{color:rgba(255,246,232,.85);max-width:62ch;margin:0}
footer{background:var(--grape-deep);color:rgba(255,246,232,.7);padding:40px 0;font-size:14px}
footer a{color:var(--cream)}
.flinks{display:flex;gap:20px;flex-wrap:wrap;margin-bottom:18px}
.disclaimer{max-width:70ch;font-size:13px;line-height:1.6;opacity:.75}
@media(max-width:820px){.hero{grid-template-columns:1fr;gap:28px;text-align:left}
.hero h1{font-size:32px}main{padding-top:44px}}
"""


def dimensions(name):
    """Real pixel size, so the browser reserves the right space and the page
    does not jump while images load."""
    try:
        from PIL import Image
        with Image.open(os.path.join(DOCS, name)) as im:
            return im.size
    except Exception:
        return None, None


def esc(text):
    return html.escape(str(text), quote=True)


def page(lang):
    c = CONTENT[lang]
    up = "" if lang == "en" else "../"
    canonical = SITE if lang == "en" else f"{SITE}{lang}/"

    alts = "\n".join(
        f'  <link rel="alternate" hreflang="{code}" href="{SITE if code == "en" else SITE + code + "/"}">'
        for code in LANGS)
    alts += f'\n  <link rel="alternate" hreflang="x-default" href="{SITE}">'

    langbar = "".join(
        f'<span>{LANG_NAMES[code]}</span>' if code == lang
        else f'<a href="{SITE if code == "en" else SITE + code + "/"}" hreflang="{code}">{LANG_NAMES[code]}</a>'
        for code in LANGS)

    schema = {
        "@context": "https://schema.org",
        "@type": "SoftwareApplication",
        "name": "Multi-Tofu",
        "applicationCategory": "UtilitiesApplication",
        "applicationSubCategory": "Game utility",
        "operatingSystem": "macOS 12 or later",
        "softwareVersion": VERSION,
        "url": canonical,
        "downloadUrl": DOWNLOAD,
        "installUrl": RELEASES,
        "codeRepository": REPO,
        "license": "https://www.apache.org/licenses/LICENSE-2.0",
        "isAccessibleForFree": True,
        "inLanguage": LANGS,
        "description": c["description"],
        "image": f"{SITE}assets/og-card.png",
        "offers": {"@type": "Offer", "price": "0", "priceCurrency": "USD"},
        "author": {"@type": "Organization", "name": "MinutesBack",
                   "url": "https://github.com/MinutesBack"},
    }

    features = "\n".join(
        f'      <div class="card"><h3>{esc(t)}</h3><p>{esc(b)}</p></div>'
        for t, b in c["features"])
    steps = "\n".join(
        f'      <div class="step"><h3>{esc(t)}</h3><p style="margin:0;color:var(--muted);font-size:15px">{esc(b)}</p></div>'
        for t, b in c["steps"])
    keys = "\n".join(
        f'      <tr><td>{esc(a)}</td><td><kbd>{esc(k)}</kbd></td></tr>'
        for a, k in c["keys"])
    compat = "\n".join(f'      <li>{esc(x)}</li>' for x in c["compat"])
    wheel_w, wheel_h = dimensions("wheel.png")
    shot = "preferences-fr.png" if lang == "fr" else "preferences.png"
    shot_w, shot_h = dimensions(shot)

    return f"""<!doctype html>
<html lang="{lang}">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>{esc(c["title"])}</title>
  <meta name="description" content="{esc(c["description"])}">
  <link rel="canonical" href="{canonical}">
{alts}
  <meta property="og:type" content="website">
  <meta property="og:site_name" content="Multi-Tofu">
  <meta property="og:locale" content="{c["locale"]}">
  <meta property="og:title" content="{esc(c["title"])}">
  <meta property="og:description" content="{esc(c["description"])}">
  <meta property="og:url" content="{canonical}">
  <meta property="og:image" content="{SITE}assets/og-card.png">
  <meta name="twitter:card" content="summary_large_image">
  <meta name="twitter:title" content="{esc(c["title"])}">
  <meta name="twitter:description" content="{esc(c["description"])}">
  <meta name="twitter:image" content="{SITE}assets/og-card.png">
  <meta name="theme-color" content="#4a4076">
  <link rel="icon" type="image/png" sizes="32x32" href="{up}assets/favicon-32.png">
  <link rel="apple-touch-icon" href="{up}assets/apple-touch-icon.png">
  <script type="application/ld+json">{json.dumps(schema, ensure_ascii=False)}</script>
  <style>{CSS}</style>
</head>
<body>
<header>
  <div class="wrap">
    <nav>
      <span class="brand"><img src="{up}assets/logo-128.png" alt="{esc(c["alt_logo"])}">Multi-Tofu</span>
      <span class="langs">{langbar}</span>
    </nav>
    <div class="hero">
      <div>
        <img class="hero-logo" src="{up}assets/logo.png" alt="{esc(c["alt_logo"])}">
        <h1>{esc(c["tagline"])}</h1>
        <p>{esc(c["lede"])}</p>
        <div class="cta">
          <a class="btn" href="{DOWNLOAD}">{esc(c["download"])}</a>
          <a class="btn-ghost" href="{REPO}">{esc(c["source"])}</a>
        </div>
        <p class="sub">{esc(c["download_sub"])}</p>
      </div>
      <div class="hero-art">
        <img src="{up}wheel.png" alt="{esc(c["alt_wheel"])}" width="{wheel_w}" height="{wheel_h}">
      </div>
    </div>
  </div>
</header>

<main class="wrap">
  <section>
    <h2>{esc(c["features_title"])}</h2>
    <div class="grid">
{features}
    </div>
  </section>

  <section>
    <h2>{esc(c["names_title"])}</h2>
    <p class="prose">{esc(c["names_body"])}</p>
  </section>

  <section>
    <img class="shot" src="{up}{shot}" alt="{esc(c["alt_prefs"])}" loading="lazy" width="{shot_w}" height="{shot_h}">
  </section>

  <section>
    <h2>{esc(c["install_title"])}</h2>
    <div class="steps">
{steps}
    </div>
  </section>

  <section>
    <h2>{esc(c["keys_title"])}</h2>
    <table>
{keys}
    </table>
    <p class="note">{esc(c["keys_note"])}</p>
  </section>

  <section class="safe">
    <h2>{esc(c["safe_title"])}</h2>
    <p>{esc(c["safe_body"])}</p>
  </section>

  <section>
    <h2>{esc(c["why_title"])}</h2>
    <p class="prose">{esc(c["why_body"])}</p>
  </section>

  <section>
    <h2>{esc(c["compat_title"])}</h2>
    <ul class="plain">
{compat}
    </ul>
  </section>
</main>

<footer>
  <div class="wrap">
    <div class="flinks">
      <a href="{REPO}#readme">{esc(c["footer_docs"])}</a>
      <a href="{REPO}/issues">{esc(c["footer_issues"])}</a>
      <a href="{REPO}/blob/main/LICENSE">{esc(c["footer_licence"])}</a>
      <a href="{RELEASES}">{esc(c["download"])}</a>
    </div>
    <p class="disclaimer">{esc(c["disclaimer"])}</p>
  </div>
</footer>
</body>
</html>
"""


def main():
    written = []
    for lang in LANGS:
        target = DOCS if lang == "en" else os.path.join(DOCS, lang)
        os.makedirs(target, exist_ok=True)
        path = os.path.join(target, "index.html")
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(page(lang))
        written.append(path)

    open(os.path.join(DOCS, ".nojekyll"), "w").close()

    urls = "".join(
        f"  <url><loc>{SITE if l == 'en' else SITE + l + '/'}</loc>"
        + "".join(f'<xhtml:link rel="alternate" hreflang="{o}" '
                  f'href="{SITE if o == "en" else SITE + o + "/"}"/>' for o in LANGS)
        + f'<xhtml:link rel="alternate" hreflang="x-default" href="{SITE}"/>'
        + "</url>\n" for l in LANGS)
    with open(os.path.join(DOCS, "sitemap.xml"), "w", encoding="utf-8") as fh:
        fh.write('<?xml version="1.0" encoding="UTF-8"?>\n'
                 '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" '
                 'xmlns:xhtml="http://www.w3.org/1999/xhtml">\n' + urls + '</urlset>\n')
    with open(os.path.join(DOCS, "robots.txt"), "w", encoding="utf-8") as fh:
        fh.write(f"User-agent: *\nAllow: /\n\nSitemap: {SITE}sitemap.xml\n")

    for path in written:
        print("wrote", os.path.relpath(path, ROOT))
    print("wrote docs/sitemap.xml, docs/robots.txt, docs/.nojekyll")


if __name__ == "__main__":
    main()
