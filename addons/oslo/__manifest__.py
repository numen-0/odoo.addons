{
    "name": "Oslo",
    "version": "18.0.1.0.0",
    "category": "Operations",
    "summary": "Track production uptime streaks",
    "description": """
Oslo
====

A simple production uptime tracker.

Keep a history of production outages and track the currently active uptime
streak.
""",
    "author": "numen-0",
    "license": "Other OSI approved licence",
    "depends": [
        "base",
        "base_setup", # https://github.com/odoo/odoo/issues/166313
    ],
    "data": [
        "security/oslo_groups.xml",
        "security/ir.model.access.csv",
        "views/oslo_outage_views.xml",
        "views/oslo_analytics.xml",
        "views/oslo_home.xml",
        "views/oslo_menus.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "oslo/static/src/xml/*.xml",
            "oslo/static/src/css/*.css",
            "oslo/static/src/js/*.js",
        ],
    },
    "installable": True,
    "application": True,
}
