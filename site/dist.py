#!/usr/bin/env python3
"""Собирает папку dist/ с файлами сайта для публикации на Cloudflare Pages.

Запуск из корня репозитория после `python site/build.py`:  python site/dist.py [папка]
В dist попадают только файлы сайта (без README, инструкций и исходников).
"""
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from build import GOOGLE_VERIFY, INDEXNOW_KEY, LANGS, PATH, PLATS, ROOT  # noqa: E402
from pages_i18n import SLUG  # noqa: E402

out = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "dist"
if out.exists():
    shutil.rmtree(out)
out.mkdir(parents=True)

files = ["404.html", "sitemap.xml", "robots.txt", "llms.txt", f"{INDEXNOW_KEY}.txt", GOOGLE_VERIFY]
for lang in LANGS:
    files.append(f"{PATH[lang]}index.html")
    files += [f"{PATH[lang]}{SLUG[p]}/index.html" for p in PLATS]
for f in files:
    dst = out / f
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(ROOT / f, dst)

(out / "site").mkdir()
shutil.copy2(ROOT / "site/site.js", out / "site/site.js")
shutil.copytree(ROOT / "site/fonts", out / "site/fonts")
shutil.copytree(ROOT / "docs", out / "docs")
(out / "_headers").write_text(
    "/*\n  X-Content-Type-Options: nosniff\n  Referrer-Policy: strict-origin-when-cross-origin\n"
    "/docs/*\n  Cache-Control: public, max-age=604800\n/site/fonts/*\n  Cache-Control: public, max-age=31536000, immutable\n",
    encoding="utf-8", newline="\n")
print("dist готов:", out, sum(1 for _ in out.rglob("*") if _.is_file()), "файлов")
