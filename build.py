#!/usr/bin/env python3
"""
Genera el sitio trilingüe de Coyhaique River Lodge (es / en / fr).

  python3 build.py

Fuente única:
  src/template.html       estructura HTML (una sola vez)
  src/i18n/{es,en,fr}.json   textos por idioma
  src/data/site.json      datos neutros (contacto, programas, disponibilidad, video)
Salida (se puede desplegar tal cual en Vercel):
  es/index.html  en/index.html  fr/index.html
  index.html (selector de idioma / x-default), sitemap.xml, robots.txt, vercel.json

Solo usa la biblioteca estándar de Python 3.8+.
"""
import html
import json
import re
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
LANGS = ["es", "en", "fr"]
DEFAULT_LANG = "es"

# ---------------------------------------------------------------- iconos
ICONS = {
    "bed": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M3 19V6M3 15h18v4M21 15v-3a3 3 0 0 0-3-3h-7v6"/><circle cx="7" cy="11.5" r="1.7"/></svg>',
    "fish": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M2.5 12c3-4.2 7-6 10.5-6 3 0 5.6 1.5 7.5 6-1.9 4.5-4.5 6-7.5 6-3.5 0-7.5-1.8-10.5-6z"/><path d="M20.5 12l2 -3.2M20.5 12l2 3.2"/><circle cx="8.2" cy="10.8" r=".9" fill="currentColor"/></svg>',
    "utensils": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M6 3v7M9 3v7M3.5 3v4.5A3.5 3.5 0 0 0 7 11h1a3.5 3.5 0 0 0 3.5-3.5V3M7.5 11v10M18 3c-2.2 1.4-3.2 3.8-3.2 6.5 0 2 1 3.2 3.2 3.5V21"/></svg>',
    "leaf": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M5 19c0-8 5-13 15-14 0 10-5 15-13 15"/><path d="M5 19c3-5 6-8 10-10"/></svg>',
    "bolt": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M13 2 4.5 13.5H11L10 22l8.5-11.5H12z"/></svg>',
    "heart": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M12 20s-7.5-4.6-7.5-10.2A4.3 4.3 0 0 1 12 7.2a4.3 4.3 0 0 1 7.5 2.6C19.5 15.4 12 20 12 20z"/></svg>',
    "glass": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M7 3h10l-.7 6.5a4.3 4.3 0 0 1-8.6 0z"/><path d="M12 13.8V21M8.5 21h7"/></svg>',
    "person": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" aria-hidden="true"><circle cx="12" cy="8" r="4"/><path d="M4 20c0-4 3.6-7 8-7s8 3 8 7"/></svg>',
}


# ---------------------------------------------------------------- utilidades
def load(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def esc(s):
    return html.escape(str(s), quote=True)


def lookup(ctx, dotted):
    cur = ctx
    for part in dotted.split("."):
        if isinstance(cur, dict) and part in cur:
            cur = cur[part]
        else:
            raise KeyError(f"clave no encontrada: {dotted}")
    return cur


def flatten_keys(obj, prefix=""):
    """Estructura de claves para comprobar que los 3 idiomas están alineados."""
    out = set()
    if isinstance(obj, dict):
        for k, v in obj.items():
            out |= flatten_keys(v, f"{prefix}{k}.")
    elif isinstance(obj, list):
        out.add(f"{prefix}[{len(obj)}]")
        for i, v in enumerate(obj):
            out |= flatten_keys(v, f"{prefix}{i}.")
    else:
        out.add(prefix.rstrip("."))
    return out


def fmt_date(d, t):
    return t["date_single"].format(d=d.day, m=t["months"][d.month - 1], y=d.year)


def fmt_range(a, b, t):
    m = t["months"]
    if a.year == b.year and a.month == b.month:
        return t["date_same_month"].format(d1=a.day, d2=b.day, m=m[a.month - 1], y=a.year)
    if a.year == b.year:
        return t["date_same_year"].format(d1=a.day, d2=b.day, m1=m[a.month - 1], m2=m[b.month - 1], y=a.year)
    return t["date_diff_year"].format(d1=a.day, d2=b.day, m1=m[a.month - 1], m2=m[b.month - 1], y1=a.year, y2=b.year)


def fmt_price(n, lang):
    s = f"{int(n):,}"
    return {"es": s.replace(",", "."), "en": s, "fr": s.replace(",", " ")}[lang]


def nights_label(prog, tp):
    lo, hi = prog["nights_min"], prog.get("nights_max")
    if hi and hi != lo:
        return tp["nights_range"].format(min=lo, max=hi)
    if hi is None:
        return (tp["nights_from_one"] if lo == 1 else tp["nights_from_many"]).format(min=lo)
    return f"{lo}"


def image_size(path):
    try:
        from PIL import Image  # opcional
        with Image.open(path) as im:
            return im.size
    except Exception:
        return None


# ---------------------------------------------------------------- bloques
def build_blocks(lang, t, site):
    base = site["base_url"].rstrip("/")
    assets = "../assets"
    c = site["contact"]
    b = {}

    b["robots"] = (
        '<meta name="robots" content="noindex, nofollow">'
        if site.get("noindex")
        else '<meta name="robots" content="index, follow, max-image-preview:large">'
    )
    b["hreflang"] = "\n".join(
        [f'<link rel="alternate" hreflang="{l}" href="{base}/{l}/">' for l in LANGS]
        + [f'<link rel="alternate" hreflang="x-default" href="{base}/">']
    )
    other_locales = {"es": "es_CL", "en": "en_US", "fr": "fr_FR"}
    b["og_alternates"] = "\n".join(
        f'<meta property="og:locale:alternate" content="{other_locales[l]}">' for l in LANGS if l != lang
    )

    b["nav"] = "\n".join(f'<a href="{esc(i["href"])}">{i["label"]}</a>' for i in t["nav"]) + (
        f'\n<a class="only-mobile" href="#contact">{t["ui"]["contact"]}</a>'
    )
    names = {l: load(SRC / "i18n" / f"{l}.json")["lang_name"] for l in LANGS}
    switch = []
    for l in LANGS:
        cur = ' aria-current="true"' if l == lang else ""
        switch.append(
            f'<a href="../{l}/" hreflang="{l}" lang="{l}" data-lang="{l}" title="{esc(names[l])}"{cur}>{l.upper()}</a>'
        )
    b["lang_switch"] = "\n".join(switch)
    b["lang_options"] = "\n".join(
        '<option value="%s"%s>%s</option>' % (l, " selected" if l == lang else "", names[l]) for l in LANGS
    )

    b["pillars"] = "\n".join(
        f'<a class="pillar" href="{esc(p["href"])}">{ICONS[p["icon"]]}<h3>{p["title"]}</h3><p>{p["text"]}</p></a>'
        for p in t["pillars"]
    )
    b["stats"] = "\n".join(f'<div class="stat"><b>{s["value"]}</b><span>{s["label"]}</span></div>' for s in t["stats"])

    lodge_imgs = ["lodge-principal.jpg", "lodge-las-ardillas.jpg", "lodge-puerto-sanchez.jpg"]
    cards = []
    for it, img in zip(t["lodges"]["items"], lodge_imgs):
        sz = image_size(ROOT / "assets" / "img" / img)
        wh = f' width="{sz[0]}" height="{sz[1]}"' if sz else ""
        cards.append(
            f'<article class="lodge-card"><img src="{assets}/img/{img}" alt="{esc(it["img_alt"])}"{wh} loading="lazy">'
            f'<div class="body"><span class="tag">{it["tag"]}</span><h3>{it["name"]}</h3><p>{it["text"]}</p></div></article>'
        )
    b["lodges"] = "\n".join(cards)

    # programas
    tp = t["programs"]
    pcards = []
    for prog in site["programs"]:
        item = tp["items"][prog["id"]]
        price = prog.get("price_from_usd")
        price_html = (
            f'<p class="prog-price">{tp["price_from"].format(price=fmt_price(price, lang))}</p>'
            if price
            else f'<p class="prog-price tbc">{tp["price_tbc"]}</p>'
        )
        lis = "".join(f"<li>{x}</li>" for x in item["includes"])
        pcards.append(
            f'<article class="prog-card"><span class="pill pill-dur">{nights_label(prog, tp)}</span>'
            f'<h3>{item["name"]}</h3><p>{item["desc"]}</p><h4>{tp["includes"]}</h4><ul class="check-list">{lis}</ul>'
            f'<div class="prog-foot">{price_html}'
            f'<a class="btn btn-terracotta btn-sm" href="#contact" data-slot-program="{prog["id"]}">{tp["cta"]}</a></div></article>'
        )
    b["programs"] = "\n".join(pcards)
    b["program_options"] = "\n".join(
        f'<option value="{p["id"]}">{tp["items"][p["id"]]["name"]}</option>' for p in site["programs"]
    )

    # disponibilidad
    ta = t["availability"]
    av = site["availability"]
    slots = sorted(av["slots"], key=lambda s: (s["start"], s["program"]))
    rows, seen = [], []
    for s in slots:
        a, z = date.fromisoformat(s["start"]), date.fromisoformat(s["end"])
        nights = (z - a).days
        spots = int(s["spots"])
        status = s.get("status") or ("full" if spots == 0 else "few" if spots <= 2 else "available")
        pill = {"available": "pill-live", "few": "pill-few", "full": "pill-full"}[status]
        pname = tp["items"][s["program"]]["name"]
        label = f"{pname} · {fmt_range(a, z, ta)}"
        spots_txt = ta["spots_0"] if spots == 0 else ta["spots_1"] if spots == 1 else ta["spots_n"].format(n=spots)
        nights_txt = ta["nights_1"] if nights == 1 else ta["nights_n"].format(n=nights)
        cta = ta["cta_wait"] if status == "full" else ta["cta_ask"]
        if s["program"] not in seen:
            seen.append(s["program"])
        tr_cls = ' class="is-full"' if status == "full" else ""
        rows.append(
            f'<tr data-program="{s["program"]}"{tr_cls}>'
            f'<td class="prog" data-label="{esc(ta["col_program"])}">{pname}</td>'
            f'<td data-label="{esc(ta["col_dates"])}">{fmt_range(a, z, ta)}</td>'
            f'<td data-label="{esc(ta["col_nights"])}">{nights_txt}</td>'
            f'<td data-label="{esc(ta["col_spots"])}">{spots_txt}</td>'
            f'<td data-label="{esc(ta["col_status"])}"><span class="pill {pill}">{ta["status"][status]}</span></td>'
            f'<td class="act"><a class="btn btn-outline-dark btn-sm" href="#contact" data-slot-program="{s["program"]}" '
            f'data-slot-start="{s["start"]}" data-slot-end="{s["end"]}" data-slot-label="{esc(label)}">{cta}</a></td></tr>'
        )
    b["avail_rows"] = "\n".join(rows)
    filters = [f'<button class="filter-btn" type="button" data-filter="all" aria-pressed="true">{ta["all"]}</button>']
    filters += [
        f'<button class="filter-btn" type="button" data-filter="{p}" aria-pressed="false">{tp["items"][p]["name"]}</button>'
        for p in seen
    ]
    b["avail_filters"] = "\n".join(filters)
    b["sample_banner"] = f'<p class="sample-banner">{ta["sample_note"]}</p>' if av.get("sample") else ""

    # gastronomía
    b["gastro_items"] = "\n".join(
        f'<div class="gastro-item">{ICONS[i["icon"]]}<h3>{i["title"]}</h3><p>{i["text"]}</p></div>'
        for i in t["gastro"]["items"]
    )
    b["team"] = "\n".join(
        f'<div class="team-card"><div class="avatar">{ICONS["person"]}</div><h4>{m["name"]}</h4>'
        f'<span class="role">{m["role"]}</span><p>{m["bio"]}</p></div>'
        for m in t["team"]["items"]
    )
    b["testimonials"] = "\n".join(
        f'<div class="testi-card"><div class="stars" aria-hidden="true">★★★★★</div><p class="quote">“{q["quote"]}”</p>'
        f'<div class="who">{q["who"]}<span>{q["meta"]}</span></div>'
        f'<div class="placeholder-flag">{t["testimonials"]["placeholder"]}</div></div>'
        for q in t["testimonials"]["items"]
    )
    gal = []
    for n, alt in enumerate(t["gallery"]["alts"], start=1):
        f = f"gal-{n}.jpg"
        sz = image_size(ROOT / "assets" / "img" / f)
        wh = f' width="{sz[0]}" height="{sz[1]}"' if sz else ""
        gal.append(
            f'<a href="{assets}/img/{f}" target="_blank" rel="noopener" aria-label="{esc(t["gallery"]["open"])}">'
            f'<img src="{assets}/img/{f}" alt="{esc(alt)}"{wh} loading="lazy"></a>'
        )
    b["gallery"] = "\n".join(gal)

    b["footer_explore"] = "\n".join(f'<a href="{esc(l["href"])}">{l["label"]}</a>' for l in t["footer"]["explore_links"])
    social = [("Instagram", c.get("instagram")), ("Google Reviews", c.get("google_reviews")), ("TripAdvisor", c.get("tripadvisor"))]
    b["footer_social"] = "\n".join(
        f'<a href="{esc(url) if url else "#"}" target="_blank" rel="noopener">{name}</a>' for name, url in social
    )

    # JSON-LD (LodgingBusiness)
    ld = {
        "@context": "https://schema.org",
        "@type": "LodgingBusiness",
        "name": "Coyhaique River Lodge",
        "url": f"{base}/{lang}/",
        "description": t["meta"]["description"],
        "image": f"{base}/assets/img/hero-poster.jpg",
        "telephone": c["phone_tel"],
        "email": c["email"],
        "address": {
            "@type": "PostalAddress",
            "streetAddress": c["street"],
            "addressLocality": c["locality"],
            "addressRegion": c["region"],
            "addressCountry": c["country"],
        },
        "inLanguage": lang,
        "contactPoint": {
            "@type": "ContactPoint",
            "contactType": "reservations",
            "telephone": c["phone_tel"],
            "email": c["email"],
            "availableLanguage": ["es", "en", "fr"],
        },
    }
    sameas = [u for u in (c.get("instagram"), c.get("google_reviews"), c.get("tripadvisor")) if u]
    if sameas:
        ld["sameAs"] = sameas
    b["jsonld"] = '<script type="application/ld+json">' + json.dumps(ld, ensure_ascii=False).replace("</", "<\\/") + "</script>"
    return b


def build_config(lang, t, site):
    f = t["contact"]["form"]
    cfg = {
        "lang": lang,
        "formEndpoint": site.get("form_endpoint", ""),
        "email": site["contact"]["email"],
        "autoRevealMs": 3500,
        "labels": {k: f[k] for k in ("name", "email", "phone", "reply_lang", "program", "arrival", "departure", "guests", "message", "slot_selected")},
        "msg": {
            "sending": f["sending"],
            "submit": f["submit"],
            "success": f["success"],
            "error": f["error"].format(email=site["contact"]["email"]),
            "mailto": f["mailto"],
        },
    }
    return json.dumps(cfg, ensure_ascii=False).replace("</", "<\\/")


# ---------------------------------------------------------------- render
PLACEHOLDER = re.compile(r"\{\{(@?)\s*([\w.]+)\s*\}\}")
BLOCK = re.compile(r"<!--@([\w-]+)-->")


def render(tpl, ctx, blocks):
    def rep_block(m):
        name = m.group(1)
        if name not in blocks:
            raise KeyError(f"bloque desconocido: {name}")
        return blocks[name]

    def rep_var(m):
        val = lookup(ctx, m.group(2))
        return esc(val) if m.group(1) else str(val)

    out = BLOCK.sub(rep_block, tpl)
    return PLACEHOLDER.sub(rep_var, out)


def build_page(lang, tpl, site, i18n):
    t = i18n[lang]
    base = site["base_url"].rstrip("/")
    hero = site["hero"]
    pre = lambda p: ("../" + p) if p else ""
    av = site["availability"]
    ctx = {
        "lang": lang,
        "t": t,
        "site": site,
        "base": base,
        "assets": "../assets",
        "page_url": f"{base}/{lang}/",
        "hero_mp4": pre(hero.get("mp4", "")),
        "hero_webm": pre(hero.get("webm", "")),
        "hero_hls": hero.get("hls", ""),
        "avail_title": t["availability"]["title"].format(season=av["season"]),
        "avail_updated": t["availability"]["updated"].format(date=fmt_date(date.fromisoformat(av["updated"]), t["availability"])),
        "config_json": build_config(lang, t, site),
    }
    return render(tpl, ctx, build_blocks(lang, t, site))


def build_root(site):
    base = site["base_url"].rstrip("/")
    robots = "noindex, nofollow" if site.get("noindex") else "index, follow"
    names = {l: load(SRC / "i18n" / f"{l}.json")["lang_name"] for l in LANGS}
    links = "\n".join(f'    <a href="{l}/" hreflang="{l}" data-lang="{l}">{names[l]}</a>' for l in LANGS)
    alts = "\n".join(
        [f'<link rel="alternate" hreflang="{l}" href="{base}/{l}/">' for l in LANGS]
        + [f'<link rel="alternate" hreflang="x-default" href="{base}/">']
    )
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Coyhaique River Lodge — Patagonia</title>
<meta name="description" content="Coyhaique River Lodge · Español · English · Français">
<meta name="robots" content="{robots}">
<link rel="canonical" href="{base}/">
{alts}
<link rel="icon" type="image/png" href="assets/img/logo.png">
<style>
  html,body{{height:100%;margin:0;}}
  body{{display:flex;flex-direction:column;align-items:center;justify-content:center;gap:28px;background:#241610 url(assets/img/hero-poster.jpg) center/cover;
       font-family:'Manrope',system-ui,sans-serif;color:#F7F3EA;text-align:center;}}
  body::before{{content:"";position:fixed;inset:0;background:rgba(20,12,8,.62);z-index:0;}}
  body > *{{position:relative;z-index:1;}}
  img{{height:96px;width:auto;filter:brightness(0) invert(1);}}
  nav{{display:flex;gap:14px;flex-wrap:wrap;justify-content:center;}}
  a{{color:#F7F3EA;text-decoration:none;font-weight:700;letter-spacing:.06em;text-transform:uppercase;font-size:14px;
     border:1.5px solid #F7F3EA;border-radius:100px;padding:14px 28px;}}
  a:hover,a:focus-visible{{background:#7A4A2B;border-color:#7A4A2B;outline:none;}}
</style>
</head>
<body>
  <img src="assets/img/logo-hero.png" alt="Coyhaique River Lodge">
  <nav aria-label="Language">
{links}
  </nav>
<script>
  // Elige idioma: preferencia guardada > idioma del navegador > inglés
  try {{
    var saved = localStorage.getItem('crl_lang');
    var pool = saved ? [saved] : (navigator.languages || [navigator.language || '']);
    var pick = null;
    for (var i = 0; i < pool.length && !pick; i++) {{
      var l = String(pool[i]).slice(0, 2).toLowerCase();
      if (l === 'es' || l === 'en' || l === 'fr') pick = l;
    }}
    if (!/[?&]stay\\b/.test(location.search)) location.replace((pick || 'en') + '/');
  }} catch (e) {{}}
</script>
</body>
</html>
"""


def build_sitemap(site):
    base = site["base_url"].rstrip("/")
    alts = "\n".join(
        [f'    <xhtml:link rel="alternate" hreflang="{l}" href="{base}/{l}/"/>' for l in LANGS]
        + [f'    <xhtml:link rel="alternate" hreflang="x-default" href="{base}/"/>']
    )
    today = date.today().isoformat()
    urls = "\n".join(
        f"  <url>\n    <loc>{base}/{l}/</loc>\n    <lastmod>{today}</lastmod>\n{alts}\n  </url>" for l in LANGS
    )
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" xmlns:xhtml="http://www.w3.org/1999/xhtml">\n'
        f"{urls}\n</urlset>\n"
    )


# ---------------------------------------------------------------- comprobaciones
def check_parity(i18n):
    ok = True
    ref = flatten_keys(i18n[DEFAULT_LANG])
    for l in LANGS:
        if l == DEFAULT_LANG:
            continue
        keys = flatten_keys(i18n[l])
        for k in sorted(ref - keys):
            print(f"  [!] falta en {l}.json: {k}")
            ok = False
        for k in sorted(keys - ref):
            print(f"  [!] sobra en {l}.json: {k}")
            ok = False
    return ok


def check_html(lang, out):
    ok = True
    if "{{" in out or "<!--@" in out:
        print(f"  [!] {lang}: quedan marcadores sin resolver")
        ok = False
    ids = set(re.findall(r'\bid="([^"]+)"', out))
    for href in set(re.findall(r'href="#([^"]+)"', out)):
        if href and href not in ids:
            print(f"  [!] {lang}: enlace interno roto #{href}")
            ok = False
    for src in set(re.findall(r'(?:src|href)="\.\./(assets/[^"]+)"', out)):
        if not (ROOT / src).exists():
            print(f"  [!] {lang}: archivo inexistente {src}")
            ok = False
    return ok


def main():
    site = load(SRC / "data" / "site.json")
    i18n = {l: load(SRC / "i18n" / f"{l}.json") for l in LANGS}
    tpl = (SRC / "template.html").read_text(encoding="utf-8")

    ok = check_parity(i18n)
    for lang in LANGS:
        out = build_page(lang, tpl, site, i18n)
        ok = check_html(lang, out) and ok
        d = ROOT / lang
        d.mkdir(exist_ok=True)
        (d / "index.html").write_text(out, encoding="utf-8")
        print(f"  ok  {lang}/index.html  ({len(out) // 1024} KB)")

    (ROOT / "index.html").write_text(build_root(site), encoding="utf-8")
    (ROOT / "sitemap.xml").write_text(build_sitemap(site), encoding="utf-8")
    base = site["base_url"].rstrip("/")
    robots = "User-agent: *\nDisallow: /\n" if site.get("noindex") else f"User-agent: *\nAllow: /\n\nSitemap: {base}/sitemap.xml\n"
    (ROOT / "robots.txt").write_text(robots, encoding="utf-8")
    vercel = {
        "cleanUrls": True,
        "trailingSlash": True,
        "headers": [{"source": "/assets/(.*)", "headers": [{"key": "Cache-Control", "value": "public, max-age=86400"}]}],
    }
    (ROOT / "vercel.json").write_text(json.dumps(vercel, indent=2) + "\n", encoding="utf-8")
    print("  ok  index.html, sitemap.xml, robots.txt, vercel.json")
    if site.get("noindex"):
        print("  aviso: noindex=true (maqueta). Pasar a false en src/data/site.json al lanzar.")
    if not ok:
        print("Hay advertencias arriba.")
        sys.exit(1)
    print("Listo.")


if __name__ == "__main__":
    main()
