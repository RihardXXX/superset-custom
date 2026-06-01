# Centaur Analytics — кастомизированный Apache Superset 6.1.0

Production-образ Apache Superset `6.1.0`, собранный из исходников и
кастомизированный под задачу. Репозиторий — форк официального
[apache/superset](https://github.com/apache/superset) на базе тега `6.1.0`
(commit `c83fb2b`). Каждая доработка внесена отдельным Pull Request в ветку
`main`.

## Что сделано

| # | Задача | Где реализовано | PR |
|---|--------|-----------------|----|
| 1 | Установка `clickhouse-connect` в образ | `Dockerfile` (стадия `lean`) | [#7](https://github.com/RihardXXX/superset-custom/pull/7) |
| 2 | Замена favicon | `superset/config.py` (`FAVICONS`) + `superset-frontend/src/assets/images/custom-favicon.png` | [#42](https://github.com/RihardXXX/superset-custom/pull/42) |
| 3 | Замена логотипа | `superset/config.py` (`APP_ICON`, `APP_NAME`) + `custom-logo.png` | [#51](https://github.com/RihardXXX/superset-custom/pull/51) |
| 4 | Убрать «Powered by Apache Superset» | `superset/views/base.py` (`show_watermark = False`) | [#52](https://github.com/RihardXXX/superset-custom/pull/52) |
| 5 | Dashboard как стартовая страница для всех | `superset/initialization/__init__.py`, `superset/config.py` (`DEFAULT_LANDING_DASHBOARD`) | [#69](https://github.com/RihardXXX/superset-custom/pull/69) |
| 6 | Убрать префикс `/superset/` из URL | фронтенд `routes.tsx` + билдеры ссылок, backend, `docker/nginx/superset.conf` | [#66](https://github.com/RihardXXX/superset-custom/pull/66) |
| 7 | `README.md` + production `docker-compose.yml` | этот файл, `docker-compose.yml`, `docker/superset_config_docker.py` | этот PR |

Подробности по каждому пункту — в описании соответствующего PR.

## Архитектура запуска

```
            :80                     :8088
 браузер ───────►  nginx  ───────►  superset (gunicorn)
                   (чистые URL)      ├─ postgres   (метаданные)
                                     ├─ redis      (кэш + Celery broker)
                                     ├─ superset-worker      (Celery)
                                     └─ superset-worker-beat (расписания)
```

`nginx` отдаёт пользователю URL без `/superset/` и проксирует их во Flask-приложение,
которое внутри по-прежнему обслуживает страницы под `/superset/*`. Фронтенд при этом
нативно генерирует ссылки уже без префикса.

## 1. Как собрать Docker-образ

Образ собирается из исходников по корневому `Dockerfile`, production-стадия — `lean`:

```bash
# отдельно образ (опционально)
docker build --target lean -t superset-custom:6.1.0 .
```

В `lean`-стадию доустановлены `clickhouse-connect` (драйвер ClickHouse) и
`psycopg2-binary` (драйвер PostgreSQL для БД метаданных). Фронтенд (с заменёнными
favicon/логотипом и URL без `/superset/`) собирается webpack-ом внутри стадии
`superset-node`.

## 2. Как запустить Superset

Весь стек поднимается одной командой (образ соберётся автоматически):

```bash
docker compose up -d --build
```

Дождитесь, пока сервис `superset` станет `healthy` (`docker compose ps`), затем
откройте:

```
http://localhost/          # стартовая страница = dashboard (для всех ролей)
```

Логин по умолчанию: **admin / admin**.

Настройки переопределяются через `.env` (см. `.env.example`): секретный ключ,
доступы к БД, и `DEFAULT_LANDING_DASHBOARD` — id или slug дашборда, который будет
стартовой страницей.

### Быстрая проверка результата

```bash
# нет /superset/ в URL дашборда
curl -sI http://localhost/dashboard/world_health/ | head -n1      # 200

# старый URL редиректится на чистый
curl -sI http://localhost/superset/dashboard/world_health/ | head -n1   # 301 -> /dashboard/...

# стартовая страница: один корректный 302 на дашборд
curl -sI http://localhost/ | grep -i location                     # /dashboard/world_health/
```

Стартовая страница и чистые URL работают и для обычного пользователя (роль
`Gamma`). При инициализации (`superset-init` → `docker/init_landing.py`) лендинг-дашборд
автоматически публикуется и расшаривается на роль `Gamma` (через `DASHBOARD_RBAC`),
поэтому свежесозданный не-админ сразу попадает на полностью доступный дашборд.
Проверить можно так:

```bash
# создать не-админа
docker compose exec superset superset fab create-user \
  --role Gamma --username viewer --password viewer \
  --firstname V --lastname Iewer --email viewer@centaur.local
# войти под viewer/viewer на http://localhost — попадёте на /dashboard/world_health/ (200)
```

## 3. Что бы я ещё изменил для Production

- **Секреты и конфиги.** `SECRET_KEY`, пароли БД и админа — только из секрет-менеджера
  (Vault / Docker secrets / SOPS), не из `.env` в репозитории. Включить ротацию ключа.
- **TLS.** Терминировать HTTPS на nginx/ingress, `PREFERRED_URL_SCHEME=https`,
  `SESSION_COOKIE_SECURE=True`, `TALISMAN_ENABLED=True` с настроенным CSP.
- **БД и отказоустойчивость.** Managed PostgreSQL с репликами и бэкапами, Redis с
  персистентностью/Sentinel, а не контейнеры на одном хосте; пулы соединений (PgBouncer).
- **Масштабирование.** Несколько реплик `superset` и `superset-worker` за балансировщиком,
  тюнинг gunicorn (`SERVER_WORKER_AMOUNT`, `gevent`), отдельные очереди Celery.
- **Удаление префикса `/superset/` «по-настоящему».** Текущее решение — reverse-proxy +
  правки фронта/билдеров ссылок. Для 100% (включая внутренние XHR `/superset/explore_json`,
  `/superset/log`) — перенос Flask-blueprint на корень с устранением коллизий
  маршрутов (`ExploreView`, `SqlLabView`) и полной пересборкой фронтенда.
- **Стартовый дашборд.** Сейчас — глобальный редирект + расшаривание дашборда на роли.
  Для гибкости — выбор лендинга по роли/пользователю (через `UserAttribute` или
  кастомный mutator) и graceful-fallback на welcome, если у пользователя нет доступа.
- **Observability.** Прометей-метрики gunicorn/Celery, централизованные логи (JSON),
  Sentry, healthchecks/alerting, statsd (`STATS_LOGGER`).
- **CI/CD и образ.** Пин версий зависимостей (включая `clickhouse-connect`), multi-arch
  сборка, скан образа (Trivy), SBOM, тэги по версии, прогон `pre-commit`/тестов в CI.
- **Брендинг.** Логотип/иконку — в нескольких размерах (PWA-манифест, retina), плюс
  кастомная тема Superset под фирстиль.

---

Основано на [Apache Superset](https://github.com/apache/superset) 6.1.0,
лицензия Apache License 2.0. Кастомизации помечены в коде комментариями
`Custom (Centaur)`.
