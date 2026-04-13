import json
import os
import re
import secrets
import smtplib
from datetime import datetime, timedelta
from pathlib import Path
from email.mime.text import MIMEText
from urllib import error as urllib_error
from urllib import request as urllib_request
from urllib.parse import urlencode

from flask import Flask, Response, jsonify, redirect, render_template, request, session, url_for

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY") or "reusrevela-private-area-session-v1"
app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(days=30)
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"

CALC_URL = os.environ.get("CALC_URL", "https://calculadora.reusrevela.cat")
CALC_SIGNUP_URL = os.environ.get("CALC_SIGNUP_URL", f"{CALC_URL.rstrip('/')}/api/public/professional-signup")
CALC_SIGNUP_TOKEN = os.environ.get("CALC_SIGNUP_TOKEN", "")
CALC_BRIDGE_LOGIN_URL = os.environ.get("CALC_BRIDGE_LOGIN_URL", f"{CALC_URL.rstrip('/')}/api/public/bridge-login")
CALC_BRIDGE_TOKEN = os.environ.get("CALC_BRIDGE_TOKEN", "")
CONTACT_EMAIL = os.environ.get("CONTACT_EMAIL", "reusrevela@gmail.com")
SMTP_HOST = os.environ.get("SMTP_HOST")
SMTP_PORT = int(os.environ.get("SMTP_PORT", "587"))
SMTP_USER = os.environ.get("SMTP_USER")
SMTP_PASSWORD = os.environ.get("SMTP_PASSWORD")
SMTP_FROM = os.environ.get("SMTP_FROM", CONTACT_EMAIL)
SMTP_USE_TLS = os.environ.get("SMTP_USE_TLS", "true").lower() != "false"
PRIVATE_AREA_DB_PATH = os.environ.get("PRIVATE_AREA_DB_PATH", os.path.join(os.path.dirname(__file__), "private_area_store.json"))
CANVAS_SIZE_IMAGE_DIR = Path(app.static_folder) / "img" / "lienzos" / "by-size"

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
        "key": "settings",
        "status": "ready",
        "eyebrow": {"ca": "Base comuna", "es": "Base común"},
        "title": {"ca": "Ajustos", "es": "Ajustes"},
        "summary": {
            "ca": "Revisa i toca els marges comercials des d'un sol punt.",
            "es": "Revisa y toca los márgenes comerciales desde un solo punto.",
        },
        "href": "area_privada_ajustos",
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


FRAME_ORDER_FIELDS = [
    "quote_ref",
    "client_name",
    "client_phone",
    "piece_type",
    "piece_width",
    "piece_height",
    "final_size",
    "frame_main",
    "frame_pre",
    "glass",
    "interior",
    "print_label",
    "total",
    "pending",
    "deposit",
    "notes",
]

DEFAULT_COMMERCIAL_SETTINGS = {
    "general": 35.0,
    "frames": 35.0,
    "canvas": 35.0,
    "prints": 30.0,
    "albums": 40.0,
    "foam": 35.0,
    "laminate_foam": 35.0,
    "fine_art": 38.0,
}


CANVAS_DRAFT_FIELDS = [
    "size",
    "qty",
    "edit",
    "margin",
    "show_file_size",
]


def _empty_private_area_store():
    return {
        "frames_order_drafts": {},
        "canvas_order_drafts": {},
        "clients": {},
        "commercial_settings": dict(DEFAULT_COMMERCIAL_SETTINGS),
    }


def get_private_area_db():
    return PRIVATE_AREA_DB_PATH



def init_private_area_db():
    try:
        store_path = Path(PRIVATE_AREA_DB_PATH)
        if store_path.parent:
            store_path.parent.mkdir(parents=True, exist_ok=True)
        if not store_path.exists():
            store_path.write_text(
                json.dumps(_empty_private_area_store(), ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        return True
    except OSError:
        return False



def _normalize_frame_order_payload(payload=None):
    payload = payload if isinstance(payload, dict) else {}
    normalized = {}
    for key in FRAME_ORDER_FIELDS:
        value = payload.get(key, "")
        normalized[key] = "" if value is None else str(value).strip()
    return normalized


def _normalize_canvas_draft_payload(payload=None):
    payload = payload if isinstance(payload, dict) else {}
    normalized = {}
    for key in CANVAS_DRAFT_FIELDS:
        value = payload.get(key, "")
        normalized[key] = "" if value is None else str(value).strip()
    return normalized



def _format_saved_timestamp(value):
    if not value:
        return ""
    try:
        dt = datetime.fromisoformat(str(value))
    except ValueError:
        return str(value)
    return dt.strftime("%d/%m/%Y %H:%M")



def _read_private_area_store():
    if not init_private_area_db():
        return _empty_private_area_store()
    store_path = Path(PRIVATE_AREA_DB_PATH)
    try:
        data = json.loads(store_path.read_text(encoding="utf-8") or "{}")
    except (OSError, ValueError, TypeError):
        data = {}
    if not isinstance(data, dict):
        data = {}
    drafts = data.get("frames_order_drafts")
    if not isinstance(drafts, dict):
        data["frames_order_drafts"] = {}
    canvas_drafts = data.get("canvas_order_drafts")
    if not isinstance(canvas_drafts, dict):
        data["canvas_order_drafts"] = {}
    clients = data.get("clients")
    if not isinstance(clients, dict):
        data["clients"] = {}
    settings = data.get("commercial_settings")
    if not isinstance(settings, dict):
        settings = {}
    data["commercial_settings"] = {
        key: parse_non_negative_float(settings.get(key), default=default_value)
        for key, default_value in DEFAULT_COMMERCIAL_SETTINGS.items()
    }
    return data



def _write_private_area_store(data):
    if not init_private_area_db():
        return False
    store_path = Path(PRIVATE_AREA_DB_PATH)
    try:
        store_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        return True
    except OSError:
        return False


def get_private_commercial_settings():
    store = _read_private_area_store()
    settings = store.get("commercial_settings", {})
    normalized = {
        key: parse_non_negative_float(settings.get(key), default=default_value)
        for key, default_value in DEFAULT_COMMERCIAL_SETTINGS.items()
    }
    normalized["foam"] = normalized["general"]
    normalized["laminate_foam"] = normalized["general"]
    return normalized


def save_private_commercial_settings(payload=None):
    payload = payload or {}
    store = _read_private_area_store()
    normalized = {
        key: parse_non_negative_float(payload.get(key), default=default_value)
        for key, default_value in DEFAULT_COMMERCIAL_SETTINGS.items()
    }
    normalized["foam"] = normalized["general"]
    normalized["laminate_foam"] = normalized["general"]
    store["commercial_settings"] = normalized
    _write_private_area_store(store)
    return store["commercial_settings"]



def _draft_sort_key(item):
    return item.get("updated_at") if isinstance(item, dict) else ""



def _store_to_saved_order(row):
    row = row if isinstance(row, dict) else {}
    return {
        "draft_id": str(row.get("draft_id", "") or ""),
        "quote_ref": str(row.get("quote_ref", "") or ""),
        "client_name": str(row.get("client_name", "") or ""),
        "final_size_label": str(row.get("final_size_label", "") or ""),
        "total": float(row.get("total") or 0.0),
        "updated_at": row.get("updated_at", ""),
        "updated_at_label": _format_saved_timestamp(row.get("updated_at", "")),
    }



def list_saved_frames_orders(limit=8):
    drafts = _read_private_area_store().get("frames_order_drafts", {})
    rows = [row for row in drafts.values() if isinstance(row, dict)]
    rows = sorted(rows, key=_draft_sort_key, reverse=True)
    return [_store_to_saved_order(row) for row in rows[: max(int(limit or 1), 1)]]



def get_saved_frames_order(draft_id):
    draft_id = str(draft_id or "").strip()
    if not draft_id:
        return None

    drafts = _read_private_area_store().get("frames_order_drafts", {})
    row = drafts.get(draft_id)
    if not isinstance(row, dict):
        return None
    return _normalize_frame_order_payload(row.get("payload") or {})



def save_frames_order_draft(payload):
    normalized = _normalize_frame_order_payload(payload)
    draft_id = str((payload or {}).get("draft_id") or "").strip() or secrets.token_urlsafe(8)
    updated_at = datetime.utcnow().isoformat(timespec="seconds")
    total = parse_non_negative_float(normalized.get("total"), default=0.0)

    store = _read_private_area_store()
    drafts = store.setdefault("frames_order_drafts", {})
    drafts[draft_id] = {
        "draft_id": draft_id,
        "quote_ref": normalized.get("quote_ref", ""),
        "client_name": normalized.get("client_name", ""),
        "client_phone": normalized.get("client_phone", ""),
        "final_size_label": normalized.get("final_size", ""),
        "total": total,
        "updated_at": updated_at,
        "payload": normalized,
    }
    if not _write_private_area_store(store):
        raise RuntimeError("private_area_db_unavailable")
    return {
        "draft_id": draft_id,
        "updated_at": updated_at,
        "payload": normalized,
    }


def _store_to_saved_canvas_draft(row):
    row = row if isinstance(row, dict) else {}
    return {
        "draft_id": str(row.get("draft_id", "") or ""),
        "size_label": str(row.get("size_label", "") or ""),
        "quantity": parse_positive_int(row.get("quantity"), default=1),
        "edit_label": str(row.get("edit_label", "") or ""),
        "updated_at": row.get("updated_at", ""),
        "updated_at_label": _format_saved_timestamp(row.get("updated_at", "")),
    }


def list_saved_canvas_drafts(limit=8):
    drafts = _read_private_area_store().get("canvas_order_drafts", {})
    rows = [row for row in drafts.values() if isinstance(row, dict)]
    rows = sorted(rows, key=_draft_sort_key, reverse=True)
    return [_store_to_saved_canvas_draft(row) for row in rows[: max(int(limit or 1), 1)]]


def get_saved_canvas_draft(draft_id):
    draft_id = str(draft_id or "").strip()
    if not draft_id:
        return None

    drafts = _read_private_area_store().get("canvas_order_drafts", {})
    row = drafts.get(draft_id)
    if not isinstance(row, dict):
        return None
    return _normalize_canvas_draft_payload(row.get("payload") or {})


def save_canvas_draft(payload):
    normalized = _normalize_canvas_draft_payload(payload)
    draft_id = str((payload or {}).get("draft_id") or "").strip() or secrets.token_urlsafe(8)
    updated_at = datetime.utcnow().isoformat(timespec="seconds")

    size_item = get_canvas_size_by_id(normalized.get("size"))
    edit_item = get_canvas_edit_by_id(normalized.get("edit"))
    lang = (payload or {}).get("lang") or get_lang()
    quantity = parse_positive_int(normalized.get("qty"), default=1)

    store = _read_private_area_store()
    drafts = store.setdefault("canvas_order_drafts", {})
    drafts[draft_id] = {
        "draft_id": draft_id,
        "size_label": f"{size_item['final'][0]} x {size_item['final'][1]} cm",
        "quantity": quantity,
        "edit_label": edit_item["label"][lang],
        "updated_at": updated_at,
        "payload": normalized,
    }
    if not _write_private_area_store(store):
        raise RuntimeError("private_area_db_unavailable")
    return {
        "draft_id": draft_id,
        "updated_at": updated_at,
        "payload": normalized,
    }


def _slugify_client_fragment(value):
    safe = "".join(ch.lower() if ch.isalnum() else "-" for ch in str(value or "").strip())
    safe = "-".join(part for part in safe.split("-") if part)
    return safe[:40]


def _normalize_private_client_payload(payload=None):
    payload = payload if isinstance(payload, dict) else {}
    return {
        "name": str(payload.get("name") or "").strip(),
        "company": str(payload.get("company") or "").strip(),
        "email": str(payload.get("email") or "").strip(),
        "phone": str(payload.get("phone") or "").strip(),
        "city": str(payload.get("city") or "").strip(),
        "notes": str(payload.get("notes") or "").strip(),
        "source": str(payload.get("source") or "").strip() or "private_area",
        "last_order_ref": str(payload.get("last_order_ref") or "").strip(),
    }


def _coerce_private_client_row(payload=None, fallback_id=""):
    payload = payload if isinstance(payload, dict) else {}
    client_id = str(payload.get("id") or fallback_id or "").strip()
    order_count_value = payload.get("order_count")
    try:
        order_count = int(str(order_count_value).strip())
    except (TypeError, ValueError):
        order_count = 0
    if order_count < 0:
        order_count = 0
    return {
        "id": client_id,
        "name": str(payload.get("name") or "").strip(),
        "company": str(payload.get("company") or "").strip(),
        "email": str(payload.get("email") or "").strip(),
        "phone": str(payload.get("phone") or "").strip(),
        "city": str(payload.get("city") or "").strip(),
        "notes": str(payload.get("notes") or "").strip(),
        "source": str(payload.get("source") or "").strip() or "private_area",
        "last_order_ref": str(payload.get("last_order_ref") or "").strip(),
        "updated_at": str(payload.get("updated_at") or "").strip(),
        "created_at": str(payload.get("created_at") or "").strip(),
        "order_count": order_count,
    }


def _client_sort_key(item):
    return item.get("updated_at") or ""


def save_private_client(payload, client_id=""):
    normalized = _normalize_private_client_payload(payload)
    if not normalized["name"] and not normalized["phone"] and not normalized["email"]:
        raise ValueError("missing_client_identity")

    client_id = str(client_id or "").strip()
    if not client_id:
        base_name = _slugify_client_fragment(normalized["name"] or normalized["email"] or normalized["phone"] or "client")
        base_phone = _slugify_client_fragment(normalized["phone"] or "sense-telefon")
        client_id = f"client_{base_name}_{base_phone}"[:80]

    updated_at = datetime.utcnow().isoformat(timespec="seconds")
    store = _read_private_area_store()
    clients = store.setdefault("clients", {})
    existing = _coerce_private_client_row(clients.get(client_id), fallback_id=client_id)
    order_count = existing.get("order_count", 0)
    clients[client_id] = {
        "id": client_id,
        "name": normalized["name"] or existing.get("name", ""),
        "company": normalized["company"] or existing.get("company", ""),
        "email": normalized["email"] or existing.get("email", ""),
        "phone": normalized["phone"] or existing.get("phone", ""),
        "city": normalized["city"] or existing.get("city", ""),
        "notes": normalized["notes"] or existing.get("notes", ""),
        "source": normalized["source"] or existing.get("source", "private_area"),
        "last_order_ref": normalized["last_order_ref"] or existing.get("last_order_ref", ""),
        "updated_at": updated_at,
        "created_at": existing.get("created_at") or updated_at,
        "order_count": order_count,
    }
    if not _write_private_area_store(store):
        raise RuntimeError("private_area_db_unavailable")
    return clients[client_id]


def list_private_clients(limit=12):
    clients = _read_private_area_store().get("clients", {})
    rows = []
    for key, row in clients.items():
        normalized = _coerce_private_client_row(row, fallback_id=key)
        if not normalized["id"]:
            continue
        rows.append(normalized)
    rows = sorted(rows, key=_client_sort_key, reverse=True)
    return rows[: max(int(limit or 1), 1)]


def get_private_client(client_id):
    client_id = str(client_id or "").strip()
    if not client_id:
        return None
    row = _read_private_area_store().get("clients", {}).get(client_id)
    normalized = _coerce_private_client_row(row, fallback_id=client_id)
    return normalized if normalized["id"] else None


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


def build_direct_calc_url(service=None, lang=None, source="web"):
    lang = lang or get_lang()
    service = normalize_calc_service(service)
    query = {
        "source": source,
        "lang": lang,
    }
    if service == "frames":
        if source == "private_area":
            settings = get_private_commercial_settings()
            query["commercial_margin"] = parse_non_negative_float(
                settings.get("frames"),
                default=DEFAULT_COMMERCIAL_SETTINGS["frames"],
            )
            query["commercial_print_margin"] = parse_non_negative_float(
                settings.get("prints"),
                default=DEFAULT_COMMERCIAL_SETTINGS["prints"],
            )
        return f"{CALC_URL.rstrip('/')}/calculadora?{urlencode(query)}"
    if service != "general":
        query["service"] = service
    return f"{CALC_URL.rstrip('/')}?{urlencode(query)}"


def build_calc_login_url(service=None, lang=None, source="web"):
    lang = lang or get_lang()
    service = normalize_calc_service(service)
    params = {
        "lang": lang,
        "source": source,
    }
    if service != "general":
        params["service"] = service
    return url_for("area_privada_acces", **params)


def build_calc_target_path(service=None):
    service = normalize_calc_service(service)
    if service == "frames":
        return "/calculadora"
    return "/"


def permanent_redirect_to(endpoint, **values):
    params = request.args.to_dict(flat=True)
    params.update(values)
    return redirect(url_for(endpoint, **params), code=301)


def get_bridge_error_message(code, lang=None):
    lang = lang or get_lang()
    messages = {
        "invalid_credentials": {
            "ca": "No hem pogut validar l'usuari o la contrasenya. Revisa les dades i torna-ho a provar.",
            "es": "No hemos podido validar el usuario o la contrasena. Revisa los datos y vuelve a intentarlo.",
        },
        "pending": {
            "ca": "El teu acces encara esta pendent de validacio. Si ho necessites, t'ho revisem.",
            "es": "Tu acceso todavia esta pendiente de validacion. Si lo necesitas, lo revisamos contigo.",
        },
        "blocked": {
            "ca": "Aquest acces esta bloquejat. Contacta amb nosaltres i ho revisem.",
            "es": "Este acceso esta bloqueado. Contacta con nosotros y lo revisamos.",
        },
        "bridge_not_configured": {
            "ca": "L'acces unificat encara no esta configurat del tot. Pots entrar igualment a la calculadora classica.",
            "es": "El acceso unificado todavia no esta configurado del todo. Puedes entrar igualmente en la calculadora clasica.",
        },
        "network_error": {
            "ca": "No hem pogut connectar amb la calculadora ara mateix. Torna-ho a provar d'aqui un moment.",
            "es": "No hemos podido conectar con la calculadora ahora mismo. Vuelve a intentarlo dentro de un momento.",
        },
        "forbidden": {
            "ca": "L'acces unificat no esta disponible ara mateix. Pots entrar des del login habitual.",
            "es": "El acceso unificado no esta disponible ahora mismo. Puedes entrar desde el login habitual.",
        },
        "missing_credentials": {
            "ca": "Introdueix l'usuari i la contrasenya per continuar.",
            "es": "Introduce el usuario y la contrasena para continuar.",
        },
        "unknown": {
            "ca": "No s'ha pogut completar l'acces. Torna-ho a provar o entra des del login habitual.",
            "es": "No se ha podido completar el acceso. Vuelve a intentarlo o entra desde el login habitual.",
        },
    }
    return messages.get(code, messages["unknown"]).get(lang, messages["unknown"]["ca"])


def request_calc_bridge_login(username, password, service=None, lang=None, source="web"):
    if not CALC_BRIDGE_LOGIN_URL or not CALC_BRIDGE_TOKEN:
        return {"ok": False, "error": "bridge_not_configured"}

    payload = {
        "username": (username or "").strip().lower(),
        "password": password or "",
        "service": normalize_calc_service(service),
        "lang": lang or get_lang(),
        "source": source or "web",
        "next": build_calc_target_path(service),
    }
    req = urllib_request.Request(
        CALC_BRIDGE_LOGIN_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "X-Bridge-Token": CALC_BRIDGE_TOKEN,
        },
        method="POST",
    )
    try:
        with urllib_request.urlopen(req, timeout=12) as resp:
            body = resp.read().decode("utf-8")
            return json.loads(body or "{}")
    except urllib_error.HTTPError as exc:
        try:
            body = exc.read().decode("utf-8")
            data = json.loads(body or "{}")
            if isinstance(data, dict) and data.get("error"):
                return data
        except Exception:
            pass
        return {"ok": False, "error": "unknown"}
    except (urllib_error.URLError, TimeoutError, ValueError):
        return {"ok": False, "error": "network_error"}


def request_calc_professional_summary(username):
    username = (username or "").strip().lower()
    if not username or not CALC_BRIDGE_TOKEN or not CALC_URL:
        return None

    payload = {
        "username": username,
    }
    req = urllib_request.Request(
        f"{CALC_URL.rstrip('/')}/api/public/professional-summary",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "X-Bridge-Token": CALC_BRIDGE_TOKEN,
        },
        method="POST",
    )
    try:
        with urllib_request.urlopen(req, timeout=4) as resp:
            body = resp.read().decode("utf-8")
            data = json.loads(body or "{}")
            return data if isinstance(data, dict) and data.get("ok") else None
    except urllib_error.HTTPError:
        return None
    except (urllib_error.URLError, TimeoutError, ValueError, Exception):
        return None


def request_calc_margin_sync(username, settings=None):
    username = (username or "").strip().lower()
    if not username or not CALC_BRIDGE_TOKEN or not CALC_URL:
        return {"attempted": False, "reason": "missing_context"}

    settings = settings or get_private_commercial_settings()
    normalized_settings = {
        key: parse_non_negative_float(
            settings.get(key),
            default=DEFAULT_COMMERCIAL_SETTINGS[key],
        )
        for key in DEFAULT_COMMERCIAL_SETTINGS
    }
    normalized_settings["foam"] = normalized_settings["general"]
    normalized_settings["laminate_foam"] = normalized_settings["general"]
    payload = {
        "username": username,
        "marge": normalized_settings["frames"],
        "marge_impressio": normalized_settings["prints"],
        "margins": normalized_settings,
    }
    req = urllib_request.Request(
        f"{CALC_URL.rstrip('/')}/api/public/commercial-settings-sync",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "X-Bridge-Token": CALC_BRIDGE_TOKEN,
        },
        method="POST",
    )
    try:
        with urllib_request.urlopen(req, timeout=12) as resp:
            body = resp.read().decode("utf-8")
            return {"attempted": True, "ok": True, "response": json.loads(body or "{}")}
    except urllib_error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="ignore")
        return {"attempted": True, "ok": False, "status": exc.code, "detail": detail}
    except (urllib_error.URLError, TimeoutError, ValueError) as exc:
        return {"attempted": True, "ok": False, "detail": str(exc)}


def fetch_calc_pricing():
    """Obté les tarifes professionals de la calculadora.
    Retorna un dict amb claus impressio, laminate_only, encolat_pro,
    o None si no es pot connectar.
    """
    if not CALC_BRIDGE_TOKEN or not CALC_URL:
        return None
    req = urllib_request.Request(
        f"{CALC_URL.rstrip('/')}/api/public/pricing",
        headers={"X-Bridge-Token": CALC_BRIDGE_TOKEN},
        method="GET",
    )
    try:
        with urllib_request.urlopen(req, timeout=4) as resp:
            data = json.loads(resp.read().decode("utf-8") or "{}")
            return data if isinstance(data, dict) and data.get("ok") else None
    except Exception:
        return None


def _parse_ref_dims(ref):
    """Extreu (ample, alt) d'una referència tipus '20x30' o 'ENC30x40'."""
    m = re.search(r'(\d+)[xX](\d+)', ref or '')
    if m:
        return int(m.group(1)), int(m.group(2))
    return None, None


def _find_closest_impressio(impressio_list, width, height):
    """Troba el preu més baix de la taula impressio que cobreixi
    les dimensions sol·licitades (en qualsevol orientació).
    Si cap mida cobreix, retorna la més gran disponible.
    """
    candidates = []
    for item in impressio_list:
        rw, rh = _parse_ref_dims(item.get('ref', ''))
        if rw is None:
            continue
        if (rw >= width and rh >= height) or (rw >= height and rh >= width):
            candidates.append(item)
    if candidates:
        return min(candidates, key=lambda x: float(x.get('preu', 0)))
    if impressio_list:
        return max(impressio_list, key=lambda x: float(x.get('preu', 0)))
    return None


def _find_closest_laminate(laminate_list, width, height):
    """Troba el preu més baix de la taula laminate_only que cobreixi
    les dimensions sol·licitades (en qualsevol orientació).
    """
    candidates = []
    for item in laminate_list:
        rw, rh = _parse_ref_dims(item.get('ref', ''))
        if rw is None:
            continue
        if (rw >= width and rh >= height) or (rw >= height and rh >= width):
            candidates.append(item)
    if candidates:
        return min(candidates, key=lambda x: float(x.get('preu', 0)))
    if laminate_list:
        return max(laminate_list, key=lambda x: float(x.get('preu', 0)))
    return None


def build_calc_request_url(service=None):
    calc_service = get_calc_service(service)
    params = {
        "pro": 1,
        "subject": calc_service["subject"],
    }
    if calc_service["key"] != "general":
        params["service"] = calc_service["key"]
    return url_for("contacte", **params)


def get_private_target_endpoint(service=None):
    service = normalize_calc_service(service)
    endpoint_map = {
        "general": "area_privada",
        "canvas": "area_privada_lienzos",
        "photo_print": "area_privada_impresions",
        "fine_art": "area_privada_impresions",
        "albums": "area_privada_tarifari",
        "frames": "area_privada_marcos",
    }
    return endpoint_map.get(service, "area_privada")


def get_request_target_path():
    query = request.query_string.decode("utf-8", errors="ignore")
    return f"{request.path}?{query}" if query else request.path


def normalize_private_next_path(value, service=None):
    value = str(value or "").strip()
    if value.startswith("/area-privada"):
        return value
    return url_for(get_private_target_endpoint(service), lang=get_lang())


def build_private_access_url(service=None, next_path=""):
    params = {
        "lang": get_lang(),
        "source": "private_area",
    }
    service = normalize_calc_service(service)
    if service != "general":
        params["service"] = service
    next_path = str(next_path or "").strip()
    if next_path.startswith("/area-privada"):
        params["next_path"] = next_path
    return url_for("area_privada_acces", **params)


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
        "CALC_DIRECT_URL": build_direct_calc_url(calc_service["key"]),
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


def build_private_nav():
    lang = get_lang()
    current_endpoint = request.endpoint or ""
    cart_count = get_private_order_line_count()
    links = [
        {
            "endpoint": "area_privada",
            "label": "Portal" if lang == "ca" else "Portal",
        },
        {
            "endpoint": "area_privada_comanda",
            "label": "Comanda" if lang == "ca" else "Pedido",
            "badge": cart_count if cart_count > 0 else None,
        },
        {
            "endpoint": "area_privada_ajustos",
            "label": "Ajustos" if lang == "ca" else "Ajustes",
        },
    ]

    return [
        {
            "href": url_for(item["endpoint"]),
            "label": item["label"],
            "active": current_endpoint == item["endpoint"],
            "badge": item.get("badge"),
        }
        for item in links
    ]


def get_private_professional_session():
    data = session.get("private_professional")
    return data if isinstance(data, dict) else {}


def has_private_professional_session():
    return bool(get_private_professional_session().get("username"))


def get_private_order_line_count():
    order = _get_private_order_session()
    return len(order.get("lines", []))


def build_private_shell_context():
    lang = get_lang()
    professional = get_private_professional_session()
    is_logged = bool(professional.get("username"))
    return {
        "private_area_nav": True,
        "private_nav_links": build_private_nav(),
        "private_return_url": url_for("professionals"),
        "private_login_url": url_for("area_privada_acces", lang=lang, source="private_area"),
        "private_logout_url": url_for("area_privada_sortir", lang=lang),
        "private_cart_url": url_for("area_privada_comanda", lang=lang),
        "private_cart_count": get_private_order_line_count(),
        "private_professional": {
            "logged_in": is_logged,
            "username": professional.get("username", ""),
            "name": professional.get("name", ""),
            "business_name": professional.get("business_name", ""),
            "pending_count": sum(
                1 for q in professional.get("recent_quotes", [])
                if q.get("pendent")
            ),
            "recent_quotes": professional.get("recent_quotes", []),
            "label": (
                "Sessió professional activa" if lang == "ca" else "Sesión profesional activa"
            ) if is_logged else (
                "Accés professional pendent" if lang == "ca" else "Acceso profesional pendiente"
            ),
            "detail": professional.get("username", "") if is_logged else (
                "Encara no s'ha validat cap sessió" if lang == "ca" else "Todavía no se ha validado ninguna sesión"
            ),
        },
    }


def get_canvas_size_image_url(size_id):
    size_id = str(size_id or "").strip()
    default_url = url_for("static", filename="img/lienzos/private-canvas-main.webp")
    if not size_id:
        return default_url

    candidate = CANVAS_SIZE_IMAGE_DIR / f"{size_id}.webp"
    if candidate.exists():
        return url_for("static", filename=f"img/lienzos/by-size/{size_id}.webp")
    return default_url


def classify_canvas_size(final_width, final_height, lang, group="standard"):
    if final_width == final_height:
        orientation = "square"
        orientation_label = "Quadrat" if lang == "ca" else "Cuadrado"
    elif group == "panoramic":
        orientation = "horizontal"
        orientation_label = "Panoràmic" if lang == "ca" else "Panorámico"
    elif final_width > final_height:
        orientation = "horizontal"
        orientation_label = "Horitzontal" if lang == "ca" else "Horizontal"
    else:
        orientation = "vertical"
        orientation_label = "Vertical"

    larger_side = max(final_width, final_height)
    if larger_side <= 60:
        size_band = "small"
        size_band_label = "Petit format" if lang == "ca" else "Formato pequeño"
    elif larger_side <= 100:
        size_band = "medium"
        size_band_label = "Format mitjà" if lang == "ca" else "Formato medio"
    else:
        size_band = "large"
        size_band_label = "Gran format" if lang == "ca" else "Gran formato"

    return {
        "orientation": orientation,
        "orientation_label": orientation_label,
        "size_band": size_band,
        "size_band_label": size_band_label,
    }


def build_canvas_module_context(draft_payload=None, draft_id="", safe_mode=False):
    lang = get_lang()
    source_payload = draft_payload if isinstance(draft_payload, dict) else {}
    default_margin_percent = DEFAULT_COMMERCIAL_SETTINGS["canvas"] if safe_mode else get_default_margin_for_product("canvas")
    selected_size_id = (request.args.get("size") or source_payload.get("size") or "").strip()
    selected_edit_id = (request.args.get("edit") or source_payload.get("edit") or "").strip()
    selected_quantity = parse_positive_int(request.args.get("qty") or source_payload.get("qty"), default=1)
    selected_margin_percent = parse_non_negative_float(
        request.args.get("margin") or source_payload.get("margin"),
        default=default_margin_percent,
    )
    selected_show_file_size = parse_bool_flag(request.args.get("show_file_size") or source_payload.get("show_file_size"))
    default_size_id = f"{CANVAS_PRICING['sizes'][0]['final'][0]}x{CANVAS_PRICING['sizes'][0]['final'][1]}"
    default_edit_id = CANVAS_PRICING["edit_options"][0]["id"]
    valid_size_ids = {f"{item['final'][0]}x{item['final'][1]}" for item in CANVAS_PRICING["sizes"]}
    valid_edit_ids = {item["id"] for item in CANVAS_PRICING["edit_options"]}
    selected_size_id = selected_size_id if selected_size_id in valid_size_ids else default_size_id
    selected_edit_id = selected_edit_id if selected_edit_id in valid_edit_ids else default_edit_id
    sizes = []
    for item in CANVAS_PRICING["sizes"]:
        final_width, final_height = item["final"]
        file_width, file_height = item["file"]
        size_id = f"{final_width}x{final_height}"
        size_meta = classify_canvas_size(final_width, final_height, lang, item["group"])
        sizes.append(
            {
                "id": size_id,
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
                "orientation": size_meta["orientation"],
                "orientation_label": size_meta["orientation_label"],
                "size_band": size_meta["size_band"],
                "size_band_label": size_meta["size_band_label"],
                "image_url": get_canvas_size_image_url(size_id),
                "selected": size_id == selected_size_id,
            }
        )

    selected_size = next((item for item in sizes if item["id"] == selected_size_id), sizes[0])

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
                    "selected": item["id"] == selected_edit_id,
                }
                for item in CANVAS_PRICING["edit_options"]
            ],
        }
        ,
        "canvas_draft": {
            "draft_id": draft_id,
            "selected_size_id": selected_size_id,
            "selected_quantity": selected_quantity,
            "selected_edit_id": selected_edit_id,
            "selected_margin_percent": selected_margin_percent,
            "selected_show_file_size": selected_show_file_size,
            "saved_drafts": [] if safe_mode else list_saved_canvas_drafts(),
            "default_margin_percent": default_margin_percent,
        },
        "canvas_preview": {
            "image_url": selected_size["image_url"],
            "selected_label": selected_size["final_label"],
            "selected_orientation": selected_size["orientation_label"],
        },
    }


def get_default_margin_for_product(product_key, profile_id="default"):
    settings = get_private_commercial_settings()
    return float(settings.get(product_key, settings.get("general", CANVAS_PRICING["default_margin_percent"])))


def build_pricing_view_context():
    lang = get_lang()
    settings = get_private_commercial_settings()
    pricing_data = fetch_calc_pricing()
    impressio_list  = pricing_data.get("impressio", [])    if pricing_data else []
    laminate_list   = pricing_data.get("laminate_only", []) if pricing_data else []
    encolat_list    = pricing_data.get("encolat_pro", [])   if pricing_data else []
    return {
        "pricing_view": {
            "margins": settings,
            "margin_note": {
                "ca": "La vista PVP utilitza el marge guardat a Ajustos comercials i mostra el preu final amb IVA inclòs.",
                "es": "La vista PVP usa el margen guardado en Ajustes comerciales y muestra el precio final con IVA incluido.",
            }[lang],
            "cost_note": {
                "ca": "La vista cost mostra la tarifa base per al fotògraf, abans d'aplicar el marge comercial.",
                "es": "La vista coste muestra la tarifa base para el fotógrafo, antes de aplicar el margen comercial.",
            }[lang],
            "pricing_connected": bool(impressio_list),
            "impressio": impressio_list,
            "laminate_only": laminate_list,
            "encolat_pro": [r for r in encolat_list if r.get("tipus") == "encolat"],
            "protter":     [r for r in encolat_list if r.get("tipus") == "protter"],
        }
    }


def build_private_settings_context():
    lang = get_lang()
    settings = get_private_commercial_settings()
    product_labels = {
        "general": {"ca": "Marge general", "es": "Margen general"},
        "frames": {"ca": "Marcs", "es": "Marcos"},
        "canvas": {"ca": "Llenços", "es": "Lienzos"},
        "prints": {"ca": "Impressions", "es": "Impresiones"},
        "albums": {"ca": "Àlbums", "es": "Álbumes"},
        "foam": {"ca": "Foam", "es": "Foam"},
        "laminate_foam": {"ca": "Laminat + foam", "es": "Laminado + foam"},
        "fine_art": {"ca": "Fine art", "es": "Fine art"},
    }
    descriptions = {
        "general": {
            "ca": "Serveix com a base comuna quan un producte encara no té marge propi.",
            "es": "Sirve como base común cuando un producto todavía no tiene margen propio.",
        },
        "frames": {
            "ca": "De moment queda preparat aquí per poder-lo unificar també amb marcs.",
            "es": "De momento queda preparado aquí para poder unificarlo también con marcos.",
        },
        "canvas": {
            "ca": "És el marge que veus per defecte a llenços i al tarifari.",
            "es": "Es el margen que ves por defecto en lienzos y en el tarifario.",
        },
        "prints": {
            "ca": "És el marge per defecte d'impressions, foam i laminat.",
            "es": "Es el margen por defecto de impresiones, foam y laminado.",
        },
        "albums": {
            "ca": "Queda preparat per quan entri el mòdul d'àlbums.",
            "es": "Queda preparado para cuando entre el módulo de álbumes.",
        },
        "foam": {
            "ca": "Et permet reservar un marge específic per a productes muntats sobre foam.",
            "es": "Te permite reservar un margen específico para productos montados sobre foam.",
        },
        "laminate_foam": {
            "ca": "Per separar la combinaciÃ³ de laminat i foam quan la vulguis treballar com a producte propi.",
            "es": "Para separar la combinaciÃ³n de laminado y foam cuando quieras trabajarla como producto propio.",
        },
        "fine_art": {
            "ca": "Preparat per a còpia fine art i treballs expositius.",
            "es": "Preparado para copia fine art y trabajos expositivos.",
        },
    }
    return {
        "private_settings": {
            "saved": parse_bool_flag(request.args.get("saved")),
            "entries": [
                {
                    "key": key,
                    "label": product_labels[key][lang],
                    "description": descriptions[key][lang],
                    "value": settings[key],
                }
                for key in ("general", "frames", "canvas", "prints", "fine_art", "albums")
            ],
        }
    }


def format_measure_value(value):
    if not value:
        return ""
    rounded = round(float(value), 2)
    if abs(rounded - round(rounded)) < 0.01:
        return str(int(round(rounded)))
    return ("%.2f" % rounded).rstrip("0").rstrip(".")


def build_prints_module_context():
    lang = get_lang()
    default_margin_percent = get_default_margin_for_product("prints")
    selected_paper_id = (request.args.get("paper") or PRINT_PRODUCTS_CONFIG["papers"][0]["id"]).strip().lower()
    selected_build_id = (request.args.get("build") or PRINT_PRODUCTS_CONFIG["build_options"][0]["id"]).strip().lower()
    selected_width = parse_non_negative_float(request.args.get("width"), default=30.0)
    selected_height = parse_non_negative_float(request.args.get("height"), default=40.0)
    selected_quantity = parse_positive_int(request.args.get("qty"), default=1)
    selected_margin_percent = parse_non_negative_float(request.args.get("margin"), default=default_margin_percent)
    selected_view = (request.args.get("view") or "client").strip().lower()
    selected_view = selected_view if selected_view in {"cost", "client"} else "client"

    # Preu automàtic des de la calculadora segons el tipus d'acabat
    cost_explicit = request.args.get("cost")
    pricing_data = fetch_calc_pricing()
    impressio_list  = pricing_data.get("impressio", [])   if pricing_data else []
    laminate_list   = pricing_data.get("laminate_only", []) if pricing_data else []

    matched_print    = _find_closest_impressio(impressio_list, selected_width, selected_height)
    matched_laminate = _find_closest_laminate(laminate_list,   selected_width, selected_height)

    print_cost    = float(matched_print["preu"])    if matched_print    else 0.0
    laminate_cost = float(matched_laminate["preu"]) if matched_laminate else 0.0

    # Cost base per tipus d'acabat:
    # print_only     → preu impressió
    # laminate_only  → preu laminat
    # laminate_foam  → preu impressió + preu laminat
    # without_print  → 0 (client porta la imatge)
    # foam_only      → no hi ha tarifa, cal entrada manual
    if selected_build_id == "print_only":
        auto_cost = print_cost
        auto_ref  = matched_print["ref"] if matched_print else ""
        can_auto  = bool(impressio_list)
    elif selected_build_id == "laminate_only":
        auto_cost = laminate_cost
        auto_ref  = matched_laminate["ref"] if matched_laminate else ""
        can_auto  = bool(laminate_list)
    elif selected_build_id == "laminate_foam":
        auto_cost = print_cost + laminate_cost
        auto_ref  = f"{matched_print['ref'] if matched_print else '?'} + {matched_laminate['ref'] if matched_laminate else '?'}"
        can_auto  = bool(impressio_list and laminate_list)
    elif selected_build_id == "without_print":
        auto_cost = 0.0
        auto_ref  = ""
        can_auto  = True
    else:
        # foam_only: sense tarifa automàtica
        auto_cost = 0.0
        auto_ref  = ""
        can_auto  = False

    if cost_explicit is not None:
        selected_cost = parse_non_negative_float(cost_explicit, default=auto_cost)
        cost_is_auto = False
    else:
        selected_cost = auto_cost
        cost_is_auto = can_auto

    paper_lookup = {item["id"]: item for item in PRINT_PRODUCTS_CONFIG["papers"]}
    build_lookup = {item["id"]: item for item in PRINT_PRODUCTS_CONFIG["build_options"]}
    selected_paper = paper_lookup.get(selected_paper_id, PRINT_PRODUCTS_CONFIG["papers"][0])
    selected_build = build_lookup.get(selected_build_id, PRINT_PRODUCTS_CONFIG["build_options"][0])

    professional_subtotal = round(selected_cost * selected_quantity, 2)
    professional_vat = round(professional_subtotal * CANVAS_PRICING["vat_rate"], 2)
    professional_total = round(professional_subtotal + professional_vat, 2)
    margin_amount = round(professional_subtotal * (selected_margin_percent / 100), 2)
    client_subtotal = round(professional_subtotal + margin_amount, 2)
    client_vat = round(client_subtotal * CANVAS_PRICING["vat_rate"], 2)
    client_total = round(client_subtotal + client_vat, 2)
    size_label = f"{format_measure_value(selected_width)} x {format_measure_value(selected_height)} cm"

    return {
        "prints_module": {
            "papers": [
                {
                    "id": item["id"],
                    "label": item["label"][lang],
                    "description": item["description"][lang],
                    "selected": item["id"] == selected_paper["id"],
                }
                for item in PRINT_PRODUCTS_CONFIG["papers"]
            ],
            "build_options": [
                {
                    "id": item["id"],
                    "label": item["label"][lang],
                    "summary": item["summary"][lang],
                    "selected": item["id"] == selected_build["id"],
                }
                for item in PRINT_PRODUCTS_CONFIG["build_options"]
            ],
            "selected_paper_id": selected_paper["id"],
            "selected_build_id": selected_build["id"],
            "selected_width": selected_width,
            "selected_height": selected_height,
            "selected_quantity": selected_quantity,
            "selected_cost": selected_cost,
            "selected_margin_percent": selected_margin_percent,
            "selected_view": selected_view,
            "view_is_cost": selected_view == "cost",
            "view_is_client": selected_view == "client",
            "size_label": size_label,
            "summary_title": f"{selected_build['label'][lang]} · {size_label}",
            "professional_subtotal": professional_subtotal,
            "professional_vat": professional_vat,
            "professional_total": professional_total,
            "margin_amount": margin_amount,
            "client_subtotal": client_subtotal,
            "client_vat": client_vat,
            "client_total": client_total,
            "cost_is_auto": cost_is_auto,
            "auto_ref": auto_ref,
            "pricing_connected": bool(impressio_list),
            "can_auto": can_auto,
            "add_to_order_url": url_for(
                "area_privada_comanda",
                lang=lang,
                append=1,
                product="print",
                paper=selected_paper["id"],
                build=selected_build["id"],
                width=format_measure_value(selected_width),
                height=format_measure_value(selected_height),
                qty=selected_quantity,
                cost=format(selected_cost, ".2f"),
                margin=format(selected_margin_percent, ".2f"),
            ),
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


def build_line_file_info(lang, method="dropbox", name="", link="", notes=""):
    labels = {
        "dropbox": {"ca": "Dropbox compartit", "es": "Dropbox compartido"},
        "link": {"ca": "Enllaç extern", "es": "Enlace externo"},
        "later": {"ca": "Enviar més tard", "es": "Enviar más tarde"},
    }
    selected_method = method if method in labels else "dropbox"
    return {
        "method": selected_method,
        "method_label": labels[selected_method][lang],
        "name": str(name or "").strip(),
        "link": str(link or "").strip(),
        "notes": str(notes or "").strip(),
        "has_content": bool(str(name or "").strip() or str(link or "").strip() or str(notes or "").strip()),
    }


def build_unified_order_line(
    *,
    line_id,
    reference,
    product_type,
    product_type_label,
    source,
    title,
    summary,
    quantity,
    professional_subtotal,
    professional_vat,
    professional_total,
    margin_percent,
    margin_amount,
    client_subtotal,
    client_vat,
    client_total,
    vat_rate_percent,
    file_info=None,
    metadata=None,
    editable_in="",
    created_at=None,
    extra=None,
):
    line = {
        "line_id": line_id,
        "reference": reference,
        "product_type": product_type,
        "product_type_label": product_type_label,
        "source": source,
        "title": title,
        "summary": summary,
        "quantity": quantity,
        "professional_subtotal": professional_subtotal,
        "professional_vat": professional_vat,
        "professional_total": professional_total,
        "margin_percent": margin_percent,
        "margin_amount": margin_amount,
        "client_subtotal": client_subtotal,
        "client_vat": client_vat,
        "client_total": client_total,
        "vat_rate_percent": vat_rate_percent,
        "file_info": file_info or build_line_file_info(get_lang()),
        "metadata": metadata or [],
        "editable_in": editable_in,
        "created_at": created_at or datetime.utcnow().isoformat(timespec="seconds"),
    }
    if isinstance(extra, dict):
        line.update(extra)
    return line


def build_order_return_params(source="", draft_id=""):
    params = {"lang": get_lang()}
    if source == "frames":
        params["source"] = "frames"
        if draft_id:
            params["draft"] = draft_id
        return params

    for key in ("size", "edit", "qty", "margin", "show_file_size", "delivery", "client"):
        value = request.args.get(key)
        if value not in (None, ""):
            params[key] = value
    return params


def _normalize_canvas_order_line_payload(payload=None):
    payload = payload if isinstance(payload, dict) else {}
    return {
        "product_type": "canvas",
        "line_id": str(payload.get("line_id") or "").strip(),
        "size": str(payload.get("size") or payload.get("size_id") or "").strip(),
        "qty": str(payload.get("qty") or payload.get("quantity") or "1").strip(),
        "edit": str(payload.get("edit") or payload.get("edit_id") or "").strip(),
        "margin": str(payload.get("margin") or payload.get("margin_percent") or CANVAS_PRICING["default_margin_percent"]).strip(),
        "show_file_size": "1" if parse_bool_flag(payload.get("show_file_size")) else "0",
        "file_method": str(payload.get("file_method") or "dropbox").strip(),
        "file_name": str(payload.get("file_name") or "").strip(),
        "file_link": str(payload.get("file_link") or "").strip(),
        "file_notes": str(payload.get("file_notes") or "").strip(),
    }


def _normalize_print_order_line_payload(payload=None):
    payload = payload if isinstance(payload, dict) else {}
    return {
        "product_type": "print",
        "line_id": str(payload.get("line_id") or "").strip(),
        "paper": str(payload.get("paper") or "").strip(),
        "build": str(payload.get("build") or "").strip(),
        "width": str(payload.get("width") or "30").strip(),
        "height": str(payload.get("height") or "40").strip(),
        "qty": str(payload.get("qty") or payload.get("quantity") or "1").strip(),
        "cost": str(payload.get("cost") or payload.get("professional_unit_cost") or "0").strip(),
        "margin": str(payload.get("margin") or payload.get("margin_percent") or get_default_margin_for_product("prints")).strip(),
        "file_method": str(payload.get("file_method") or "dropbox").strip(),
        "file_name": str(payload.get("file_name") or "").strip(),
        "file_link": str(payload.get("file_link") or "").strip(),
        "file_notes": str(payload.get("file_notes") or "").strip(),
    }


def _normalize_private_order_session_line(payload=None):
    payload = payload if isinstance(payload, dict) else {}
    product_type = str(payload.get("product_type") or "").strip().lower() or "canvas"
    if product_type == "print":
        return _normalize_print_order_line_payload(payload)
    return _normalize_canvas_order_line_payload(payload)


def _get_private_order_session():
    order = session.get("private_order")
    if not isinstance(order, dict):
        legacy = session.get("private_canvas_order")
        if isinstance(legacy, dict):
            order = {"lines": legacy.get("lines", [])}
        else:
            order = {"lines": []}
    lines = order.get("lines")
    if not isinstance(lines, list):
        order["lines"] = []
    order["lines"] = [_normalize_private_order_session_line(line) for line in order["lines"]]
    return order


def _write_private_order_session(order):
    session["private_order"] = {"lines": order.get("lines", [])}
    session.pop("private_canvas_order", None)
    session.modified = True


def add_private_order_line_to_session(payload):
    normalized = _normalize_private_order_session_line(payload)
    normalized["line_id"] = normalized["line_id"] or f"line_{secrets.token_urlsafe(6)}"
    order = _get_private_order_session()
    order.setdefault("lines", []).append(normalized)
    _write_private_order_session(order)
    return normalized["line_id"]


def remove_private_order_line_from_session(line_id):
    line_id = str(line_id or "").strip()
    if not line_id:
        return
    order = _get_private_order_session()
    order["lines"] = [line for line in order.get("lines", []) if str(line.get("line_id") or "").strip() != line_id]
    _write_private_order_session(order)


def update_private_order_line_file_in_session(line_id, payload):
    line_id = str(line_id or "").strip()
    if not line_id:
        return False
    order = _get_private_order_session()
    updated = False
    for line in order.get("lines", []):
        if str(line.get("line_id") or "").strip() != line_id:
            continue
        line["file_method"] = str(payload.get("file_method") or "dropbox").strip() or "dropbox"
        line["file_name"] = str(payload.get("file_name") or "").strip()
        line["file_link"] = str(payload.get("file_link") or "").strip()
        line["file_notes"] = str(payload.get("file_notes") or "").strip()
        updated = True
        break
    if updated:
        _write_private_order_session(order)
    return updated


def clear_private_order_session():
    session.pop("private_order", None)
    session.pop("private_canvas_order", None)
    session.modified = True


def add_canvas_order_line_to_session(payload):
    return add_private_order_line_to_session({**(payload or {}), "product_type": "canvas"})


def remove_canvas_order_line_from_session(line_id):
    return remove_private_order_line_from_session(line_id)


def update_canvas_order_line_file_in_session(line_id, payload):
    return update_private_order_line_file_in_session(line_id, payload)


def clear_canvas_order_session():
    return clear_private_order_session()


def _build_canvas_order_line_from_payload(payload, lang, index=1):
    normalized = _normalize_canvas_order_line_payload(payload)
    size_item = get_canvas_size_by_id(normalized.get("size"))
    edit_item = get_canvas_edit_by_id(normalized.get("edit"))
    quantity = parse_positive_int(normalized.get("qty"), default=1)
    margin_percent = parse_non_negative_float(normalized.get("margin"), default=CANVAS_PRICING["default_margin_percent"])
    show_file_size = parse_bool_flag(normalized.get("show_file_size"))
    line = build_canvas_order_line(
        size_item=size_item,
        edit_item=edit_item,
        quantity=quantity,
        margin_percent=margin_percent,
        show_file_size=show_file_size,
        lang=lang,
    )
    file_method = normalized.get("file_method") or "dropbox"
    file_method_labels = {
        "dropbox": {"ca": "Dropbox compartit", "es": "Dropbox compartido"},
        "link": {"ca": "Enllaç extern", "es": "Enlace externo"},
        "later": {"ca": "Enviar més tard", "es": "Enviar más tarde"},
    }
    line_id = normalized.get("line_id") or f"line_{index:02d}"
    reference = f"LINE-{index:02d}"
    file_info = build_line_file_info(
        lang,
        method=file_method,
        name=normalized.get("file_name", ""),
        link=normalized.get("file_link", ""),
        notes=normalized.get("file_notes", ""),
    )
    metadata = [
        {"label": {"ca": "Mida final", "es": "Medida final"}[lang], "value": line["final_label"]},
        {"label": {"ca": "Preparació", "es": "Preparación"}[lang], "value": line["edit_label"]},
    ]
    if show_file_size:
        metadata.append(
            {"label": {"ca": "Fitxer amb marge", "es": "Archivo con margen"}[lang], "value": line["file_label"]}
        )
    return build_unified_order_line(
        line_id=line_id,
        reference=reference,
        product_type="canvas",
        product_type_label={"ca": "Llenç", "es": "Lienzo"}[lang],
        source="private_area",
        title=f"{ {'ca': 'Llenç', 'es': 'Lienzo'}[lang] } {line['final_label']}",
        summary=line["edit_label"],
        quantity=quantity,
        professional_subtotal=line["professional_subtotal"],
        professional_vat=line["professional_vat"],
        professional_total=line["professional_total"],
        margin_percent=line["margin_percent"],
        margin_amount=line["margin_amount"],
        client_subtotal=line["client_subtotal"],
        client_vat=line["client_vat"],
        client_total=line["client_total"],
        vat_rate_percent=line["vat_rate_percent"],
        file_info=file_info,
        metadata=metadata,
        editable_in="canvas",
        extra={
            **line,
            "is_suggested": False,
            "file_method": file_info["method"],
            "file_method_label": file_method_labels.get(file_method, file_method_labels["dropbox"])[lang],
            "file_name": file_info["name"],
            "file_link": file_info["link"],
            "file_notes": file_info["notes"],
            "edit_url": url_for(
                "area_privada_lienzos",
                lang=lang,
                size=line["size_id"],
                qty=quantity,
                edit=edit_item["id"],
                margin=margin_percent,
                show_file_size="1" if show_file_size else "0",
            ),
        },
    )


def _build_print_order_line_from_payload(payload, lang, index=1):
    normalized = _normalize_print_order_line_payload(payload)
    paper_lookup = {item["id"]: item for item in PRINT_PRODUCTS_CONFIG["papers"]}
    build_lookup = {item["id"]: item for item in PRINT_PRODUCTS_CONFIG["build_options"]}
    paper_item = paper_lookup.get(normalized.get("paper"), PRINT_PRODUCTS_CONFIG["papers"][0])
    build_item = build_lookup.get(normalized.get("build"), PRINT_PRODUCTS_CONFIG["build_options"][0])
    width = parse_non_negative_float(normalized.get("width"), default=30.0)
    height = parse_non_negative_float(normalized.get("height"), default=40.0)
    quantity = parse_positive_int(normalized.get("qty"), default=1)
    professional_unit_cost = parse_non_negative_float(normalized.get("cost"), default=0.0)
    margin_percent = parse_non_negative_float(normalized.get("margin"), default=get_default_margin_for_product("prints"))

    size_label = f"{format_measure_value(width)} x {format_measure_value(height)} cm"
    professional_subtotal = round(professional_unit_cost * quantity, 2)
    professional_vat = round(professional_subtotal * CANVAS_PRICING["vat_rate"], 2)
    professional_total = round(professional_subtotal + professional_vat, 2)
    margin_amount = round(professional_subtotal * (margin_percent / 100), 2)
    client_subtotal = round(professional_subtotal + margin_amount, 2)
    client_vat = round(client_subtotal * CANVAS_PRICING["vat_rate"], 2)
    client_total = round(client_subtotal + client_vat, 2)
    file_info = build_line_file_info(
        lang,
        method=normalized.get("file_method") or "dropbox",
        name=normalized.get("file_name", ""),
        link=normalized.get("file_link", ""),
        notes=normalized.get("file_notes", ""),
    )
    build_label = build_item["label"][lang]
    paper_value = "-" if build_item["id"] == "without_print" else paper_item["label"][lang]
    metadata = [
        {"label": {"ca": "Mida", "es": "Medida"}[lang], "value": size_label},
        {"label": {"ca": "Acabat", "es": "Acabado"}[lang], "value": build_label},
        {"label": {"ca": "Paper", "es": "Papel"}[lang], "value": paper_value},
    ]
    line_id = normalized.get("line_id") or f"line_{index:02d}"
    reference = f"LINE-{index:02d}"
    return build_unified_order_line(
        line_id=line_id,
        reference=reference,
        product_type="print",
        product_type_label={"ca": "Impressió", "es": "Impresión"}[lang],
        source="private_area",
        title=f"{build_label} · {size_label}",
        summary=paper_item["description"][lang] if build_item["id"] != "without_print" else build_item["summary"][lang],
        quantity=quantity,
        professional_subtotal=professional_subtotal,
        professional_vat=professional_vat,
        professional_total=professional_total,
        margin_percent=margin_percent,
        margin_amount=margin_amount,
        client_subtotal=client_subtotal,
        client_vat=client_vat,
        client_total=client_total,
        vat_rate_percent=int(CANVAS_PRICING["vat_rate"] * 100),
        file_info=file_info,
        metadata=metadata,
        editable_in="prints",
        extra={
            "print_size_label": size_label,
            "paper_id": paper_item["id"],
            "paper_label": paper_item["label"][lang],
            "build_id": build_item["id"],
            "build_label": build_label,
            "professional_unit_cost": professional_unit_cost,
            "edit_url": url_for(
                "area_privada_impresions",
                lang=lang,
                paper=paper_item["id"],
                build=build_item["id"],
                width=format_measure_value(width),
                height=format_measure_value(height),
                qty=quantity,
                cost=format(professional_unit_cost, ".2f"),
                margin=format(margin_percent, ".2f"),
            ),
        },
    )


def _build_private_order_line_from_payload(payload, lang, index=1):
    payload = payload if isinstance(payload, dict) else {}
    product_type = str(payload.get("product_type") or "").strip().lower() or "canvas"
    if product_type == "print":
        return _build_print_order_line_from_payload(payload, lang, index=index)
    return _build_canvas_order_line_from_payload(payload, lang, index=index)


def build_private_order_context(safe_mode=False):
    lang = get_lang()
    session_lines = [] if safe_mode else _get_private_order_session().get("lines", [])
    order_lines = []
    for index, item in enumerate(session_lines, start=1):
        try:
            order_lines.append(_build_private_order_line_from_payload(item, lang, index=index))
        except Exception:
            app.logger.exception("private_order_line_failed", extra={"line_index": index})

    if not order_lines and any(request.args.get(key) for key in ("size", "edit", "qty", "margin", "show_file_size")):
        order_lines = [
            _build_canvas_order_line_from_payload(
                {
                    "size": request.args.get("size"),
                    "qty": request.args.get("qty"),
                    "edit": request.args.get("edit"),
                    "margin": request.args.get("margin"),
                    "show_file_size": request.args.get("show_file_size"),
                },
                lang,
                index=1,
            )
        ]

    professional_subtotal = round(sum(line["professional_subtotal"] for line in order_lines), 2)
    professional_vat = round(sum(line["professional_vat"] for line in order_lines), 2)
    professional_total = round(sum(line["professional_total"] for line in order_lines), 2)
    margin_amount = round(sum(line["margin_amount"] for line in order_lines), 2)
    client_subtotal = round(sum(line["client_subtotal"] for line in order_lines), 2)
    client_vat = round(sum(line["client_vat"] for line in order_lines), 2)
    client_total = round(sum(line["client_total"] for line in order_lines), 2)
    margin_percent = order_lines[0]["margin_percent"] if order_lines else CANVAS_PRICING["default_margin_percent"]

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

    saved_clients = [] if safe_mode else list_private_clients(limit=12)
    selected_client_id = (request.args.get("client") or "").strip()
    if not selected_client_id and saved_clients:
        selected_client_id = saved_clients[0]["id"]

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
        "order_model": {
            "schema": "unified_order_line_v1",
            "ready_for_mixed_products": True,
        },
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
        "has_lines": bool(order_lines),
        "clients": [
            {
                "id": item["id"],
                "name": item.get("name", ""),
                "company": item.get("company", ""),
                "email": item["email"],
                "phone": item["phone"],
                "city": item.get("city", ""),
                "last_order": item.get("last_order_ref") or (
                    {"ca": "Sense comandes encara", "es": "Sin pedidos todavia"}[lang]
                ),
                "source": item.get("source", "private_area"),
                "notes": item.get("notes", ""),
                "selected": item["id"] == selected_client_id,
                "select_url": url_for("area_privada_comanda", **{**build_order_return_params(), "client": item["id"]}),
            }
            for item in saved_clients
        ],
        "selected_client_id": selected_client_id,
        "has_clients": bool(saved_clients),
        "client_save_url": url_for("area_privada_comanda_client_save"),
        "return_params": build_order_return_params(),
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



def _build_frames_source_data(base_payload=None):
    source_data = _normalize_frame_order_payload(base_payload)
    for key in FRAME_ORDER_FIELDS:
        value = request.args.get(key)
        if value is not None:
            source_data[key] = str(value).strip()
    return source_data



def build_frames_order_context(base_payload=None, draft_id=""):
    lang = get_lang()
    vat_rate = CANVAS_PRICING["vat_rate"]
    source_data = _build_frames_source_data(base_payload)

    total = round(parse_non_negative_float(source_data.get("total"), default=0.0), 2)
    deposit = round(parse_non_negative_float(source_data.get("deposit"), default=0.0), 2)
    pending_value = source_data.get("pending")
    pending = round(
        parse_non_negative_float(pending_value, default=max(total - deposit, 0.0)),
        2,
    )
    if not pending_value and total:
        pending = round(max(total - deposit, 0.0), 2)

    client_subtotal = round(total / (1 + vat_rate), 2) if total else 0.0
    client_vat = round(total - client_subtotal, 2)

    piece_type_id = (source_data.get("piece_type") or "").strip().lower()
    piece_labels = {
        "fotografia": {"ca": "Fotografia", "es": "Fotografia"},
        "lamina": {"ca": "Lamina", "es": "Lamina"},
        "pintura_sense_bastidor": {"ca": "Pintura sense bastidor", "es": "Pintura sin bastidor"},
        "pintura_amb_bastidor": {"ca": "Pintura amb bastidor", "es": "Pintura con bastidor"},
        "puzzle": {"ca": "Puzzle", "es": "Puzzle"},
        "default": {"ca": "Peca emmarcada", "es": "Pieza enmarcada"},
    }
    piece_type_label = piece_labels.get(piece_type_id, piece_labels["default"])[lang]

    piece_width = round(parse_non_negative_float(source_data.get("piece_width"), default=0.0), 2)
    piece_height = round(parse_non_negative_float(source_data.get("piece_height"), default=0.0), 2)

    def format_measure(value):
        if not value:
            return ""
        rounded = round(value, 2)
        if abs(rounded - round(rounded)) < 0.01:
            return str(int(round(rounded)))
        return ("%.2f" % rounded).rstrip("0").rstrip(".")

    piece_measure = (
        f"{format_measure(piece_width)} x {format_measure(piece_height)} cm"
        if piece_width and piece_height
        else ""
    )
    final_size = (source_data.get("final_size") or "").strip() or piece_measure

    quote_ref = (source_data.get("quote_ref") or "").strip()
    quote_display = quote_ref or f"MARCS-{datetime.now():%d%m%y}"
    client_name = (source_data.get("client_name") or "").strip()
    client_phone = (source_data.get("client_phone") or "").strip()
    frame_main = (source_data.get("frame_main") or "").strip()
    frame_pre = (source_data.get("frame_pre") or "").strip()
    glass = (source_data.get("glass") or "").strip()
    interior = (source_data.get("interior") or "").strip()
    print_label = (source_data.get("print_label") or "").strip()
    notes = (source_data.get("notes") or "").strip()

    materials = []
    if frame_main:
        materials.append({"label": {"ca": "Marc principal", "es": "Marco principal"}[lang], "value": frame_main})
    if frame_pre:
        materials.append({"label": {"ca": "Pre-marc", "es": "Pre-marco"}[lang], "value": frame_pre})
    if glass:
        materials.append({"label": {"ca": "Proteccio", "es": "Proteccion"}[lang], "value": glass})
    if interior:
        materials.append({"label": {"ca": "Interior", "es": "Interior"}[lang], "value": interior})
    if print_label:
        materials.append({"label": {"ca": "Impressio", "es": "Impresion"}[lang], "value": print_label})
    if not materials:
        materials.append(
            {
                "label": {"ca": "Configuracio", "es": "Configuracion"}[lang],
                "value": {"ca": "Sense detalls importats", "es": "Sin detalles importados"}[lang],
            }
        )

    imported_label = {
        "ca": "Pressupost importat des de la calculadora de marcs",
        "es": "Presupuesto importado desde la calculadora de marcos",
    }[lang]
    missing_size_label = {"ca": "Mesura pendent", "es": "Medida pendiente"}[lang]
    missing_client_label = {"ca": "Client pendent", "es": "Cliente pendiente"}[lang]
    missing_phone_label = {"ca": "Telefon pendent", "es": "Telefono pendiente"}[lang]

    frame_metadata = [
        {"label": {"ca": "Peça", "es": "Pieza"}[lang], "value": piece_type_label},
        {"label": {"ca": "Mesura final", "es": "Medida final"}[lang], "value": final_size or missing_size_label},
    ]
    if piece_measure:
        frame_metadata.append({"label": {"ca": "Mesura de la peça", "es": "Medida de la pieza"}[lang], "value": piece_measure})
    frame_metadata.extend(materials)

    line = build_unified_order_line(
        line_id="frame_imported",
        reference=quote_display,
        product_type="frame",
        product_type_label={"ca": "Marc", "es": "Marco"}[lang],
        source="frames",
        title=f"{ {'ca': 'Marc', 'es': 'Marco'}[lang] } {final_size or missing_size_label}",
        summary=imported_label,
        quantity=1,
        professional_subtotal=0.0,
        professional_vat=0.0,
        professional_total=0.0,
        margin_percent=0.0,
        margin_amount=0.0,
        client_subtotal=client_subtotal,
        client_vat=client_vat,
        client_total=total,
        vat_rate_percent=int(vat_rate * 100),
        file_info=build_line_file_info(lang, method="later"),
        metadata=frame_metadata,
        editable_in="frames",
        extra={
            "is_imported": True,
            "final_label": final_size or missing_size_label,
            "edit_label": imported_label,
            "deposit_total": deposit,
            "pending_total": pending,
            "piece_label": piece_type_label,
            "piece_measure": piece_measure,
            "frame_main": frame_main,
            "frame_pre": frame_pre,
            "glass": glass,
            "interior": interior,
            "print_label": print_label,
            "materials": materials,
        },
    )

    recent_orders = [
        {
            "reference": quote_display,
            "date": datetime.now().strftime("%d/%m/%Y"),
            "status": {"ca": "Importada des de marcs", "es": "Importada desde marcos"}[lang],
            "total": total,
        }
    ]

    saved_client = None
    if client_name or client_phone:
        try:
            saved_client = save_private_client(
                {
                    "name": client_name,
                    "phone": client_phone,
                    "company": piece_type_label,
                    "city": {"ca": "Importat des de marcs", "es": "Importado desde marcos"}[lang],
                    "notes": notes,
                    "source": "frames",
                    "last_order_ref": quote_display,
                }
            )
        except (RuntimeError, ValueError):
            saved_client = None

    client_entry = {
        "id": (saved_client or {}).get("id", "client_imported"),
        "name": (saved_client or {}).get("name") or client_name or missing_client_label,
        "company": (saved_client or {}).get("company") or piece_type_label,
        "email": (saved_client or {}).get("email", ""),
        "phone": (saved_client or {}).get("phone") or client_phone or missing_phone_label,
        "city": (saved_client or {}).get("city") or {"ca": "Arriba des de marcs", "es": "Llega desde marcos"}[lang],
        "last_order": (saved_client or {}).get("last_order_ref") or quote_display,
        "source": (saved_client or {}).get("source", "frames"),
        "notes": (saved_client or {}).get("notes", ""),
        "selected": True,
        "select_url": url_for("area_privada_comanda", **{**build_order_return_params("frames", draft_id), "client": (saved_client or {}).get("id", "client_imported")}),
    }


def build_canvas_order_context():
    return build_private_order_context()

    return {
        "generated_at": datetime.now(),
        "order_model": {
            "schema": "unified_order_line_v1",
            "ready_for_mixed_products": True,
        },
        "origin": "frames",
        "origin_label": {"ca": "Importada des de marcs", "es": "Importada desde marcos"}[lang],
        "quote_ref": quote_display,
        "client_name": client_name or missing_client_label,
        "client_phone": client_phone or missing_phone_label,
        "piece_type_label": piece_type_label,
        "piece_measure": piece_measure,
        "final_size_label": final_size or missing_size_label,
        "notes": notes,
        "draft_id": draft_id,
        "save_payload": source_data,
        "saved_drafts": list_saved_frames_orders(),
        "line_count": 1,
        "quantity_total": 1,
        "lines": [line],
        "professional_subtotal": 0.0,
        "professional_vat": 0.0,
        "professional_total": 0.0,
        "margin_percent": 0.0,
        "margin_amount": 0.0,
        "client_subtotal": client_subtotal,
        "client_vat": client_vat,
        "client_total": total,
        "deposit_total": deposit,
        "pending_total": pending,
        "vat_rate_percent": int(vat_rate * 100),
        "delivery_options": [],
        "selected_delivery": "",
        "clients": [client_entry],
        "selected_client_id": client_entry["id"],
        "has_clients": True,
        "client_save_url": url_for("area_privada_comanda_client_save"),
        "return_params": build_order_return_params("frames", draft_id),
        "recent_orders": recent_orders,
        "has_internal_costs": False,
        "frames_entry_url": build_calc_login_url("frames", source="private_area"),
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


@app.route("/albums-fotografics")
def albumes_fotograficos():
    return render_template("albumes_fotograficos.html", lang=get_lang(), CALC_URL=CALC_URL)


@app.route("/albumes-fotograficos")
def albumes_fotograficos_redirect():
    return permanent_redirect_to("albumes_fotograficos")


@app.route("/marcs-a-mida")
def marcos_a_medida():
    return render_template("marcos_a_medida.html", lang=get_lang(), CALC_URL=CALC_URL)


@app.route("/marcos-a-medida")
def marcos_a_medida_redirect():
    return permanent_redirect_to("marcos_a_medida")


@app.route("/impressio-llencos")
def impresion_lienzos():
    return render_template("impresion_lienzos.html", lang=get_lang(), CALC_URL=CALC_URL)


@app.route("/impresion-lienzos")
def impresion_lienzos_redirect():
    return permanent_redirect_to("impresion_lienzos")


@app.route("/impressio-hahnemuhle")
def impresion_hahnemuhle():
    return render_template("impresion_hahnemuhle.html", lang=get_lang(), CALC_URL=CALC_URL)


@app.route("/impresion-hahnemuhle")
def impresion_hahnemuhle_redirect():
    return permanent_redirect_to("impresion_hahnemuhle")


@app.route("/qui-som")
def sobre():
    return render_template("sobre.html", lang=get_lang(), CALC_URL=CALC_URL)


@app.route("/sobre")
def sobre_redirect():
    return permanent_redirect_to("sobre")


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


@app.route("/area-professional")
def calculadora():
    # Legacy public entry kept only as a permanent redirect.
    # calculadora.html stays in the repo on purpose in case we want to recover it later.
    # return render_template(
    #     "calculadora.html",
    #     lang=get_lang(),
    #     CALC_URL=CALC_URL,
    #     **build_calc_page_context(request.args.get("service")),
    # )
    return permanent_redirect_to("professionals")


@app.route("/calculadora")
def calculadora_redirect():
    return permanent_redirect_to("calculadora")


@app.route("/area-privada")
def area_privada():
    if not has_private_professional_session():
        return redirect(build_private_access_url("general", next_path=get_request_target_path()))
    return render_template(
        "area_privada_v2.html",
        lang=get_lang(),
        private_modules=build_private_modules(),
        **build_private_shell_context(),
    )


@app.route("/area-privada/acces", methods=["GET", "POST"])
def area_privada_acces():
    lang = get_lang()
    service = normalize_calc_service(request.values.get("service"))
    source = (request.values.get("source") or "web").strip() or "web"
    username = (request.form.get("username") or "").strip()
    next_path = normalize_private_next_path(request.values.get("next_path"), service=service)
    access_error = ""

    if request.method == "GET" and has_private_professional_session():
        return redirect(next_path)

    if request.method == "POST":
        password = request.form.get("password") or ""
        result = request_calc_bridge_login(username, password, service=service, lang=lang, source=source)
        if result.get("ok") and result.get("redirect_url"):
            session["private_professional"] = {
                "username": username,
                "service": service,
                "source": source,
                "logged_at": datetime.utcnow().isoformat(timespec="seconds"),
                "calc_frames_redirect_url": str(result.get("redirect_url") or "").strip() if service == "frames" else "",
            }
            summary = request_calc_professional_summary(username)
            if summary:
                session["private_professional"]["name"] = summary.get("name", "")
                session["private_professional"]["business_name"] = summary.get("business_name", "")
                session["private_professional"]["profile_type"] = summary.get("profile_type", "")
                session["private_professional"]["access_status"] = summary.get("access_status", "")
                session["private_professional"]["recent_quotes"] = summary.get("recent_quotes", [])
            session.permanent = True
            session.modified = True
            return redirect(next_path)
        raw_error = result.get("error") or "unknown"
        access_error = "network_error" if raw_error == "network_error" else "auth_error"

    return render_template(
        "area_privada_login.html",
        lang=lang,
        calc_service=get_calc_service(service, lang),
        service=service,
        source=source,
        username=username,
        next_path=next_path,
        access_error=access_error,
        access_error_message=get_bridge_error_message(access_error, lang) if access_error else "",
        CALC_DIRECT_URL=build_direct_calc_url(service, lang, source),
        CALC_REQUEST_URL=build_calc_request_url(service),
        **build_private_shell_context(),
    )


@app.route("/area-privada/sortir")
def area_privada_sortir():
    session.pop("private_professional", None)
    session.modified = True
    return redirect(url_for("professionals", lang=get_lang()))


@app.route("/area-privada/tarifari")
def area_privada_tarifari():
    if not has_private_professional_session():
        return redirect(build_private_access_url("general", next_path=get_request_target_path()))
    return render_template(
        "area_privada_tarifari_v2.html",
        lang=get_lang(),
        private_modules=build_private_modules(),
        **build_canvas_module_context(),
        **build_pricing_view_context(),
        **build_private_shell_context(),
    )


@app.route("/area-privada/ajustos", methods=["GET", "POST"])
def area_privada_ajustos():
    if not has_private_professional_session():
        return redirect(build_private_access_url("general", next_path=get_request_target_path()))
    if request.method == "POST":
        settings = save_private_commercial_settings(request.form)
        professional = session.get("private_professional") or {}
        request_calc_margin_sync(professional.get("username"), settings=settings)
        return redirect(url_for("area_privada_ajustos", lang=get_lang(), saved=1))
    return render_template(
        "area_privada_ajustos.html",
        lang=get_lang(),
        private_modules=build_private_modules(),
        **build_private_settings_context(),
        **build_private_shell_context(),
    )


@app.route("/api/private/commercial-settings-sync", methods=["POST"])
def api_private_commercial_settings_sync():
    provided_token = request.headers.get("X-Bridge-Token", "").strip()
    if not CALC_BRIDGE_TOKEN or provided_token != CALC_BRIDGE_TOKEN:
        return jsonify({"ok": False, "error": "forbidden"}), 403

    payload = request.get_json(silent=True) or {}
    current = get_private_commercial_settings()
    for key in ("general", "frames", "canvas", "prints", "foam", "laminate_foam", "fine_art", "albums"):
        if key in payload:
            current[key] = parse_non_negative_float(
                payload.get(key),
                default=DEFAULT_COMMERCIAL_SETTINGS.get(key, current.get(key, 0.0)),
            )
    current["foam"] = current["general"]
    current["laminate_foam"] = current["general"]
    save_private_commercial_settings(current)
    return jsonify({"ok": True, "settings": current})


@app.route("/area-privada/lienzos")
def area_privada_lienzos():
    if not has_private_professional_session():
        return redirect(build_private_access_url("canvas", next_path=get_request_target_path()))
    draft_id = (request.args.get("draft") or "").strip()
    draft_payload = get_saved_canvas_draft(draft_id) if draft_id else None
    try:
        canvas_context = build_canvas_module_context(
            draft_payload=draft_payload,
            draft_id=draft_id if draft_payload else "",
        )
        shell_context = build_private_shell_context()
    except Exception:
        app.logger.exception("area_privada_lienzos_failed")
        session.pop("private_order", None)
        session.pop("private_canvas_order", None)
        session.modified = True
        canvas_context = build_canvas_module_context(safe_mode=True)
        shell_context = build_private_shell_context()
    return render_template(
        "area_privada_lienzos_v3.html",
        lang=get_lang(),
        private_modules=build_private_modules(),
        **canvas_context,
        **shell_context,
    )


@app.route("/area-privada/impresiones")
def area_privada_impresions():
    if not has_private_professional_session():
        return redirect(build_private_access_url("photo_print", next_path=get_request_target_path()))
    return render_template(
        "area_privada_impresions.html",
        lang=get_lang(),
        private_modules=build_private_modules(),
        **build_prints_module_context(),
        **build_private_shell_context(),
    )


@app.route("/area-privada/marcos")
def area_privada_marcos():
    if not has_private_professional_session():
        return redirect(build_private_access_url("frames", next_path=get_request_target_path()))
    professional = get_private_professional_session()
    calc_redirect_url = str(professional.get("calc_frames_redirect_url") or "").strip()
    if calc_redirect_url:
        session["private_professional"] = {
            **professional,
            "calc_frames_redirect_url": "",
        }
        session.modified = True
        return redirect(calc_redirect_url)
    try:
        return redirect(build_direct_calc_url("frames", source="private_area"))
    except Exception:
        app.logger.exception("area_privada_marcos_redirect_failed")
        fallback_query = urlencode({"source": "private_area", "lang": get_lang()})
        return redirect(f"{CALC_URL.rstrip('/')}/calculadora?{fallback_query}")


@app.route("/area-privada/comanda")
def area_privada_comanda():
    if not has_private_professional_session():
        return redirect(build_private_access_url("general", next_path=get_request_target_path()))
    source = (request.args.get("source") or "").strip().lower()
    if source != "frames" and parse_bool_flag(request.args.get("append")):
        product_type = (request.args.get("product") or "canvas").strip().lower()
        if product_type == "print":
            add_private_order_line_to_session(
                {
                    "product_type": "print",
                    "paper": request.args.get("paper"),
                    "build": request.args.get("build"),
                    "width": request.args.get("width"),
                    "height": request.args.get("height"),
                    "qty": request.args.get("qty"),
                    "cost": request.args.get("cost"),
                    "margin": request.args.get("margin"),
                }
            )
        else:
            add_canvas_order_line_to_session(
                {
                    "size": request.args.get("size"),
                    "qty": request.args.get("qty"),
                    "edit": request.args.get("edit"),
                    "margin": request.args.get("margin"),
                    "show_file_size": request.args.get("show_file_size"),
                }
            )
        return redirect(url_for("area_privada_comanda", lang=get_lang()))
    draft_id = (request.args.get("draft") or "").strip()
    saved_payload = get_saved_frames_order(draft_id) if source == "frames" and draft_id else None
    try:
        order_data = (
            build_frames_order_context(saved_payload, draft_id=draft_id if saved_payload else "")
            if source == "frames"
            else build_private_order_context()
        )
        shell_context = build_private_shell_context()
    except Exception:
        app.logger.exception("area_privada_comanda_failed", extra={"source": source})
        session.pop("private_order", None)
        session.pop("private_canvas_order", None)
        session.modified = True
        order_data = (
            build_frames_order_context(saved_payload, draft_id=draft_id if saved_payload else "")
            if source == "frames"
            else build_private_order_context(safe_mode=True)
        )
        shell_context = build_private_shell_context()
    template_name = "area_privada_comanda_marcs.html" if source == "frames" else "area_privada_comanda_v2.html"
    return render_template(
        template_name,
        lang=get_lang(),
        private_modules=build_private_modules(),
        order_data=order_data,
        **shell_context,
    )


@app.route("/area-privada/comanda/linia/eliminar", methods=["POST"])
def area_privada_comanda_line_remove():
    remove_canvas_order_line_from_session(request.form.get("line_id"))
    next_path = (request.form.get("next_path") or "").strip()
    if next_path.startswith("/area-privada/comanda"):
        return redirect(next_path)
    return redirect(url_for("area_privada_comanda", lang=get_lang()))


@app.route("/area-privada/comanda/linia/fitxer", methods=["POST"])
def area_privada_comanda_line_file_save():
    update_canvas_order_line_file_in_session(
        request.form.get("line_id"),
        {
            "file_method": request.form.get("file_method"),
            "file_name": request.form.get("file_name"),
            "file_link": request.form.get("file_link"),
            "file_notes": request.form.get("file_notes"),
        },
    )
    next_path = (request.form.get("next_path") or "").strip()
    if next_path.startswith("/area-privada/comanda"):
        return redirect(next_path)
    return redirect(url_for("area_privada_comanda", lang=get_lang()))


@app.route("/area-privada/comanda/buidar", methods=["POST"])
def area_privada_comanda_clear():
    clear_canvas_order_session()
    return redirect(url_for("area_privada_comanda", lang=get_lang()))


@app.route("/area-privada/comanda/client/guardar", methods=["POST"])
def area_privada_comanda_client_save():
    payload = {
        "name": request.form.get("name"),
        "company": request.form.get("company"),
        "email": request.form.get("email"),
        "phone": request.form.get("phone"),
        "city": request.form.get("city"),
        "notes": request.form.get("notes"),
        "source": request.form.get("source") or "private_area",
        "last_order_ref": request.form.get("last_order_ref"),
    }
    try:
        client = save_private_client(payload)
    except (RuntimeError, ValueError):
        return redirect(url_for("area_privada_comanda", **build_order_return_params(request.form.get("order_source"), request.form.get("order_draft"))))

    next_path = (request.form.get("next_path") or "").strip()
    if next_path.startswith("/area-privada/comanda"):
        separator = "&" if "?" in next_path else "?"
        return redirect(f"{next_path}{separator}client={client['id']}")

    redirect_params = build_order_return_params(request.form.get("order_source"), request.form.get("order_draft"))
    redirect_params["client"] = client["id"]
    return redirect(url_for("area_privada_comanda", **redirect_params))


@app.route("/api/private-orders/frames/save", methods=["POST"])
def api_private_orders_frames_save():
    data = request.get_json(silent=True) or {}
    payload = _normalize_frame_order_payload(data)

    if not any(payload.get(key) for key in ("quote_ref", "client_name", "frame_main", "frame_pre", "final_size")):
        return jsonify({"ok": False, "error": "missing_payload"}), 400

    try:
        saved = save_frames_order_draft({**payload, "draft_id": data.get("draft_id")})
    except RuntimeError:
        return jsonify({"ok": False, "error": "db_unavailable"}), 503
    lang = (data.get("lang") or get_lang() or "ca").strip().lower() or "ca"
    draft_url = url_for(
        "area_privada_comanda",
        source="frames",
        draft=saved["draft_id"],
        lang=lang,
    )
    return jsonify(
        {
            "ok": True,
            "draft_id": saved["draft_id"],
            "saved_at": _format_saved_timestamp(saved["updated_at"]),
            "url": draft_url,
        }
    )


@app.route("/api/private-orders/canvas/save", methods=["POST"])
def api_private_orders_canvas_save():
    data = request.get_json(silent=True) or {}

    try:
        saved = save_canvas_draft(
            {
                **data,
                "draft_id": data.get("draft_id"),
                "lang": data.get("lang") or get_lang(),
            }
        )
    except RuntimeError:
        return jsonify({"ok": False, "error": "db_unavailable"}), 503

    lang = (data.get("lang") or get_lang() or "ca").strip().lower() or "ca"
    draft_url = url_for("area_privada_lienzos", draft=saved["draft_id"], lang=lang)
    return jsonify(
        {
            "ok": True,
            "draft_id": saved["draft_id"],
            "saved_at": _format_saved_timestamp(saved["updated_at"]),
            "url": draft_url,
        }
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
