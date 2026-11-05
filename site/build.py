#!/usr/bin/env python3
"""Собирает лендинг CineTV: index.html (ru), uk/index.html, en/index.html, sitemap.xml, robots.txt.

Запуск из корня репозитория:  python site/build.py
Ссылки на скачивание берутся из последних релизов GitHub (без токена, API открытый).
В браузере посетителя ссылки ещё раз обновляет site/site.js, так что страница не устаревает
после нового релиза и без пересборки.
"""
import datetime
import html
import json
import os
import re
import sys
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from i18n import T, SOURCES  # noqa: E402
from pages_i18n import P as PAGES, UI as PUI, SLUG  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
HERE = Path(__file__).parent
REPO = "kholodniakruslan/CineTV-releases"
SITE = "https://cinetv-app.pages.dev/"
GH = f"https://github.com/{REPO}"
LANGS = ["ru", "uk", "en"]  # ru корень, остальные в подпапках
PATH = {"ru": "", "uk": "uk/", "en": "en/"}
ROOT_REL = {"ru": "", "uk": "../", "en": "../"}

ANDROID = [f"docs/0{i}-{n}.jpg" for i, n in
           enumerate(["home", "films", "series", "movie", "series-page", "cast"], 1)]
WINDOWS = ["docs/win-01-home.jpg", "docs/win-02-films.jpg", "docs/win-03-series.jpg",
           "docs/win-04-movie.jpg", "docs/win-demo.gif"]
WIN_THUMB = WINDOWS[:4] + ["docs/win-04-movie.jpg"]

ICON = {
    "android": '<svg viewBox="0 0 24 24" width="30" height="30" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><rect x="2" y="4" width="20" height="13" rx="2"/><path d="M8 21h8M12 17v4"/></svg>',
    "windows": '<svg viewBox="0 0 24 24" width="28" height="28" fill="currentColor"><path d="M3 5.5 10.5 4.4v7.1H3zM11.5 4.3 21 3v8.5h-9.5zM3 12.5h7.5v7.1L3 18.5zM11.5 12.5H21V21l-9.5-1.3z"/></svg>',
    "macos": '<svg viewBox="0 0 24 24" width="28" height="28" fill="currentColor"><path d="M16.4 12.7c0-2.3 1.9-3.4 2-3.5-1.1-1.6-2.8-1.8-3.4-1.8-1.4-.1-2.8.9-3.5.9-.7 0-1.9-.8-3.1-.8-1.6 0-3.1.9-3.9 2.4-1.7 2.9-.4 7.2 1.2 9.6.8 1.2 1.8 2.5 3 2.4 1.2-.1 1.7-.8 3.1-.8s1.9.8 3.1.8c1.3 0 2.1-1.2 2.9-2.3.9-1.3 1.3-2.6 1.3-2.7-.1 0-2.7-1-2.7-4.2zM14.1 5.6c.6-.8 1.1-1.9.9-3-.9 0-2.1.6-2.7 1.4-.6.7-1.1 1.8-1 2.9 1.1.1 2.2-.5 2.8-1.3z"/></svg>',
    "dl": '<svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 3v12M7 10l5 5 5-5M4 21h16"/></svg>',
}

RULES = {
    "android": ("android-v", [("arm64", r"arm64-v8a.*\.apk$", "b_arm64"), ("v7a", r"armeabi-v7a.*\.apk$", "b_v7a")]),
    "windows": ("windows-v", [("setup", r"setup.*\.exe$", "b_win_setup"), ("zip", r"portable.*\.zip$", "b_win_zip")]),
    "macos": ("macos-v", [("arm", r"arm64.*\.dmg$", "b_mac_arm"), ("x64", r"x64.*\.dmg$", "b_mac_x64")]),
}
GOOGLE_VERIFY = "google1f397e7dfdda9dc3.html"  # подтверждение сайта в Google Search Console: файл должен оставаться в корне
INDEXNOW_KEY = "b7d1f3a9c24e4f6e8a0c5d7e9f1b3a52"  # ключ IndexNow: публичный по замыслу, лежит файлом в корне сайта
PLATS = ("android", "windows", "macos")
GUIDE = {"android": "android/README.md", "windows": "windows/README.md", "macos": "macos/README.md"}


def esc(s):
    return html.escape(s, quote=True)


def fetch_releases():
    """Последние релизы с GitHub. При сбое сети возвращает пустой список: ссылки тогда ведут на страницу релизов."""
    try:
        headers = {"Accept": "application/vnd.github+json", "User-Agent": "cinetv-landing-build"}
        if os.environ.get("GITHUB_TOKEN"):  # в Actions: токен поднимает лимит запросов к API
            headers["Authorization"] = "Bearer " + os.environ["GITHUB_TOKEN"]
        req = urllib.request.Request(f"https://api.github.com/repos/{REPO}/releases?per_page=40", headers=headers)
        with urllib.request.urlopen(req, timeout=20) as r:
            return json.load(r)
    except Exception as e:  # noqa: BLE001
        print("предупреждение: релизы не получены:", e, file=sys.stderr)
        return []


def latest(releases):
    out = {}
    for plat, (prefix, files) in RULES.items():
        rel = next((r for r in releases if not r["draft"] and not r["prerelease"] and r["tag_name"].startswith(prefix)), None)
        if not rel:
            out[plat] = {"version": "", "links": {}}
            continue
        links = {}
        for key, pattern, _ in files:
            a = next((a for a in rel["assets"] if re.search(pattern, a["name"], re.I)), None)
            if a:
                links[key] = a["browser_download_url"]
        out[plat] = {"version": rel["tag_name"][len(prefix):], "links": links}
    return out


def platform_row(p, t, rel, with_guide):
    prefix, files = RULES[p]
    info = rel[p]
    btns = ""
    for key, _, label in files:
        href = info["links"].get(key, f"{GH}/releases?q={p}&expanded=true")
        btns += f'<a class="dl" data-dl="{p}-{key}" href="{esc(href)}" rel="noopener"><span>{esc(t[label])}</span>{ICON["dl"]}</a>'
    ver = info["version"] or t["dl_loading"]
    guide = f'<a href="{SLUG[p]}/">{esc(t["dl_guide"])}</a>' if with_guide else ""
    ver_html = f'<span class="ver">{esc(t["dl_version"])} <span data-ver="{p}">{esc(ver)}</span></span>' if with_guide else ""
    return (
        f'<article class="drow reveal" id="plat-{p}" data-plat="{p}">'
        f'<div class="dwho"><span class="pi">{ICON[p]}</span><div><h3>{esc(t["os_" + p])}<em class="mine">{esc(t["rec"])}</em></h3>'
        f'<p class="req">{esc(t["p_" + p + "_req"])}</p>{ver_html}</div></div>'
        f'<div class="dls">{btns}</div>'
        f'<div class="more">{guide}<a href="{GH}/releases?q={p}&expanded=true" rel="noopener">{esc(t["dl_all"])}</a></div></article>'
    )


def wrap_words(text, start=0):
    out = []
    for n, w in enumerate(text.split(), start):
        out.append(f'<span class="w" style="--i:{n}">{esc(w)}</span>')
    return " ".join(out)


def lang_switch(lang, root, tail):
    return "".join(
        f'<a href="{(root + PATH[l] + tail) or "./"}" hreflang="{l}" lang="{l}"' + (' aria-current="page"' if l == lang else '') + f'>{l.upper()}</a>'
        for l in LANGS
    )


def line_icon(body):
    return ('<svg viewBox="0 0 24 24" width="26" height="26" fill="none" stroke="currentColor" stroke-width="1.7" '
            'stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">' + body + '</svg>')


FEATURE_ICONS = [
    line_icon('<rect x="3" y="3" width="7" height="7" rx="1.5"/><rect x="14" y="3" width="7" height="7" rx="1.5"/><rect x="3" y="14" width="7" height="7" rx="1.5"/><rect x="14" y="14" width="7" height="7" rx="1.5"/>'),
    line_icon('<circle cx="11" cy="11" r="7"/><path d="m20 20-3.5-3.5"/>'),
    line_icon('<path d="M21 12a9 9 0 0 1-15.5 6.2M3 12a9 9 0 0 1 15.5-6.2"/><path d="M18.5 2v4h-4M5.5 22v-4h4"/>'),
    line_icon('<path d="M3 14v-2a9 9 0 0 1 18 0v2"/><rect x="3" y="14" width="4" height="7" rx="1.5"/><rect x="17" y="14" width="4" height="7" rx="1.5"/>'),
    line_icon('<circle cx="12" cy="12" r="9"/><path d="m10 8.5 5.5 3.5-5.5 3.5z"/>'),
    line_icon('<rect x="8" y="2" width="8" height="20" rx="4"/><circle cx="12" cy="8" r="1.5"/><path d="M12 13v.01M12 17v.01"/>'),
    line_icon('<rect x="4" y="11" width="16" height="10" rx="2.5"/><path d="M8 11V8a4 4 0 0 1 8 0v3"/>'),
    line_icon('<circle cx="12" cy="12" r="9"/><path d="M3 12h18M12 3a14 14 0 0 1 0 18M12 3a14 14 0 0 0 0 18"/>'),
    line_icon('<path d="M12 3v12m0 0-4-4m4 4 4-4M4 19h16"/>'),
]


def render(lang, rel, css):
    t = T[lang]
    root = ROOT_REL[lang]
    url = SITE + PATH[lang]

    hreflang = "\n".join(
        f'<link rel="alternate" hreflang="{l}" href="{SITE + PATH[l]}">' for l in LANGS
    ) + f'\n<link rel="alternate" hreflang="x-default" href="{SITE}">'
    og_alt = "\n".join(f'<meta property="og:locale:alternate" content="{T[l]["locale"]}">' for l in LANGS if l != lang)

    lang_links = "".join(
        f'<a href="{(root + PATH[l]) or "./"}" hreflang="{l}" lang="{l}"' + (' aria-current="page"' if l == lang else '') + f'>{l.upper()}</a>'
        for l in LANGS
    )

    src_html = "".join(f"<span>{esc(s)}</span>" for s in SOURCES)
    src_list = "".join(f"<li>{esc(s)}</li>" for s in SOURCES)

    feats = "".join(
        f'<article class="fcell reveal"><span class="fic">{FEATURE_ICONS[i]}</span><h3>{esc(h)}</h3><p>{esc(p)}</p></article>'
        for i, (_, h, p) in enumerate(t["features"])
    )

    a_shots = [{"src": root + f, "title": ti, "text": tx} for f, (ti, tx) in zip(ANDROID, t["shots_android"])]
    w_shots = [{"src": root + f, "title": ti, "text": tx} for f, (ti, tx) in zip(WINDOWS, t["shots_windows"])]
    m_shots = [dict(s) for s in w_shots[:4]]  # на macOS приложение выглядит так же, как на Windows
    thumbs = ""
    for name, files, shots in (("android", ANDROID, a_shots), ("windows", WIN_THUMB, w_shots), ("macos", WINDOWS[:4], m_shots)):
        for i, (f, s) in enumerate(zip(files, shots)):
            thumbs += (f'<button class="thumb" data-set="{name}" data-i="{i}" aria-label="{esc(s["title"])}">'
                       f'<img src="{root}{f}" width="224" height="126" loading="lazy" alt="{esc(s["title"] + ": " + s["text"])}"></button>')

    hero_buttons = ""
    for p in ("android", "windows", "macos"):
        v = rel[p]["version"] or t["dl_loading"]
        hero_buttons += (f'<a class="dlb" data-os="{p}" href="#plat-{p}"><span class="dic">{ICON[p]}</span>'
                         f'<span class="dtx"><b>{esc(t["os_" + p])}</b><small>v<span data-ver="{p}">{esc(v)}</span></small></span></a>')

    plats = "".join(platform_row(p, t, rel, True) for p in PLATS)
    foot_pages = "".join(f'<a href="{SLUG[p]}/">{esc(t["g_" + p][0])}</a>' for p in PLATS)

    guides = ""
    for p in ("android", "windows", "macos"):
        gt, gx = t["g_" + p]
        guides += (f'<article class="guide reveal"><span class="pi" aria-hidden="true">{ICON[p]}</span><h3>{esc(gt)}</h3>'
                   f'<p>{esc(gx)}</p><a href="{SLUG[p]}/">{esc(t["dl_guide"])} →</a></article>')

    words = {"n": 0}

    def wrap_words(text):
        out = []
        for w in text.split():
            out.append(f'<span class="w" style="--i:{words["n"]}">{esc(w)}</span>')
            words["n"] += 1
        return " ".join(out)
    h1_html = wrap_words(t["h1_a"]) + " <em>" + wrap_words(t["h1_b"]) + "</em>"

    steps = "".join(f'<li class="reveal"><h3>{esc(h)}</h3><p>{esc(p)}</p></li>' for h, p in t["steps"])
    faq = "".join(f'<details class="reveal"><summary>{esc(q)}</summary><p>{esc(a)}</p></details>' for q, a in t["faq"])

    slide_files = ["docs/01-home.jpg", "docs/04-movie.jpg", "docs/03-series.jpg"]
    hero_slides = "".join(
        f'<img src="{root}{f}" width="1920" height="1080" alt="{esc(t["alt_banner"]) if i == 0 else ""}"'
        + (' class="on" fetchpriority="high"' if i == 0 else ' loading="lazy"') + '>'
        for i, f in enumerate(slide_files)
    )
    fonts = ["inter-latin"] + (["inter-cyrillic"] if lang != "en" else [])
    font_preload = "\n".join(
        f'<link rel="preload" href="{root}site/fonts/{f}.woff2" as="font" type="font/woff2" crossorigin>' for f in fonts)

    ld = {
        "@context": "https://schema.org",
        "@graph": [
            {
                "@type": "SoftwareApplication",
                "@id": SITE + "#app",
                "name": "CineTV",
                "applicationCategory": t["ld_cat"],
                "operatingSystem": "Android TV, Windows, macOS",
                "description": t["desc"],
                "url": url,
                "image": SITE + f"docs/og-{lang}.png",
                "screenshot": [SITE + f for f in ANDROID[:3]],
                "inLanguage": ["ru", "uk", "en"],
                "isAccessibleForFree": True,
                "offers": {"@type": "Offer", "price": "0", "priceCurrency": "USD"},
                "downloadUrl": GH + "/releases",
                "softwareVersion": rel["android"]["version"] or None,
                "author": {"@type": "Person", "name": "kholodniakruslan", "url": "https://github.com/kholodniakruslan"},
            },
            {"@type": "WebSite", "@id": SITE + "#site", "name": "CineTV", "url": url, "inLanguage": lang},
            {
                "@type": "FAQPage",
                "mainEntity": [
                    {"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": a}}
                    for q, a in t["faq"]
                ],
            },
        ],
    }
    ld["@graph"][0] = {k: v for k, v in ld["@graph"][0].items() if v is not None}

    js_data = {"repo": REPO, "shots": {"android": a_shots, "windows": w_shots, "macos": m_shots}}

    first = a_shots[0]
    values = {
        "lang": lang, "root": root, "url": url, "site": SITE, "css": css.replace("__ROOT__", root),
        "hreflang": hreflang, "og_alt_locales": og_alt, "lang_links": lang_links,
        "jsonld": json.dumps(ld, ensure_ascii=False),
        "h1_html": h1_html, "foot_pages": foot_pages, "hero_buttons": hero_buttons, "hero_slides": hero_slides, "guides_html": guides, "font_preload": font_preload,
        "sources_html": src_html, "sources_list": src_list, "features_html": feats,
        "thumbs_html": thumbs, "platforms_html": plats, "steps_html": steps, "faq_html": faq,
        "first_alt": esc(first["title"] + ": " + first["text"]), "first_title": esc(first["title"]),
        "first_text": esc(first["text"]), "year": datetime.date.today().year,
        "js_data": json.dumps(js_data, ensure_ascii=False).replace("</", "<\\/"),
    }
    for k, v in t.items():
        if isinstance(v, str):
            values.setdefault(k, esc(v))

    page = (HERE / "template.html").read_text(encoding="utf-8")

    def sub(m):
        k = m.group(1)
        if k not in values:
            raise KeyError(f"нет значения для {{{{{k}}}}}")
        return str(values[k])
    return re.sub(r"\{\{(\w+)\}\}", sub, page)


def render_page(lang, plat, rel, css):
    t = T[lang]
    ui = PUI[lang]
    pp = PAGES[lang][plat]
    root = "../" if lang == "ru" else "../../"
    slug = SLUG[plat]
    url = SITE + PATH[lang] + slug + "/"
    home_url = SITE + PATH[lang]

    hreflang = "\n".join(
        f'<link rel="alternate" hreflang="{l}" href="{SITE + PATH[l] + slug + "/"}">' for l in LANGS
    ) + f'\n<link rel="alternate" hreflang="x-default" href="{SITE + slug + "/"}">'
    og_alt = "\n".join(f'<meta property="og:locale:alternate" content="{T[l]["locale"]}">' for l in LANGS if l != lang)

    words = pp["h1"].split()
    h1_html = wrap_words(" ".join(words[:-1])) + " <em>" + wrap_words(words[-1], len(words) - 1) + "</em>"

    shot = {"android": "docs/01-home.jpg", "windows": "docs/win-01-home.jpg", "macos": "docs/win-04-movie.jpg"}[plat]
    shot_alt = f'{pp["h1"]}: {ui["shot_alt"]}'
    req_html = "".join(f"<li>{esc(x)}</li>" for x in pp["req"])
    steps_html = "".join(f'<li class="reveal"><h3>{esc(h)}</h3><p>{esc(x)}</p></li>' for h, x in pp["steps"])
    faq_html = "".join(f'<details class="reveal"><summary>{esc(q)}</summary><p>{esc(a)}</p></details>' for q, a in pp["faq"])

    others = ""
    for p in PLATS:
        if p == plat:
            continue
        gt, gx = t["g_" + p]
        others += (f'<article class="guide reveal"><span class="pi" aria-hidden="true">{ICON[p]}</span><h3>{esc(gt)}</h3>'
                   f'<p>{esc(gx)}</p><a href="../{SLUG[p]}/">{esc(ui["more"])} →</a></article>')
    foot_pages = "".join(f'<a href="../{SLUG[p]}/">{esc(t["g_" + p][0])}</a>' for p in PLATS)

    fonts = ["inter-latin"] + (["inter-cyrillic"] if lang != "en" else [])
    font_preload = "\n".join(
        f'<link rel="preload" href="{root}site/fonts/{f}.woff2" as="font" type="font/woff2" crossorigin>' for f in fonts)

    os_name = {"android": "Android TV", "windows": "Windows", "macos": "macOS"}[plat]
    ld = {
        "@context": "https://schema.org",
        "@graph": [
            {k: v for k, v in {
                "@type": "SoftwareApplication",
                "name": "CineTV",
                "applicationCategory": t["ld_cat"],
                "operatingSystem": os_name,
                "description": pp["desc"],
                "url": url,
                "image": SITE + f"docs/og-{lang}.png",
                "inLanguage": ["ru", "uk", "en"],
                "isAccessibleForFree": True,
                "offers": {"@type": "Offer", "price": "0", "priceCurrency": "USD"},
                "downloadUrl": GH + f"/releases?q={plat}",
                "softwareVersion": rel[plat]["version"] or None,
            }.items() if v is not None},
            {
                "@type": "BreadcrumbList",
                "itemListElement": [
                    {"@type": "ListItem", "position": 1, "name": ui["home"], "item": home_url},
                    {"@type": "ListItem", "position": 2, "name": pp["h1"], "item": url},
                ],
            },
            {
                "@type": "FAQPage",
                "mainEntity": [
                    {"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": a}}
                    for q, a in pp["faq"]
                ],
            },
        ],
    }

    values = {
        "lang": lang, "root": root, "url": url, "site": SITE, "css": css.replace("__ROOT__", root),
        "home": "../", "hreflang": hreflang, "og_alt_locales": og_alt,
        "lang_links": lang_switch(lang, root, slug + "/"),
        "jsonld": json.dumps(ld, ensure_ascii=False),
        "ptitle": esc(pp["title"]), "pdesc": esc(pp["desc"]), "ph1": esc(pp["h1"]), "plead": esc(pp["lead"]),
        "h1_html": h1_html, "plat": plat, "pver": esc(rel[plat]["version"] or t["dl_loading"]),
        "pshot": shot, "pshot_alt": esc(shot_alt),
        "platform_row": platform_row(plat, t, rel, False),
        "req_html": req_html, "steps_html": steps_html, "faq_html": faq_html, "other_html": others,
        "foot_pages": foot_pages, "font_preload": font_preload, "year": datetime.date.today().year,
        "js_data": json.dumps({"repo": REPO, "shots": {}}),
    }
    for k, v in ui.items():
        values["ui_" + k] = esc(v)
    for k, v in t.items():
        if isinstance(v, str):
            values.setdefault(k, esc(v))

    page = (HERE / "page.html").read_text(encoding="utf-8")

    def sub(m):
        k = m.group(1)
        if k not in values:
            raise KeyError(f"нет значения для {{{{{k}}}}}")
        return str(values[k])
    return re.sub(r"\{\{(\w+)\}\}", sub, page)


def render_404(css):
    links = "".join(
        f'<a class="btn primary" style="margin:6px" href="{SITE + PATH[l]}">{esc(PUI[l]["nf_title"] if False else T[l]["lang_name"])}</a>' for l in LANGS)
    ui = PUI["ru"]
    return f"""<!doctype html>
<html lang="ru"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>404: CineTV</title><meta name="robots" content="noindex"><meta name="color-scheme" content="dark">
<link rel="icon" type="image/png" href="{SITE}docs/icon.png"><style>{css.replace("__ROOT__", SITE)}</style></head>
<body><div class="bg" aria-hidden="true"><div class="aurora"><i class="blob b1"></i><i class="blob b2"></i></div></div>
<main class="wrap" style="min-height:100vh;display:flex;flex-direction:column;align-items:center;justify-content:center;text-align:center">
<p class="eyebrow">404</p><h1 style="font-size:clamp(34px,6vw,64px);margin:0 0 14px">{esc(PUI["ru"]["nf_title"])} / {esc(PUI["en"]["nf_title"])}</h1>
<p class="lead" style="margin:0 0 28px">{esc(PUI["ru"]["nf_text"])} / {esc(PUI["en"]["nf_text"])}</p>
<div>{links}</div></main></body></html>
"""


def main():
    css = (HERE / "style.css").read_text(encoding="utf-8")
    css = re.sub(r"/\*.*?\*/", "", css, flags=re.S)
    css = re.sub(r"\s*\n\s*", "\n", css).strip()
    rel = latest(fetch_releases())
    print("версии:", {p: rel[p]["version"] or "?" for p in rel})
    for lang in LANGS:
        out = ROOT / PATH[lang] / "index.html"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(render(lang, rel, css), encoding="utf-8", newline="\n")
        print("записан", out.relative_to(ROOT))

    for lang in LANGS:
        for plat in PLATS:
            out = ROOT / PATH[lang] / SLUG[plat] / "index.html"
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(render_page(lang, plat, rel, css), encoding="utf-8", newline="\n")
            print("записан", out.relative_to(ROOT))
    (ROOT / "404.html").write_text(render_404(css), encoding="utf-8", newline="\n")

    today = datetime.date.today().isoformat()

    def group(tail):
        alts = "".join(f'    <xhtml:link rel="alternate" hreflang="{l}" href="{SITE + PATH[l] + tail}"/>\n' for l in LANGS)
        alts += f'    <xhtml:link rel="alternate" hreflang="x-default" href="{SITE + tail}"/>\n'
        return "".join(f"  <url>\n    <loc>{SITE + PATH[l] + tail}</loc>\n    <lastmod>{today}</lastmod>\n{alts}  </url>\n" for l in LANGS)

    urls = group("") + "".join(group(SLUG[p] + "/") for p in PLATS)
    (ROOT / "sitemap.xml").write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" xmlns:xhtml="http://www.w3.org/1999/xhtml">\n'
        + urls + "</urlset>\n", encoding="utf-8", newline="\n")
    (ROOT / "robots.txt").write_text(f"User-agent: *\nAllow: /\n\nSitemap: {SITE}sitemap.xml\n", encoding="utf-8", newline="\n")
    (ROOT / ".nojekyll").write_text("", encoding="utf-8")
    (ROOT / GOOGLE_VERIFY).write_text(f"google-site-verification: {GOOGLE_VERIFY}", encoding="utf-8", newline=chr(10))
    (ROOT / f"{INDEXNOW_KEY}.txt").write_text(INDEXNOW_KEY, encoding="utf-8", newline="\n")
    llms = ["# CineTV", "", "> " + T["en"]["desc"], "", "## Pages", "",
            f"- [Home (English)]({SITE}en/)", f"- [Главная (русский)]({SITE})", f"- [Головна (українська)]({SITE}uk/)"]
    for p in PLATS:
        llms.append(f"- [{PAGES['en'][p]['h1']}]({SITE}en/{SLUG[p]}/): {PAGES['en'][p]['desc']}")
    llms += ["", "## Downloads", "", f"- [All releases]({GH}/releases)"]
    (ROOT / "llms.txt").write_text("\n".join(llms) + "\n", encoding="utf-8", newline="\n")


if __name__ == "__main__":
    main()
