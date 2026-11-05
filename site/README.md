# Сайт CineTV

Адрес: https://cinetv-app.pages.dev/ (Cloudflare Pages, проект `cinetv-app`).

- Тексты на трёх языках: `i18n.py`, разметка: `template.html`, стили: `style.css`, скрипт: `site.js`.
- Пересборка страниц: `python site/build.py` (создаёт `index.html`, `uk/index.html`, `en/index.html`, `sitemap.xml`, `robots.txt`).
- Новые релизы подхватываются на странице сами (скрипт читает GitHub Releases), пересобирать ради них не нужно.
- Публикация: собрать, скопировать в отдельную папку `index.html`, `uk/`, `en/`, `docs/`, `site/site.js`, `sitemap.xml`, `robots.txt` и выполнить
  `npx wrangler pages deploy <папка> --project-name cinetv-app --branch main`.
