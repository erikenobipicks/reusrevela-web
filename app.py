import json
import os
import secrets
import smtplib
from datetime import datetime
from pathlib import Path
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
    payload = payload or {}
    normalized = {}
    for key in FRAME_ORDER_FIELDS:
        value = payload.get(key, "")
        normalized[key] = "" if value is None else str(value).strip()
    return normalized


def _normalize_canvas_draft_payload(payload=None):
    payload = payload or {}
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



def _draft_sort_key(item):
    return item.get("updated_at") or ""



def _store_to_saved_order(row):
    return {
        "draft_id": row.get("draft_id", ""),
        "quote_ref": row.get("quote_ref", ""),
        "client_name": row.get("client_name", ""),
        "final_size_label": row.get("final_size_label", ""),
        "total": float(row.get("total") or 0.0),
        "updated_at": row.get("updated_at", ""),
        "updated_at_label": _format_saved_timestamp(row.get("updated_at", "")),
    }



def list_saved_frames_orders(limit=8):
    drafts = _read_private_area_store().get("frames_order_drafts", {})
    rows = sorted(drafts.values(), key=_draft_sort_key, reverse=True)
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
    return {
        "draft_id": row.get("draft_id", ""),
        "size_label": row.get("size_label", ""),
        "quantity": int(row.get("quantity") or 1),
        "edit_label": row.get("edit_label", ""),
        "updated_at": row.get("updated_at", ""),
        "updated_at_label": _format_saved_timestamp(row.get("updated_at", "")),
    }


def list_saved_canvas_drafts(limit=8):
    drafts = _read_private_area_store().get("canvas_order_drafts", {})
    rows = sorted(drafts.values(), key=_draft_sort_key, reverse=True)
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
    payload = payload or {}
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
    existing = clients.get(client_id, {}) if isinstance(clients.get(client_id), dict) else {}
    order_count = int(existing.get("order_count") or 0)
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
    rows = [row for row in clients.values() if isinstance(row, dict)]
    rows = sorted(rows, key=_client_sort_key, reverse=True)
    return rows[: max(int(limit or 1), 1)]


def get_private_client(client_id):
    client_id = str(client_id or "").strip()
    if not client_id:
        return None
    row = _read_private_area_store().get("clients", {}).get(client_id)
    return row if isinstance(row, dict) else None


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
    links = [
        {
            "endpoint": "area_privada",
            "label": "Portal" if lang == "ca" else "Portal",
        },
        {
            "endpoint": "area_privada_tarifari",
            "label": "Tarifari" if lang == "ca" else "Tarifario",
        },
        {
            "endpoint": "area_privada_lienzos",
            "label": "Llenços" if lang == "ca" else "Lienzos",
        },
        {
            "endpoint": "area_privada_impresions",
            "label": "Impressions" if lang == "ca" else "Impresiones",
        },
        {
            "endpoint": "area_privada_marcos",
            "label": "Marcs" if lang == "ca" else "Marcos",
        },
        {
            "endpoint": "area_privada_comanda",
            "label": "Comanda" if lang == "ca" else "Pedido",
        },
    ]

    return [
        {
            "href": url_for(item["endpoint"]),
            "label": item["label"],
            "active": current_endpoint == item["endpoint"],
        }
        for item in links
    ]


def build_private_shell_context():
    return {
        "private_area_nav": True,
        "private_nav_links": build_private_nav(),
        "private_return_url": url_for("professionals"),
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


def build_canvas_module_context(draft_payload=None, draft_id=""):
    lang = get_lang()
    source_payload = draft_payload or {}
    selected_size_id = (request.args.get("size") or source_payload.get("size") or "").strip()
    selected_edit_id = (request.args.get("edit") or source_payload.get("edit") or "").strip()
    selected_quantity = parse_positive_int(request.args.get("qty") or source_payload.get("qty"), default=1)
    selected_margin_percent = parse_non_negative_float(
        request.args.get("margin") or source_payload.get("margin"),
        default=CANVAS_PRICING["default_margin_percent"],
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
            "saved_drafts": list_saved_canvas_drafts(),
        },
        "canvas_preview": {
            "image_url": selected_size["image_url"],
            "selected_label": selected_size["final_label"],
            "selected_orientation": selected_size["orientation_label"],
        },
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

    saved_clients = list_private_clients(limit=12)
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

    line = {
        "reference": quote_display,
        "is_imported": True,
        "quantity": 1,
        "final_label": final_size or missing_size_label,
        "edit_label": imported_label,
        "client_total": total,
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
    }

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

    return {
        "generated_at": datetime.now(),
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
        **build_private_shell_context(),
    )


@app.route("/area-privada/acces", methods=["GET", "POST"])
def area_privada_acces():
    lang = get_lang()
    service = normalize_calc_service(request.values.get("service"))
    source = (request.values.get("source") or "web").strip() or "web"
    username = (request.form.get("username") or "").strip()
    access_error = ""

    if request.method == "POST":
        password = request.form.get("password") or ""
        result = request_calc_bridge_login(username, password, service=service, lang=lang, source=source)
        if result.get("ok") and result.get("redirect_url"):
            return redirect(result["redirect_url"])
        access_error = result.get("error") or "unknown"

    return render_template(
        "area_privada_login.html",
        lang=lang,
        calc_service=get_calc_service(service, lang),
        service=service,
        source=source,
        username=username,
        access_error=access_error,
        access_error_message=get_bridge_error_message(access_error, lang) if access_error else "",
        CALC_DIRECT_URL=build_direct_calc_url(service, lang, source),
        CALC_REQUEST_URL=build_calc_request_url(service),
        **build_private_shell_context(),
    )


@app.route("/area-privada/tarifari")
def area_privada_tarifari():
    return render_template(
        "area_privada_tarifari_v2.html",
        lang=get_lang(),
        private_modules=build_private_modules(),
        **build_canvas_module_context(),
        **build_pricing_view_context(),
        **build_private_shell_context(),
    )


@app.route("/area-privada/lienzos")
def area_privada_lienzos():
    draft_id = (request.args.get("draft") or "").strip()
    draft_payload = get_saved_canvas_draft(draft_id) if draft_id else None
    return render_template(
        "area_privada_lienzos_v3.html",
        lang=get_lang(),
        private_modules=build_private_modules(),
        **build_canvas_module_context(draft_payload=draft_payload, draft_id=draft_id if draft_payload else ""),
        **build_private_shell_context(),
    )


@app.route("/area-privada/impresiones")
def area_privada_impresions():
    return render_template(
        "area_privada_impresions.html",
        lang=get_lang(),
        private_modules=build_private_modules(),
        **build_prints_module_context(),
        **build_private_shell_context(),
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
        **build_private_shell_context(),
    )


@app.route("/area-privada/comanda")
def area_privada_comanda():
    source = (request.args.get("source") or "").strip().lower()
    draft_id = (request.args.get("draft") or "").strip()
    saved_payload = get_saved_frames_order(draft_id) if source == "frames" and draft_id else None
    order_data = (
        build_frames_order_context(saved_payload, draft_id=draft_id if saved_payload else "")
        if source == "frames"
        else build_canvas_order_context()
    )
    template_name = "area_privada_comanda_marcs.html" if source == "frames" else "area_privada_comanda_v2.html"
    return render_template(
        template_name,
        lang=get_lang(),
        private_modules=build_private_modules(),
        order_data=order_data,
        **build_private_shell_context(),
    )


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
