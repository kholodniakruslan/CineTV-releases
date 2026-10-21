/*
 * HDRezka plugin for Lampa (prototype).
 *
 * Adds a "HDRezka" button to the movie/series card: it searches the site, lets you pick the match,
 * the voice-over, the season/episode and starts the Lampa player. The logic is a JS port of src/HDRezka.Api.
 *
 * Install: Lampa -> Settings -> Extensions -> add plugin by URL.
 * Settings (stored in Lampa.Storage): hdrezka_base (default https://hdrezka.sh),
 * hdrezka_proxy (optional CORS proxy template with {url}, e.g. https://proxy.example/?url={url}).
 *
 * The code is ES5 on purpose: it has to run on very old WebViews (Android 5.x).
 */
(function () {
    'use strict';

    var VERSION = '0.1.0';
    var DEFAULT_BASE = 'https://hdrezka.sh';
    var DEFAULT_PROXY = '';

    if (window.plugin_hdrezka_ready) return;
    window.plugin_hdrezka_ready = true;

    // ---------- settings ----------

    function store(key, def) {
        var v = Lampa.Storage.get(key, def);
        return v === undefined || v === null || v === '' ? def : v;
    }

    function baseUrl() { return String(store('hdrezka_base', DEFAULT_BASE)).replace(/\/+$/, ''); }
    function proxyTpl() { return String(store('hdrezka_proxy', DEFAULT_PROXY)); }

    // ---------- network ----------

    function SiteError(message, kind) {
        this.message = message;
        this.kind = kind || 'error';
    }

    function looksLikeChallenge(body) {
        if (body.length > 60000) return false;
        return body.indexOf('/.within.website/') >= 0
            || body.indexOf('Проверяем, что вы не бот') >= 0
            || /Making sure you're not a bot/i.test(body);
    }

    /** XHR with an optional proxy. Resolves to the response text. */
    function http(method, url, form) {
        return new Promise(function (resolve, reject) {
            var target = url;
            var proxy = proxyTpl();
            if (proxy) target = proxy.indexOf('{url}') >= 0 ? proxy.replace('{url}', encodeURIComponent(url)) : proxy + url;

            var xhr = new XMLHttpRequest();
            xhr.open(method, target, true);
            xhr.timeout = 30000;
            if (method === 'POST') {
                xhr.setRequestHeader('Content-Type', 'application/x-www-form-urlencoded; charset=UTF-8');
                xhr.setRequestHeader('X-Requested-With', 'XMLHttpRequest');
            }
            xhr.onload = function () {
                var body = xhr.responseText || '';
                if (looksLikeChallenge(body)) return reject(new SiteError('Сайт просит пройти проверку на бота', 'challenge'));
                if (xhr.status === 404) return reject(new SiteError('Страница не найдена', 'notfound'));
                if (xhr.status < 200 || xhr.status >= 300) return reject(new SiteError('HTTP ' + xhr.status, 'http'));
                resolve(body);
            };
            xhr.onerror = function () { reject(new SiteError('Ошибка сети (возможно, нужен прокси из-за CORS)', 'network')); };
            xhr.ontimeout = function () { reject(new SiteError('Таймаут запроса', 'network')); };
            xhr.send(form || null);
        });
    }

    function encodeForm(pairs) {
        return pairs.map(function (p) { return encodeURIComponent(p[0]) + '=' + encodeURIComponent(p[1]); }).join('&');
    }

    function toBase(url) {
        // the site's links may point to other mirrors: keep only the path
        if (/^\/\//.test(url)) url = 'https:' + url;
        if (/^https?:\/\//.test(url)) return baseUrl() + url.replace(/^https?:\/\/[^\/]+/, '');
        return baseUrl() + (url.charAt(0) === '/' ? '' : '/') + url;
    }

    function parseHtml(html) {
        return new DOMParser().parseFromString(html, 'text/html');
    }

    function txt(el) { return el ? (el.textContent || '').replace(/^\s+|\s+$/g, '') : ''; }

    function all(root, sel) { return Array.prototype.slice.call(root.querySelectorAll(sel)); }

    // ---------- search ----------

    function search(query) {
        var q = encodeURIComponent(query.replace(/^\s+|\s+$/g, '')).replace(/%20/g, '+');
        return http('GET', baseUrl() + '/search/?do=search&subaction=search&q=' + q).then(function (html) {
            var doc = parseHtml(html);
            return all(doc, '.b-content__inline_item').map(function (item) {
                var link = item.querySelector('.b-content__inline_item-link');
                var a = link ? link.querySelector('a') : null;
                var misc = link && link.querySelector('div') ? txt(link.querySelector('div')) : '';
                var year = (misc.match(/(\d{4})/) || [])[1] || '';
                var entity = item.querySelector('i.entity');
                return {
                    title: txt(a),
                    url: item.getAttribute('data-url') || (a ? a.getAttribute('href') : '') || '',
                    misc: misc,
                    year: year,
                    entity: entity && entity.firstChild ? txt(entity.firstChild) : ''
                };
            }).filter(function (r) { return r.url; });
        });
    }

    // ---------- movie page ----------

    /** Splits the top-level arguments of a JS call starting right after "(". */
    function splitArgs(s, start) {
        var args = [], cur = '', depth = 0, quote = '';
        for (var i = start; i < s.length; i++) {
            var c = s.charAt(i);
            if (quote) {
                cur += c;
                if (c === '\\' && i + 1 < s.length) cur += s.charAt(++i);
                else if (c === quote) quote = '';
                continue;
            }
            if (c === '"' || c === '\'') { quote = c; cur += c; }
            else if (c === '{' || c === '[' || c === '(') { depth++; cur += c; }
            else if (c === '}' || c === ']') { depth--; cur += c; }
            else if (c === ')') {
                if (depth === 0) { args.push(cur.replace(/^\s+|\s+$/g, '')); return args; }
                depth--; cur += c;
            }
            else if (c === ',' && depth === 0) { args.push(cur.replace(/^\s+|\s+$/g, '')); cur = ''; }
            else cur += c;
        }
        return args;
    }

    function toInt(s) { var n = parseInt(s, 10); return isNaN(n) ? 0 : n; }

    function parseTranslators(doc, fallbackId, camrip, ads, director) {
        var items = all(doc, '.b-translator__item[data-translator_id]');
        if (!items.length) items = all(doc, '#translators-list [data-translator_id]');
        var res = items.map(function (e) {
            var name = e.getAttribute('title') || txt(e) || 'Unknown';
            var img = e.querySelector('img');
            var flag = img ? (img.getAttribute('src') || '') : '';
            var code = flag ? flag.split('/').pop().replace(/\.[^.]*$/, '') : '';
            var prem = /b-prem_translator/.test(e.className) ||
                (e.parentNode && /b-prem_translator/.test(e.parentNode.className || ''));
            var isCam = e.getAttribute('data-camrip') === '1';
            var isAds = e.getAttribute('data-ads') === '1';
            var label = name;
            if (isCam && !/CAMRip/i.test(label)) label += ' (CAMRip)';
            if (isAds && label.indexOf('AD') < 0) label += ' (AD)';
            if (code) label += ' (' + code.toUpperCase() + ')';
            if (prem) label += ' (PREMIUM)';
            return {
                id: toInt(e.getAttribute('data-translator_id')),
                name: label,
                camrip: isCam,
                ads: isAds,
                director: e.getAttribute('data-director') === '1',
                premium: !!prem,
                active: /(^|\s)active(\s|$)/.test(e.className)
            };
        });
        if (res.length) return res;

        // a single voice-over is not rendered as a list: take its name from the info table
        var title = '';
        all(doc, 'table.b-post__info tr').forEach(function (tr) {
            var tds = tr.querySelectorAll('td');
            if (!title && tds.length >= 2 && txt(tds[0]).indexOf('В переводе') === 0) title = txt(tds[1]);
        });
        return [{ id: fallbackId, name: title || 'Оригинал', camrip: camrip, ads: ads, director: director, premium: false, active: true }];
    }

    function parseSeasons(seasonsRoot, episodesRoot) {
        var episodes = {};
        all(episodesRoot, '.b-simple_episode__item').forEach(function (e) {
            var sid = e.getAttribute('data-season_id'), eid = e.getAttribute('data-episode_id');
            if (!sid || !eid) return;
            (episodes[sid] = episodes[sid] || []).push({ id: toInt(eid), title: txt(e) });
        });
        var res = [];
        all(seasonsRoot, '.b-simple_season__item').forEach(function (s) {
            var id = s.getAttribute('data-tab_id');
            if (!id) return;
            res.push({ id: toInt(id), title: txt(s), episodes: episodes[id] || [] });
        });
        return res;
    }

    /** Builds the player state from a movie page, or throws when the page has no player. */
    function loadMovie(url) {
        return http('GET', toBase(url)).then(function (html) {
            var doc = parseHtml(html);
            var m = /sof\.tv\.(initCDN(?:Movies|Series)Events)\(/.exec(html);
            if (!m) throw new SiteError('На странице нет плеера', 'noplayer');
            var args = splitArgs(html, m.index + m[0].length);
            if (args.length < 5) throw new SiteError('Не удалось разобрать плеер', 'parse');

            var isSerial = m[1] === 'initCDNSeriesEvents';
            var movieId = toInt(args[0]), translatorId = toInt(args[1]);
            var season = 0, episode = 0, camrip = false, ads = false, director = false;
            if (isSerial) { season = toInt(args[2]); episode = toInt(args[3]); }
            else { camrip = args[2] === '1'; ads = args[3] === '1'; director = args[4] === '1'; }

            var translators = parseTranslators(doc, translatorId, camrip, ads, director);
            var current = null;
            translators.forEach(function (t) { if (!current && t.active) current = t; });
            if (!current) {
                translators.forEach(function (t) {
                    if (!current && t.id === translatorId && (isSerial || t.director === director)) current = t;
                });
            }
            var favsEl = doc.querySelector('#ctrl_favs');
            return {
                movieId: movieId,
                isSerial: isSerial,
                favs: favsEl ? (favsEl.getAttribute('value') || '') : '',
                translators: translators,
                translator: current || translators[0],
                seasons: isSerial ? parseSeasons(doc, doc) : [],
                season: season,
                episode: episode
            };
        });
    }

    // ---------- streams ----------

    var TRASH = [
        '//_//QEBAQEAhIyMhXl5e', '//_//Xl5eIUAjIyEhIyM=', '//_//JCQhIUAkJEBeIUAjJCRA',
        '//_//IyMjI14hISMjIUBA', '//_//JCQjISFAIyFAIyM='
    ];

    function decodeBase64Utf8(s) {
        var bin = atob(s);
        try { return decodeURIComponent(escape(bin)); } catch (e) { return bin; }
    }

    var QUALITY_ORDER = ['360p', '480p', '720p', '1080p', '1080p Ultra', '2K', '4K'];

    function qualityRank(q) {
        var i = QUALITY_ORDER.indexOf(q);
        return i >= 0 ? i : QUALITY_ORDER.length;
    }

    /** Parses "[360p]url or url,[480p]url..." (plain) or its old base64-with-junk form. */
    function parseStreams(raw) {
        var res = [];
        if (!raw || !/\S/.test(raw)) return res;
        var text = raw.replace(/^\s+|\s+$/g, '');

        if (text.charAt(0) !== '[') {
            try {
                var again = true;
                while (again) {
                    again = false;
                    for (var i = 0; i < TRASH.length; i++) {
                        if (text.indexOf(TRASH[i]) >= 0) { text = text.split(TRASH[i]).join(''); again = true; }
                    }
                }
                text = decodeBase64Utf8(text.split('#h').join(''));
            } catch (e) { return res; }
        }

        text.split(/,(?=\[)/).forEach(function (line) {
            var q = /^\[([\s\S]*?)\]/.exec(line);
            if (!q) return;
            var name = q[1].replace(/<[^>]+>/g, '').replace(/^\s+|\s+$/g, '');
            var premium = /prem/i.test(q[1]);
            var mp4 = [], hls = [];
            line.substring(q[0].length).split(/\sor\s/).forEach(function (part) {
                var u = part.replace(/^[\s,]+|[\s,]+$/g, '');
                if (!/^https?:\/\//.test(u)) return;
                if (/\.mp4$/i.test(u)) mp4.push(u);
                else if (/\.m3u8$/i.test(u)) hls.push(u);
            });
            if (!mp4.length && !hls.length) return;
            res.push({ quality: name, premium: premium, url: mp4[0] || hls[0] });
        });
        res.sort(function (a, b) { return qualityRank(a.quality) - qualityRank(b.quality); });
        return res;
    }

    function parseSubtitles(subtitle, codes) {
        var res = [], re = /\[(.+?)\](https?:\/\/\S+?\.vtt)\b/g, m;
        if (!subtitle) return res;
        while ((m = re.exec(subtitle))) res.push({ label: m[1], url: m[2] });
        return res;
    }

    function str(obj, name) {
        return obj && typeof obj[name] === 'string' && obj[name] ? obj[name] : null;
    }

    /** One call to the player endpoint. action: get_movie | get_episodes | get_stream. */
    function query(player, action, translator, season, episode) {
        var form = [['id', player.movieId], ['translator_id', translator.id]];
        if (player.isSerial) {
            if (action !== 'get_episodes') { form.push(['season', season]); form.push(['episode', episode]); }
        } else {
            form.push(['is_camrip', translator.camrip ? '1' : '0']);
            form.push(['is_ads', translator.ads ? '1' : '0']);
            form.push(['is_director', translator.director ? '1' : '0']);
        }
        form.push(['favs', player.favs]);
        form.push(['action', action]);

        var url = baseUrl() + '/ajax/get_cdn_series/?t=' + new Date().getTime();
        return http('POST', url, encodeForm(form)).then(function (body) {
            var json;
            try { json = JSON.parse(body); } catch (e) { throw new SiteError('Некорректный ответ сайта', 'parse'); }
            if (json.success !== true) throw new SiteError(str(json, 'message') || 'Сайт отказал в запросе', 'ajax');
            return json;
        });
    }

    function seasonsOf(json) {
        var s = str(json, 'seasons'), e = str(json, 'episodes');
        return s && e ? parseSeasons(parseHtml(s), parseHtml(e)) : [];
    }

    // ---------- UI helpers ----------

    function noty(text) { try { Lampa.Noty.show(text); } catch (e) { /* ignore */ } }

    function loading(on) {
        try {
            if (Lampa.Loading) { on ? Lampa.Loading.start(function () { }) : Lampa.Loading.stop(); }
        } catch (e) { /* ignore */ }
    }

    function errorText(e) {
        if (e && e.kind === 'challenge') {
            return 'HDRezka: сайт просит проверку на бота. Без прокси, который её проходит, плагин работать не будет';
        }
        return 'HDRezka: ' + (e && e.message ? e.message : e);
    }

    function select(title, items, onSelect, onBack) {
        var back = Lampa.Controller.enabled().name;
        Lampa.Select.show({
            title: title,
            items: items,
            onSelect: onSelect,
            onBack: function () {
                if (onBack) onBack();
                else Lampa.Controller.toggle(back);
            }
        });
    }

    function run(promise) {
        loading(true);
        return promise.then(function (v) { loading(false); return v; }, function (e) {
            loading(false);
            noty(errorText(e));
            throw e;
        });
    }

    // ---------- flow ----------

    function playStreams(streams, subtitles, title) {
        var usable = streams.filter(function (s) { return !s.premium; });
        if (!usable.length) usable = streams;
        if (!usable.length) return noty('HDRezka: потоки не найдены');

        var best = usable[usable.length - 1];
        var quality = {};
        usable.slice().reverse().forEach(function (s) { quality[s.quality] = s.url; });

        Lampa.Player.play({
            title: title,
            url: best.url,
            quality: quality,
            subtitles: subtitles
        });
        try { Lampa.Player.playlist([{ title: title, url: best.url, quality: quality, subtitles: subtitles }]); } catch (e) { /* ignore */ }
    }

    function startMovie(player, translator, title) {
        run(query(player, 'get_movie', translator)).then(function (json) {
            playStreams(parseStreams(str(json, 'url')),
                parseSubtitles(str(json, 'subtitle')), title);
        }, function () { });
    }

    function pickEpisode(player, translator, seasons, title) {
        function pickSeason() {
            if (seasons.length <= 1) return pickEp(seasons[0]);
            select(title + ' — сезон', seasons.map(function (s) { return { title: s.title, season: s }; }),
                function (it) { pickEp(it.season, pickSeason); });
        }
        function pickEp(season, back) {
            if (!season || !season.episodes.length) return noty('HDRezka: серии не найдены');
            select(title + ' — ' + season.title,
                season.episodes.map(function (e) { return { title: e.title, episode: e }; }),
                function (it) {
                    run(query(player, 'get_stream', translator, season.id, it.episode.id)).then(function (json) {
                        playStreams(parseStreams(str(json, 'url')), parseSubtitles(str(json, 'subtitle')),
                            title + ' — ' + season.title + ', ' + it.episode.title);
                    }, function () { });
                }, back);
        }
        pickSeason();
    }

    function chooseTranslator(player, title) {
        function go(tr) {
            if (!player.isSerial) return startMovie(player, tr, title);
            run(query(player, 'get_episodes', tr)).then(function (json) {
                var seasons = seasonsOf(json);
                if (!seasons.length) seasons = player.seasons;
                pickEpisode(player, tr, seasons, title);
            }, function () { });
        }
        if (player.translators.length <= 1) return go(player.translator);
        select(title + ' — озвучка', player.translators.map(function (t) { return { title: t.name, tr: t, selected: t === player.translator }; }),
            function (it) { go(it.tr); });
    }

    function openResult(result) {
        run(loadMovie(result.url)).then(function (player) {
            chooseTranslator(player, result.title);
        }, function () { });
    }

    function pickResult(results, queryText) {
        select('HDRezka — ' + queryText,
            results.map(function (r) {
                return { title: r.title, subtitle: [r.entity, r.misc].filter(Boolean).join(' · '), result: r };
            }).concat([{ title: '🔍 Искать вручную', manual: true }, { title: '⚙ Настройки плагина', settings: true }]),
            function (it) {
                if (it.manual) return manualSearch(queryText);
                if (it.settings) return settingsDialog();
                openResult(it.result);
            });
    }

    function runSearch(queryText, year) {
        run(search(queryText)).then(function (results) {
            if (year) {
                var same = results.filter(function (r) { return r.year && Math.abs(toInt(r.year) - toInt(year)) <= 1; });
                if (same.length === 1) return openResult(same[0]);
                if (same.length > 1) results = same;
            }
            if (!results.length) {
                noty('HDRezka: ничего не найдено');
                return manualSearch(queryText);
            }
            if (results.length === 1) return openResult(results[0]);
            pickResult(results, queryText);
        }, function () { });
    }

    function manualSearch(initial) {
        var back = Lampa.Controller.enabled().name;
        Lampa.Input.edit({ title: 'HDRezka: поиск', value: initial || '', free: true, nosave: true }, function (value) {
            Lampa.Controller.toggle(back);
            if (value && /\S/.test(value)) runSearch(value);
        });
    }

    function settingsDialog() {
        select('HDRezka — настройки', [
            { title: 'Адрес сайта', subtitle: baseUrl(), key: 'hdrezka_base', def: DEFAULT_BASE },
            { title: 'CORS-прокси', subtitle: proxyTpl() || 'не задан', key: 'hdrezka_proxy', def: DEFAULT_PROXY }
        ], function (it) {
            var back = Lampa.Controller.enabled().name;
            Lampa.Input.edit({ title: it.title, value: String(store(it.key, it.def)), free: true, nosave: true }, function (value) {
                Lampa.Storage.set(it.key, (value || '').replace(/^\s+|\s+$/g, ''));
                Lampa.Controller.toggle(back);
                noty('Сохранено');
            });
        });
    }

    function startFromCard(movie) {
        var title = movie.title || movie.name || movie.original_title || movie.original_name || '';
        var date = movie.release_date || movie.first_air_date || '';
        var year = (date.match(/\d{4}/) || [])[0];
        if (!title) return manualSearch('');
        runSearch(title, year);
    }

    // ---------- integration ----------

    function addButton(e) {
        var render = e.object.activity.render();
        if (render.find('.view--hdrezka').length) return;

        var btn = $('<div class="full-start__button selector view--hdrezka"><span>HDRezka</span></div>');
        btn.on('hover:enter', function () { startFromCard(e.data.movie); });

        var anchor = render.find('.view--torrent');
        if (anchor.length) anchor.first().after(btn);
        else {
            var box = render.find('.full-start-new__buttons, .full-start__buttons').first();
            if (box.length) box.append(btn);
            else return;
        }
        try { Lampa.Controller.collectionSet(render); } catch (err) { /* ignore */ }
    }

    function init() {
        try {
            Lampa.Manifest.plugins = { type: 'video', version: VERSION, name: 'HDRezka', description: 'Онлайн-просмотр с HDRezka' };
        } catch (e) { /* ignore */ }

        Lampa.Listener.follow('full', function (e) {
            if (e.type === 'complite') addButton(e);
        });
    }

    if (window.appready) init();
    else Lampa.Listener.follow('app', function (e) { if (e.type === 'ready') init(); });
})();
