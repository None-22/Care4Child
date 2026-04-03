"""
Care4Child — مولّد مخطط قاعدة البيانات (ERD) مخصص
=========================================
الأستخدام:
    python generate_erd.py                   # يولّد PNG
    python generate_erd.py --format pdf      # يولّد PDF
    python generate_erd.py --format jpg      # يولّد JPG
    python generate_erd.py --format svg      # يولّد SVG
    python generate_erd.py --app medical     # تطبيق واحد فقط
    python generate_erd.py --table Child     # جدول واحد فقط
    python generate_erd.py --theme light     # ثيم فاتح
    python generate_erd.py --theme dark      # ثيم داكن (الافتراضي)
    python generate_erd.py --theme minimal   # ثيم بسيط / للتقرير
"""

import argparse
import os
import sys

try:
    import graphviz
except ImportError:
    print("❌ قم بتثبيت: pip install graphviz")
    sys.exit(1)

# ─────────────────────────────────────────────────────────────
# THEMES
# ─────────────────────────────────────────────────────────────
THEMES = {
    "dark": {
        "bg":           "#0D1117",
        "graph_bg":     "#161B22",
        "header_medical":       "#1a6b4a",
        "header_centers":       "#2d3282",
        "header_users":         "#1a4a6a",
        "header_notifications": "#7a5200",
        "header_auth":          "#6a1a1a",
        "header_django":        "#3a3a3a",
        "header_font":          "#FFFFFF",
        "row_bg":       "#1E2530",
        "row_alt":      "#242D3A",
        "row_font":     "#C9D1D9",
        "border":       "#30363D",
        "pk_color":     "#FFD700",
        "fk_color":     "#818CF8",
        "edge_color":   "#58A6FF",
        "font":         "arial",
    },
    "light": {
        "bg":           "#FFFFFF",
        "graph_bg":     "#FFFFFF",
        "header_medical":       "#1565C0",
        "header_centers":       "#1565C0",
        "header_users":         "#1565C0",
        "header_notifications": "#1565C0",
        "header_auth":          "#1565C0",
        "header_django":        "#1565C0",
        "header_font":          "#FFFFFF",
        "row_bg":       "#FFFFFF",
        "row_alt":      "#FFFFFF",
        "row_font":     "#000000",
        "border":       "#000000",
        "pk_color":     "#000000",
        "fk_color":     "#000000",
        "edge_color":   "#000000",
        "font":         "arial",
    },
    "minimal": {
        "bg":           "#FFFFFF",
        "graph_bg":     "#FFFFFF",
        "header_medical":       "#2C3E50",
        "header_centers":       "#2C3E50",
        "header_users":         "#2C3E50",
        "header_notifications": "#2C3E50",
        "header_auth":          "#2C3E50",
        "header_django":        "#2C3E50",
        "header_font":          "#FFFFFF",
        "row_bg":       "#FFFFFF",
        "row_alt":      "#F8F9FA",
        "row_font":     "#000000",
        "border":       "#BBBBBB",
        "pk_color":     "#C0392B",
        "fk_color":     "#2980B9",
        "edge_color":   "#555555",
        "font":         "arial",
    },
}

# ─────────────────────────────────────────────────────────────
# SCHEMA DEFINITION
# ─────────────────────────────────────────────────────────────
SCHEMA = {
    "medical": [
        {
            "name": "Family",
            "db_table": "medical_family",
            "fields": [
                ("id",          "BigAutoField",  "PK"),
                ("father_name", "CharField",     ""),
                ("mother_name", "CharField",     ""),
                ("access_code", "CharField",     "UQ"),
                ("notes",       "TextField",     "NULL"),
                ("created_at",  "DateTimeField", ""),
                ("account_id",    "→ CustomUser", "FK/1:1"),
                ("created_by_id", "→ CustomUser", "FK"),
            ],
        },
        {
            "name": "Child",
            "db_table": "medical_child",
            "fields": [
                ("id",                   "BigAutoField", "PK"),
                ("full_name",            "CharField",    ""),
                ("gender",               "CharField(1)", ""),
                ("date_of_birth",        "DateField",    ""),
                ("place_of_birth",       "CharField",    ""),
                ("is_completed",         "BooleanField", ""),
                ("completed_date",       "DateField",    "NULL"),
                ("created_at",           "DateTimeField",""),
                ("family_id",            "→ Family",     "FK"),
                ("health_center_id",     "→ HealthCenter","FK"),
                ("birth_governorate_id", "→ Governorate","FK"),
                ("birth_directorate_id", "→ Directorate","FK"),
                ("created_by_id",        "→ CustomUser", "FK"),
            ],
        },
        {
            "name": "Vaccine",
            "db_table": "medical_vaccine",
            "fields": [
                ("id",          "BigAutoField",  "PK"),
                ("name_ar",     "CharField",     ""),
                ("name_en",     "CharField",     "NULL"),
                ("description", "TextField",     "NULL"),
                ("key",         "CharField",     "NULL"),
                ("is_active",   "BooleanField",  ""),
            ],
        },
        {
            "name": "VaccineSchedule",
            "db_table": "medical_vaccineschedule",
            "fields": [
                ("id",            "BigAutoField",      "PK"),
                ("dose_number",   "IntegerField",      ""),
                ("age_in_months", "FloatField",        ""),
                ("stage",         "CharField(10)",     ""),
                ("vaccine_id",    "→ Vaccine",         "FK"),
            ],
        },
        {
            "name": "ChildVaccineSchedule",
            "db_table": "medical_childvaccineschedule",
            "fields": [
                ("id",                  "BigAutoField", "PK"),
                ("due_date",            "DateField",    ""),
                ("is_taken",            "BooleanField", ""),
                ("child_id",            "→ Child",      "FK"),
                ("vaccine_schedule_id", "→ VaccineSchedule", "FK"),
            ],
        },
        {
            "name": "VaccineRecord",
            "db_table": "medical_vaccinerecord",
            "fields": [
                ("id",          "BigAutoField",  "PK"),
                ("dose_number", "IntegerField",  ""),
                ("date_given",  "DateField",     ""),
                ("notes",       "TextField",     "NULL"),
                ("created_at",  "DateTimeField", ""),
                ("child_id",    "→ Child",       "FK"),
                ("vaccine_id",  "→ Vaccine",     "FK"),
                ("staff_id",    "→ CustomUser",  "FK"),
            ],
            "unique_together": "UNIQUE(child, vaccine, dose_number)",
        },
    ],
    "centers": [
        {
            "name": "Governorate",
            "db_table": "centers_governorate",
            "fields": [
                ("id",      "BigAutoField",  "PK"),
                ("name_ar", "CharField",     ""),
                ("name_en", "CharField",     "NULL"),
                ("code",    "CharField(5)",  "UQ"),
            ],
        },
        {
            "name": "Directorate",
            "db_table": "centers_directorate",
            "fields": [
                ("id",             "BigAutoField", "PK"),
                ("name_ar",        "CharField",    ""),
                ("name_en",        "CharField",    "NULL"),
                ("code",           "CharField(5)", ""),
                ("governorate_id", "→ Governorate","FK"),
            ],
            "unique_together": "UNIQUE(governorate, code)",
        },
        {
            "name": "HealthCenter",
            "db_table": "centers_healthcenter",
            "fields": [
                ("id",             "BigAutoField", "PK"),
                ("center_code",    "CharField",    "UQ"),
                ("name_ar",        "CharField",    ""),
                ("name_en",        "CharField",    "NULL"),
                ("address",        "TextField",    ""),
                ("license_number", "CharField",    "NULL"),
                ("working_hours",  "CharField",    "NULL"),
                ("is_active",      "BooleanField", ""),
                ("created_at",     "DateTimeField",""),
                ("governorate_id", "→ Governorate","FK"),
                ("directorate_id", "→ Directorate","FK"),
            ],
        },
    ],
    "users": [
        {
            "name": "CustomUser",
            "db_table": "users_customuser",
            "fields": [
                ("id",              "BigAutoField",  "PK"),
                ("username",        "CharField",     "UQ"),
                ("password",        "CharField",     ""),
                ("email",           "CharField",     ""),
                ("first_name",      "CharField",     ""),
                ("last_name",       "CharField",     ""),
                ("role",            "CharField(20)", ""),
                ("phone",           "CharField",     "NULL"),
                ("fcm_token",       "TextField",     "NULL"),
                ("is_active",       "BooleanField",  ""),
                ("is_staff",        "BooleanField",  ""),
                ("is_superuser",    "BooleanField",  ""),
                ("date_joined",     "DateTimeField", ""),
                ("last_login",      "DateTimeField", "NULL"),
                ("health_center_id","→ HealthCenter","FK"),
            ],
        },
    ],
    "notifications": [
        {
            "name": "NotificationLog",
            "db_table": "notifications_notificationlog",
            "fields": [
                ("id",                "BigAutoField",  "PK"),
                ("title",             "CharField",     ""),
                ("body",              "TextField",     ""),
                ("notification_type", "CharField(20)", ""),
                ("sent_via_fcm",      "BooleanField",  ""),
                ("fcm_response",      "TextField",     "NULL"),
                ("is_read",           "BooleanField",  ""),
                ("created_at",        "DateTimeField", ""),
                ("recipient_id",      "→ CustomUser",  "FK"),
            ],
        },
    ],
    "auth": [
        {
            "name": "AuthToken",
            "db_table": "authtoken_token",
            "fields": [
                ("key",     "CharField(40)", "PK"),
                ("created", "DateTimeField", ""),
                ("user_id", "→ CustomUser",  "FK/1:1"),
            ],
        },
    ],
}

# FK relations: (from_table, from_field, to_table)
RELATIONS = [
    # medical
    ("Family",    "account_id",    "CustomUser"),
    ("Family",    "created_by_id", "CustomUser"),
    ("Child",     "family_id",     "Family"),
    ("Child",     "health_center_id", "HealthCenter"),
    ("Child",     "birth_governorate_id", "Governorate"),
    ("Child",     "birth_directorate_id", "Directorate"),
    ("Child",     "created_by_id", "CustomUser"),
    ("VaccineSchedule",       "vaccine_id",           "Vaccine"),
    ("ChildVaccineSchedule",  "child_id",             "Child"),
    ("ChildVaccineSchedule",  "vaccine_schedule_id",  "VaccineSchedule"),
    ("VaccineRecord",         "child_id",             "Child"),
    ("VaccineRecord",         "vaccine_id",           "Vaccine"),
    ("VaccineRecord",         "staff_id",             "CustomUser"),
    # centers
    ("Directorate",  "governorate_id", "Governorate"),
    ("HealthCenter", "governorate_id", "Governorate"),
    ("HealthCenter", "directorate_id", "Directorate"),
    # users
    ("CustomUser",   "health_center_id", "HealthCenter"),
    # notifications
    ("NotificationLog", "recipient_id", "CustomUser"),
    # auth
    ("AuthToken", "user_id", "CustomUser"),
]

# ─────────────────────────────────────────────────────────────
# BUILD TABLE HTML LABEL
# ─────────────────────────────────────────────────────────────
def build_label(tbl, app, theme):
    t = THEMES[theme]
    # Use uniform blue header for all apps in light/minimal theme
    header_color = t[f"header_{app}"]
    header_font  = t["header_font"]
    row_bg       = t["row_bg"]
    row_alt      = t["row_alt"]
    row_font     = t["row_font"]
    pk_color     = t["pk_color"]
    fk_color     = t["fk_color"]
    border       = t["border"]
    font         = t["font"]

    app_icons = {
        "medical": "🩺", "centers": "🏥",
        "users": "👤", "notifications": "🔔", "auth": "🔑",
    }

    rows = ""
    for i, (fname, ftype, fkey) in enumerate(tbl["fields"]):
        bg = row_bg

        if fkey == "PK":
            key_badge = f'<FONT COLOR="{pk_color}"><B>PK </B></FONT>'
        elif "FK" in fkey or "1:1" in fkey:
            key_badge = f'<FONT COLOR="{fk_color}"><B>{fkey} </B></FONT>'
        elif fkey == "UQ":
            key_badge = f'<FONT COLOR="{fk_color}"><B>UQ </B></FONT>'
        elif fkey == "NULL":
            key_badge = ""
        else:
            key_badge = ""

        rows += (
            f'<TR>'
            f'<TD ALIGN="LEFT" BGCOLOR="{bg}">'
            f'<FONT FACE="{font}" COLOR="{row_font}" POINT-SIZE="10">'
            f'{key_badge}{fname}'
            f'</FONT>'
            f'</TD>'
            f'<TD ALIGN="LEFT" BGCOLOR="{bg}">'
            f'<FONT FACE="{font}" COLOR="{row_font}" POINT-SIZE="9">'
            f'{ftype}'
            f'</FONT>'
            f'</TD>'
            f'</TR>'
        )

    unique = ""
    if "unique_together" in tbl:
        unique = (
            f'<TR><TD COLSPAN="2" ALIGN="LEFT" BGCOLOR="{row_alt}">'
            f'<FONT FACE="{font}" COLOR="#888888" POINT-SIZE="8">'
            f'UNIQUE({tbl["unique_together"].replace("UNIQUE(","").replace(")","") })'
            f'</FONT></TD></TR>'
        )

    label = (
        f'<<TABLE BORDER="1" CELLBORDER="0" CELLSPACING="0" CELLPADDING="5" '
        f'BGCOLOR="{row_bg}">'
        f'<TR><TD COLSPAN="2" BGCOLOR="{header_color}" ALIGN="CENTER">'
        f'<FONT FACE="{font}" COLOR="{header_font}" POINT-SIZE="11">'
        f'<B>{tbl["name"]}</B>'
        f'</FONT>'
        f'</TD></TR>'
        f'{rows}'
        f'{unique}'
        f'</TABLE>>'
    )
    return label


# ─────────────────────────────────────────────────────────────
# GENERATE DIAGRAM
# ─────────────────────────────────────────────────────────────
def generate(fmt="png", theme="dark", app_filter=None, table_filter=None, output_dir="schema_viewer"):
    t = THEMES[theme]
    os.makedirs(output_dir, exist_ok=True)

    # determine what to include
    selected_schema = {}
    if app_filter:
        if app_filter in SCHEMA:
            selected_schema = {app_filter: SCHEMA[app_filter]}
        else:
            print(f"❌ التطبيق '{app_filter}' غير موجود. الخيارات: {list(SCHEMA.keys())}")
            return
    elif table_filter:
        for app, tables in SCHEMA.items():
            for tbl in tables:
                if tbl["name"].lower() == table_filter.lower():
                    selected_schema = {app: [tbl]}
                    break
        if not selected_schema:
            print(f"❌ الجدول '{table_filter}' غير موجود.")
            return
    else:
        selected_schema = SCHEMA

    # build table name → node id map
    table_node = {}
    all_tables = []
    for app, tables in selected_schema.items():
        for tbl in tables:
            table_node[tbl["name"]] = tbl["name"]
            all_tables.append((app, tbl))

    # figure out output filename
    if table_filter:
        fname = f"erd_{table_filter.lower()}"
    elif app_filter:
        fname = f"erd_{app_filter}"
    else:
        fname = "erd_full"

    out_path = os.path.join(output_dir, fname)

    dg = graphviz.Digraph(
        name="Care4Child_ERD",
        filename=fname,
        directory=output_dir,
        format=fmt,
        graph_attr={
            "bgcolor":    t["graph_bg"],
            "rankdir":    "TB",
            "splines":    "ortho",
            "nodesep":    "0.8",
            "ranksep":    "1.2",
            "fontname":   t["font"],
            "fontcolor":  t["row_font"],
            "pad":        "0.5",
            "dpi":        "180",
            "label":      "Care4Child — Database Schema",
            "labelloc":   "t",
            "labeljust":  "c",
            "fontsize":   "18",
        },
        node_attr={
            "shape":     "none",
            "margin":    "0",
            "fontname":  t["font"],
        },
        edge_attr={
            "color":     t["edge_color"],
            "arrowhead": "normal",
            "arrowtail": "none",
            "dir":       "forward",
            "arrowsize": "0.7",
            "penwidth":  "1.0",
            "style":     "solid",
        },
    )

    # group by app (subgraph clusters)
    for app, tables in selected_schema.items():
        cluster_name = f"cluster_{app}"
        with dg.subgraph(name=cluster_name) as c:
            c.attr(
                label="",
                style="invis",
                penwidth="0",
            )
            for tbl in tables:
                label = build_label(tbl, app, theme)
                c.node(tbl["name"], label=label)

    # add edges (node-to-node)
    visible_names = {tbl["name"] for _, tbl in all_tables}
    for (from_t, from_f, to_t) in RELATIONS:
        if from_t in visible_names and to_t in visible_names:
            dg.edge(
                from_t,
                to_t,
                fontname=t["font"],
                fontsize="8",
                fontcolor=t["edge_color"],
            )

    # render
    rendered = dg.render(cleanup=True)
    print(f"✅ تم الحفظ: {rendered}")
    return rendered


# ─────────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────────
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Care4Child ERD Generator")
    parser.add_argument("--format",  default="png",  choices=["png", "pdf", "jpg", "svg"], help="صيغة الملف")
    parser.add_argument("--theme",   default="dark", choices=["dark", "light", "minimal"],  help="الثيم")
    parser.add_argument("--app",     default=None,   help="اسم التطبيق (medical, centers, users, notifications, auth)")
    parser.add_argument("--table",   default=None,   help="اسم الجدول (Child, Family, Vaccine ...)")
    parser.add_argument("--output",  default="schema_viewer", help="مجلد الحفظ")
    parser.add_argument("--all-formats", action="store_true", help="يصدّر PNG + PDF + SVG دفعة واحدة")
    parser.add_argument("--build-everything", action="store_true", help="يصدّر كافة الخيارات (مجمع ومنفصل، بجميع الثيمات والصيغ)")
    args = parser.parse_args()

    if args.build_everything:
        themes = ["dark", "light", "minimal"]
        apps = [None, "medical", "centers", "users", "notifications", "auth"]
        formats = ["png", "pdf", "svg"]
        for theme in themes:
            theme_dir = os.path.join(args.output, theme)
            os.makedirs(theme_dir, exist_ok=True)
            for app in apps:
                for fmt in formats:
                    generate(fmt=fmt, theme=theme, app_filter=app,
                             table_filter=None, output_dir=theme_dir)
        print("✅ تم بناء جميع المخططات بنجاح (مجمعة ومنفصلة) بجميع الثيمات والصيغ!")
    elif args.all_formats:
        for fmt in ["png", "pdf", "svg"]:
            generate(fmt=fmt, theme=args.theme, app_filter=args.app,
                     table_filter=args.table, output_dir=args.output)
    else:
        generate(fmt=args.format, theme=args.theme, app_filter=args.app,
                 table_filter=args.table, output_dir=args.output)
