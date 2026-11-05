# Сайт CineTV

Адрес: https://cinetv-app.pages.dev/ (Cloudflare Pages, проект `cinetv-app`).

- Тексты на трёх языках: `i18n.py`, разметка: `template.html`, стили: `style.css`, скрипт: `site.js`.
- Пересборка страниц: `python site/build.py` (создаёт `index.html`, `uk/index.html`, `en/index.html`, `sitemap.xml`, `robots.txt`).
- Новые релизы подхватываются на странице сами (скрипт читает GitHub Releases), пересобирать ради них не нужно.
- Публикация: собрать, скопировать в отдельную папку `index.html`, `uk/`, `en/`, `docs/`, `site/site.js`, `site/fonts/`, `sitemap.xml`, `robots.txt` и выполнить
  `npx wrangler pages deploy <папка> --project-name cinetv-app --branch main`.
- Превью для соцсетей (`docs/og-*.png`): `python site/og.py` (нужен Edge или Chrome).
- Шрифт Inter (лицензия SIL OFL 1.1) лежит в `site/fonts/` и отдаётся с самого сайта, внешних запросов страница не делает, кроме API релизов GitHub.
- Страницы платформ (`/android-tv/`, `/windows/`, `/macos/` на трёх языках): тексты в `pages_i18n.py`, разметка в `page.html`.
- Папку для публикации собирает `python site/dist.py <папка>`; автодеплой делает это сам и после публикации сообщает поисковым системам об обновлении (IndexNow, ключ лежит файлом в корне сайта).
