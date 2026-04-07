import json
import os
import secrets
import smtplib
from datetime import datetime
from email.mime.text import MIMEText
from urllib import error as urllib_error
from urllib import request as urllib_request
from urllib.parse import urlencode

from flask import Flask, Response, jsonify, redirect, render_template, request, session, url_for

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", secrets.token_hex(32))

CALC_URL = os.environ.get("CALC_URL", "https://calculadora.reusrevela.cat")
CALC_SIGNUP_URL = os.environ.get("CALC_SIGNUP_URL", f"{CALC_URL.rstrip('/')}/api/public/professional-signup")
CALC_SIGNUP_TOKEN = os.environ.get("CALC_SIGNUP_TOKEN", "")
CONTACT_EMAIL = os.environ.get("CONTACT_EMAIL", "reusrevela@gmail.com")
SMTP_HOST = os.environ.get("SMTP_HOST")
SMTP_PORT = int(os.environ.get("SMTP_PORT", "587"))
SMTP_USER = os.environ.get("SMTP_USER")
SMTP_PASSWORD = os.environ.get("SMTP_PASSWORD")
SMTP_FROM = os.environ.get("SMTP_FROM", CONTACT_EMAIL)
SMTP_USE_TLS = os.environ.get("SMTP_USE_TLS", "true").lower() != "false"

CALC_SERVICE_CONFIG = {
    "general": {
        "subject": "pro_access",
        "label": {
            "ca": "el catàleg professional",
            "es": "el catálogo profesional",
        },
    },
    "albums": {
        "subject": "albums",
        "label": {
            "ca": "àlbums fotogràfics",
            "es": "álbumes fotográficos",
        },
    },
    "frames": {
        "subject": "frames",
        "label": {
            "ca": "marcs a mida",
            "es": "marcos a medida",
        },
    },
    "canvas": {
        "subject": "canvas",
        "label": {
            "ca": "llenços impresos",
            "es": "lienzos impresos",
        },
    },
    "photo_print": {
        "subject": "photo_print",
        "label": {
            "ca": "impressió fotogràfica",
            "es": "impresión fotográfica",
        },
    },
    "fine_art": {
        "subject": "fine_art",
        "label": {
            "ca": "fine art Hahnemuhle",
            "es": "fine art Hahnemuhle",
        },
    },
}

PRIVATE_MODULES = [
    {
        "key": "pricing",
        "status": "ready",
        "eyebrow": {"ca": "Base viva", "es": "Base viva"},
        "title": {"ca": "Tarifari", "es": "Tarifario"},
        "summary": {
            "ca": "Consulta preus, formats i PVP des d'un sol lloc, sense dependre de PDFs antics.",
            "es": "Consulta precios, formatos y PVP desde un solo lugar, sin depender de PDFs antiguos.",
        },
        "href": "area_privada_tarifari",
    },
    {
        "key": "canvas",
        "status": "ready",
        "eyebrow": {"ca": "Primer mòdul", "es": "Primer módulo"},
        "title": {"ca": "Llenços", "es": "Lienzos"},
        "summary": {
            "ca": "Mesures reals, laminat Protter inclòs i preparació del fitxer resolta en pocs passos.",
            "es": "Medidas reales, laminado Protter incluido y preparación del archivo resuelta en pocos pasos.",
        },
        "href": "area_privada_lienzos",
    },
    {
        "key": "prints",
        "status": "ready",
        "eyebrow": {"ca": "Següent mòdul", "es": "Siguiente módulo"},
        "title": {"ca": "Impressions", "es": "Impresiones"},
        "summary": {
            "ca": "Còpia en Lustre o Silk, amb opcions de laminat i foam; si cal marc, es calcula a part.",
            "es": "Copia en Lustre o Silk, con opciones de laminado y foam; si hace falta marco, se calcula aparte.",
        },
        "href": "area_privada_impresions",
    },
    {
        "key": "frames",
        "status": "ready",
        "eyebrow": {"ca": "Integració segura", "es": "Integración segura"},
        "title": {"ca": "Marcs", "es": "Marcos"},
        "summary": {
            "ca": "Accés directe a la calculadora actual de marcs, amb el catàleg i els càlculs de sempre.",
            "es": "Acceso directo a la calculadora actual de marcos, con el catálogo y los cálculos de siempre.",
        },
        "href": "area_privada_marcos",
    },
    {
        "key": "albums",
        "status": "planned",
        "eyebrow": {"ca": "Següent fase", "es": "Siguiente fase"},
        "title": {"ca": "Àlbums", "es": "Álbumes"},
        "summary": {
            "ca": "Formats, cobertes i pàgines per pressupostar àlbums des del mateix compte professional.",
            "es": "Formatos, cubiertas y páginas para presupuestar álbumes desde la misma cuenta profesional.",
        },
        "href": None,
    },
    {
        "key": "finishes",
        "status": "planned",
        "eyebrow": {"ca": "Base comuna", "es": "Base común"},
        "title": {"ca": "Acabats", "es": "Acabados"},
        "summary": {
            "ca": "Acabats i extres compartits per aplicar-los allà on toqui sense repetir feina.",
            "es": "Acabados y extras compartidos para aplicarlos donde toque sin repetir trabajo.",
        },
        "href": None,
    },
    {
        "key": "orders",
        "status": "ready",
        "eyebrow": {"ca": "Operativa", "es": "Operativa"},
        "title": {"ca": "Comandes", "es": "Pedidos"},
        "summary": {
            "ca": "Agrupa línies, prepara pressupost, ordre de taller i recepció del fitxer en una sola comanda.",
            "es": "Agrupa líneas, prepara presupuesto, orden de taller y recepción del archivo en un solo pedido.",
        },
        "href": "area_privada_comanda",
    },
]

CANVAS_PRICING = {
    "vat_rate": 0.21,
    "default_margin_percent": 30.0,
    "fixed_features": {
        "frame_depth_cm": 4,
        "laminate_label": {
            "ca": "Laminat Protter al buit mantenint la textura del llenç",
            "es": "Laminado Protter al vacío manteniendo la textura del lienzo",
        },
    },
    "sizes": [
        {"group": "standard", "final": [30, 30], "file": [40, 40], "price": 39.50},
        {"group": "standard", "final": [30, 40], "file": [40, 50], "price": 40.00},
        {"group": "standard", "final": [30, 50], "file": [40, 60], "price": 52.00},
        {"group": "standard", "final": [40, 40], "file": [50, 50], "price": 48.00},
        {"group": "standard", "final": [40, 50], "file": [50, 60], "price": 51.00},
        {"group": "standard", "final": [50, 50], "file": [60, 60], "price": 52.00},
        {"group": "standard", "final": [50, 60], "file": [60, 70], "price": 54.00},
        {"group": "standard", "final": [50, 70], "file": [60, 80], "price": 56.00},
        {"group": "standard", "final": [50, 80], "file": [60, 90], "price": 70.00},
        {"group": "standard", "final": [60, 60], "file": [70, 70], "price": 60.00},
        {"group": "standard", "final": [60, 80], "file": [70, 90], "price": 66.00},
        {"group": "standard", "final": [60, 90], "file": [70, 100], "price": 68.00},
        {"group": "standard", "final": [60, 100], "file": [70, 110], "price": 79.00},
        {"group": "standard", "final": [70, 70], "file": [80, 80], "price": 65.00},
        {"group": "standard", "final": [70, 100], "file": [80, 110], "price": 78.00},
        {"group": "standard", "final": [70, 150], "file": [80, 160], "price": 110.00},
        {"group": "standard", "final": [80, 80], "file": [90, 90], "price": 87.00},
        {"group": "standard", "final": [80, 100], "file": [90, 110], "price": 92.00},
        {"group": "standard", "final": [80, 150], "file": [90, 160], "price": 120.00},
        {"group": "standard", "final": [90, 90], "file": [100, 100], "price": 95.00},
        {"group": "standard", "final": [90, 120], "file": [100, 130], "price": 105.00},
        {"group": "standard", "final": [90, 150], "file": [100, 160], "price": 120.00},
        {"group": "standard", "final": [90, 200], "file": [100, 210], "price": 170.00},
        {"group": "standard", "final": [100, 100], "file": [110, 110], "price": 105.00},
        {"group": "standard", "final": [100, 150], "file": [110, 160], "price": 135.00},
        {"group": "panoramic", "final": [50, 120], "file": [60, 130], "price": 78.00},
        {"group": "panoramic", "final": [50, 200], "file": [60, 210], "price": 105.00},
        {"group": "panoramic", "final": [60, 150], "file": [70, 160], "price": 95.00},
        {"group": "panoramic", "final": [60, 200], "file": [70, 210], "price": 105.00},
        {"group": "panoramic", "final": [65, 120], "file": [75, 130], "price": 87.00},
        {"group": "panoramic", "final": [65, 200], "file": [75, 210], "price": 125.00},
        {"group": "panoramic", "final": [70, 200], "file": [80, 210], "price": 140.00},
        {"group": "panoramic", "final": [80, 200], "file": [90, 210], "price": 155.00},
    ],
    "edit_options": [
        {
            "id": "none",
            "label": {"ca": "Arxiu preparat pel fotògraf", "es": "Archivo preparado por el fotógrafo"},
            "description": {
                "ca": "El fotògraf entrega l'arxiu final amb els 5 cm per costat ja resolts.",
                "es": "El fotógrafo entrega el archivo final con los 5 cm por lado ya resueltos.",
            },
            "price": 0.0,
            "includes_preview": False,
        },
        {
            "id": "extend_only",
            "label": {"ca": "Ampliar llenç", "es": "Ampliar lienzo"},
            "description": {
                "ca": "Afegim els 5 cm per costat per al muntatge sobre bastidor.",
                "es": "Añadimos los 5 cm por lado para el montaje sobre bastidor.",
            },
            "price": 2.0,
            "includes_preview": False,
        },
        {
            "id": "extend_quality",
            "label": {"ca": "Ampliar i adaptar qualitat", "es": "Ampliar y adaptar calidad"},
            "description": {
                "ca": "Extensió del llenç amb ajust bàsic per a fotografies amb menys qualitat.",
                "es": "Extensión del lienzo con ajuste básico para fotografías con menos calidad.",
            },
            "price": 5.0,
            "includes_preview": False,
        },
        {
            "id": "full_retouch",
            "label": {"ca": "Retoc complet", "es": "Retoque completo"},
            "description": {
                "ca": "Inclou marges, millora de qualitat, neteja d'elements i prova prèvia sense cost. Si la imatge és complexa, s'avisarà abans.",
                "es": "Incluye márgenes, mejora de calidad, limpieza de elementos y prueba previa sin coste. Si la imagen es compleja, se avisará antes.",
            },
            "price": 15.0,
            "includes_preview": True,
        },
    ],
}

COMMERCIAL_MARGIN_PROFILES = [
    {
        "id": "default",
        "name": {"ca": "Client general", "es": "Cliente general"},
        "description": {
            "ca": "Perfil base per a consulta ràpida de PVP.",
            "es": "Perfil base para consulta rápida de PVP.",
        },
        "margins": {
            "canvas": 35.0,
            "prints": 30.0,
            "albums": 40.0,
            "foam": 32.0,
        },
    },
    {
        "id": "premium",
        "name": {"ca": "Client premium", "es": "Cliente premium"},
        "description": {
            "ca": "Perfil amb més marge per a treballs més cuidats.",
            "es": "Perfil con más margen para trabajos más cuidados.",
        },
        "margins": {
            "canvas": 45.0,
            "prints": 38.0,
            "albums": 48.0,
            "foam": 40.0,
        },
    },
]

PRINT_PRODUCTS_CONFIG = {
    "papers": [
        {
            "id": "lustre",
            "label": {"ca": "Paper fotogràfic Lustre", "es": "Papel fotográfico Lustre"},
            "description": {
                "ca": "Còpia impresa en paper Lustre a la mida que el client necessiti.",
                "es": "Copia impresa en papel Lustre a la medida que el cliente necesite.",
            },
        },
        {
            "id": "silk",
            "label": {"ca": "Paper fotogràfic Silk", "es": "Papel fotográfico Silk"},
            "description": {
                "ca": "Còpia impresa en paper Silk per a treballs que demanen un acabat diferent.",
                "es": "Copia impresa en papel Silk para trabajos que requieren un acabado distinto.",
            },
        },
    ],
    "build_options": [
        {
            "id": "print_only",
            "label": {"ca": "Només impressió", "es": "Solo impresión"},
            "summary": {
                "ca": "Còpia impresa en Lustre o Silk sense suport addicional.",
                "es": "Copia impresa en Lustre o Silk sin soporte adicional.",
            },
        },
        {
            "id": "laminate_only",
            "label": {"ca": "Afegir només laminat", "es": "Añadir solo laminado"},
            "summary": {
                "ca": "Aplicar laminat sobre la fotografia impresa quan ens passis la tarifa.",
                "es": "Aplicar laminado sobre la fotografía impresa cuando nos pases la tarifa.",
            },
        },
        {
            "id": "foam_only",
            "label": {"ca": "Només foam", "es": "Solo foam"},
            "summary": {
                "ca": "Muntatge sobre foam, incloent-hi el cas en què el client porta la imatge ja impresa.",
                "es": "Montaje sobre foam, incluyendo el caso en que el cliente trae la imagen ya impresa.",
            },
        },
        {
            "id": "laminate_foam",
            "label": {"ca": "Laminat + foam", "es": "Laminado + foam"},
            "summary": {
                "ca": "Acabat combinat per a impressions que han d'anar protegides i muntades.",
                "es": "Acabado combinado para impresiones que tienen que ir protegidas y montadas.",
            },
        },
        {
            "id": "without_print",
            "label": {"ca": "Sense fotografia impresa", "es": "Sin fotografía impresa"},
            "summary": {
                "ca": "El client porta la imatge i només necessita el suport o l'acabat final.",
                "es": "El cliente trae la imagen y solo necesita el soporte o acabado final.",
            },
        },
    ],
}


def get_lang():
    return session.get("lang", "ca")


@app.context_processor
def inject_globals():
    return {
        "current_year": datetime.now().year,
        "CALC_ENTRY_URL": url_for("calculadora"),
    }


def normalize_calc_service(value):
    value = (value or "").strip().lower().replace("-", "_")
    return value if value in CALC_SERVICE_CONFIG else "general"


def get_calc_service(value, lang=None):
    lang = lang or get_lang()
    key = normalize_calc_service(value)
    config = CALC_SERVICE_CONFIG[key]
    return {
        "key": key,
        "subject": config["subject"],
        "label": config["label"].get(lang, config["label"]["ca"]),
    }


def build_calc_login_url(service=None, lang=None, source="web"):
    lang = lang or get_lang()
    service = normalize_calc_service(service)
    query = {
        "source": source,
        "lang": lang,
    }
    if service != "general":
        query["service"] = service
    return f"{CALC_URL.rstrip('/')}?{urlencode(query)}"


def build_calc_request_url(service=None):
    calc_service = get_calc_service(service)
    params = {
        "pro": 1,
        "subject": calc_service["subject"],
    }
    if calc_service["key"] != "general":
        params["service"] = calc_service["key"]
    return url_for("contacte", **params)


def build_contact_prefill():
    lang = get_lang()
    requested_subject = (request.args.get("subject") or "").strip()
    calc_service = get_calc_service(request.args.get("service"), lang)

    is_professional = bool(request.args.get("pro"))
    subject = requested_subject or ("pro_access" if is_professional else "photo_print")
    if not requested_subject and is_professional:
        subject = calc_service["subject"]

    message = (request.args.get("message") or "").strip()
    if not message and is_professional:
        if lang == "ca":
            message = (
                f"Hola, voldria sol·licitar accés a la calculadora professional per treballar "
                f"{calc_service['label']}. El meu perfil és: []. Web o Instagram: []. "
                "CIF/NIF: []. Productes o formats que necessito: []."
            )
        else:
            message = (
                f"Hola, me gustaría solicitar acceso a la calculadora profesional para trabajar "
                f"{calc_service['label']}. Mi perfil es: []. Web o Instagram: []. "
                "CIF/NIF: []. Productos o formatos que necesito: []."
            )

    return {
        "is_professional": is_professional,
        "subject": subject,
        "message": message,
        "service": calc_service["key"],
        "service_label": calc_service["label"],
    }


def build_calc_page_context(service=None):
    calc_service = get_calc_service(service)
    return {
        "calc_service": calc_service,
        "CALC_LOGIN_URL": build_calc_login_url(calc_service["key"]),
        "CALC_REQUEST_URL": build_calc_request_url(calc_service["key"]),
    }


def build_private_modules():
    lang = get_lang()
    modules = []
    for module in PRIVATE_MODULES:
        href = url_for(module["href"]) if module.get("href") else None
        modules.append(
            {
                "key": module["key"],
                "status": module["status"],
                "eyebrow": module["eyebrow"][lang],
                "title": module["title"][lang],
                "summary": module["summary"][lang],
                "href": href,
            }
        )
    return modules


def build_canvas_module_context():
    lang = get_lang()
    sizes = []
    for item in CANVAS_PRICING["sizes"]:
        final_width, final_height = item["final"]
        file_width, file_height = item["file"]
        sizes.append(
            {
                "id": f"{final_width}x{final_height}",
                "group": item["group"],
                "group_label": "Formats estàndard" if item["group"] == "standard" and lang == "ca" else
                               "Formatos estándar" if item["group"] == "standard" else
                               "Formats panoràmics" if lang == "ca" else "Formatos panorámicos",
                "final_label": f"{final_width} x {final_height} cm",
                "file_label": f"{file_width} x {file_height} cm",
                "price": item["price"],
                "final_width": final_width,
                "final_height": final_height,
                "file_width": file_width,
                "file_height": file_height,
            }
        )

    return {
        "canvas_pricing": {
            "vat_rate": CANVAS_PRICING["vat_rate"],
            "default_margin_percent": CANVAS_PRICING["default_margin_percent"],
            "fixed_features": {
                "frame_depth_cm": CANVAS_PRICING["fixed_features"]["frame_depth_cm"],
                "laminate_label": CANVAS_PRICING["fixed_features"]["laminate_label"][lang],
            },
            "sizes": sizes,
            "edit_options": [
                {
                    "id": item["id"],
                    "label": item["label"][lang],
                    "price": item.get("price"),
                    "description": item["description"][lang],
                    "includes_preview": item["includes_preview"],
                }
                for item in CANVAS_PRICING["edit_options"]
            ],
        }
    }


def build_pricing_view_context():
    lang = get_lang()
    selected_profile_id = (request.args.get("pricing_profile") or "default").strip().lower()
    profile_lookup = {item["id"]: item for item in COMMERCIAL_MARGIN_PROFILES}
    selected_profile = profile_lookup.get(selected_profile_id, COMMERCIAL_MARGIN_PROFILES[0])

    return {
        "pricing_view": {
            "selected_profile_id": selected_profile["id"],
            "profiles": [
                {
                    "id": item["id"],
                    "name": item["name"][lang],
                    "description": item["description"][lang],
                    "selected": item["id"] == selected_profile["id"],
                }
                for item in COMMERCIAL_MARGIN_PROFILES
            ],
            "profile_margins": {
                item["id"]: item["margins"]
                for item in COMMERCIAL_MARGIN_PROFILES
            },
            "margins": selected_profile["margins"],
        }
    }


def build_prints_module_context():
    lang = get_lang()
    return {
        "prints_module": {
            "papers": [
                {
                    "id": item["id"],
                    "label": item["label"][lang],
                    "description": item["description"][lang],
                }
                for item in PRINT_PRODUCTS_CONFIG["papers"]
            ],
            "build_options": [
                {
                    "id": item["id"],
                    "label": item["label"][lang],
                    "summary": item["summary"][lang],
                }
                for item in PRINT_PRODUCTS_CONFIG["build_options"]
            ],
            "frames_entry_url": url_for("calculadora", service="frames"),
        }
    }


def parse_positive_int(value, default=1):
    try:
        parsed = int(str(value).strip())
    except (TypeError, ValueError):
        return default
    return parsed if parsed > 0 else default


def parse_non_negative_float(value, default=0.0):
    try:
        parsed = float(str(value).strip().replace(",", "."))
    except (TypeError, ValueError):
        return default
    return parsed if parsed >= 0 else default


def parse_bool_flag(value):
    return str(value or "").strip().lower() in {"1", "true", "yes", "on"}


def get_canvas_size_by_id(size_id):
    size_lookup = {
        f"{item['final'][0]}x{item['final'][1]}": item
        for item in CANVAS_PRICING["sizes"]
    }
    default_item = CANVAS_PRICING["sizes"][0]
    default_id = f"{default_item['final'][0]}x{default_item['final'][1]}"
    return size_lookup.get(size_id or default_id, default_item)


def get_canvas_edit_by_id(edit_id):
    edit_lookup = {item["id"]: item for item in CANVAS_PRICING["edit_options"]}
    default_item = CANVAS_PRICING["edit_options"][0]
    return edit_lookup.get(edit_id or default_item["id"], default_item)


def build_canvas_order_line(size_item, edit_item, quantity, margin_percent, show_file_size, lang):
    vat_rate = CANVAS_PRICING["vat_rate"]
    base_unit = size_item["price"]
    edit_unit = edit_item["price"]
    professional_subtotal = round((base_unit + edit_unit) * quantity, 2)
    professional_vat = round(professional_subtotal * vat_rate, 2)
    professional_total = round(professional_subtotal + professional_vat, 2)
    margin_amount = round(professional_subtotal * (margin_percent / 100), 2)
    client_subtotal = round(professional_subtotal + margin_amount, 2)
    client_vat = round(client_subtotal * vat_rate, 2)
    client_total = round(client_subtotal + client_vat, 2)

    return {
        "size_id": f"{size_item['final'][0]}x{size_item['final'][1]}",
        "final_label": f"{size_item['final'][0]} x {size_item['final'][1]} cm",
        "file_label": f"{size_item['file'][0]} x {size_item['file'][1]} cm",
        "show_file_size": show_file_size,
        "quantity": quantity,
        "edit_id": edit_item["id"],
        "edit_label": edit_item["label"][lang],
        "edit_description": edit_item["description"][lang],
        "includes_preview": edit_item["includes_preview"],
        "base_unit": base_unit,
        "edit_unit": edit_unit,
        "professional_subtotal": professional_subtotal,
        "professional_vat": professional_vat,
        "professional_total": professional_total,
        "margin_percent": margin_percent,
        "margin_amount": margin_amount,
        "client_subtotal": client_subtotal,
        "client_vat": client_vat,
        "client_total": client_total,
        "vat_rate_percent": int(vat_rate * 100),
    }


def build_canvas_order_context():
    lang = get_lang()
    size_item = get_canvas_size_by_id(request.args.get("size"))
    edit_item = get_canvas_edit_by_id(request.args.get("edit"))
    quantity = parse_positive_int(request.args.get("qty"), default=1)
    margin_percent = parse_non_negative_float(
        request.args.get("margin"),
        default=CANVAS_PRICING["default_margin_percent"],
    )
    show_file_size = parse_bool_flag(request.args.get("show_file_size"))

    primary_line = build_canvas_order_line(
        size_item=size_item,
        edit_item=edit_item,
        quantity=quantity,
        margin_percent=margin_percent,
        show_file_size=show_file_size,
        lang=lang,
    )
    secondary_line = build_canvas_order_line(
        size_item=get_canvas_size_by_id("30x40"),
        edit_item=get_canvas_edit_by_id("extend_only"),
        quantity=1,
        margin_percent=margin_percent,
        show_file_size=False,
        lang=lang,
    )
    secondary_line["reference"] = "LINE-02"
    secondary_line["is_suggested"] = True

    order_lines = [primary_line, secondary_line]
    professional_subtotal = round(sum(line["professional_subtotal"] for line in order_lines), 2)
    professional_vat = round(sum(line["professional_vat"] for line in order_lines), 2)
    professional_total = round(sum(line["professional_total"] for line in order_lines), 2)
    margin_amount = round(sum(line["margin_amount"] for line in order_lines), 2)
    client_subtotal = round(sum(line["client_subtotal"] for line in order_lines), 2)
    client_vat = round(sum(line["client_vat"] for line in order_lines), 2)
    client_total = round(sum(line["client_total"] for line in order_lines), 2)

    delivery_options = [
        {
            "id": "dropbox",
            "label": {
                "ca": "Dropbox compartit",
                "es": "Dropbox compartido",
            },
            "description": {
                "ca": "Manteniu el flux actual: carpeta compartida i referència de la comanda.",
                "es": "Mantenéis el flujo actual: carpeta compartida y referencia del pedido.",
            },
            "help": {
                "ca": "Recomanat perquè ja forma part del vostre procés.",
                "es": "Recomendado porque ya forma parte de vuestro proceso.",
            },
            "recommended": True,
        },
        {
            "id": "link",
            "label": {
                "ca": "Enllaç extern",
                "es": "Enlace externo",
            },
            "description": {
                "ca": "WeTransfer, Drive, Smash o qualsevol URL que el fotògraf vulgui enganxar.",
                "es": "WeTransfer, Drive, Smash o cualquier URL que el fotógrafo quiera pegar.",
            },
            "help": {
                "ca": "Ideal per a treballs puntuals o quan no vol usar la carpeta compartida.",
                "es": "Ideal para trabajos puntuales o cuando no quiere usar la carpeta compartida.",
            },
            "recommended": False,
        },
        {
            "id": "later",
            "label": {
                "ca": "Enviar més tard",
                "es": "Enviar más tarde",
            },
            "description": {
                "ca": "La comanda queda creada i el fitxer es pot associar després.",
                "es": "El pedido queda creado y el archivo se puede asociar después.",
            },
            "help": {
                "ca": "Útil per tancar el pressupost abans de rebre la imatge definitiva.",
                "es": "Útil para cerrar el presupuesto antes de recibir la imagen definitiva.",
            },
            "recommended": False,
        },
    ]

    selected_delivery = request.args.get("delivery") or "dropbox"
    selected_delivery = (
        selected_delivery
        if selected_delivery in {item["id"] for item in delivery_options}
        else "dropbox"
    )

    sample_clients = [
        {
            "id": "client_001",
            "name": "Marta Puig",
            "company": {
                "ca": "Sessió familiar Primavera",
                "es": "Sesión familiar Primavera",
            },
            "email": "marta@example.com",
            "phone": "+34 600 123 123",
            "city": {
                "ca": "Reus",
                "es": "Reus",
            },
            "last_order": {
                "ca": "2 comandes aquest mes",
                "es": "2 pedidos este mes",
            },
        },
        {
            "id": "client_002",
            "name": "Estudi Grau",
            "company": {
                "ca": "Reportatge d'interiors",
                "es": "Reportaje de interiores",
            },
            "email": "estudi@example.com",
            "phone": "+34 600 456 456",
            "city": {
                "ca": "Tarragona",
                "es": "Tarragona",
            },
            "last_order": {
                "ca": "Client recurrent",
                "es": "Cliente recurrente",
            },
        },
    ]
    selected_client_id = request.args.get("client") or sample_clients[0]["id"]

    recent_orders = [
        {
            "reference": "RR-24031",
            "date": "28/03/2026",
            "status": {"ca": "Pressupost enviat", "es": "Presupuesto enviado"},
            "total": 186.34,
        },
        {
            "reference": "RR-24018",
            "date": "12/03/2026",
            "status": {"ca": "En producció", "es": "En producción"},
            "total": 94.38,
        },
        {
            "reference": "RR-23977",
            "date": "20/02/2026",
            "status": {"ca": "Lliurat", "es": "Entregado"},
            "total": 312.18,
        },
    ]

    return {
        "generated_at": datetime.now(),
        "lines": [
            {
                **line,
                "reference": f"LINE-{index:02d}",
                "is_suggested": line.get("is_suggested", False),
            }
            for index, line in enumerate(order_lines, start=1)
        ],
        "line_count": len(order_lines),
        "quantity_total": sum(line["quantity"] for line in order_lines),
        "professional_subtotal": professional_subtotal,
        "professional_vat": professional_vat,
        "professional_total": professional_total,
        "margin_percent": margin_percent,
        "margin_amount": margin_amount,
        "client_subtotal": client_subtotal,
        "client_vat": client_vat,
        "client_total": client_total,
        "vat_rate_percent": int(CANVAS_PRICING["vat_rate"] * 100),
        "delivery_options": [
            {
                "id": item["id"],
                "label": item["label"][lang],
                "description": item["description"][lang],
                "help": item["help"][lang],
                "recommended": item["recommended"],
                "selected": item["id"] == selected_delivery,
            }
            for item in delivery_options
        ],
        "selected_delivery": selected_delivery,
        "clients": [
            {
                "id": item["id"],
                "name": item["name"],
                "company": item["company"][lang],
                "email": item["email"],
                "phone": item["phone"],
                "city": item["city"][lang],
                "last_order": item["last_order"][lang],
                "selected": item["id"] == selected_client_id,
            }
            for item in sample_clients
        ],
        "selected_client_id": selected_client_id,
        "recent_orders": [
            {
                "reference": item["reference"],
                "date": item["date"],
                "status": item["status"][lang],
                "total": item["total"],
            }
            for item in recent_orders
        ],
    }


def clean_profile_type(value):
    allowed = {"professional", "studio", "gallery", "association"}
    value = (value or "").strip().lower()
    return value if value in allowed else "professional"


def normalize_subject(value):
    mapping = {
        "photo_print": "Impresión fotográfica",
        "albums": "Álbumes fotográficos",
        "frames": "Enmarcación a medida",
        "canvas": "Impresión de lienzos",
        "fine_art": "Impresión Hahnemühle / fine art",
        "pro_access": "Acceso al área profesional",
        "association_exhibition": "Asociación o exposición fotográfica",
        "retouch": "Retoque o restauración",
        "other": "Otra consulta",
    }
    normalized = (value or "").strip()
    return mapping.get(normalized, normalized or "Consulta web")


def is_professional_request(subject, profile_type, explicit_flag=False):
    if explicit_flag:
        return True

    normalized = (subject or "").strip().lower()
    if profile_type in {"professional", "studio", "gallery", "association"}:
        return any(token in normalized for token in ("profession", "asoci", "associ", "expos"))

    return any(token in normalized for token in ("profession", "asoci", "associ", "expos"))


def build_contact_message(message, professional_data):
    if not professional_data.get("is_professional"):
        return message

    details = [
        "",
        "---",
        "Dades professionals",
        f"Perfil: {professional_data.get('profile_type') or '-'}",
        f"Empresa: {professional_data.get('business_name') or '-'}",
        f"Web: {professional_data.get('web_url') or '-'}",
        f"Instagram: {professional_data.get('instagram') or '-'}",
        f"CIF/NIF: {professional_data.get('fiscal_id') or '-'}",
    ]
    return "\n".join([message.strip(), *details]).strip()


def sync_professional_signup(name, email, phone, subject, message, professional_data):
    if not professional_data.get("is_professional"):
        return {"attempted": False, "status": "skipped"}

    if not CALC_SIGNUP_URL or not CALC_SIGNUP_TOKEN:
        return {"attempted": False, "status": "not_configured"}

    payload = {
        "name": name,
        "email": email,
        "phone": phone,
        "subject": subject,
        "message": message,
        "profile_type": professional_data.get("profile_type"),
        "business_name": professional_data.get("business_name"),
        "web_url": professional_data.get("web_url"),
        "instagram": professional_data.get("instagram"),
        "fiscal_id": professional_data.get("fiscal_id"),
    }

    req = urllib_request.Request(
        CALC_SIGNUP_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "X-Signup-Token": CALC_SIGNUP_TOKEN,
        },
        method="POST",
    )

    try:
        with urllib_request.urlopen(req, timeout=12) as response:
            body = response.read().decode("utf-8")
        return {"attempted": True, "status": "ok", "response": body}
    except urllib_error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="ignore")
        return {"attempted": True, "status": "http_error", "code": exc.code, "detail": detail}
    except Exception as exc:
        return {"attempted": True, "status": "error", "detail": str(exc)}


def send_contact_email(name, email, phone, subject, message):
    if not SMTP_HOST:
        return False

    body = (
        "Nou missatge des del formulari web de Reus Revela.\n\n"
        f"Nom: {name}\n"
        f"Email: {email}\n"
        f"Telèfon: {phone or '-'}\n"
        f"Assumpte: {subject}\n\n"
        "Missatge:\n"
        f"{message}\n"
    )

    msg = MIMEText(body, _charset="utf-8")
    msg["Subject"] = f"[Web Reus Revela] {subject}"
    msg["From"] = SMTP_FROM
    msg["To"] = CONTACT_EMAIL
    msg["Reply-To"] = email

    with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=15) as server:
        if SMTP_USE_TLS:
            server.starttls()
        if SMTP_USER and SMTP_PASSWORD:
            server.login(SMTP_USER, SMTP_PASSWORD)
        server.send_message(msg)

    return True


@app.route("/")
def index():
    return render_template("index.html", lang=get_lang(), CALC_URL=CALC_URL)


@app.route("/serveis")
def serveis():
    return render_template("serveis.html", lang=get_lang(), CALC_URL=CALC_URL)


@app.route("/albumes-fotograficos")
def albumes_fotograficos():
    return render_template("albumes_fotograficos.html", lang=get_lang(), CALC_URL=CALC_URL)


@app.route("/marcos-a-medida")
def marcos_a_medida():
    return render_template("marcos_a_medida.html", lang=get_lang(), CALC_URL=CALC_URL)


@app.route("/impresion-lienzos")
def impresion_lienzos():
    return render_template("impresion_lienzos.html", lang=get_lang(), CALC_URL=CALC_URL)


@app.route("/impresion-hahnemuhle")
def impresion_hahnemuhle():
    return render_template("impresion_hahnemuhle.html", lang=get_lang(), CALC_URL=CALC_URL)


@app.route("/sobre")
def sobre():
    return render_template("sobre.html", lang=get_lang(), CALC_URL=CALC_URL)


@app.route("/contacte")
def contacte():
    return render_template(
        "contacte.html",
        lang=get_lang(),
        CALC_URL=CALC_URL,
        contact_defaults=build_contact_prefill(),
    )


@app.route("/professionals")
def professionals():
    return render_template(
        "professionals.html",
        lang=get_lang(),
        CALC_URL=CALC_URL,
        **build_calc_page_context(request.args.get("service")),
    )


@app.route("/calculadora")
def calculadora():
    return render_template(
        "calculadora.html",
        lang=get_lang(),
        CALC_URL=CALC_URL,
        **build_calc_page_context(request.args.get("service")),
    )


@app.route("/area-privada")
def area_privada():
    return render_template(
        "area_privada_v2.html",
        lang=get_lang(),
        private_modules=build_private_modules(),
    )


@app.route("/area-privada/tarifari")
def area_privada_tarifari():
    return render_template(
        "area_privada_tarifari_v2.html",
        lang=get_lang(),
        private_modules=build_private_modules(),
        **build_canvas_module_context(),
        **build_pricing_view_context(),
    )


@app.route("/area-privada/lienzos")
def area_privada_lienzos():
    return render_template(
        "area_privada_lienzos_v3.html",
        lang=get_lang(),
        private_modules=build_private_modules(),
        **build_canvas_module_context(),
    )


@app.route("/area-privada/impresiones")
def area_privada_impresions():
    return render_template(
        "area_privada_impresions.html",
        lang=get_lang(),
        private_modules=build_private_modules(),
        **build_prints_module_context(),
    )


@app.route("/area-privada/marcos")
def area_privada_marcos():
    return render_template(
        "area_privada_marcos.html",
        lang=get_lang(),
        private_modules=build_private_modules(),
        calc_service=get_calc_service("frames"),
        CALC_LOGIN_URL=build_calc_login_url("frames", source="private_area"),
        CALC_REQUEST_URL=build_calc_request_url("frames"),
    )


@app.route("/area-privada/comanda")
def area_privada_comanda():
    return render_template(
        "area_privada_comanda_v2.html",
        lang=get_lang(),
        private_modules=build_private_modules(),
        order_data=build_canvas_order_context(),
    )


@app.route("/sitemap.xml")
def sitemap():
    pages = [
        "index",
        "serveis",
        "albumes_fotograficos",
        "marcos_a_medida",
        "impresion_lienzos",
        "impresion_hahnemuhle",
        "sobre",
        "contacte",
        "professionals",
        "calculadora",
        "area_privada",
        "area_privada_tarifari",
        "area_privada_lienzos",
        "area_privada_impresions",
        "area_privada_marcos",
        "area_privada_comanda",
    ]

    urls = []
    for endpoint in pages:
        urls.append(
            f"""
  <url>
    <loc>{url_for(endpoint, _external=True)}</loc>
    <changefreq>weekly</changefreq>
    <priority>{"1.0" if endpoint == "index" else "0.8"}</priority>
  </url>"""
        )

    xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
{''.join(urls)}
</urlset>
"""
    return Response(xml, mimetype="application/xml")


@app.route("/robots.txt")
def robots():
    content = f"""User-agent: *
Allow: /

Sitemap: {url_for('sitemap', _external=True)}
"""
    return Response(content, mimetype="text/plain")


@app.route("/lang/<code>")
def set_lang(code):
    if code in ("ca", "es"):
        session["lang"] = code
    return redirect(request.referrer or url_for("index"))


@app.route("/api/contacte", methods=["POST"])
def api_contacte():
    data = request.get_json(silent=True) or {}

    name = data.get("nom", "").strip()
    email = data.get("email", "").strip()
    phone = data.get("telefon", "").strip()
    subject = normalize_subject(data.get("assumpte"))
    message = data.get("missatge", "").strip()
    explicit_professional_flag = str(data.get("es_professional", "")).lower() == "true"
    profile_type = clean_profile_type(data.get("tipus_professional"))
    professional_data = {
        "is_professional": is_professional_request(subject, profile_type, explicit_professional_flag),
        "profile_type": profile_type,
        "business_name": data.get("nom_empresa", "").strip(),
        "web_url": data.get("web_url", "").strip(),
        "instagram": data.get("instagram", "").strip(),
        "fiscal_id": data.get("fiscal_id", "").strip(),
    }
    full_message = build_contact_message(message, professional_data)

    if not name or not email or not message:
        return jsonify({"ok": False, "error": "missing_fields"}), 400

    if "@" not in email or "." not in email.split("@")[-1]:
        return jsonify({"ok": False, "error": "invalid_email"}), 400

    app.logger.info(
        "Contacte web: %s <%s> | %s | %s",
        name,
        email,
        subject,
        (full_message[:120] + "...") if len(full_message) > 120 else full_message,
    )

    email_sent = False
    try:
        email_sent = send_contact_email(name, email, phone, subject, full_message)
    except Exception:
        app.logger.exception("No s'ha pogut enviar el correu del formulari de contacte")

    professional_signup = sync_professional_signup(name, email, phone, subject, full_message, professional_data)
    if professional_signup.get("status") not in {"skipped", "not_configured", "ok"}:
        app.logger.warning("Professional signup sync issue: %s", professional_signup)

    return jsonify({"ok": True, "email_sent": email_sent, "professional_signup": professional_signup})


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5001)
