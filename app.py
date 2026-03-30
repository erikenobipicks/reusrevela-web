import json
import os
import secrets
import smtplib
from datetime import datetime
from email.mime.text import MIMEText
from urllib import error as urllib_error
from urllib import request as urllib_request

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


def get_lang():
    return session.get("lang", "ca")


@app.context_processor
def inject_globals():
    return {"current_year": datetime.now().year}


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
        "pro_access": "Acceso área profesionales",
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
    return render_template("contacte.html", lang=get_lang(), CALC_URL=CALC_URL)


@app.route("/professionals")
def professionals():
    return render_template("professionals.html", lang=get_lang(), CALC_URL=CALC_URL)


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
