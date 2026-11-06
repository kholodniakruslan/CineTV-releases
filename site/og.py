#!/usr/bin/env python3
"""Делает превью для соцсетей docs/og-ru.png, og-uk.png, og-en.png (1200x630) через headless Edge/Chrome.
Запуск из корня репозитория: python site/og.py (нужен установленный Edge или Chrome)."""
import subprocess, sys, tempfile, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from i18n import T

ROOT = Path(__file__).resolve().parent.parent
BROWSERS = [r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
            r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
            r"C:\Program Files\Google\Chrome\Application\chrome.exe"]
exe = next((b for b in BROWSERS if Path(b).exists()), None)
if not exe:
    sys.exit("Не найден Edge или Chrome")

HTML = """<!doctype html><meta charset=utf-8><style>
@font-face{{font-family:Inter;font-weight:100 900;src:url('{font_lat}') format('woff2');unicode-range:U+0000-00FF,U+2000-206F}}
@font-face{{font-family:Inter;font-weight:100 900;src:url('{font_cyr}') format('woff2');unicode-range:U+0400-04FF}}
*{{margin:0;box-sizing:border-box}}body{{width:1200px;height:630px;overflow:hidden;font-family:Inter,sans-serif;color:#fff;
background:radial-gradient(90% 120% at 90% 0%,#3a2380,transparent 60%),linear-gradient(135deg,#0d0b1c,#171234);display:flex;align-items:center;padding:0 70px;gap:30px}}
.l{{flex:1.05}}.logo{{display:flex;align-items:center;gap:20px;margin-bottom:34px}}.logo img{{width:92px;height:92px;border-radius:22px}}
.logo b{{font-size:76px;letter-spacing:-3px;font-weight:800}}
h1{{font-size:46px;line-height:1.12;letter-spacing:-1.5px;font-weight:700;color:#e4defc;margin-bottom:34px}}
.p{{display:flex;gap:12px;margin-bottom:30px}}.p span{{padding:11px 18px;border-radius:999px;background:#6c54d6;font-weight:700;font-size:21px;white-space:nowrap}}
.f{{font-size:23px;color:#a8a5c2}}
.r{{flex:1;position:relative}}.r .tv{{border-radius:16px;padding:7px;background:#2c2850;box-shadow:0 30px 80px -20px #6c54d6,0 0 0 1px #ffffff22}}
.r img{{width:100%;border-radius:10px;display:block}}
</style><div class=l><div class=logo><img src='{icon}'><b>CineTV</b></div><h1>{tag}</h1>
<div class=p><span>Android TV</span><span>Windows</span><span>macOS</span><span>Linux</span></div><div class=f>{foot}</div></div>
<div class=r><div class=tv><img src='{shot}'></div></div>"""

with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
    for lang, t in T.items():
        f = Path(tmp) / f"og-{lang}.html"
        f.write_text(HTML.format(
            font_lat=(ROOT / "site/fonts/inter-latin.woff2").as_uri(), font_cyr=(ROOT / "site/fonts/inter-cyrillic.woff2").as_uri(),
            icon=(ROOT / "docs/icon.png").as_uri(), shot=(ROOT / "docs/01-home.jpg").as_uri(),
            tag=t["og_tag"], foot=t["og_foot"]), encoding="utf-8")
        out = ROOT / f"docs/og-{lang}.png"
        out.unlink(missing_ok=True)
        subprocess.run([exe, "--headless=new", f"--user-data-dir={tmp}/profile-{lang}", "--disable-gpu", "--hide-scrollbars", "--allow-file-access-from-files",
                        "--window-size=1200,630", "--virtual-time-budget=4000", f"--screenshot={out}", f.as_uri()],
                       check=True, capture_output=True)
        for _ in range(60):  # браузер пишет файл уже после выхода запускающего процесса
            if out.exists() and out.stat().st_size > 0:
                break
            time.sleep(0.5)
        else:
            sys.exit(f"не удалось создать {out}")
        print("записан", out.relative_to(ROOT))
