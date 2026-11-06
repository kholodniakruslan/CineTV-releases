#!/usr/bin/env python3
"""Делает баннер README docs/banner.png (1280x640) через headless Edge/Chrome.
Запуск из корня репозитория: python site/banner.py (нужен установленный Edge или Chrome)."""
import subprocess, sys, tempfile, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from build import ICON

ROOT = Path(__file__).resolve().parent.parent
BROWSERS = [r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
            r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
            r"C:\Program Files\Google\Chrome\Application\chrome.exe"]
exe = next((b for b in BROWSERS if Path(b).exists()), None)
if not exe:
    sys.exit("Не найден Edge или Chrome")

PLATS = [("android", "Android TV"), ("windows", "Windows"), ("macos", "macOS"), ("linux", "Linux")]
chips = "".join(f'<span class="chip"><i>{ICON[k]}</i>{name}</span>' for k, name in PLATS)

HTML = """<!doctype html><meta charset=utf-8><style>
@font-face{{font-family:Inter;font-weight:100 900;src:url('{font_lat}') format('woff2');unicode-range:U+0000-00FF,U+2000-206F}}
@font-face{{font-family:Inter;font-weight:100 900;src:url('{font_cyr}') format('woff2');unicode-range:U+0400-04FF}}
*{{margin:0;box-sizing:border-box}}
body{{width:1280px;height:640px;overflow:hidden;position:relative;font-family:Inter,sans-serif;color:#fff;
background:radial-gradient(60% 90% at 88% 10%,#46279a 0%,transparent 62%),radial-gradient(50% 70% at 62% 105%,#2a1a66 0%,transparent 65%),linear-gradient(135deg,#0b0a19,#14112b 55%,#1b1240)}}
body::before{{content:"";position:absolute;inset:0;background-image:radial-gradient(rgba(255,255,255,.07) 1px,transparent 1.2px);background-size:26px 26px;
-webkit-mask-image:linear-gradient(90deg,transparent 35%,#000 100%);mask-image:linear-gradient(90deg,transparent 35%,#000 100%)}}
.l{{position:absolute;left:72px;top:0;bottom:0;width:580px;display:flex;flex-direction:column;justify-content:center}}
.logo{{display:flex;align-items:center;gap:18px;margin-bottom:34px}}
.logo img{{width:68px;height:68px;border-radius:17px;box-shadow:0 10px 30px -8px #6c54d6}}
.logo b{{font-size:44px;font-weight:800;letter-spacing:-1.5px}}
h1{{font-size:56px;line-height:1.06;letter-spacing:-2.2px;font-weight:800;margin-bottom:20px}}
h1 em{{font-style:normal;background:linear-gradient(90deg,#b9a6ff,#7b62f0 70%);-webkit-background-clip:text;background-clip:text;color:transparent}}
.sub{{font-size:21px;line-height:1.45;color:#b4b0d4;margin-bottom:34px}}
.chips{{display:flex;flex-wrap:wrap;gap:8px;margin-bottom:26px}}
.chip{{display:inline-flex;align-items:center;gap:8px;height:42px;padding:0 15px 0 11px;border-radius:999px;background:rgba(255,255,255,.07);
border:1px solid rgba(255,255,255,.14);font-size:16.5px;font-weight:700;white-space:nowrap}}
.chip i{{display:grid;place-items:center;color:#b9a6ff}}.chip svg{{width:22px;height:22px}}
.free{{display:flex;gap:22px;font-size:16.5px;color:#9a97bd}}.free span::before{{content:"";display:inline-block;width:8px;height:8px;border-radius:50%;background:#35d07f;margin-right:9px;vertical-align:1px}}
.tv{{position:absolute;left:640px;top:74px;width:560px;padding:7px;border-radius:18px;background:#2a2650;box-shadow:0 40px 90px -25px #6c54d6,0 0 0 1px rgba(255,255,255,.14);
transform:perspective(1600px) rotateY(-9deg) rotateZ(1deg);transform-origin:left center}}
.tv img{{display:block;width:100%;border-radius:12px}}
.win{{position:absolute;left:760px;top:268px;width:430px;border-radius:12px;overflow:hidden;background:#1a1836;
box-shadow:0 36px 80px -20px #000,0 0 0 1px rgba(255,255,255,.16);transform:perspective(1600px) rotateY(-9deg) rotateZ(1deg);transform-origin:left center}}
.win .bar{{height:24px;background:#201d40;display:flex;align-items:center;gap:6px;padding-left:10px}}
.win .bar i{{width:8px;height:8px;border-radius:50%;background:#ff5f57}}.win .bar i:nth-child(2){{background:#febc2e}}.win .bar i:nth-child(3){{background:#28c840}}
.win img{{display:block;width:100%;aspect-ratio:16/10;object-fit:cover}}
</style>
<div class=l><div class=logo><img src='{icon}'><b>CineTV</b></div>
<h1>Фильмы и сериалы<br><em>на большом экране</em></h1>
<p class=sub>Один каталог на телевизоре и компьютере: озвучка, субтитры и «Продолжить просмотр».</p>
<div class=chips>{chips}</div>
<div class=free><span>Бесплатно</span><span>Без рекламы</span><span>Без регистрации</span></div></div>
<div class=tv><img src='{tv}'></div>
<div class=win><div class=bar><i></i><i></i><i></i></div><img src='{win}'></div>"""

with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
    f = Path(tmp) / "banner.html"
    f.write_text(HTML.format(
        font_lat=(ROOT / "site/fonts/inter-latin.woff2").as_uri(), font_cyr=(ROOT / "site/fonts/inter-cyrillic.woff2").as_uri(),
        icon=(ROOT / "docs/icon.png").as_uri(), tv=(ROOT / "docs/01-home.jpg").as_uri(), win=(ROOT / "docs/linux-04-movie.jpg").as_uri(),
        chips=chips), encoding="utf-8")
    out = ROOT / "docs/banner.png"
    out.unlink(missing_ok=True)
    subprocess.run([exe, "--headless=new", f"--user-data-dir={tmp}/profile", "--disable-gpu", "--hide-scrollbars", "--allow-file-access-from-files",
                    "--window-size=1280,640", "--virtual-time-budget=4000", f"--screenshot={out}", f.as_uri()], check=True, capture_output=True)
    for _ in range(60):
        if out.exists() and out.stat().st_size > 0:
            break
        time.sleep(0.5)
    else:
        sys.exit(f"не удалось создать {out}")
    print("записан", out.relative_to(ROOT))
