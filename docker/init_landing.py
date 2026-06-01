# Custom (Centaur) — make the landing dashboard reachable by non-admin users
# out of the box.
#
# Run after docker-init.sh (which loads the example dashboards). It takes the
# DEFAULT_LANDING_DASHBOARD (id or slug), publishes it and grants the built-in
# `Gamma` role access via DASHBOARD_RBAC, so a freshly created non-admin user
# lands on a fully accessible dashboard. Safe to run repeatedly (idempotent).
from __future__ import annotations

import os
import sys


def main() -> int:
    landing = os.environ.get("DEFAULT_LANDING_DASHBOARD")
    if not landing:
        print("[init_landing] DEFAULT_LANDING_DASHBOARD not set, nothing to do")
        return 0

    from superset.app import create_app

    app = create_app()
    with app.app_context():
        from flask_appbuilder.security.sqla.models import Role

        from superset import db
        from superset.models.dashboard import Dashboard

        query = db.session.query(Dashboard)
        dashboard = (
            query.filter_by(id=int(landing)).one_or_none()
            if str(landing).isdigit()
            else query.filter_by(slug=str(landing)).one_or_none()
        )
        if dashboard is None:
            print(f"[init_landing] dashboard '{landing}' not found, skipping")
            return 0

        dashboard.published = True
        gamma = db.session.query(Role).filter_by(name="Gamma").one_or_none()
        if gamma is not None and gamma not in dashboard.roles:
            dashboard.roles.append(gamma)
        db.session.commit()
        print(
            f"[init_landing] dashboard '{dashboard.slug or dashboard.id}' published "
            f"and shared with roles: {[r.name for r in dashboard.roles]}"
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
