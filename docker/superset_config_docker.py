# Custom (Centaur) — runtime Superset configuration for the production-emulation
# docker-compose stack. It is mounted into the image at
# /app/pythonpath/superset_config.py and therefore OVERRIDES the defaults from
# superset/config.py at runtime.
#
# Branding (favicon, logo, app name, watermark, landing dashboard) lives in
# superset/config.py / superset/views/base.py and is baked into the image — this
# file only wires up infrastructure (metadata DB, cache, Celery, proxy).
from __future__ import annotations

import os

# --------------------------------------------------------------------------
# Secrets
# --------------------------------------------------------------------------
# In real production set a strong, unique value via the SUPERSET_SECRET_KEY env
# var (e.g. `openssl rand -base64 42`). The fallback exists only so the demo
# stack starts with zero configuration.
SECRET_KEY = os.environ.get(
    "SUPERSET_SECRET_KEY",
    "centaur-demo-not-for-production-please-override-this-secret-key",
)

# --------------------------------------------------------------------------
# Metadata database (PostgreSQL)
# --------------------------------------------------------------------------
DATABASE_USER = os.environ.get("DATABASE_USER", "superset")
DATABASE_PASSWORD = os.environ.get("DATABASE_PASSWORD", "superset")
DATABASE_HOST = os.environ.get("DATABASE_HOST", "postgres")
DATABASE_PORT = os.environ.get("DATABASE_PORT", "5432")
DATABASE_DB = os.environ.get("DATABASE_DB", "superset")

SQLALCHEMY_DATABASE_URI = (
    f"postgresql+psycopg2://{DATABASE_USER}:{DATABASE_PASSWORD}"
    f"@{DATABASE_HOST}:{DATABASE_PORT}/{DATABASE_DB}"
)
SQLALCHEMY_ENGINE_OPTIONS = {"pool_pre_ping": True}

# --------------------------------------------------------------------------
# Redis (caching + Celery broker/result backend)
# --------------------------------------------------------------------------
REDIS_HOST = os.environ.get("REDIS_HOST", "redis")
REDIS_PORT = int(os.environ.get("REDIS_PORT", "6379"))

_CACHE_BASE = {
    "CACHE_TYPE": "RedisCache",
    "CACHE_DEFAULT_TIMEOUT": 300,
    "CACHE_REDIS_HOST": REDIS_HOST,
    "CACHE_REDIS_PORT": REDIS_PORT,
}
CACHE_CONFIG = {**_CACHE_BASE, "CACHE_KEY_PREFIX": "superset_", "CACHE_REDIS_DB": 1}
DATA_CACHE_CONFIG = {**_CACHE_BASE, "CACHE_KEY_PREFIX": "superset_data_", "CACHE_REDIS_DB": 2}
FILTER_STATE_CACHE_CONFIG = {
    **_CACHE_BASE,
    "CACHE_KEY_PREFIX": "superset_filter_",
    "CACHE_REDIS_DB": 3,
}
EXPLORE_FORM_DATA_CACHE_CONFIG = {
    **_CACHE_BASE,
    "CACHE_KEY_PREFIX": "superset_form_",
    "CACHE_REDIS_DB": 4,
}


class CeleryConfig:
    broker_url = f"redis://{REDIS_HOST}:{REDIS_PORT}/0"
    result_backend = f"redis://{REDIS_HOST}:{REDIS_PORT}/0"
    imports = ("superset.sql_lab", "superset.tasks.scheduler")
    worker_prefetch_multiplier = 1
    task_acks_late = False


CELERY_CONFIG = CeleryConfig

# --------------------------------------------------------------------------
# Reverse proxy
# --------------------------------------------------------------------------
# The stack runs behind the nginx reverse proxy that strips the /superset/
# prefix. ProxyFix makes Flask trust the X-Forwarded-* headers so generated
# URLs and redirects use the correct external scheme/host (avoids broken 302s).
ENABLE_PROXY_FIX = True
PROXY_FIX_CONFIG = {"x_for": 1, "x_proto": 1, "x_host": 1, "x_port": 1, "x_prefix": 1}

# Keep CSRF protection on in production.
WTF_CSRF_ENABLED = True

# A couple of handy feature flags for a realistic deployment.
FEATURE_FLAGS = {
    "DASHBOARD_RBAC": True,
    "EMBEDDED_SUPERSET": False,
}
