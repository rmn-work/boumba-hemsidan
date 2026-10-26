from flask import (Flask, render_template_string, request, redirect, url_for, flash, session, Response,
                   send_file, jsonify)
from flask_mail import Mail, Message
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import os
import random
from datetime import datetime, timedelta
import csv
import io
import qrcode
import time
import secrets
import json
import base64
import warnings
from reportlab.lib.pagesizes import A6, letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from werkzeug.security import generate_password_hash, check_password_hash
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication


app = Flask(__name__)
app.config.update(
    SECRET_KEY=os.environ.get('SECRET_KEY', 'urban-nation-super-secret-key-2026'),
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE='Lax',
    PERMANENT_SESSION_LIFETIME=1800,
    MAIL_SERVER=os.environ.get('MAIL_SERVER', 'smtp.gmail.com'),
    MAIL_PORT=int(os.environ.get('MAIL_PORT', 587)),
    MAIL_USE_TLS=os.environ.get('MAIL_USE_TLS', 'true').lower() in ['true', 'on', '1'],
    MAIL_USERNAME=os.environ.get('MAIL_USERNAME', 'support@urbannation.se'),
    MAIL_PASSWORD=os.environ.get('MAIL_PASSWORD', 'votre_mot_de_passe'),
    MAIL_DEFAULT_SENDER=('URBAN NATION', 'no-reply@urbannation.se')
)

mail = Mail(app)

UPLOAD_FOLDER = 'static/uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
LOGO_URL = "/static/uploads/image1.jpeg"
HERO_DJ_BG = "/static/uploads/image2.png"


limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    storage_uri="memory://",
    default_limits=["200 per day", "50 per hour"]
)

GLOBAL_LIVE = {
    "active": False,
    "title": "URBAN NATION Live Stream",
    "platforms": {
        "youtube": {"active": False, "url": ""},
        "facebook": {"active": False, "url": ""},
        "tiktok": {"active": False, "url": ""},
        "instagram": {"active": False, "url": ""}
    }
}

LIVE_ANALYTICS = {
    "youtube": 0,
    "facebook": 0,
    "tiktok": 0,
    "instagram": 0,
    "direct": 0
}

def is_new_product(product_date_str):
    try:
        product_date = datetime.strptime(product_date_str, "%Y-%m-%d")
        current_date = datetime.now()
        return (current_date - product_date) <= timedelta(days=21)
    except Exception:
        return False


app.jinja_env.globals.update(is_new_product=is_new_product)

PRODUCT_TYPES = [
    {"id": "clothing", "name": "Kläder (Klädesplagg)"},
    {"id": "ticket", "name": "Biljett (Event/Fest)"},
    {"id": "skor", "name": "Skor"}
]

PROMO_CODES = [
    {"code": "URBAN2026", "discount_percent": 10},
    {"code": "VIP20", "discount_percent": 20},
    {"code": "SUMMER15", "discount_percent": 15}
]

PRODUCTS = [
    {
        "id": 1,
        "type": "clothing",
        "name": "Urban Nation Oversized Hoodie",
        "price": 699,
        "discount_price": 499,
        "promo_badge": "BLACK FRIDAY",
        "total_stock": 50,
        "sold": 48,
        "date": "2026-10-01",
        "sizes": ["S", "M", "L", "XL"],
        "colors": ["Svart (Noir)", "Vit (Blanc)", "Grå (Gris)"],
        "image": "https://images.unsplash.com/photo-1556905055-8f358a7a47b2?auto=format&fit=crop&w=500&q=60",
        "images": [
            "https://images.unsplash.com/photo-1556905055-8f358a7a47b2?auto=format&fit=crop&w=500&q=60",
            "https://images.unsplash.com/photo-1509967419530-da38b4704bc6?auto=format&fit=crop&w=500&q=60"
        ],
        "desc": "Skön hoodie i ekologisk bomull med Urban Nation tryck."
    },
    {
        "id": 2,
        "type": "clothing",
        "name": "Nordic Minimalist Jacket",
        "price": 1299,
        "discount_price": None,
        "promo_badge": "",
        "total_stock": 30,
        "sold": 5,
        "date": "2026-09-10",
        "sizes": ["M", "L", "XL"],
        "colors": ["Svart (Noir)", "Marinblå (Bleu Nuit)"],
        "image": "https://images.unsplash.com/photo-1544441893-675973e31985?auto=format&fit=crop&w=500&q=60",
        "images": [
            "https://images.unsplash.com/photo-1544441893-675973e31985?auto=format&fit=crop&w=500&q=60"
        ],
        "desc": "Vindtät jacka för Skandinaviskt klimat."
    },
    {
        "id": 3,
        "type": "ticket",
        "name": "Midnight Techno Rave - Biljett",
        "price": 250,
        "discount_price": 200,
        "promo_badge": "SÄSONGSREA",
        "total_stock": 100,
        "sold": 97,
        "date": "2026-10-10",
        "sizes": [],
        "colors": [],
        "image": "https://images.unsplash.com/photo-1516450360452-9312f5e86fc7?auto=format&fit=crop&w=500&q=60",
        "images": [
            "https://images.unsplash.com/photo-1516450360452-9312f5e86fc7?auto=format&fit=crop&w=500&q=60"
        ],
        "desc": "Inträde till helgens hemliga fest i Stockholm med Urban Nation. Inkl. garderob."
    }
]

EVENTS = [
    {
        "id": 1,
        "title": "Urban Nation Afrobeat - Winter Edition",
        "date": "2026-11-14",
        "time": "23:00 - 05:00",
        "location": "xxx, Luleå",
        "price": 250,
        "image": "https://images.unsplash.com/photo-1516450360452-9312f5e86fc7?auto=format&fit=crop&w=500&q=60",
        "desc": "En exklusiv kväll med internationella DJ:s och spektakulärt ljus. Åldersgräns 20 år."
    },
    {
        "id": 2,
        "title": "Urban Nation Fashion & Hip-Hop Night",
        "date": "2026-12-05",
        "time": "21:00 - 03:00",
        "location": "xxx, Umeå",
        "price": 200,
        "image": "https://images.unsplash.com/photo-1492684223066-81342ee5ff30?auto=format&fit=crop&w=500&q=60",
        "desc": "Lansering av nya streetwear-kollektionen kombinerat med live hip-hop uppträdanden."
    },
    {
        "id": 1,
        "title": "URBAN NATION - Dancehall Music",
        "date": "2026-11-20",
        "location": "Stockholm Club Central",
        "min_age": 18,
        "categories": [
            {"name": "Standard", "price": 250, "total_stock": 200, "sold": 120},
            {"name": "VIP Access", "price": 450, "total_stock": 50, "sold": 42},
            {"name": "Backstage Pass", "price": 750, "total_stock": 15, "sold": 14}
        ]
    }
]

CUSTOMERS = [
    {
        "id": 1,
        "name": "Anna Andersson",
        "first_name": "Anna",
        "last_name": "Andersson",
        "email": "anna.andersson@example.se",
        "phone": "070-123 45 67",
        "address": "Sveavägen 10",
        "postal_code": "111 57",
        "city": "Stockholm",
        "password": "password123",
        "total_orders": 2
    }
]

ORDERS = [
    {
        "id": 98412,
        "customer_email": "anna.andersson@example.se",
        "customer_name": "Anna Andersson",
        "date": "2026-10-10 14:23",
        "order_items": [
            {"id": 1, "name": "Urban Nation Oversized Hoodie (Svart / M)", "price": 499, "type": "clothing"},
            {"id": 3, "name": "Midnight Techno Rave - Biljett (Standard)", "price": 200, "type": "ticket"}
        ],
        "total": 699,
        "shipping": "PostNord Utlämningsställe",
        "tracking_number": "SE123456789PN",
        "status": "Levererad / Avslutad"
    }
]

RETURNS = [
    {
        "id": 101,
        "order_id": 98412,
        "customer_email": "anna.andersson@example.se",
        "reason": "Fel storlek (för stor)",
        "item_name": "Urban Nation Oversized Hoodie (Svart / M)",
        "amount": 499,
        "status": "Under behandling"
    }
]

ADMIN_LOGS = [
    {"timestamp": "2026-10-16 10:00", "action": "Inloggning i adminpanelen", "details": "Admin anslöt till systemet."}
]


def log_admin_action(action, details):
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M")
    ADMIN_LOGS.insert(0, {"timestamp": current_time, "action": action, "details": details})


SHIPPING_OPTIONS = [
    {"id": "postnord_servicepoint", "name": "PostNord Utlämningsställe (1-3 arbetsdagar)", "price": 49},
    {"id": "postnord_home", "name": "PostNord Hemleverans", "price": 99},
    {"id": "dhl_express", "name": "DHL Express", "price": 129},
    {"id": "digital", "name": "Digital leverans (Endast för biljetter - QR-kod)", "price": 0}
]

PAYMENT_METHODS = [
    {"id": "swish", "name": "Swish (Direktbetalning via mobil)", "desc": "Betala direkt med BankID i mobilen."},
    {"id": "klarna", "name": "Klarna - Betala senare / Delbetala", "desc": "Få hem varorna först, betala om 30 dagar."},
    {"id": "card", "name": "Kortbetalning (Visa / Mastercard)", "desc": "Säker betalning med debet-/kreditkort."}
]


def get_current_user():
    user_email = session.get('user_email')
    if user_email:
        return next((c for c in CUSTOMERS if c['email'].lower() == user_email.lower()), None)
    return None


@app.route('/login/<provider>')
def social_login(provider):
    provider_name = provider.capitalize()
    flash(f"Inloggning med {provider_name} är under utveckling.", "info")
    return redirect(url_for('user_login'))


@app.route('/logout')
def user_logout():
    session.pop('user_email', None)
    flash("Du har loggats ut.", "info")
    return redirect(url_for('index'))


def generate_pdf_ticket_buffer(order_id, ticket_name, customer_name, customer_email):
    qr_data = f"TICKET-ORD-{order_id}-{ticket_name}"
    qr_img = qrcode.make(qr_data)
    qr_buffer = io.BytesIO()
    qr_img.save(qr_buffer, format='PNG')
    qr_buffer.seek(0)

    pdf_buffer = io.BytesIO()
    doc = SimpleDocTemplate(pdf_buffer, pagesize=A6, rightMargin=15, leftMargin=15, topMargin=15, bottomMargin=15)
    story = []

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle('TitleStyle', parent=styles['Heading1'], fontSize=16, leading=18,
                                 textColor=colors.HexColor('#111111'), alignment=1)
    subtitle_style = ParagraphStyle('SubTitleStyle', parent=styles['Normal'], fontSize=9,
                                    textColor=colors.HexColor('#666666'), alignment=1)
    event_style = ParagraphStyle('EventStyle', parent=styles['Heading2'], fontSize=11, leading=13,
                                 textColor=colors.HexColor('#111111'), alignment=0)
    text_style = ParagraphStyle('TextStyle', parent=styles['Normal'], fontSize=8, leading=10,
                                textColor=colors.HexColor('#333333'))

    story.append(Paragraph("URBAN NATION", title_style))
    story.append(Paragraph("OFFICIELL EVENTBILJETT • STOCKHOLM", subtitle_style))
    story.append(Spacer(1, 10))

    data = [
        [Paragraph(f"<b>Event/Kategori:</b> {ticket_name}", event_style)],
        [Paragraph(f"<b>Ordernummer:</b> #{order_id}", text_style)],
        [Paragraph(f"<b>Gäst:</b> {customer_name}", text_style)],
        [Paragraph(f"<b>E-post:</b> {customer_email}", text_style)],
        [Paragraph("<b>Giltighet:</b> Gäller för 1 person", text_style)]
    ]

    table = Table(data, colWidths=[240])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#f8f9fa')),
        ('PADDING', (0, 0), (-1, -1), 6),
        ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor('#dddddd')),
    ]))
    story.append(table)
    story.append(Spacer(1, 10))
    story.append(Image(qr_buffer, width=80, height=80))
    story.append(Spacer(1, 5))
    story.append(Paragraph("Skanna denna kod i entrén", subtitle_style))

    doc.build(story)
    pdf_buffer.seek(0)
    return pdf_buffer


def check_event_age_eligibility(birth_date_str, min_age, event_date_str):
    birth_date = datetime.strptime(birth_date_str, "%Y-%m-%d")
    event_date = datetime.strptime(event_date_str, "%Y-%m-%d")
    eligible_date = datetime(birth_date.year + min_age, birth_date.month, birth_date.day)

    if event_date >= eligible_date:
        return True, 0
    else:
        days_remaining = (eligible_date - event_date).days
        return False, days_remaining


EVENTS = []


@app.route('/admin/add_event', methods=['POST'])
def add_event():
    if not session.get('admin_logged'):
        return redirect(url_for('admin_login'))

    global EVENTS
    title = request.form.get('title')
    date = request.form.get('date')
    time = request.form.get('time')
    location = request.form.get('location')
    min_age = int(request.form.get('min_age', 18))
    desc = request.form.get('desc', '')
    base_price = float(request.form.get('price', 250))
    announcement_active = 'announcement_active' in request.form
    announcement_text = request.form.get('announcement_text', '')
    announcement_image_path = None
    announcement_file = request.files.get('announcement_file')
    if announcement_file and announcement_file.filename != '':
        filename = f"announce_{random.randint(1000, 9999)}_{announcement_file.filename}"
        filepath = os.path.join(app.config.get('UPLOAD_FOLDER', 'static/uploads'), filename)
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        announcement_file.save(filepath)
        announcement_image_path = f"/{filepath}"

    image_url = request.form.get('image_url')
    file = request.files.get('image_file')

    if file and file.filename != '':
        filename = f"event_{random.randint(1000, 9999)}_{file.filename}"
        filepath = os.path.join(app.config.get('UPLOAD_FOLDER', 'static/uploads'), filename)
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        file.save(filepath)
        image_path = f"/{filepath}"
    elif image_url:
        image_path = image_url
    else:
        image_path = "/static/uploads/image1.jpeg"

    checked_types = request.form.getlist('ticket_types')
    custom_categories = []

    if 'Early Bird' in checked_types:
        custom_categories.append({
            "name": "Early Bird",
            "price": int(request.form.get('price_early_bird', 200)),
            "total_stock": int(request.form.get('stock_early_bird', 50)),
            "sold": 0
        })

    if 'Standard' in checked_types:
        custom_categories.append({
            "name": "Standard",
            "price": int(request.form.get('price_standard', base_price)),
            "total_stock": int(request.form.get('stock_standard', 150)),
            "sold": 0
        })

    if 'VIP / Fast Track' in checked_types:
        custom_categories.append({
            "name": "VIP / Fast Track",
            "price": int(request.form.get('price_vip', 375)),
            "total_stock": int(request.form.get('stock_vip', 40)),
            "sold": 0
        })

    if not custom_categories:
        custom_categories = [{"name": "Standard", "price": int(base_price), "total_stock": 100, "sold": 0}]

    total_tickets_sum = sum(cat['total_stock'] for cat in custom_categories)
    new_id = max([e['id'] for e in EVENTS], default=0) + 1

    new_event = {
        "id": new_id,
        "title": title,
        "date": date,
        "time": time,
        "location": location,
        "price": base_price,
        "min_age": min_age,
        "desc": desc,
        "total_tickets": total_tickets_sum,
        "categories": custom_categories,
        "image": image_path,
        "announcement_active": announcement_active,
        "announcement_text": announcement_text,
        "announcement_image": announcement_image_path
    }

    EVENTS.append(new_event)
    flash("Evenemang och meddelande har publicerats!", "success")
    return redirect(url_for('admin_dashboard') + '#events')


@app.route('/admin/edit_event/<int:event_id>', methods=['POST'])
def edit_event(event_id):
    if not session.get('admin_logged'):
        return redirect(url_for('admin_login'))

    global EVENTS
    event = next((e for e in EVENTS if e['id'] == event_id), None)
    if event:
        event['title'] = request.form.get('title')
        event['date'] = request.form.get('date')
        event['time'] = request.form.get('time')
        event['location'] = request.form.get('location')
        event['min_age'] = int(request.form.get('min_age', 18))
        event['desc'] = request.form.get('desc', '')
        flash("Evenemanget har uppdaterats!", "success")
    else:
        flash("Kunde inte hitta evenemanget.", "danger")

    return redirect(url_for('admin_dashboard') + '#events')


@app.route('/admin/delete_event/<int:event_id>')
def delete_event(event_id):
    if not session.get('admin_logged'):
        return redirect(url_for('admin_login'))

    global EVENTS
    initial_len = len(EVENTS)
    EVENTS = [e for e in EVENTS if e['id'] != event_id]

    if len(EVENTS) < initial_len:
        flash("Evenemanget har tagits bort.", "success")
    else:
        flash("Kunde inte hitta evenemanget.", "danger")

    return redirect(url_for('admin_dashboard') + '#events')


# --- STOCKAGE GLOBAL POUR L'ANNONCE ---
global_announcement = {"active": False, "text": "", "image": None}


@app.route('/admin/update_announcement', methods=['POST'])
def update_announcement():
    if not session.get('admin_logged'):
        return redirect(url_for('admin_login'))

    global global_announcement
    is_active = 'announcement_active' in request.form
    text = request.form.get('announcement_text', '')
    image_path = global_announcement.get('image')
    file = request.files.get('announcement_file')

    if file and file.filename != '':
        filename = f"announce_{random.randint(1000, 9999)}_{file.filename}"
        filepath = os.path.join(app.config.get('UPLOAD_FOLDER', 'static/uploads'), filename)
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        file.save(filepath)
        image_path = f"/{filepath}"

    global_announcement = {
        "active": is_active,
        "text": text,
        "image": image_path
    }

    flash("Meddelandet har uppdaterats!", "success")
    return redirect(url_for('admin_dashboard') + '#events')


@app.route('/admin/delete_announcement')
def delete_announcement():
    if not session.get('admin_logged'):
        return redirect(url_for('admin_login'))

    global global_announcement
    global_announcement = {"active": False, "text": "", "image": None}

    flash("Meddelandet har raderats.", "info")
    return redirect(url_for('admin_dashboard') + '#events')


SCANNER_TOKENS = {}


@app.route('/admin/generate_scanner_link', methods=['POST'])
def generate_scanner_link():
    if not session.get('admin_logged'): return redirect(url_for('admin_login'))
    token = secrets.token_hex(6)
    password = f"{random.randint(100, 999)}-{random.randint(100, 999)}"
    expires_at = time.time() + (6 * 3600)
    expires_formatted = datetime.fromtimestamp(expires_at).strftime("%Y-%m-%d %H:%M")

    SCANNER_TOKENS[token] = {
        "password": password,
        "expires_at": expires_at,
        "expires_formatted": expires_formatted
    }
    log_admin_action("Scanner-länk skapad",
                     f"En tillfällig scanner-länk (Token: {token}) skapades med 6 timmars giltighet.")
    flash("Ny tidsbegränsad scanner-länk har genererats!", "success")
    return redirect(url_for('admin_dashboard') + '#scanner-section')


@app.route('/scanner/<token>', methods=['GET', 'POST'])
def agent_scanner_page(token):
    token_data = SCANNER_TOKENS.get(token)

    if not token_data:
        return "<h3>❌ Ogiltig eller borttagen scanner-länk.</h3>", 404

    if time.time() > token_data["expires_at"]:
        return "<h3>⏰ Denna scanner-länk har gått ut (giltig i max 6 timmar). Begär en ny länk från administratören.</h3>", 403

    session_key = f"scanner_auth_{token}"

    if request.method == 'POST':
        input_password = request.form.get('password', '').strip()
        if input_password == token_data['password']:
            session[session_key] = True
            flash("Inloggad i skannern!", "success")
            return redirect(url_for('agent_scanner_page', token=token))
        else:
            flash("Felaktigt lösenord för skannern.", "danger")

    if not session.get(session_key):
        return render_template_string(SCANNER_LOGIN_TEMPLATE, token=token, expires=token_data['expires_formatted'])

    return render_template_string(SCANNER_AGENT_TEMPLATE, token=token, expires=token_data['expires_formatted'])


TICKET_SCANS = []
GUESTS = []

@app.route('/api/scan_ticket', methods=['POST'])
def api_scan_ticket():
    data = request.get_json()
    ticket_code = data.get('ticket_code', '').strip()

    if not ticket_code:
        return jsonify({"status": "INVALID", "message": "Ogiltig QR-kod."})

    already_scanned = next((s for s in TICKET_SCANS if s['ticket_code'] == ticket_code), None)
    if already_scanned:
        return jsonify({
            "status": "ALREADY_USED",
            "message": f"Biljetten har redan skannats klockan {already_scanned['timestamp']}!"
        })

    now = datetime.now()
    scan_entry = {
        "ticket_code": ticket_code,
        "guest_name": "Verifierad Gäst",
        "category": "VIP / Standard",
        "min_age": 18,
        "timestamp": now.strftime("%Y-%m-%d %H:%M:%S"),
        "hour": now.hour
    }
    TICKET_SCANS.insert(0, scan_entry)

    return jsonify({
        "status": "VALID",
        "category": scan_entry["category"],
        "guest_name": scan_entry["guest_name"],
        "min_age": scan_entry["min_age"],
        "message": "Biljetten är godkänd."
    })


@app.route('/admin/issue_vip_ticket', methods=['POST'])
def issue_vip_ticket():
    if not session.get('admin_logged'):
        return redirect(url_for('admin_login'))

    guest_email = request.form.get('guest_email', '').strip().lower()
    guest_name = request.form.get('guest_name', '').strip()
    event_name = request.form.get('event_name', '').strip()
    ticket_category = request.form.get('ticket_category', 'VIP Guest')

    if not guest_email or not guest_name:
        flash("E-post och namn krävs för att utfärda GUESTS = [VIP-biljett.", "danger")
        return redirect(url_for('admin_dashboard'))

    order_id = random.randint(10000, 99999)
    ticket_code = f"VIP-{order_id}-{random.randint(1000, 9999)}"

    new_vip_order = {
        "id": order_id,
        "customer_email": guest_email,
        "customer_name": guest_name,
        "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "order_items": [{
            "id": 999,
            "name": f"{event_name} ({ticket_category})",
            "price": 0,
            "quantity": 1,
            "type": "ticket",
            "ticket_code": ticket_code
        }],
        "total": 0,
        "shipping": "Digital Leverans",
        "status": "Godkänd (VIP Inbjudan)"
    }
    ORDERS.insert(0, new_vip_order)
    send_vip_invitation_email(guest_email, guest_name, event_name)
    log_admin_action("VIP Biljett Utfärdad", f"VIP-biljett skickad till {guest_name} ({guest_email}) för {event_name}.")
    flash(f"VIP-biljett har lagts till i kontot för {guest_email} och en inbjudan har skickats!", "success")
    return redirect(url_for('admin_dashboard') + '#vip-section')


@app.route('/api/get_checkin_stats')
def get_checkin_stats():
    selected_event = request.args.get('event', 'ALL')
    show_archive = request.args.get('archive', 'false') == 'true' # Paramètre pour afficher les archives ou non

    if selected_event == 'ALL':
        filtered_scans = TICKET_SCANS
        total_tickets = sum(int(e.get('total_tickets', 100)) for e in events) if 'events' in globals() and events else 100
    else:
        filtered_scans = [s for s in TICKET_SCANS if s.get('category') == selected_event]
        matching_event = next((e for e in events if e.get('title') == selected_event), None) if 'events' in globals() else None
        total_tickets = int(matching_event.get('total_tickets', 100)) if matching_event else 100

    if not show_archive:
        now = datetime.now()
        forty_eight_hours_ago = now - timedelta(hours=48)
        filtered_scans = [
            s for s in filtered_scans
            if datetime.strptime(s['timestamp'], "%Y-%m-%d %H:%M:%S") >= forty_eight_hours_ago
        ]

    checked_in = len(filtered_scans)
    percent = round((checked_in / total_tickets * 100), 1) if total_tickets > 0 else 0
    hours_map = [15, 16, 17, 18, 19, 20, 21, 22, 23, 0, 1, 2, 3, 4, 5, 6, 7]
    hourly_counts = [0] * len(hours_map)

    for scan in filtered_scans:
        scan_hour = scan.get('hour')
        if scan_hour in hours_map:
            idx = hours_map.index(scan_hour)
            hourly_counts[idx] += 1

    return jsonify({
        'checked_in': checked_in,
        'total_tickets': total_tickets,
        'percent': percent,
        'hourly_counts': hourly_counts,
        'history': filtered_scans
    })


@app.route('/admin/add_guest', methods=['POST'])
def add_guest():
    if not session.get('admin_logged'):
        return redirect(url_for('admin_login'))

    global GUESTS
    name = request.form.get('guest_name')
    email = request.form.get('guest_email')
    # Récupération de la liste des événements cochés
    selected_events = request.form.getlist('guest_events')

    new_id = max([g['id'] for g in GUESTS], default=0) + 1

    new_guest = {
        "id": new_id,
        "name": name,
        "email": email,
        "events_invited": selected_events,
        "invitation_sent": False,
        "checked_in": False,
        "checkin_time": None,
        "archived": False,
        "timestamp": datetime.now().isoformat()
    }

    GUESTS.append(new_guest)
    flash("Inbjuden gäst har lagts till!", "success")
    return redirect(url_for('admin_dashboard') + '#guests')


@app.route('/admin/send_invitation/<int:guest_id>', methods=['POST', 'GET'])
def send_invitation(guest_id):
    if not session.get('admin_logged'):
        return redirect(url_for('admin_login'))

    global GUESTS
    for guest in GUESTS:
        if guest['id'] == guest_id:
            guest['invitation_sent'] = True
            event_name = guest['events_invited'][0] if guest['events_invited'] else "URBAN NATION Event"
            guest['invitation_sent'] = True
            send_vip_invitation_email(guest['email'], guest['name'], event_name)
            flash(f"Inbjudan och VIP-biljett har skickats till {guest['name']}!", "success")
            break

    return redirect(url_for('admin_dashboard') + '#guests')


@app.route('/api/scan_guest/<int:guest_id>', methods=['POST'])
def scan_guest(guest_id):
    """Route appelée par le scanner pour valider la présence de l'invité"""
    global GUESTS
    for guest in GUESTS:
        if guest['id'] == guest_id:
            guest['checked_in'] = True
            guest['checkin_time'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            return {"status": "success", "message": f"{guest['name']} är markerad som PRESENT!"}

    return {"status": "error", "message": "Gäst hittades inte."}, 404


@app.route('/admin/archive_guest/<int:guest_id>')
def archive_guest(guest_id):
    if not session.get('admin_logged'):
        return redirect(url_for('admin_login'))

    global GUESTS
    for guest in GUESTS:
        if guest['id'] == guest_id:
            guest['archived'] = not guest.get('archived', False)  # Permet d'archiver ou de restaurer
            status_text = "arkiverats" if guest['archived'] else "återställts"
            flash(f"Gästen har {status_text}.", "info")
            break

    return redirect(url_for('admin_dashboard') + '#guests')


def send_order_confirmation_email(order):
    try:
        subject = f"Orderbekräftelse URBAN NATION #{order['id']}"
        recipient = order['customer_email']

        items_html = ""
        has_tickets = False
        ticket_items = []

        for item in order['order_items']:
            items_html += f"<tr><td style='padding: 8px; border-bottom: 1px solid #eee;'>{item['name']}</td><td style='padding: 8px; border-bottom: 1px solid #eee; text-align: right;'>{item['price']} SEK</td></tr>"
            if item.get('type') == 'ticket':
                has_tickets = True
                ticket_items.append(item)

        html_body = f"""
        <div style="font-family: 'Helvetica Neue', Arial, sans-serif; max-width: 600px; margin: 0 auto; border: 1px solid #e0e0e0; border-radius: 8px; overflow: hidden; background-color: #ffffff;">
            <div style="background-color: #111; color: #ffffff; padding: 25px; text-align: center;">
                <h1 style="margin: 0; font-size: 26px; letter-spacing: 2px; text-transform: uppercase;">URBAN NATION</h1>
                <p style="margin: 5px 0 0 0; color: #ffffff; font-size: 13px; font-weight: bold;">STOCKHOLM</p>
            </div>
            <div style="padding: 25px; color: #333333;">
                <p>Hej <strong>{order.get('customer_name', 'Kund')}</strong>,</p>
                <p>Tack för din beställning! Din order <strong>#{order['id']}</strong> behandlas nu.</p>

                <h3 style="border-bottom: 2px solid #111; padding-bottom: 5px; margin-top: 25px; text-transform: uppercase; font-size: 16px;">Orderöversikt</h3>
                <table style="width: 100%; border-collapse: collapse; margin-bottom: 20px;">
                    <thead>
                        <tr style="background-color: #f8f9fa;">
                            <th style="padding: 10px; text-align: left;">Produkt / Biljett</th>
                            <th style="padding: 10px; text-align: right;">Pris</th>
                        </tr>
                    </thead>
                    <tbody>
                        {items_html}
                    </tbody>
                </table>

                <div style="background-color: #f8f9fa; padding: 15px; border-radius: 5px; margin-bottom: 20px; border-left: 4px solid #111;">
                    <p style="margin: 3px 0;"><strong>Leveranssätt:</strong> {order['shipping']}</p>
                    <p style="margin: 3px 0;"><strong>Spårningsnummer:</strong> {order.get('tracking_number', 'Uppdateras inom kort')}</p>
                    <p style="margin: 10px 0 0 0; font-size: 18px; color: #111;"><strong>Totalt betalat: {order['total']} SEK</strong></p>
                </div>

                {"<p style='background-color: #f8f9fa; color: #111; padding: 12px; border-radius: 5px; font-weight: bold; border: 1px solid #111;'>🎟️ Dina eventbiljetter finns bifogade i detta mejl som PDF.</p>" if has_tickets else ""}

                <p style="margin-top: 30px; font-size: 12px; color: #777777; text-align: center;">
                    URBAN NATION Stockholm | Sveavägen 10, Stockholm | support@urbannation.se
                </p>
            </div>
        </div>
        """

        msg = Message(subject=subject, recipients=[recipient], html=html_body)

        if has_tickets:
            for t_item in ticket_items:
                pdf_buf = generate_pdf_ticket_buffer(order['id'], t_item['name'], order.get('customer_name', 'Gäst'),
                                                     recipient)
                msg.attach(
                    filename=f"UrbanNation_Biljett_{order['id']}.pdf",
                    content_type="application/pdf",
                    data=pdf_buf.getvalue()
                )

        mail.send(msg)
        return True
    except Exception as e:
        return False


@app.route('/admin/export/orders')
def export_orders_csv():
    if not session.get('admin_logged'): return redirect(url_for('admin_login'))
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(
        ['Order ID', 'Datum', 'Kund Name', 'E-post', 'Produkter', 'Totalt (SEK)', 'Frakt', 'Spårningsnummer', 'Status'])
    for o in ORDERS:
        items_str = ", ".join([i['name'] for i in o['order_items']])
        writer.writerow(
            [o['id'], o['date'], o.get('customer_name', ''), o['customer_email'], items_str, o['total'], o['shipping'],
             o.get('tracking_number', '-'), o['status']])
    response = Response(output.getvalue(), mimetype="text/csv")
    response.headers["Content-Disposition"] = "attachment; filename=UrbanNation_Orders_Export.csv"
    return response


@app.route('/admin/export/customers')
def export_customers_csv():
    if not session.get('admin_logged'): return redirect(url_for('admin_login'))
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['Kund ID', 'Namn', 'E-post', 'Telefon', 'Adress', 'Postnummer', 'Stad', 'Totalt Beställningar'])
    for c in CUSTOMERS:
        writer.writerow(
            [c['id'], c['name'], c['email'], c['phone'], c['address'], c['postal_code'], c['city'], c['total_orders']])
    response = Response(output.getvalue(), mimetype="text/csv")
    response.headers["Content-Disposition"] = "attachment; filename=UrbanNation_Kunder_Export.csv"
    return response


@app.route('/admin/export/event_attendees')
def export_event_attendees_csv():
    if not session.get('admin_logged'): return redirect(url_for('admin_login'))
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['Order ID', 'Deltagare Namn', 'E-post', 'Biljett / Event', 'Status'])
    for o in ORDERS:
        for item in o['order_items']:
            if item['type'] == 'ticket':
                writer.writerow(
                    [o['id'], o.get('customer_name', 'Gäst'), o['customer_email'], item['name'], 'Giltig (Betald)'])
    response = Response(output.getvalue(), mimetype="text/csv")
    response.headers["Content-Disposition"] = "attachment; filename=UrbanNation_Event_Deltagare_List.csv"
    return response


@app.route('/admin/export_sales_csv')
def export_sales_csv():
    if not session.get('admin_logged'):
        return redirect(url_for('admin_login'))

    filter_month = request.args.get('month', '')
    filter_year = request.args.get('year', '')

    output = io.StringIO()
    writer = csv.writer(output, delimiter=';')

    writer.writerow([
        'Order ID', 'Datum', 'Kund Namn', 'E-post', 'Produkt/Biljett',
        'Kategori/Typ', 'Antal', 'Pris Inkl. Moms (SEK)', 'Moms %',
        'Moms Belopp (SEK)', 'Belopp Exkl. Moms (SEK)', 'Betalningsstatus'
    ])

    for order in ORDERS:
        order_date_str = order.get('date', '')

        if filter_year and not order_date_str.startswith(filter_year):
            continue
        if filter_month:
            expected_month_str = f"-{filter_month}-"
            if expected_month_str not in order_date_str:
                continue

        for item in order.get('order_items', []):
            item_type = item.get('type', 'clothing')
            vat_rate = 6 if item_type == 'ticket' else 25

            price_incl = item.get('price', 0)
            qty = item.get('quantity', 1)
            total_incl = price_incl * qty

            total_excl = round(total_incl / (1 + (vat_rate / 100)), 2)
            vat_amount = round(total_incl - total_excl, 2)

            writer.writerow([
                order.get('id'),
                order_date_str,
                order.get('customer_name', 'Gäst'),
                order.get('customer_email', ''),
                item.get('name'),
                'Biljett (6% moms)' if item_type == 'ticket' else 'Kläder/Merch (25% moms)',
                qty,
                total_incl,
                f"{vat_rate}%",
                vat_amount,
                total_excl,
                order.get('status', 'Godkänd')
            ])

    output.seek(0)
    filename = f"URBAN_NATION_Moms_Rapport_{filter_year or 'Alla'}_{filter_month or 'Alla'}.csv"
    return Response(
        output.getvalue(),
        mimetype="text/csv; charset=utf-8-sig",
        headers={"Content-Disposition": f"attachment;filename={filename}"}
    )


@app.route('/admin/sales_report_pdf')
def sales_report_pdf():
    if not session.get('admin_logged'):
        return redirect(url_for('admin_login'))

    total_clothing_incl = 0
    total_clothing_vat = 0
    total_ticket_incl = 0
    total_ticket_vat = 0

    detailed_items = []

    for order in ORDERS:
        for item in order.get('order_items', []):
            item_type = item.get('type', 'clothing')
            qty = item.get('quantity', 1)
            total_incl = item.get('price', 0) * qty

            if item_type == 'ticket':
                vat_rate = 6
                total_excl = round(total_incl / 1.06, 2)
                vat_amt = round(total_incl - total_excl, 2)
                total_ticket_incl += total_incl
                total_ticket_vat += vat_amt
            else:
                vat_rate = 25
                total_excl = round(total_incl / 1.25, 2)
                vat_amt = round(total_incl - total_excl, 2)
                total_clothing_incl += total_incl
                total_clothing_vat += vat_amt

            detailed_items.append({
                "order_id": order.get('id'),
                "date": order.get('date'),
                "customer": order.get('customer_name'),
                "item_name": item.get('name'),
                "type_label": "Biljett (6%)" if item_type == 'ticket' else "Kläder/Merch (25%)",
                "vat_rate": vat_rate,
                "total_incl": total_incl,
                "vat_amt": vat_amt,
                "total_excl": total_excl
            })

    total_grand_incl = total_clothing_incl + total_ticket_incl
    total_grand_vat = total_clothing_vat + total_ticket_vat

    return render_template_string(
        SALES_REPORT_PDF_TEMPLATE,
        items=detailed_items,
        total_clothing_incl=total_clothing_incl,
        total_clothing_vat=total_clothing_vat,
        total_ticket_incl=total_ticket_incl,
        total_ticket_vat=total_ticket_vat,
        total_grand_incl=total_grand_incl,
        total_grand_vat=total_grand_vat,
        now_date=datetime.now().strftime("%Y-%m-%d %H:%M")
    )

@app.route('/admin/add_type', methods=['POST'])
def admin_add_type():
    if not session.get('admin_logged'): return redirect(url_for('admin_login'))
    type_name = request.form.get('type_name', '').strip()
    if type_name:
        type_id = type_name.lower().replace(" ", "_").replace("(", "").replace(")", "")
        if not any(t['id'] == type_id for t in PRODUCT_TYPES):
            PRODUCT_TYPES.append({"id": type_id, "name": type_name})
            log_admin_action("Ny kategori skapad", f"Kategorin '{type_name}' lades till.")
            flash(f"Kategorin '{type_name}' har lagts till!", "success")
    return redirect(url_for('admin_dashboard') + '#categories')


@app.route('/admin/edit_type/<string:type_id>', methods=['POST'])
def admin_edit_type(type_id):
    if not session.get('admin_logged'): return redirect(url_for('admin_login'))
    new_name = request.form.get('type_name', '').strip()
    for t in PRODUCT_TYPES:
        if t['id'] == type_id:
            old_name = t['name']
            t['name'] = new_name
            log_admin_action("Kategori uppdaterad", f"Kategori ändrades från '{old_name}' till '{new_name}'.")
            flash(f"Kategorin har uppdaterats!", "success")
            break
    return redirect(url_for('admin_dashboard') + '#categories')


@app.route('/admin/delete_type/<string:type_id>')
def admin_delete_type(type_id):
    if not session.get('admin_logged'): return redirect(url_for('admin_login'))
    global PRODUCT_TYPES
    rem_name = next((t['name'] for t in PRODUCT_TYPES if t['id'] == type_id), type_id)
    PRODUCT_TYPES = [t for t in PRODUCT_TYPES if t['id'] != type_id]
    log_admin_action("Kategori borttagen", f"Kategorin '{rem_name}' raderades.")
    flash("Kategorin har tagits bort.", "info")
    return redirect(url_for('admin_dashboard') + '#categories')


@app.route('/admin/order/resend_email/<int:order_id>')
def admin_resend_email(order_id):
    if not session.get('admin_logged'): return redirect(url_for('admin_login'))
    order = next((o for o in ORDERS if o['id'] == order_id), None)
    if order:
        send_order_confirmation_email(order)
        log_admin_action("E-post skickad igen", f"Orderbekräftelse för order #{order_id} skickades till {order['customer_email']}.")
        flash(f"Orderbekräftelse har skickats igen till {order['customer_email']}!", "success")
    return redirect(url_for('admin_dashboard') + '#orders')


@app.route('/admin/order/update/<int:order_id>', methods=['POST'])
def admin_update_order(order_id):
    if not session.get('admin_logged'): return redirect(url_for('admin_login'))
    new_status = request.form.get('status')
    tracking = request.form.get('tracking_number', '').strip()
    for o in ORDERS:
        if o['id'] == order_id:
            o['status'] = new_status
            if tracking: o['tracking_number'] = tracking
            log_admin_action("Order uppdaterad", f"Order #{order_id} uppdaterades till status: {new_status}.")
            flash(f"Order #{order_id} har uppdaterats!", "success")
            break
    return redirect(url_for('admin_dashboard') + '#orders')


@app.route('/admin/return/process/<int:return_id>/<string:action>')
def admin_process_return(return_id, action):
    if not session.get('admin_logged'): return redirect(url_for('admin_login'))
    ret = next((r for r in RETURNS if r['id'] == return_id), None)
    if ret:
        if action == 'approve':
            ret['status'] = "Godkänd & Återbetald"
            log_admin_action("Retur godkänd", f"Retur #{return_id} för order #{ret['order_id']} godkändes.")
            flash(f"Retur #{return_id} har godkänts och återbetalats.", "success")
        elif action == 'reject':
            ret['status'] = "Avslagen"
            log_admin_action("Retur avslagen", f"Retur #{return_id} för order #{ret['order_id']} avslogs.")
            flash(f"Retur #{return_id} har avslagits.", "warning")
    return redirect(url_for('admin_dashboard') + '#returns')


@app.route('/download_ticket/<int:order_id>/<path:ticket_name>')
def download_ticket_pdf(order_id, ticket_name):
    current_user = get_current_user()
    if not current_user:
        flash("Du måste vara inloggad för att ladda ner biljetten.", "warning")
        return redirect(url_for('user_login'))
    pdf_buffer = generate_pdf_ticket_buffer(order_id, ticket_name, current_user['name'], current_user['email'])
    return send_file(pdf_buffer, as_attachment=True, download_name=f"UrbanNation_Biljett_{order_id}.pdf",
                     mimetype='application/pdf')


@app.route('/')
def index():
    cart = request.cookies.get('cart', '')
    cart_count = len(cart.split(',')) if cart else 0
    current_user = get_current_user()
    top_products = sorted(PRODUCTS, key=lambda x: x['sold'], reverse=True)[:10]

    return render_template_string(
        HOME_TEMPLATE,
        products=PRODUCTS,
        top_products=top_products,
        events=EVENTS,
        product_types=PRODUCT_TYPES,
        cart_count=cart_count,
        current_user=current_user,
        logo_url=LOGO_URL,
        hero_bg=HERO_DJ_BG,
        global_announcement=global_announcement,
        global_live = GLOBAL_LIVE,
    )


@app.route('/add/<int:product_id>', methods=['POST', 'GET'])
def add_to_cart(product_id):
    size = request.form.get('size', 'Standard') if request.method == 'POST' else 'Standard'
    color = request.form.get('color', 'Standard') if request.method == 'POST' else 'Standard'
    ticket_category = request.form.get('ticket_category', '')
    prod = next((p for p in PRODUCTS if p['id'] == product_id), None)
    if not prod: return redirect(url_for('index'))
    item_price = prod['discount_price'] if prod.get('discount_price') else prod['price']
    if prod['type'] == 'ticket' and ticket_category:
        if ticket_category == 'early':
            item_price = int(prod['price'] * 0.8)
        elif ticket_category == 'vip':
            item_price = int(prod['price'] * 1.5)
    cart = request.cookies.get('cart', '')
    cart_list = cart.split(',') if cart else []
    cart_list.append(f"{product_id}:{size}:{color}:{ticket_category}:{item_price}")
    resp = redirect(url_for('index'))
    resp.set_cookie('cart', ','.join(cart_list))
    flash("Produkten/Biljetten har lagts till i varukorgen!", "success")
    return resp


@app.route('/login', methods=['GET', 'POST'])
@limiter.limit("10 per minute")
def user_login():
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password')
        customer = next((c for c in CUSTOMERS if c['email'].lower() == email), None)

        if customer:
            stored_pwd = customer.get('password', '')
            is_valid = check_password_hash(stored_pwd, password) if stored_pwd.startswith('pbkdf2:') else (stored_pwd == password)

            if is_valid:
                session['user_email'] = customer['email']
                flash(f"Välkommen tillbaka, {customer['name']}!", "success")
                return redirect(url_for('user_account'))

        flash("Felaktig e-postadress eller lösenord.", "danger")

    return render_template_string(USER_LOGIN_TEMPLATE, logo_url=LOGO_URL)


ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD', 'suisse2026')


@app.route('/register', methods=['GET', 'POST'])
def user_register():
    if request.method == 'POST':
        first_name = request.form.get('first_name', '').strip()
        last_name = request.form.get('last_name', '').strip()
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        phone = request.form.get('phone', '').strip()
        address = request.form.get('address', '').strip()
        postal_code = request.form.get('postal_code', '').strip()
        city = request.form.get('city', '').strip()

        if not password or len(password) < 6:
            flash("Lösenordet måste vara minst 6 tecken långt.", "danger")
        elif password != confirm_password:
            flash("Lösenorden matchar inte.", "danger")
        elif any(c['email'].lower() == email for c in CUSTOMERS):
            flash("Det finns redan ett konto registrerat med denna e-postadress.", "warning")
        else:
            full_name = f"{first_name} {last_name}".strip()
            new_id = max([c['id'] for c in CUSTOMERS]) + 1 if CUSTOMERS else 1
            hashed_password = generate_password_hash(password, method='pbkdf2:sha256', salt_length=16)
            CUSTOMERS.append({
                "id": new_id,
                "name": full_name,
                "first_name": first_name,
                "last_name": last_name,
                "email": email,
                "phone": phone,
                "address": address,
                "postal_code": postal_code,
                "city": city,
                "password": hashed_password,
                "total_orders": 0
            })

            session['user_email'] = email
            flash("Ditt konto har skapats! Välkommen till URBAN NATION.", "success")
            return redirect(url_for('user_account'))

    return render_template_string(USER_REGISTER_TEMPLATE, logo_url=LOGO_URL)


@app.route('/account', methods=['GET', 'POST'])
def user_account():
    current_user = get_current_user()
    if not current_user:
        flash("Du måste logga in för att se ditt konto.", "warning")
        return redirect(url_for('user_login'))
    if request.method == 'POST':
        current_user['first_name'] = request.form.get('first_name')
        current_user['last_name'] = request.form.get('last_name')
        current_user['name'] = f"{current_user['first_name']} {current_user['last_name']}".strip()
        current_user['phone'] = request.form.get('phone')
        current_user['address'] = request.form.get('address')
        current_user['postal_code'] = request.form.get('postal_code')
        current_user['city'] = request.form.get('city')
        flash("Dina kontouppgifter har uppdaterats!", "success")
    user_orders = [o for o in ORDERS if o['customer_email'].lower() == current_user['email'].lower()]
    user_returns = [r for r in RETURNS if r['customer_email'].lower() == current_user['email'].lower()]
    return render_template_string(USER_ACCOUNT_TEMPLATE, current_user=current_user, orders=user_orders,
                                  returns=user_returns, logo_url=LOGO_URL)


@app.route('/admin/login', methods=['GET', 'POST'])
@limiter.limit("2 per 5 minutes")
def admin_login():
    if request.method == 'POST':
        input_password = request.form.get('password', '')

        if input_password == ADMIN_PASSWORD:
            session.clear()
            session['admin_logged'] = True
            log_admin_action("Inloggning i adminpanelen", f"Admin anslöt framgångsrikt från IP: {request.remote_addr}.")
            return redirect(url_for('admin_dashboard'))
        else:
            log_admin_action("MISSLYCKAD INLOGGNING", f"Felaktigt adminlösenord från IP: {request.remote_addr}.")
            flash("Fel lösenord.", "danger")

    return render_template_string(ADMIN_LOGIN_TEMPLATE, logo_url=LOGO_URL)


@app.route('/admin', methods=['GET', 'POST'])
def admin_dashboard():
    if not session.get('admin_logged'):
        return redirect(url_for('admin_login'))

    show_all_archives = request.args.get('archive', 'false') == 'true'

    if show_all_archives:
        displayed_guests = GUESTS
    else:
        displayed_guests = [g for g in GUESTS if not g.get('archived', False)]

    total_revenue = sum(p['sold'] * (p['discount_price'] if p.get('discount_price') else p['price']) for p in PRODUCTS)
    total_items_sold = sum(p['sold'] for p in PRODUCTS)
    total_tickets_sold = sum(p['sold'] for p in PRODUCTS if p['type'] == 'ticket')
    ticket_revenue = sum(
        p['sold'] * (p['discount_price'] if p.get('discount_price') else p['price']) for p in PRODUCTS if
        p['type'] == 'ticket')
    pending_transfers = getattr(app, 'PENDING_TRANSFERS', [])

    product_names = [p.get('name') for p in PRODUCTS]
    product_stocks = [p.get('total_stock', 0) for p in PRODUCTS]
    product_sold = [p.get('sold', 0) for p in PRODUCTS]

    return render_template_string(ADMIN_DASHBOARD_TEMPLATE,
                                  products=PRODUCTS,
                                  events=EVENTS,
                                  product_types=PRODUCT_TYPES,
                                  customers=CUSTOMERS,
                                  logs=ADMIN_LOGS,
                                  orders=ORDERS,
                                  returns=RETURNS,
                                  promo_codes=PROMO_CODES,
                                  scanner_tokens=SCANNER_TOKENS,
                                  ticket_scans=TICKET_SCANS,
                                  guests=displayed_guests,
                                  global_announcement=global_announcement,
                                  global_live=GLOBAL_LIVE,
                                  pending_transfers=pending_transfers,
                                  total_revenue=total_revenue,
                                  total_items_sold=total_items_sold,
                                  total_tickets_sold=total_tickets_sold,
                                  ticket_revenue=ticket_revenue,
                                  logo_url=LOGO_URL)


@app.route('/admin/customer/update/<int:customer_id>', methods=['POST'])
def admin_update_customer(customer_id):
    if not session.get('admin_logged'):
        return redirect(url_for('admin_login'))

    cust = next((c for c in CUSTOMERS if c['id'] == customer_id), None)
    if cust:
        old_email = cust['email']
        cust['first_name'] = request.form.get('first_name', cust.get('first_name', ''))
        cust['last_name'] = request.form.get('last_name', cust.get('last_name', ''))
        cust['name'] = f"{cust['first_name']} {cust['last_name']}".strip()
        cust['email'] = request.form.get('email', cust['email']).strip().lower()
        cust['phone'] = request.form.get('phone', cust.get('phone', ''))
        cust['address'] = request.form.get('address', cust.get('address', ''))
        cust['postal_code'] = request.form.get('postal_code', cust.get('postal_code', ''))
        cust['city'] = request.form.get('city', cust.get('city', ''))
        log_admin_action(
            "Kunduppgifter uppdaterade",
            f"Kund #{customer_id} ({old_email}) uppdaterades av admin."
        )
        flash(f"Kunduppgifter för #{customer_id} har uppdaterats!", "success")

    return redirect(url_for('admin_dashboard') + '#customers-section')


@app.route('/admin/add_promo', methods=['POST'])
def admin_add_promo():
    if not session.get('admin_logged'): return redirect(url_for('admin_login'))
    code = request.form.get('code', '').strip().upper()
    discount = request.form.get('discount')
    if code and discount:
        PROMO_CODES.append({"code": code, "discount_percent": int(discount)})
        log_admin_action("Rabattkod skapad", f"Rabattkod {code} (-{discount}%) skapades.")
        flash(f"Rabattkod {code} har skapats!", "success")
    return redirect(url_for('admin_dashboard') + '#promos')


@app.route('/admin/assign_promo_badge', methods=['POST'])
def admin_assign_promo_badge():
    if not session.get('admin_logged'): return redirect(url_for('admin_login'))
    product_id = int(request.form.get('product_id'))
    promo_badge = request.form.get('promo_badge', '').strip()
    discount_price = request.form.get('discount_price', '').strip()

    prod = next((p for p in PRODUCTS if p['id'] == product_id), None)
    if prod:
        prod['promo_badge'] = promo_badge
        prod['discount_price'] = int(discount_price) if discount_price.isdigit() else None
        log_admin_action("Kampanj & Pris uppdaterat", f"Produkt '{prod['name']}' uppdaterades med kampanjbricka '{promo_badge}' och reapris {discount_price}.")
        flash(f"Kampanj och pris för '{prod['name']}' har uppdaterats!", "success")
    return redirect(url_for('admin_dashboard') + '#promos')


@app.route('/admin/clear_promo_badge/<int:product_id>')
def admin_clear_promo_badge(product_id):
    if not session.get('admin_logged'): return redirect(url_for('admin_login'))
    prod = next((p for p in PRODUCTS if p['id'] == product_id), None)
    if prod:
        log_admin_action("Kampanj borttagen", f"Kampanjbricka och reapris raderades för produkt '{prod['name']}'.")
        prod['promo_badge'] = ""
        prod['discount_price'] = None
        flash(f"Kampanjbrickan och reapriset för '{prod['name']}' har tagits bort!", "info")
    return redirect(url_for('admin_dashboard') + '#promos')


@app.route('/admin/update_stats', methods=['POST'])
def admin_update_stats():
    if not session.get('admin_logged'): return redirect(url_for('admin_login'))
    product_id = int(request.form.get('product_id'))
    extra_sold = int(request.form.get('extra_sold', 0))
    target_product = next((p for p in PRODUCTS if p['id'] == product_id), None)
    if target_product:
        target_product['sold'] += extra_sold
        log_admin_action("Statistik uppdaterad", f"La till {extra_sold} sålda enheter för '{target_product['name']}'.")
        flash(f"Statistiken har uppdaterats framgångsrikt!", "success")
    return redirect(url_for('admin_dashboard') + '#stats')


@app.route('/admin/add_product', methods=['POST'])
def admin_add_product():
    if not session.get('admin_logged'): return redirect(url_for('admin_login'))
    name = request.form.get('name')
    price = int(request.form.get('price'))
    disc = request.form.get('discount_price')
    discount_price = int(disc) if disc else None
    promo_badge = request.form.get('promo_badge', '').strip()
    total_stock = int(request.form.get('total_stock', 50))
    prod_type = request.form.get('type')
    desc = request.form.get('desc')
    sizes = [s.strip() for s in request.form.get('sizes', '').split(',') if s.strip()]
    colors = [c.strip() for c in request.form.get('colors', '').split(',') if c.strip()]

    img1_url = request.form.get('image_url')
    file = request.files.get('image_file')
    if file and file.filename != '':
        filename = f"{random.randint(1000, 9999)}_{file.filename}"
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        image_path = f"/{filepath}"
    elif img1_url:
        image_path = img1_url
    else:
        image_path = "https://images.unsplash.com/photo-1523381210434-271e8be1f52b?auto=format&fit=crop&w=500&q=60"

    new_id = max([p['id'] for p in PRODUCTS]) + 1 if PRODUCTS else 1
    PRODUCTS.append({
        "id": new_id, "type": prod_type, "name": name, "price": price,
        "discount_price": discount_price, "promo_badge": promo_badge, "total_stock": total_stock,
        "sold": 0, "date": datetime.now().strftime("%Y-%m-%d"), "sizes": sizes, "colors": colors,
        "image": image_path, "images": [image_path], "desc": desc
    })
    log_admin_action("Produkt tillagd", f"Ny produkt '{name}' skapades i systemet.")
    flash("Ny produkt/biljett har lagts till!", "success")
    return redirect(url_for('admin_dashboard') + '#products')


@app.route('/admin/delete_product/<int:product_id>')
def admin_delete_product(product_id):
    if not session.get('admin_logged'): return redirect(url_for('admin_login'))
    global PRODUCTS
    prod = next((p for p in PRODUCTS if p['id'] == product_id), None)
    p_name = prod['name'] if prod else f"ID {product_id}"
    PRODUCTS = [p for p in PRODUCTS if p['id'] != product_id]
    log_admin_action("Produkt borttagen", f"Produkten '{p_name}' raderades.")
    flash("Produkten har tagits bort.", "info")
    return redirect(url_for('admin_dashboard') + '#products')


@app.route('/admin/logout')
def admin_logout():
    session.pop('admin_logged', None)
    return redirect(url_for('index'))


@app.route('/checkout', methods=['GET', 'POST'])
def checkout():
    cart = request.cookies.get('cart', '')
    if not cart:
        flash("Din varukorg är tom.", "warning")
        return redirect(url_for('index'))

    cart_items_dict = {}
    raw_cart_list = [entry for entry in cart.split(',') if entry]
    subtotal = 0

    for idx, entry in enumerate(raw_cart_list):
        parts = entry.split(':')
        pid = int(parts[0]) if parts[0].isdigit() else 0
        size = parts[1] if len(parts) > 1 else 'Standard'
        color = parts[2] if len(parts) > 2 else 'Standard'
        ticket_cat = parts[3] if len(parts) > 3 else ''
        custom_price = float(parts[4]) if len(parts) > 4 and parts[4].replace('.', '', 1).isdigit() else None

        prod = next((p for p in PRODUCTS if p['id'] == pid), None)
        if prod:
            item_price = custom_price if custom_price is not None else (
                prod['discount_price'] if prod.get('discount_price') else prod['price'])
            item_display_name = prod['name']
            if prod['type'] == 'ticket' and ticket_cat:
                if ticket_cat == 'early':
                    item_display_name += " (Early Bird)"
                elif ticket_cat == 'vip':
                    item_display_name += " (VIP / Fast Track)"
                else:
                    item_display_name += " (Standard)"
            else:
                details = []
                if size and size != 'Standard': details.append(f"Storlek: {size}")
                if color and color != 'Standard': details.append(f"Färg: {color}")
                if details: item_display_name += f" ({', '.join(details)})"

            key = f"{pid}_{size}_{color}_{ticket_cat}_{item_price}"
            if key in cart_items_dict:
                cart_items_dict[key]['quantity'] += 1
                cart_items_dict[key]['total_price'] += item_price
            else:
                cart_items_dict[key] = {
                    "id": prod['id'],
                    "name": item_display_name,
                    "price": item_price,
                    "quantity": 1,
                    "total_price": item_price,
                    "type": prod['type'],
                    "cookie_index": idx
                }
            subtotal += item_price

    cart_items = list(cart_items_dict.values())
    total_items_count = sum(item['quantity'] for item in cart_items)

    applied_discount = 0
    promo_code_applied = ""
    promo_input = request.form.get('promo_code', '').strip().upper() if request.method == 'POST' else request.args.get(
        'promo_code', '').strip().upper()
    if promo_input:
        found_promo = next((p for p in PROMO_CODES if p['code'] == promo_input), None)
        if found_promo:
            applied_discount = round((subtotal * found_promo['discount_percent']) / 100, 2)
            promo_code_applied = found_promo['code']
            flash(f"Rabattkod tillämpad (-{found_promo['discount_percent']}%)!", "success")
        else:
            flash("Ogiltig rabattkod.", "danger")

    discounted_subtotal = max(0, subtotal - applied_discount)
    vat_amount = round(discounted_subtotal - (discounted_subtotal / 1.25), 2)
    current_user = get_current_user()

    if request.method == 'POST' and 'submit_order' in request.form:
        first_name = request.form.get('first_name', '').strip()
        last_name = request.form.get('last_name', '').strip()
        name = f"{first_name} {last_name}".strip()
        email = request.form.get('email', '').strip().lower()
        confirm_email = request.form.get('confirm_email', '').strip().lower()
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        phone = request.form.get('phone')
        address = request.form.get('address')
        postal_code = request.form.get('postal_code')
        city = request.form.get('city')
        shipping_id = request.form.get('shipping')
        payment_id = request.form.get('payment')
        birth_date_str = request.form.get('birth_date', '')

        if email != confirm_email:
            flash("E-postadresserna matchar inte.", "danger")
            return redirect(url_for('checkout'))

        if not current_user and password != confirm_password:
            flash("Lösenorden matchar inte.", "danger")
            return redirect(url_for('checkout'))

        has_tickets = any(item['type'] == 'ticket' for item in cart_items)
        if has_tickets:
            if not birth_date_str:
                flash("Födelsedatum krävs för att köpa eventbiljetter.", "danger")
                return redirect(url_for('checkout'))

            min_required_age = 18
            event_date_str = datetime.now().strftime("%Y-%m-%d")
            for item in cart_items:
                if item['type'] == 'ticket':
                    match_ev = next((e for e in EVENTS if e['title'].lower() in item['name'].lower()), None)
                    if match_ev:
                        min_required_age = match_ev.get('min_age', 18)
                        event_date_str = match_ev.get('date', datetime.now().strftime("%Y-%m-%d"))

            is_eligible, days_left = check_event_age_eligibility(birth_date_str, min_required_age, event_date_str)
            if not is_eligible:
                flash(
                    f"Köp blockerat: Du uppfyller inte åldersgränsen ({min_required_age} år) för detta event. Det är {days_left} dagar kvar tills du når åldersgränsen.",
                    "danger")
                return redirect(url_for('checkout'))

        existing_customer = next((c for c in CUSTOMERS if c['email'].lower() == email), None)
        if existing_customer:
            existing_customer['total_orders'] += 1
            if password: existing_customer['password'] = password
        else:
            new_cust_id = max([c['id'] for c in CUSTOMERS]) + 1 if CUSTOMERS else 1
            existing_customer = {
                "id": new_cust_id, "name": name, "first_name": first_name, "last_name": last_name,
                "email": email, "phone": phone, "address": address, "postal_code": postal_code,
                "city": city, "password": password if password else f"Urban{random.randint(1000, 9999)}",
                "total_orders": 1
            }
            CUSTOMERS.append(existing_customer)

        session['user_email'] = email
        selected_shipping = next((s for s in SHIPPING_OPTIONS if s['id'] == shipping_id), SHIPPING_OPTIONS[0])
        total = discounted_subtotal + selected_shipping['price']
        order_id = random.randint(10000, 99999)

        for item in cart_items:
            target_p = next((p for p in PRODUCTS if p['id'] == item['id']), None)
            if target_p: target_p['sold'] += item['quantity']

        new_order = {
            "id": order_id, "customer_email": email, "customer_name": name,
            "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "order_items": [
                {"id": i['id'], "name": i['name'], "price": i['price'], "quantity": i['quantity'], "type": i['type']}
                for i in
                cart_items],
            "total": total, "shipping": selected_shipping['name'],
            "tracking_number": f"SE{random.randint(10000000, 99999999)}PN",
            "status": "Under behandling"
        }
        ORDERS.insert(0, new_order)
        send_order_confirmation_email(new_order)

        resp = render_template_string(SUCCESS_TEMPLATE,
                                      order_id=order_id, name=name, email=email, phone=phone,
                                      address=address, postal_code=postal_code, city=city,
                                      shipping=selected_shipping, payment=payment_id,
                                      items=cart_items, subtotal=subtotal, discount=applied_discount,
                                      vat_amount=vat_amount, total=total, current_user=existing_customer,
                                      logo_url=LOGO_URL)
        resp_obj = app.make_response(resp)
        resp_obj.set_cookie('cart', '', expires=0)
        return resp_obj

    return render_template_string(CHECKOUT_TEMPLATE, items=cart_items, total_items_count=total_items_count,
                                  subtotal=subtotal, applied_discount=applied_discount,
                                  promo_code_applied=promo_code_applied, discounted_subtotal=discounted_subtotal,
                                  vat_amount=vat_amount, shipping_options=SHIPPING_OPTIONS,
                                  payment_methods=PAYMENT_METHODS, current_user=current_user,
                                  logo_url=LOGO_URL)


@app.route('/order/success/<int:order_id>')
def order_success(order_id):
    order = next((o for o in ORDERS if o['id'] == order_id), None)
    if not order:
        return redirect(url_for('index'))
    return render_template_string(ORDER_SUCCESS_TEMPLATE, order=order, logo_url=LOGO_URL)


@app.route('/cart/increase/<int:index>')
def cart_increase(index):
    cart = request.cookies.get('cart', '')
    if not cart: return redirect(url_for('checkout'))
    cart_list = [item for item in cart.split(',') if item]
    if 0 <= index < len(cart_list):
        cart_list.append(cart_list[index])
    resp = redirect(url_for('checkout'))
    resp.set_cookie('cart', ','.join(cart_list))
    return resp


@app.route('/cart/decrease/<int:index>')
def cart_decrease(index):
    cart = request.cookies.get('cart', '')
    if not cart: return redirect(url_for('checkout'))
    cart_list = [item for item in cart.split(',') if item]
    if 0 <= index < len(cart_list):
        cart_list.pop(index)
    resp = redirect(url_for('checkout'))
    resp.set_cookie('cart', ','.join(cart_list))
    return resp


@app.route('/cart/clear')
def cart_clear():
    resp = redirect(url_for('checkout'))
    resp.set_cookie('cart', '', expires=0) # Tömmer hela varukorgen
    return resp


@app.route('/download_apple_wallet/<int:order_id>/<path:item_name>')
def download_apple_wallet(order_id, item_name):
    if not session.get('user'):
        return redirect(url_for('login'))

    user = session['user']
    ticket_code = f"TICKET-{order_id}-{item_name}"
    pass_data = {
        "formatVersion": 1,
        "passTypeIdentifier": "pass.com.urbannation.tickets",
        "serialNumber": f"UN-{order_id}",
        "teamIdentifier": "URBANNATION123",
        "webServiceURL": "https://urbannation.se/api/passes/",
        "authenticationToken": "vx7wge41893122",
        "organizationName": "URBAN NATION",
        "description": "Entrébiljett till URBAN NATION Event",
        "logoText": "URBAN NATION",
        "foregroundColor": "rgb(255, 255, 255)",
        "backgroundColor": "rgb(15, 15, 15)",
        "eventTicket": {
            "primaryFields": [
                {
                    "key": "event",
                    "label": "EVENEMANG",
                    "value": item_name
                }
            ],
            "secondaryFields": [
                {
                    "key": "passenger",
                    "label": "GÄST",
                    "value": user.get('name', 'Gäst')
                }
            ],
            "auxiliaryFields": [
                {
                    "key": "order",
                    "label": "ORDER ID",
                    "value": f"#{order_id}"
                }
            ]
        },
        "barcode": {
            "format": "PKBarcodeFormatQR",
            "message": ticket_code,
            "messageEncoding": "iso-8859-1"
        }
    }

    json_bytes = json.dumps(pass_data, indent=2).encode('utf-8')
    buffer = io.BytesIO(json_bytes)
    buffer.seek(0)

    filename = f"URBAN_NATION_AppleWallet_{order_id}.pkpass"
    return Response(
        buffer.getvalue(),
        mimetype="application/vnd.apple.pkpass",
        headers={"Content-Disposition": f"attachment;filename={filename}"}
    )


@app.route('/add_google_wallet/<int:order_id>/<path:item_name>')
def add_google_wallet(order_id, item_name):
    if not session.get('user'):
        return redirect(url_for('login'))

    user = session['user']
    ticket_code = f"TICKET-{order_id}-{item_name}"
    google_pass_payload = {
        "iss": "urbannation-wallet@developer.gserviceaccount.com",
        "aud": "google",
        "typ": "savetowallet",
        "payload": {
            "eventTicketObjects": [
                {
                    "id": f"3388000000022119933.UN_TICKET_{order_id}",
                    "classId": "3388000000022119933.URBAN_NATION_EVENT",
                    "state": "ACTIVE",
                    "ticketHolderName": user.get('name', 'Gäst'),
                    "ticketNumber": ticket_code,
                    "barcode": {
                        "type": "QR_CODE",
                        "value": ticket_code
                    }
                }
            ]
        }
    }

    encoded_payload = base64.b64encode(json.dumps(google_pass_payload).encode('utf-8')).decode('utf-8')
    google_wallet_url = f"https://pay.google.com/gp/v/save/{encoded_payload}"
    return redirect(google_wallet_url)


@app.route('/transfer_ticket/<int:order_id>/<path:item_name>', methods=['POST'])
def transfer_ticket(order_id, item_name):
    if not session.get('user'):
        flash("Du måste vara inloggad för att överföra en biljett.", "warning")
        return redirect(url_for('login'))

    current_user_email = session['user']['email'].lower()
    recipient_email = request.form.get('recipient_email', '').strip().lower()

    if not recipient_email or recipient_email == current_user_email:
        flash("Ogiltig mottagare.", "danger")
        return redirect(url_for('user_account'))

    original_order = next(
        (o for o in ORDERS if o.get('id') == order_id and o.get('customer_email', '').lower() == current_user_email),
        None)
    ticket_item = next((it for it in original_order.get('order_items', []) if
                        it.get('name') == item_name and it.get('type') == 'ticket') if original_order else None, None)

    if not ticket_item:
        flash("Biljetten kunde inte hittas.", "danger")
        return redirect(url_for('user_account'))

    old_ticket_code = ticket_item.get('ticket_code', f"TICKET-{order_id}-{item_name}")
    if any(s.get('ticket_code') == old_ticket_code for s in TICKET_SCANS):
        flash("❌ Denna biljett har redan skannats i entrén och kan inte överföras.", "danger")
        return redirect(url_for('user_account'))

    transfer_request = {
        "id": random.randint(10000, 99999),
        "order_id": order_id,
        "sender_email": current_user_email,
        "sender_name": session['user'].get('name', 'Gäst'),
        "recipient_email": recipient_email,
        "ticket_name": item_name,
        "old_ticket_code": old_ticket_code,
        "request_date": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "status": "PENDING"
    }

    if not hasattr(app, 'PENDING_TRANSFERS'):
        app.PENDING_TRANSFERS = []
    app.PENDING_TRANSFERS.insert(0, transfer_request)

    log_admin_action("Överföringsbegäran",
                     f"Överföring begärd av {current_user_email} till {recipient_email} för '{item_name}'.")
    flash("⏳ Din överföringsbegäran har skickats till administratören för godkännande.", "info")
    return redirect(url_for('user_account'))


@app.route('/admin/process_transfer/<int:transfer_id>/<action>', methods=['POST'])
def process_transfer(transfer_id, action):
    if not session.get('admin_logged'):
        return redirect(url_for('admin_login'))

    pending_list = getattr(app, 'PENDING_TRANSFERS', [])
    req = next((r for r in pending_list if r['id'] == transfer_id and r['status'] == 'PENDING'), None)

    if not req:
        flash("Överföringsbegäran hittades inte.", "danger")
        return redirect(url_for('admin_dashboard'))

    if action == 'approve':
        req['status'] = 'APPROVED'

        orig_order = next((o for o in ORDERS if o.get('id') == req['order_id']), None)
        if orig_order:
            orig_order['order_items'] = [it for it in orig_order['order_items'] if it.get('name') != req['ticket_name']]

        new_order_id = random.randint(10000, 99999)
        new_ticket_code = f"TRANSFER-{new_order_id}-{random.randint(1000, 9999)}"

        transferred_order = {
            "id": new_order_id,
            "customer_email": req['recipient_email'],
            "customer_name": req['recipient_email'].split('@')[0].capitalize(),
            "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "order_items": [{
                "id": 999,
                "name": f"{req['ticket_name']} (Överförd)",
                "price": 0,
                "quantity": 1,
                "type": "ticket",
                "ticket_code": new_ticket_code
            }],
            "total": 0,
            "shipping": "Digital Överföring",
            "status": f"Godkänd överföring från {req['sender_name']}"
        }
        ORDERS.insert(0, transferred_order)
        log_admin_action("Överföring Godkänd", f"Biljett godkändes för överföring till {req['recipient_email']}.")
        flash(f"✅ Överföringen till {req['recipient_email']} har godkänts!", "success")

    elif action == 'reject':
        req['status'] = 'REJECTED'
        log_admin_action("Överföring Avslagen", f"Överföring från {req['sender_email']} avslogs.")
        flash(f"❌ Överföringsbegäran avslogs.", "warning")

    return redirect(url_for('admin_dashboard') + '#transfers-section')

def send_ticket_transfer_email(recipient_email, sender_name, event_name):
    print(f"[EMAIL TRANSFERT] Skickat till {recipient_email}: Hej! {sender_name} har överfört sin biljett för '{event_name}' till dig på URBAN NATION. Logga in eller skapa ett konto med denna e-post för att hämta din nya QR-kod!")

@app.context_processor
def inject_global_vars():
    return dict(
        global_live=GLOBAL_LIVE,
        live_analytics=LIVE_ANALYTICS
    )

@app.route('/admin/update_live', methods=['POST'])
def update_live():
    if not session.get('admin_logged'):
        return redirect(url_for('admin_login'))

    GLOBAL_LIVE['active'] = 'live_active' in request.form
    GLOBAL_LIVE['title'] = request.form.get('live_title', 'URBAN NATION Live Stream')

    # Mise à jour de l'état d'activation et des URLs de chaque plateforme
    for p in ['youtube', 'facebook', 'tiktok', 'instagram']:
        GLOBAL_LIVE['platforms'][p]['active'] = f'active_{p}' in request.form
        GLOBAL_LIVE['platforms'][p]['url'] = request.form.get(f'url_{p}', '').strip()

    return redirect('/admin#live-section')


@app.route('/api/get_live_analytics')
def get_live_analytics():
    """Renvoie les statistiques actuelles de visionnage pour le Dashboard Admin."""
    return jsonify(LIVE_ANALYTICS)


@app.route('/api/track_live_view', methods=['POST'])
def track_live_view():
    """Incrémente le compteur de vues lorsqu'un internaute clique sur un onglet de plateforme."""
    data = request.get_json() or {}
    platform = data.get('platform', '').lower()

    if platform in LIVE_ANALYTICS:
        LIVE_ANALYTICS[platform] += 1
        return jsonify({"status": "success", "analytics": LIVE_ANALYTICS})

    return jsonify({"status": "error", "message": "Plattform hittades inte"}), 400


PASSWORD_RESET_TOKENS = {}


@app.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        # Rechercher le client par son e-mail
        user = next((c for c in CUSTOMERS if c.get('email', '').lower() == email), None)

        if user:
            # Générer un token unique sécurisé
            token = secrets.token_urlsafe(32)
            PASSWORD_RESET_TOKENS[token] = email

            # En production, envoyez un vrai e-mail. Ici, on simule l'affichage du lien de réinitialisation.
            reset_link = url_for('reset_password', token=token, _external=True)
            flash(f"Un e-mail de réinitialisation a été simulé. Lien : {reset_link}", "success")
        else:
            flash("Aucun compte associé à cet e-mail n'a été trouvé.", "danger")

        return redirect(url_for('forgot_password'))

    return render_template_string(FORGOT_PASSWORD_TEMPLATE)


@app.route('/reset-password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    if token not in PASSWORD_RESET_TOKENS:
        flash("Ce lien de réinitialisation est invalide ou a expiré.", "danger")
        return redirect(url_for('index'))

    if request.method == 'POST':
        new_password = request.form.get('new_password')
        email = PASSWORD_RESET_TOKENS[token]

        # Mettre à jour le mot de passe du client
        for c in CUSTOMERS:
            if c.get('email', '').lower() == email.lower():
                c[
                    'password'] = new_password  # Pensez à hasher le mot de passe avec werkzeug.security si vous l'utilisez
                break

        # Supprimer le token après utilisation
        del PASSWORD_RESET_TOKENS[token]
        flash("Votre mot de passe a été mis à jour avec succès. Vous pouvez vous connecter.", "success")
        return redirect(url_for('index'))

    return render_template_string(RESET_PASSWORD_TEMPLATE, token=token)


@app.route('/change-password', methods=['POST'])
def change_password():
    if not session.get('user_logged'):
        flash("Veuillez vous connecter pour modifier votre mot de passe.", "danger")
        return redirect(url_for('index'))

    user_email = session.get('user_email')
    current_password = request.form.get('current_password')
    new_password = request.form.get('new_password')

    user = next((c for c in CUSTOMERS if c.get('email', '').lower() == user_email.lower()), None)

    if user and user.get('password') == current_password:
        user['password'] = new_password
        flash("Votre mot de passe a été modifié avec succès.", "success")
    else:
        flash("Le mot de passe actuel est incorrect.", "danger")

    return redirect(url_for('index') + '#profile-section')


def generate_invoice_pdf(order, customer_info):
    """Génère un PDF professionnel conforme aux normes suédoises (Skatteverket) avec TVA."""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=36, leftMargin=36, topMargin=36, bottomMargin=36)
    story = []
    styles = getSampleStyleSheet()

    # En-tête / Titre
    title_style = ParagraphStyle('InvoiceTitle', parent=styles['Heading1'], fontSize=20, leading=24,
                                 textColor=colors.HexColor('#111111'))
    story.append(Paragraph(f"FAKTURA / B2B INVOICE - #{order['id']}", title_style))
    story.append(Spacer(1, 10))

    # Calculs financiers (TVA de 25% par défaut en Suède)
    total_inc_vat = float(order.get('total', 0))
    vat_rate = 0.25
    total_ex_vat = total_inc_vat / (1 + vat_rate)
    vat_amount = total_inc_vat - total_ex_vat

    # Informations Vendeur (URBAN NATION) & Acheteur (Entreprise partenaire)
    seller_info = """
    <b>Säljare (Sändare):</b> URBAN NATION Sweden AB<br/>
    <b>Org.nr:</b> 556999-1234 | <b>Momsreg.nr:</b> SE556999123401<br/>
    <b>E-post:</b> fakturering@urbannation.se<br/>
    """

    buyer_info = f"""
    <b>Köpare (Mottagare):</b> {customer_info.get('name', '')}<br/>
    <b>Org.nr / VAT:</b> {customer_info.get('org_number', 'Ej angivet')}<br/>
    <b>E-post:</b> {customer_info.get('email', '')}<br/>
    <b>Adress:</b> {customer_info.get('address', 'B2B Partner')}
    """

    header_table_data = [[Paragraph(seller_info, styles['Normal']), Paragraph(buyer_info, styles['Normal'])]]
    header_table = Table(header_table_data, colWidths=[270, 270])
    header_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#f8f9fa')),
        ('PADDING', (0, 0), (-1, -1), 10),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e9ecef'))
    ]))

    story.append(header_table)
    story.append(Spacer(1, 15))

    # Détails de la facture
    meta_text = f"""
    <b>Fakturadatum:</b> {order.get('date', '')}<br/>
    <b>Förfallodagar:</b> 30 dagar netto<br/>
    <b>Betalningsvillkor:</b> Bankgiro 123-4567
    """
    story.append(Paragraph(meta_text, styles['Normal']))
    story.append(Spacer(1, 15))

    # Tableau des articles
    data = [["Artikel / Beskrivning", "Antal", "Pris exkl. moms", "Moms (25%)", "Totalt inkl. moms"]]
    for item in order.get('order_items', []):
        item_price = float(item.get('price', 0))
        item_ex = item_price / 1.25
        item_vat = item_price - item_ex
        data.append(
            [item.get('name', 'Produkt'), "1", f"{item_ex:.2f} SEK", f"{item_vat:.2f} SEK", f"{item_price:.2f} SEK"])

    table = Table(data, colWidths=[180, 50, 100, 90, 120])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#212529')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 6),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#dddddd')),
    ]))

    story.append(table)
    story.append(Spacer(1, 15))

    # Bloc Totaux (Exkl. moms, moms, Total att betala)
    totals_data = [
        ["Summa exkl. moms:", f"{total_ex_vat:.2f} SEK"],
        ["Moms (25%):", f"{vat_amount:.2f} SEK"],
        ["Att betala inkl. moms:", f"{total_inc_vat:.2f} SEK"]
    ]
    totals_table = Table(totals_data, colWidths=[400, 140])
    totals_table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'RIGHT'),
        ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#f8f9fa')),
        ('LINEABOVE', (0, -1), (-1, -1), 1, colors.HexColor('#212529')),
    ]))

    story.append(totals_table)
    story.append(Spacer(1, 25))
    story.append(Paragraph("Tack för ert samarbete! Godkänd för F-skatt.", styles['Italic']))

    doc.build(story)
    buffer.seek(0)
    return buffer


SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
SMTP_USER = "support@urbannation.se"
SMTP_PASSWORD = "votre_mot_de_passe_app"

def send_notification_email(to_email, subject, body_html, pdf_attachment=None, pdf_filename="facture.pdf"):
    """Envoie un e-mail au client avec support HTML et pièce jointe PDF facultative."""
    try:
        msg = MIMEMultipart()
        msg['From'] = f"URBAN NATION <{SMTP_USER}>"
        msg['To'] = to_email
        msg['Subject'] = subject

        msg.attach(MIMEText(body_html, 'html'))

        if pdf_attachment:
            part = MIMEApplication(pdf_attachment.read(), _subtype="pdf")
            part.add_header('Content-Disposition', 'attachment', filename=pdf_filename)
            msg.attach(part)

        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_USER, SMTP_PASSWORD)
            server.send_message(msg)
        return True
    except Exception as e:
        print(f"⚠️ Erreur lors de l'envoi de l'e-mail à {to_email}: {e}")
        return False


@app.route('/download_invoice/<int:order_id>')
def download_invoice(order_id):
    """Permet au client de télécharger sa facture depuis son espace 'Mitt Konto'."""
    if not session.get('user_logged'):
        return redirect('/login')

    user_email = session.get('user_email')
    customer = next((c for c in CUSTOMERS if c.get('email', '').lower() == user_email.lower()), {})
    order = next((o for o in ORDERS if o.get('id') == order_id), None)

    if not order:
        flash("Ordern hittades inte.", "danger")
        return redirect('/account')

    pdf_buffer = generate_invoice_pdf(order, customer)
    return send_file(pdf_buffer, as_attachment=True, download_name=f"Facture_URBAN_NATION_{order_id}.pdf", mimetype='application/pdf')


def process_successful_order(order, customer_info):
    """Appelé lors du paiement réussi : Génère la facture et l'envoie par mail."""
    pdf_file = generate_invoice_pdf(order, customer_info)
    subject = f"Orderbekräftelse & Faktura - Order #{order['id']} URBAN NATION"
    body_html = f"""
    <h2>Tack för din beställning, {customer_info.get('name')}!</h2>
    <p>Vi har tagit emot din order <b>#{order['id']}</b> på <b>{order['total']} SEK</b>.</p>
    <p>Din faktura och orderbekräftelse finns bifogad som PDF i detta e-postmeddelande.</p>
    <br/>
    <p>Med vänliga hälsningar,<br/><b>URBAN NATION Team</b></p>
    """
    send_notification_email(customer_info['email'], subject, body_html, pdf_attachment=pdf_file, pdf_filename=f"Faktura_Order_{order['id']}.pdf")


@app.route('/request_return/<int:order_id>', methods=['POST'])
def request_return(order_id):
    current_user = get_current_user()
    if not current_user:
        return redirect(url_for('user_login'))

    reason = request.form.get('reason')
    item_name = request.form.get('item_name')
    user_email = current_user.get('email')

    order = next((o for o in ORDERS if o.get('id') == order_id), None)
    if order:
        ret_id = max([r['id'] for r in RETURNS]) + 1 if RETURNS else 101
        RETURNS.append({
            "id": ret_id,
            "order_id": order_id,
            "customer_email": user_email,
            "reason": reason,
            "item_name": item_name,
            "amount": order.get('total', 0),
            "status": "Under behandling"
        })

        order['return_requested'] = True
        order['return_reason'] = reason

        subject_client = f"Returbegäran Mottagen - Order #{order_id}"
        html_client = f"""
        <h3>Vi har tagit emot din returbegäran för Order #{order_id}</h3>
        <p><b>Produkt:</b> {item_name}</p>
        <p><b>Anledning:</b> {reason}</p>
        <p>Vårt team granskar ditt ärende och återkommer med instruktioner och retursedel inom kort.</p>
        """
        send_notification_email(user_email, subject_client, html_client)

        subject_admin = f"🚨 NY RETURBEGÄRAN: Order #{order_id}"
        html_admin = f"""
        <h3>Ny returbegäran från {user_email}</h3>
        <p><b>Order ID:</b> #{order_id}</p>
        <p><b>Produkt:</b> {item_name}</p>
        <p><b>Orsak:</b> {reason}</p>
        <p><a href="http://127.0.0.1:5000/admin#orders-section">Gå till Admin Dashboard för att hantera returen</a></p>
        """
        send_notification_email("admin@urbannation.se", subject_admin, html_admin)

        flash("Din returbegäran har skickats till kundtjänst! En bekräftelse har skickats till din e-post.", "success")

    return redirect(url_for('user_account'))


@app.route('/admin/b2b_invoices', methods=['POST'])
def admin_add_b2b_invoice():
    if not session.get('admin_logged'):
        return redirect(url_for('admin_login'))

    company_name = request.form.get('company_name')
    org_number = request.form.get('org_number')
    email = request.form.get('email')
    items_description = request.form.get('items_description')
    amount = float(request.form.get('amount', 0))
    date = request.form.get('date')

    new_id = max([inv['id'] for inv in B2B_INVOICES]) + 1 if B2B_INVOICES else 501

    invoice_data = {
        "id": new_id,
        "company_name": company_name,
        "org_number": org_number,
        "email": email,
        "items_description": items_description,
        "amount": amount,
        "date": date,
        "status": "Skickad / Obehandlad"
    }
    B2B_INVOICES.append(invoice_data)

    try:
        order_sim = {"id": new_id, "date": date, "total": amount,
                     "order_items": [{"name": items_description, "price": amount}]}
        customer_sim = {
            "name": company_name,
            "org_number": org_number,
            "email": email,
            "address": "B2B Partner",
            "postal_code": "",
            "city": ""
        }

        pdf_file = generate_invoice_pdf(order_sim, customer_sim)

        subject = f"Faktura B2B #{new_id} - URBAN NATION Business"
        body_html = f"""
        <h3>Faktura från URBAN NATION</h3>
        <p>Hej <b>{company_name}</b>,</p>
        <p>Bifogat finner ni faktura <b>#{new_id}</b> på totalt <b>{amount} SEK</b> (inkl. moms).</p>
        <p>Vänligen betala inom 30 dagar.</p>
        """
        send_notification_email(email, subject, body_html, pdf_attachment=pdf_file,
                                pdf_filename=f"B2B_Faktura_{new_id}.pdf")
    except Exception as e:
        print(f"Erreur envoi B2B: {e}")

    flash("B2B-faktura skapad och skickad till företaget!", "success")
    return redirect(url_for('admin_dashboard') + '#b2b-section')


@app.route('/admin/download_b2b_invoice/<int:inv_id>')
def download_b2b_invoice(inv_id):
    if not session.get('admin_logged'):
        return redirect(url_for('admin_login'))

    inv = next((i for i in B2B_INVOICES if i['id'] == inv_id), None)
    if not inv:
        flash("Fakturans hittades inte.", "danger")
        return redirect(url_for('admin_dashboard'))

    order_sim = {"id": inv['id'], "date": inv['date'], "total": inv['amount'],
                 "order_items": [{"name": inv['items_description'], "price": inv['amount']}]}
    customer_sim = {
        "name": inv['company_name'],
        "org_number": inv['org_number'],
        "email": inv['email'],
        "address": "B2B Partner",
        "postal_code": "",
        "city": ""
    }

    pdf_buffer = generate_invoice_pdf(order_sim, customer_sim)
    return send_file(pdf_buffer, as_attachment=True, download_name=f"Faktura_B2B_{inv_id}.pdf",
                     mimetype='application/pdf')

# --- STYLES HARMONISÉS NOIR & BLANC (SANS JAUNE, TEXTES LISIBLES) ---

COMMON_STYLES = """
    <link href="https://fonts.googleapis.com/css2?family=Montserrat:wght@400;600;800&family=Inter:wght@300;400;600;700&display=swap" rel="stylesheet">
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <style>
        :root {
            --primary-black: #0d0d0d;
            --border-color: #e5e5e5;
        }

        /* Thème clair unifié */
        body {
            font-family: 'Inter', sans-serif;
            background-color: #ffffff !important;
            color: #111111 !important;
            position: relative;
        }

        /* Pattern de logos répétés en arrière-plan */
        body::before {
            content: "";
            position: fixed;
            top: 0;
            left: 0;
            width: 100vw;
            height: 100vh;
            background-image: url('/static/uploads/image1.jpeg');
            background-repeat: repeat;
            background-position: 0 0;
            background-size: 80px 80px;
            opacity: 0.025;
            pointer-events: none;
            z-index: -1;
        }

        h1, h2, h3, h4, h5, .brand-font {
            font-family: 'Montserrat', sans-serif;
            font-weight: 800;
            letter-spacing: -0.5px;
            color: #111111 !important;
        }

        .navbar-brand-logo {
            height: 42px;
            width: auto;
            border-radius: 50%;
            object-fit: cover;
            border: 2px solid #ffffff;
            transition: transform 0.3s ease;
        }

        .card {
            background-color: #ffffff !important;
            color: #111111 !important;
            border: 1px solid #e0e0e0 !important;
            border-radius: 12px;
            transition: transform 0.25s ease, box-shadow 0.25s ease;
        }

        .card:hover {
            transform: translateY(-4px);
            box-shadow: 0 10px 20px rgba(0,0,0,0.08) !important;
        }

        .card .card-title, .card h5, .card h4, .card p, .card span, .card div {
            color: #111111 !important;
        }

        .card .text-muted, .text-muted {
            color: #666666 !important;
        }

        .badge.bg-dark {
            background-color: #0d0d0d !important;
            color: #ffffff !important;
            border: 1px solid #444444 !important;
        }

        .badge.bg-danger {
            background-color: #dc3545 !important;
            color: #ffffff !important;
            border-color: #dc3545 !important;
        }

        .btn-dark {
            background-color: #0d0d0d !important;
            border-color: #0d0d0d !important;
            font-weight: 600;
            border-radius: 8px;
            padding: 10px 20px;
            color: #ffffff !important;
        }

        .btn-outline-dark {
            color: #111111 !important;
            border-color: #111111 !important;
        }

        .btn-warning {
            background-color: #ffffff !important;
            border-color: #111111 !important;
            font-weight: 700 !important;
            color: #111111 !important;
            border-radius: 8px;
        }

        .gallery-thumb { 
            width: 44px; 
            height: 44px; 
            object-fit: cover; 
            cursor: pointer; 
            border: 2px solid transparent; 
            border-radius: 6px; 
        }
        .gallery-thumb:hover, .gallery-thumb.active { 
            border-color: #111111; 
        }

        .countdown-timer,
        .countdown-timer * {
            font-family: monospace !important;
            font-size: 0.85rem !important;
            font-weight: 700 !important;
            background-color: #000000 !important;
            color: #ffffff !important;
            border-radius: 6px !important;
            border: 1px solid #444444 !important;
        }
    </style>
"""

# --- TEMPLATE ACCUEIL ---

HOME_TEMPLATE = """
<!DOCTYPE html>
<html lang="sv" style="scroll-behavior: smooth;">
<head>
    <meta charset="UTF-8">
    <title>URBAN NATION - Official E-commerce & Events</title>
    """ + COMMON_STYLES + """
    <style>
        /* Effet filigrane / Logo en arrière-plan (Watermark Urban Nation) */
        .bg-urban-watermark {
            position: relative;
            overflow: hidden;
        }
        .bg-urban-watermark::before {
            content: "URBAN NATION";
            position: absolute;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%) rotate(-20deg);
            font-size: 7.5rem;
            font-weight: 900;
            color: rgba(0, 0, 0, 0.04); /* Très subtil en Light Mode */
            white-space: nowrap;
            pointer-events: none;
            z-index: 0;
            font-family: 'Montserrat', sans-serif;
            letter-spacing: 4px;
        }
    </style>
</head>
<body>

    <nav class="navbar navbar-expand-lg navbar-dark bg-dark sticky-top shadow-sm py-3">
        <div class="container">
            <a class="navbar-brand d-flex align-items-center gap-2 fw-bold fs-3 text-white" href="/">
                <img src="{{ logo_url }}" alt="Urban Nation Logo" class="navbar-brand-logo" onerror="this.src='https://via.placeholder.com/40'">
                <span>URBAN <span style="color: #ffffff;">NATION</span></span>
            </a>
            <button class="navbar-toggler" type="button" data-bs-toggle="collapse" data-bs-target="#navbarBD">
                <span class="navbar-toggler-icon"></span>
            </button>
            <div class="collapse navbar-collapse" id="navbarBD">
                <ul class="navbar-nav me-auto mb-2 mb-lg-0 ms-lg-4">
                    <li class="nav-item"><a class="nav-link" href="/">Hem</a></li>
                    <li class="nav-item"><a class="nav-link" href="#events-section">Evenemang</a></li>
                    <li class="nav-item"><a class="nav-link" href="#catalog-section">Katalog</a></li>
                    <li class="nav-item"><a class="nav-link" href="#footer-section">Om oss</a></li>
                </ul>
                <div class="d-flex align-items-center gap-2">
                    {% if current_user %}
                        <a href="/account" class="btn btn-outline-light btn-sm">👤 Konto ({{ current_user.first_name if current_user.first_name else current_user.name.split()[0] }})</a>
                        <a href="/logout" class="btn btn-danger btn-sm">Logga ut</a>
                    {% else %}
                        <a href="/login" class="btn btn-outline-light btn-sm">Logga in</a>
                        <a href="/register" class="btn btn-warning btn-sm">Skapa konto</a>
                    {% endif %}
                    <a href="/checkout" class="btn btn-warning btn-sm ms-2 fw-bold">Varukorg ({{ cart_count }})</a>
                </div>
            </div>
        </div>
    </nav>

   <div class="container my-5">
    {% with messages = get_flashed_messages(with_categories=true) %}
      {% if messages %}
        {% for category, message in messages %}
          <div class="alert alert-{{ category }} rounded-3 shadow-sm">{{ message }}</div>
        {% endfor %}
      {% endif %}
    {% endwith %}

    <!-- Hero Banner avec filigrane Urban Nation en arrière-plan -->
    <div class="p-5 mb-5 text-white rounded-4 shadow-lg text-center position-relative overflow-hidden bg-urban-watermark" 
         style="background: linear-gradient(rgba(0,0,0,0.75), rgba(0,0,0,0.88)), url('{{ hero_bg }}') center/cover no-repeat;">
        <div class="mb-3 position-relative" style="z-index: 1;">
            <img src="{{ logo_url }}" alt="Urban Nation Banner Logo" style="height: 110px; width: 110px; border-radius: 50%; object-fit: cover; border: 3px solid #ffffff;" class="shadow" onerror="this.style.display='none'">
        </div>
        <h1 class="fw-bold display-4 text-uppercase tracking-wide text-white position-relative" style="z-index: 1;">URBAN <span style="color: #ffffff;">NATION</span></h1>
        <p class="lead text-light max-w-700 mx-auto opacity-90 position-relative" style="z-index: 1;">xxx</p>
        <div class="d-flex justify-content-center gap-3 mt-4 position-relative" style="z-index: 1;">
            <a href="#catalog-section" class="btn btn-warning btn-lg px-4 fw-bold">Utforska Shoppen</a>
            <a href="#events-section" class="btn btn-outline-light btn-lg px-4">Boka Eventbiljetter</a>
        </div>
    </div>
    
    <hr class="my-4">

    <!-- 🚀 AFFICHAGE DE L'ANNONCE GLOBALE "UNDER FÖRBEREDELSE" SI ACTIVÉE -->
    {% if global_announcement and global_announcement.active %}
        <div class="alert alert-warning border border-warning shadow-sm rounded-4 p-4 mb-4 position-relative" role="alert">
            <div class="d-flex align-items-start gap-3">
                <div class="fs-2">🚧</div>
                <div class="flex-grow-1">
                    <h4 class="alert-heading fw-bold text-dark mb-1">Under förberedelse</h4>
                    <p class="mb-2 text-dark fs-6">{{ global_announcement.text }}</p>
                    {% if global_announcement.image %}
                        <div class="mt-2">
                            <img src="{{ global_announcement.image }}" alt="Annonce" style="max-height: 180px; border-radius: 8px; object-fit: cover;" class="shadow-sm">
                        </div>
                    {% endif %}
                </div>
            </div>
        </div>
    {% endif %}
    
    <!-- 🔴 WIDGET FLOTTANT DE LIVE STREAMING MULTI-PLATEFORME -->
    {% if global_live.active and (global_live.platforms.youtube.active or global_live.platforms.facebook.active or global_live.platforms.tiktok.active or global_live.platforms.instagram.active) %}
    <div id="live-floating-widget" class="position-fixed bottom-0 end-0 m-3 shadow-lg rounded-4 overflow-hidden bg-dark border border-warning" style="width: 340px; z-index: 2000;">
        <div class="d-flex justify-content-between align-items-center bg-black px-3 py-2 text-white">
            <span class="small fw-bold text-danger">🔴 LIVE MULTI-STREAM</span>
            <button type="button" class="btn-close btn-close-white btn-sm" onclick="document.getElementById('live-floating-widget').style.display='none'"></button>
        </div>
    
        <!-- ONGLETS DE SÉLECTION DE LA PLATEFORME PAR L'UTILISATEUR -->
        <ul class="nav nav-tabs nav-justified bg-secondary bg-opacity-25 border-bottom border-secondary" style="font-size: 0.75rem;">
            {% if global_live.platforms.youtube.active %}
            <li class="nav-item">
                <button class="nav-link active text-white fw-bold py-1" data-bs-toggle="tab" data-bs-target="#tab-yt">YouTube</button>
            </li>
            {% endif %}
            {% if global_live.platforms.facebook.active %}
            <li class="nav-item">
                <button class="nav-link text-white fw-bold py-1" data-bs-toggle="tab" data-bs-target="#tab-fb">Facebook</button>
            </li>
            {% endif %}
            {% if global_live.platforms.tiktok.active %}
            <li class="nav-item">
                <button class="nav-link text-white fw-bold py-1" data-bs-toggle="tab" data-bs-target="#tab-tt">TikTok</button>
            </li>
            {% endif %}
            {% if global_live.platforms.instagram.active %}
            <li class="nav-item">
                <button class="nav-link text-white fw-bold py-1" data-bs-toggle="tab" data-bs-target="#tab-ig">Instagram</button>
            </li>
            {% endif %}
        </ul>
    
        <!-- FLUX VIDÉO -->
        <div class="tab-content bg-black">
            {% if global_live.platforms.youtube.active %}
            <div class="tab-pane fade show active" id="tab-yt">
                <div class="ratio ratio-169">
                    <iframe src="{{ global_live.platforms.youtube.url }}" allowfullscreen></iframe>
                </div>
            </div>
            {% endif %}
    
            {% if global_live.platforms.facebook.active %}
            <div class="tab-pane fade {% if not global_live.platforms.youtube.active %}show active{% endif %}" id="tab-fb">
                <div class="ratio ratio-169">
                    <iframe src="{{ global_live.platforms.facebook.url }}" allowfullscreen></iframe>
                </div>
            </div>
            {% endif %}
    
            {% if global_live.platforms.tiktok.active %}
            <div class="tab-pane fade {% if not global_live.platforms.youtube.active and not global_live.platforms.facebook.active %}show active{% endif %}" id="tab-tt">
                <div class="ratio ratio-169">
                    <iframe src="{{ global_live.platforms.tiktok.url }}" allowfullscreen></iframe>
                </div>
            </div>
            {% endif %}
    
            {% if global_live.platforms.instagram.active %}
            <div class="tab-pane fade {% if not global_live.platforms.youtube.active and not global_live.platforms.facebook.active and not global_live.platforms.tiktok.active %}show active{% endif %}" id="tab-ig">
                <div class="ratio ratio-169">
                    <iframe src="{{ global_live.platforms.instagram.url }}" allowfullscreen></iframe>
                </div>
            </div>
            {% endif %}
        </div>
    
        <div class="p-2 bg-dark text-white text-center small fw-bold">
            {{ global_live.title }}
        </div>
    </div>
    {% endif %}
    
    <div id="events-section" class="pt-3">
        <div class="d-flex justify-content-between align-items-center mb-4">
            <h2>Kommande Evenemang & Fester</h2>
            <span class="badge bg-dark fs-6 px-3 py-2 rounded-pill text-white border border-light">Exklusiva Event</span>
        </div>
        <div class="row mb-5">
            {% for event in events %}
            <div class="col-md-6 mb-4">
                <div class="card h-100 shadow-sm border-0 overflow-hidden">
                    <div class="row g-0 h-100">
                        <div class="col-md-5">
                            <img src="{{ event.image }}" class="img-fluid rounded-start h-100" style="object-fit: cover;" alt="{{ event.title }}">
                        </div>
                        <div class="col-md-7">
                            <div class="card-body d-flex flex-column h-100">
                                <div class="mb-2 d-flex justify-content-between align-items-center flex-wrap gap-1">
                                    <span class="badge bg-dark text-white border border-secondary px-2 py-1" style="background-color: #0d0d0d !important; color: #ffffff !important;">
                                        ⏳ <span class="countdown-timer" data-date="{{ event.date }}" style="color: #ffffff !important;">Räknar ner...</span>
                                    </span>
                                    {% if event.min_age %}
                                    <span class="badge bg-secondary">🔞 Åldersgräns: {{ event.min_age }} år</span>
                                    {% endif %}
                                </div>
                                <h4 class="card-title h5">{{ event.title }}</h4>
                                <p class="text-muted small mb-2">📍 {{ event.location }} (⏰ {{ event.time }})</p>
                                <p class="card-text text-muted small flex-grow-1">{{ event.desc }}</p>
    
                                <!-- Jauges visuelles par zone / catégorie définie par l'admin -->
                                <div class="mt-2">
                                    <h6 class="fw-bold mb-2 small text-uppercase">Välj biljettyp & tillgängliga zoner:</h6>
                                
                                    {% set categories = event.categories if event.categories else [
                                        {"name": "Standard", "price": event.price, "total_stock": 100, "sold": 0}
                                    ] %}
                                
                                    {% for cat in categories %}
                                    <div class="mb-2 p-2 border rounded bg-light">
                                        <div class="d-flex justify-content-between mb-1" style="font-size: 0.85rem;">
                                            <strong>{{ cat.name }}</strong>
                                            <span class="fw-bold">{{ cat.price }} SEK</span>
                                        </div>
                                        {% set stock_total = cat.total_stock if cat.total_stock > 0 else 100 %}
                                        {% set sold_count = cat.sold if cat.sold else 0 %}
                                        {% set percent = ((sold_count / stock_total) * 100)|round %}
                                        
                                        <div class="progress mb-1" style="height: 6px;">
                                            <div class="progress-bar {% if percent > 85 %}bg-danger{% else %}bg-dark{% endif %}" style="width: {{ percent }}%;"></div>
                                        </div>
                                        <div class="d-flex justify-content-between text-muted" style="font-size: 0.7rem;">
                                            <span>{{ stock_total - sold_count }} platser kvar</span>
                                            <span>{{ percent }}% Sålt</span>
                                        </div>
                                
                                        {% set match_id = 3 %}
                                        {% for p in products %}
                                            {% if event.title in p.name %}{% set match_id = p.id %}{% endif %}
                                        {% endfor %}
                                
                                        <form action="/add/{{ match_id }}" method="POST" class="mt-1">
                                            <input type="hidden" name="ticket_category" value="{{ cat.name|lower }}">
                                            <button type="submit" class="btn btn-dark btn-sm w-100" style="font-size: 0.75rem; padding: 2px;">Boka {{ cat.name }}</button>
                                        </form>
                                    </div>
                                    {% endfor %}
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
            {% endfor %}
        </div>
    </div>


        <hr class="my-4">

        <div id="top-section" class="pt-3">
            <div class="d-flex justify-content-between align-items-center mb-4">
                <h2>Topp 10 Mest Sålda Produkter</h2>
                <span class="badge bg-dark fs-6 px-3 py-2 rounded-pill text-white">Bestsellers</span>
            </div>
            <div class="row mb-5">
                {% for product in top_products %}
                <div class="col-md-3 mb-4">
                    <div class="card h-100 shadow-sm border-2 position-relative">
                        <div class="position-absolute top-0 start-0 m-2 d-flex flex-column gap-1">
                            <span class="badge bg-dark text-white">#{{ loop.index }} Best-seller</span>
                            {% if product.promo_badge %}<span class="badge bg-secondary fw-bold">{{ product.promo_badge }}</span>{% endif %}
                            {% if is_new_product(product.date) %}<span class="badge bg-light text-dark fw-bold border">NY</span>{% endif %}
                        </div>
                        <img src="{{ product.image }}" class="card-img-top" style="height: 200px; object-fit: cover;" alt="{{ product.name }}">
                        <div class="card-body d-flex flex-column">
                            <span class="badge bg-secondary mb-2 align-self-start">
                                {% set t_name = product.type %}
                                {% for pt in product_types %}{% if pt.id == product.type %}{% set t_name = pt.name %}{% endif %}{% endfor %}
                                {{ t_name }}
                            </span>
                            <h5 class="card-title">{{ product.name }}</h5>
                            <p class="card-text text-muted small">{{ product.desc }}</p>
                            <div class="mt-auto">
                                {% if product.discount_price %}
                                    <p class="card-text mb-0"><span class="text-decoration-line-through text-muted me-2">{{ product.price }} SEK</span><span class="fw-bold fs-5 text-dark">{{ product.discount_price }} SEK</span></p>
                                {% else %}
                                    <p class="card-text fw-bold mb-0 fs-5 text-dark">{{ product.price }} SEK</p>
                                {% endif %}
                                <small class="text-muted" style="font-size: 0.8rem;">Sålda enheter: {{ product.sold }} st</small>
                            </div>
                            <a href="/add/{{ product.id }}" class="btn btn-dark mt-2">Köp / Lägg till</a>
                        </div>
                    </div>
                </div>
                {% endfor %}
            </div>
        </div>

        <hr class="my-4">

        <div id="catalog-section" class="pt-3">
            <div class="d-flex justify-content-between align-items-center mb-3">
                <h2>Alla Produkter & Biljetter</h2>
                <div class="d-flex gap-2">
                    <input type="text" id="searchAllProducts" class="form-control form-control-sm" placeholder="🔍 Sök produkt..." onkeyup="filterAllProducts()">
                    <select id="sortAllProducts" class="form-select form-select-sm" onchange="sortAllProducts()">
                        <option value="name_asc">Namn: A till Z</option>
                        <option value="name_desc">Namn: Z till A</option>
                        <option value="date_new">Datum: Nyast först</option>
                        <option value="date_old">Datum: Äldst först</option>
                    </select>
                </div>
            </div>

            <div class="d-flex flex-wrap gap-2 mb-4" id="categoryFilterContainer">
                <button class="btn btn-dark btn-sm filter-btn active" onclick="filterCategory('all', this)">Alla</button>
                {% for t in product_types %}
                <button class="btn btn-outline-dark btn-sm filter-btn" onclick="filterCategory('{{ t.id }}', this)">{{ t.name }}</button>
                {% endfor %}
            </div>

            <div class="row" id="allProductsContainer">
                {% for product in products %}
                {% set remaining_stock = product.total_stock - product.sold %}
                <div class="col-md-3 mb-4 product-item" data-name="{{ product.name|lower }}" data-date="{{ product.date }}" data-category="{{ product.type }}">
                    <div class="card h-100 shadow-sm position-relative">
                        <div class="position-absolute top-0 end-0 m-2 d-flex flex-column gap-1 align-items-end" style="z-index: 2;">
                            {% if product.promo_badge %}<span class="badge bg-secondary fw-bold fs-6">{{ product.promo_badge }}</span>{% endif %}
                            {% if is_new_product(product.date) %}<span class="badge bg-light text-dark fw-bold fs-6 border">NY</span>{% endif %}
                            {% if remaining_stock <= 5 and remaining_stock > 0 %}
                                <span class="badge bg-danger text-white fw-bold border border-light stock-warning-badge">⚠️ Endast {{ remaining_stock }} kvar!</span>
                            {% elif remaining_stock == 0 %}
                                <span class="badge bg-secondary fw-bold">Slutsåld</span>
                            {% endif %}
                        </div>

                        <img id="main-img-{{ product.id }}" src="{{ product.image }}" class="card-img-top" style="height: 200px; object-fit: cover;" alt="{{ product.name }}">

                        {% if product.images and product.images|length > 1 %}
                        <div class="d-flex justify-content-center gap-1 p-2 bg-light">
                            {% for img in product.images %}
                            <img src="{{ img }}" class="gallery-thumb" onclick="changeProductImage({{ product.id }}, '{{ img }}')">
                            {% endfor %}
                        </div>
                        {% endif %}

                        <div class="card-body d-flex flex-column">
                            <span class="badge bg-secondary mb-2 align-self-start">
                                {% set t_name = product.type %}
                                {% for pt in product_types %}{% if pt.id == product.type %}{% set t_name = pt.name %}{% endif %}{% endfor %}
                                {{ t_name }}
                            </span>
                            <h5 class="card-title product-name">{{ product.name }}</h5>
                            <p class="card-text text-muted small">{{ product.desc }}</p>

                            <div class="mt-auto">
                                {% if product.discount_price %}
                                    <p class="card-text mb-0"><span class="text-decoration-line-through text-muted me-2">{{ product.price }} SEK</span><span class="fw-bold fs-5 text-dark">{{ product.discount_price }} SEK</span></p>
                                {% else %}
                                    <p class="card-text fw-bold mb-0 text-dark fs-5">{{ product.price }} SEK</p>
                                {% endif %}
                                <small class="text-muted product-date" style="font-size: 0.8rem;">Tillagd: {{ product.date }}</small>
                            </div>

                            <form action="/add/{{ product.id }}" method="POST" class="mt-2">
                                {% if product.type != 'ticket' %}
                                <div class="row g-1 mb-2">
                                    <div class="col-6">
                                        <select class="form-select form-select-sm" name="size">
                                            {% if product.sizes %}
                                                {% for s in product.sizes %}<option value="{{ s }}">{{ s }}</option>{% endfor %}
                                            {% else %}
                                                <option value="One size">One size</option>
                                            {% endif %}
                                        </select>
                                    </div>
                                    <div class="col-6">
                                        <select class="form-select form-select-sm" name="color">
                                            {% if product.colors %}
                                                {% for c in product.colors %}<option value="{{ c }}">{{ c }}</option>{% endfor %}
                                            {% else %}
                                                <option value="Standard">Standard</option>
                                            {% endif %}
                                        </select>
                                    </div>
                                </div>
                                {% if product.type == 'clothing' %}
                                <button type="button" class="btn btn-link btn-sm p-0 mb-2 text-decoration-none text-dark" data-bs-toggle="modal" data-bs-target="#sizeGuideModal">📏 Storleksguide</button>
                                {% endif %}
                                {% endif %}

                                <button type="submit" class="btn btn-dark w-100" {% if remaining_stock == 0 %}disabled{% endif %}>
                                    {% if remaining_stock == 0 %}Slutsåld{% else %}Köp / Lägg till{% endif %}
                                </button>
                            </form>
                        </div>
                    </div>
                </div>
                {% endfor %}
            </div>
        </div>
    </div>

    <!-- Modals, footer et scripts -->
    <div class="modal fade" id="sizeGuideModal" tabindex="-1">
      <div class="modal-dialog modal-dialog-centered">
        <div class="modal-content">
          <div class="modal-header bg-dark text-white">
            <h5 class="modal-title">📏 Storleksguide (Size Guide)</h5>
            <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal"></button>
          </div>
          <div class="modal-body">
            <p class="text-muted small">Mät din kropp enligt instruktionerna för att hitta perfekt passform och undvika returer.</p>
            <table class="table table-bordered text-center align-middle">
                <thead class="table-light">
                    <tr><th>Storlek</th><th>Bröstomfång (cm)</th><th>Längd (cm)</th><th>Axlar (cm)</th></tr>
                </thead>
                <tbody>
                    <tr><td><strong>S</strong></td><td>88 - 94</td><td>68</td><td>44</td></tr>
                    <tr><td><strong>M</strong></td><td>95 - 101</td><td>70</td><td>46</td></tr>
                    <tr><td><strong>L</strong></td><td>102 - 108</td><td>72</td><td>48</td></tr>
                    <tr><td><strong>XL</strong></td><td>109 - 116</td><td>75</td><td>50</td></tr>
                </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>

    <footer class="bg-dark text-white pt-5 pb-4 mt-5" id="footer-section">
        <div class="container text-center text-md-start">
            <div class="row text-center text-md-start">
                <div class="col-md-3 col-lg-3 col-xl-3 mx-auto mt-3">
                    <div class="d-flex align-items-center gap-2 mb-3">
                        <img src="{{ logo_url }}" alt="Urban Nation Logo" style="height: 38px; width: 38px; border-radius: 50%;" onerror="this.style.display='none'">
                        <h5 class="text-uppercase font-weight-bold text-white mb-0">URBAN NATION</h5>
                    </div>
                    <p class="small text-muted">Om Urban Nation.</p>
                </div>
                <div class="col-md-2 col-lg-2 col-xl-2 mx-auto mt-3">
                    <h5 class="text-uppercase mb-4 font-weight-bold text-white">Meny</h5>
                    <p><a href="/" class="text-white text-decoration-none">Hem</a></p>
                    <p><a href="#events-section" class="text-white text-decoration-none">Evenemang</a></p>
                    <p><a href="#catalog-section" class="text-white text-decoration-none">Katalog</a></p>
                </div>
                <div class="col-md-4 col-lg-3 col-xl-3 mx-auto mt-3">
                    <h5 class="text-uppercase mb-4 font-weight-bold text-white">Kontakt</h5>
                    <p class="small text-muted mb-1">📍 xxxvägen x, Luleå, Umeå</p>
                    <p class="small text-muted mb-1">✉️ xxx@urbannation???.se</p>
                    <p class="small text-muted mb-1">📞 +46 x xxx xxx xx</p>
                </div>
            </div>
            <hr class="mb-4 border-secondary">
            <div class="row align-items-center">
                <div class="col-md-7 col-lg-8">
                    <p class="text-muted mb-0 small">© 2026 <strong>URBAN NATION</strong>. Alla rättigheter förbehållna.</p>
                </div>
            </div>
        </div>
    </footer>

    <script>
        function updateCountdowns() {
            const timers = document.querySelectorAll('.countdown-timer');
            timers.forEach(timer => {
                const eventDateStr = timer.getAttribute('data-date');
                const eventDate = new Date(eventDateStr + "T23:59:59").getTime();
                const now = new Date().getTime();
                const distance = eventDate - now;
    
                timer.style.setProperty('color', '#ffffff', 'important');
    
                if (distance < 0) {
                    timer.innerText = "🎉 Eventet har börjat!";
                } else {
                    const days = Math.floor(distance / (1000 * 60 * 60 * 24));
                    const hours = Math.floor((distance % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60));
                    const minutes = Math.floor((distance % (1000 * 60 * 60)) / (1000 * 60));
                    timer.innerText = `${days}d ${hours}h ${minutes}m`;
                }
            });
        }
        setInterval(updateCountdowns, 1000);
        updateCountdowns();
    
        function filterCategory(catId, btn) {
            document.querySelectorAll('.filter-btn').forEach(b => {
                b.classList.remove('btn-dark', 'active');
                b.classList.add('btn-outline-dark');
            });
            btn.classList.remove('btn-outline-dark');
            btn.classList.add('btn-dark', 'active');
            let searchInput = document.getElementById('searchAllProducts').value.toLowerCase();
            let items = document.getElementsByClassName('product-item');
            for (let item of items) {
                let cat = item.getAttribute('data-category');
                let name = item.getAttribute('data-name');
                if ((catId === 'all' || cat === catId) && name.includes(searchInput)) { item.style.display = ""; } else { item.style.display = "none"; }
            }
        }
    
        function changeProductImage(prodId, newSrc) { document.getElementById('main-img-' + prodId).src = newSrc; }
    
        function filterAllProducts() {
            let input = document.getElementById('searchAllProducts').value.toLowerCase();
            let items = document.getElementsByClassName('product-item');
            for (let item of items) {
                if (item.getAttribute('data-name').includes(input)) { item.style.display = ""; } else { item.style.display = "none"; }
            }
        }
    
        function sortAllProducts() {
            let sortVal = document.getElementById('sortAllProducts').value;
            let container = document.getElementById('allProductsContainer');
            let itemsArray = Array.from(container.getElementsByClassName('product-item'));
            itemsArray.sort((a, b) => {
                let nameA = a.getAttribute('data-name'), nameB = b.getAttribute('data-name');
                let dateA = a.getAttribute('data-date'), dateB = b.getAttribute('data-date');
                if (sortVal === 'name_asc') return nameA.localeCompare(nameB);
                else if (sortVal === 'name_desc') return nameB.localeCompare(nameA);
                else if (sortVal === 'date_new') return dateB.localeCompare(dateA);
                else if (sortVal === 'date_old') return dateA.localeCompare(dateB);
            });
            itemsArray.forEach(item => container.appendChild(item));
        }
    
        // --- TRACKING DES CLICS SUR LES ONGLETS DU LIVE STREAM ---
        function trackPlatformClick(platform) {
            fetch('/api/track_live_view', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ platform: platform })
            }).catch(err => console.error("Erreur de tracking live :", err));
        }
    
        document.addEventListener('DOMContentLoaded', function() {
            document.querySelectorAll('#live-floating-widget .nav-link').forEach(btn => {
                btn.addEventListener('click', function() {
                    const platform = this.innerText.trim().toLowerCase();
                    trackPlatformClick(platform);
                });
            });
        });
        // --------------------------------------------------------
    </script>
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
</body>
</html>
"""

USER_LOGIN_TEMPLATE = """
<!DOCTYPE html>
<html lang="sv">
<head>
    <meta charset="UTF-8">
    <title>Logga in - URBAN NATION</title>
    """ + COMMON_STYLES + """
</head>
<body class="bg-light">
    <div class="container my-5" style="max-width: 450px;">
        <div class="text-center mb-4">
            <img src="{{ logo_url }}" alt="Urban Nation Logo" style="height: 80px; width: 80px; border-radius: 50%; object-fit: cover;" class="mb-2 shadow-sm" onerror="this.style.display='none'">
            <h2 class="fw-bold text-uppercase">URBAN <span style="color: #000;">NATION</span></h2>
        </div>
        <div class="card p-4 shadow-sm">
            <h4 class="mb-3 text-center">Logga in på ditt konto</h4>
            {% with messages = get_flashed_messages(with_categories=true) %}
              {% if messages %}{% for c, m in messages %}<div class="alert alert-{{ c }}">{{ m }}</div>{% endfor %}{% endif %}
            {% endwith %}

            <form method="POST">
                <div class="mb-3">
                    <label class="form-label">E-postadress</label>
                    <input type="email" class="form-control" name="email" required placeholder="namn@example.se">
                </div>
                <div class="mb-3">
                    <label class="form-label">Lösenord</label>
                    <input type="password" class="form-control" name="password" required placeholder="Ditt lösenord">
                    <div class="text-end mt-1">
                        <a href="/forgot-password" class="text-decoration-none small text-dark fw-semibold">Glömt ditt lösenord?</a>
                    </div>
                </div>
                <button type="submit" class="btn btn-dark w-100 btn-lg">Logga in</button>
            </form>

            <!-- Authentification sociale (Google, Apple, Facebook, Instagram, TikTok) -->
            <div class="d-flex align-items-center my-4">
                <hr class="flex-grow-1 border-secondary">
                <span class="px-2 text-muted small fw-bold">eller fortsätt med</span>
                <hr class="flex-grow-1 border-secondary">
            </div>

            <div class="d-flex flex-column gap-2">
                <a href="/login/google" class="btn btn-outline-dark w-100 d-flex align-items-center justify-content-center gap-2 py-2 fw-semibold">
                    <svg width="18" height="18" viewBox="0 0 24 24"><path fill="currentColor" d="M12.545 10.239v3.821h5.445c-.712 2.315-2.647 3.972-5.445 3.972a6.033 6.033 0 1 1 6.033-6.033c0 .337-.027.668-.078.991h3.918A10.024 10.024 0 0 0 12.545 2C6.98 2 2.47 6.51 2.47 12.075c0 5.564 4.51 10.075 10.075 10.075 6.115 0 10.075-4.304 10.075-10.239 0-.583-.051-1.156-.145-1.672h-9.93z"/></svg>
                    Fortsätt med Google
                </a>
                <a href="/login/apple" class="btn btn-outline-dark w-100 d-flex align-items-center justify-content-center gap-2 py-2 fw-semibold">
                    <svg width="18" height="18" viewBox="0 0 24 24"><path fill="currentColor" d="M18.71 19.5c-.83 1.24-1.71 2.45-3.05 2.47-1.34.03-1.77-.79-3.29-.79-1.53 0-2 .77-3.27.82-1.31.05-2.3-1.32-3.14-2.53C4.25 17 2.94 12.45 4.7 9.39c.87-1.52 2.43-2.48 4.12-2.51 1.28-.02 2.5.87 3.29.87.78 0 2.26-1.07 3.81-.91.65.03 2.47.26 3.64 1.98-.09.06-2.17 1.28-2.15 3.81.03 3.02 2.65 4.03 2.68 4.04-.03.07-.42 1.44-1.38 2.83M15.97 6.85c.67-.82 1.13-1.96.99-3.1-.98.04-2.19.66-2.88 1.47-.62.72-1.16 1.89-.99 3.02 1.1.09 2.23-.55 2.88-1.39"/></svg>
                    Fortsätt med Apple
                </a>
                <a href="/login/facebook" class="btn btn-outline-dark w-100 d-flex align-items-center justify-content-center gap-2 py-2 fw-semibold">
                    <svg width="18" height="18" viewBox="0 0 24 24"><path fill="currentColor" d="M22 12c0-5.52-4.48-10-10-10S2 6.48 2 12c0 4.84 3.44 8.87 8 9.8V15H7.5v-3H10V9.5C10 7.01 11.49 5.6 13.78 5.6c1.1 0 2.25.2 2.25.2v2.48h-1.27c-1.23 0-1.62.77-1.62 1.56V12h2.78l-.44 3h-2.34v6.8c4.56-.93 8-4.96 8-9.8z"/></svg>
                    Fortsätt med Facebook
                </a>
                <a href="/login/instagram" class="btn btn-outline-dark w-100 d-flex align-items-center justify-content-center gap-2 py-2 fw-semibold">
                    <svg width="18" height="18" viewBox="0 0 24 24"><path fill="currentColor" d="M12 2.163c3.204 0 3.584.012 4.85.07 3.252.148 4.771 1.691 4.919 4.919.058 1.265.069 1.645.069 4.849 0 3.205-.012 3.584-.069 4.849-.149 3.225-1.664 4.771-4.919 4.919-1.266.058-1.644.07-4.85.07-3.204 0-3.584-.012-4.849-.07-3.26-.149-4.771-1.699-4.919-4.92-.058-1.265-.07-1.644-.07-4.849 0-3.204.013-3.583.07-4.849.149-3.227 1.664-4.771 4.919-4.919 1.266-.057 1.645-.069 4.849-.069zm0-2.163c-3.259 0-3.667.014-4.947.072-4.358.2-6.78 2.618-6.98 6.98-.059 1.281-.073 1.689-.073 4.948 0 3.259.014 3.668.072 4.948.2 4.358 2.618 6.78 6.98 6.98 1.281.058 1.689.072 4.948.072 3.259 0 3.668-.014 4.948-.072 4.354-.2 6.782-2.618 6.979-6.98.059-1.28.073-1.689.073-4.948 0-3.259-.014-3.667-.072-4.947-.196-4.354-2.617-6.78-6.979-6.98-1.281-.059-1.69-.073-4.949-.073zm0 5.838c-3.403 0-6.162 2.759-6.162 6.162s2.759 6.163 6.162 6.163 6.162-2.759 6.162-6.163c0-3.403-2.759-6.162-6.162-6.162zm0 10.162c-2.209 0-4-1.79-4-4 0-2.209 1.791-4 4-4s4 1.791 4 4c0 2.21-1.791 4-4 4zm6.406-11.845c-.796 0-1.441.645-1.441 1.44s.645 1.44 1.441 1.44c.795 0 1.439-.645 1.439-1.44s-.644-1.44-1.439-1.44z"/></svg>
                    Fortsätt med Instagram
                </a>
                <a href="/login/tiktok" class="btn btn-outline-dark w-100 d-flex align-items-center justify-content-center gap-2 py-2 fw-semibold">
                    <svg width="18" height="18" viewBox="0 0 24 24"><path fill="currentColor" d="M12.525.02c1.31-.02 2.61-.01 3.91-.02.08 1.53.63 3.09 1.75 4.17 1.12 1.11 2.7 1.62 4.24 1.79v4.03c-1.44-.05-2.89-.35-4.2-.97-.57-.26-1.1-.59-1.62-.93-.01 2.92.01 5.84-.02 8.75-.08 1.4-.54 2.79-1.35 3.94-1.31 1.92-3.58 3.17-5.91 3.21-1.43.08-2.86-.31-4.08-1.03-2.02-1.19-3.44-3.37-3.65-5.71-.02-.5-.03-1-.01-1.49.18-1.9 1.12-3.72 2.58-4.96 1.66-1.44 3.98-2.13 6.15-1.72.02 1.48-.04 2.96-.04 4.44-.99-.32-2.15-.23-3.02.37-.82.56-1.36 1.5-1.42 2.5-.06 1.08.38 2.16 1.17 2.87.82.73 1.98 1.05 3.07.84 1.11-.2 2.08-.94 2.56-1.96.24-.52.35-1.1.34-1.68.02-3.67.01-7.34.01-11.01z"/></svg>
                    Fortsätt med TikTok
                </a>
            </div>

            <hr class="my-4">
            <div class="text-center">
                <p class="text-muted mb-1">Har du inget konto än?</p>
                <a href="/register" class="btn btn-outline-dark btn-sm">Skapa ett konto här</a>
            </div>
            <a href="/" class="btn btn-link mt-3 text-center d-block text-dark">&larr; Tillbaka till URBAN NATION</a>
        </div>
    </div>
</body>
</html>
"""

ADDRESS_AUTOCOMPLETE_SCRIPT = """
<script>
document.addEventListener('DOMContentLoaded', function() {
    const addressInput = document.getElementById('addressInput');
    const addressSuggestions = document.getElementById('addressSuggestions');
    const postalInput = document.getElementById('postalCodeInput');
    const cityInput = document.getElementById('cityInput');

    // 1. Autokomplettering av gatuadress (efter 3 tecken) via OpenStreetMap Nominatim
    let debounceTimer;
    if (addressInput) {
        addressInput.addEventListener('input', function() {
            clearTimeout(debounceTimer);
            const query = this.value.trim();
            if (query.length < 3) {
                addressSuggestions.style.display = 'none';
                return;
            }
            debounceTimer = setTimeout(() => {
                fetch(`https://nominatim.openstreetmap.org/search?format=json&addressdetails=1&countrycodes=se&q=${encodeURIComponent(query)}`)
                    .then(res => res.json())
                    .then(data => {
                        addressSuggestions.innerHTML = '';
                        if (data && data.length > 0) {
                            data.slice(0, 5).forEach(item => {
                                const road = item.address.road || item.display_name.split(',')[0];
                                const city = item.address.city || item.address.town || item.address.municipality || '';
                                const postcode = item.address.postcode || '';
                                const a = document.createElement('a');
                                a.className = 'list-group-item list-group-item-action py-2';
                                a.href = '#';
                                a.innerHTML = `<strong>${road}</strong> <small class="text-muted">${city ? ', ' + city : ''}</small>`;
                                a.addEventListener('click', function(e) {
                                    e.preventDefault();
                                    addressInput.value = road;
                                    if (postcode) postalInput.value = postcode;
                                    if (city) cityInput.value = city;
                                    addressSuggestions.style.display = 'none';
                                });
                                addressSuggestions.appendChild(a);
                            });
                            addressSuggestions.style.display = 'block';
                        } else {
                            addressSuggestions.style.display = 'none';
                        }
                    }).catch(() => { addressSuggestions.style.display = 'none'; });
            }, 300);
        });

        document.addEventListener('click', function(e) {
            if (e.target !== addressInput) addressSuggestions.style.display = 'none';
        });
    }

    // 2. Automatiskt ifyllande av Stad när Postnummer fylls i (med \\s+ korrigerat)
    if (postalInput) {
        postalInput.addEventListener('input', function() {
            const cleanCode = this.value.replace(/\\s+/g, '');
            if (cleanCode.length === 5) {
                fetch(`https://api.zippopotam.us/se/${cleanCode}`)
                    .then(res => res.json())
                    .then(data => {
                        if (data && data.places && data.places.length > 0) {
                            cityInput.value = data.places[0]['place name'];
                        }
                    }).catch(() => {});
            }
        });
    }

    // 3. Validering i kassan (Matchning av E-post och Lösenord)
    const checkoutForm = document.querySelector('form');
    if (checkoutForm) {
        checkoutForm.addEventListener('submit', function(e) {
            const email = document.getElementById('emailInput')?.value;
            const confirmEmail = document.getElementById('confirmEmailInput')?.value;
            const pass = document.getElementById('passwordInput')?.value;
            const confirmPass = document.getElementById('confirmPasswordInput')?.value;

            if (email && confirmEmail && email.toLowerCase() !== confirmEmail.toLowerCase()) {
                e.preventDefault();
                alert('⚠️ E-postadresserna matchar inte!');
                return false;
            }
            if (pass && confirmPass && pass !== confirmPass) {
                e.preventDefault();
                alert('⚠️ Lösenorden matchar inte!');
                return false;
            }
        });
    }
});
</script>
"""

USER_REGISTER_TEMPLATE = """
<!DOCTYPE html>
<html lang="sv">
<head>
    <meta charset="UTF-8">
    <title>Skapa konto - URBAN NATION</title>
    """ + COMMON_STYLES + """
</head>
<body class="bg-light">
    <div class="container my-5" style="max-width: 550px;">
        <div class="text-center mb-4">
            <img src="{{ logo_url }}" alt="Urban Nation Logo" style="height: 80px; width: 80px; border-radius: 50%; object-fit: cover;" class="mb-2 shadow-sm" onerror="this.style.display='none'">
            <h2 class="fw-bold text-uppercase">URBAN NATION</h2>
        </div>
        <div class="card p-4 shadow-sm">
            <h3 class="mb-3 text-center">Skapa ett URBAN NATION Konto</h3>
            {% with messages = get_flashed_messages(with_categories=true) %}
              {% if messages %}{% for c, m in messages %}<div class="alert alert-{{ c }}">{{ m }}</div>{% endfor %}{% endif %}
            {% endwith %}

            <form method="POST">
                <div class="row mb-3">
                    <div class="col-md-6"><label class="form-label">Förnamn</label><input type="text" class="form-control" name="first_name" required placeholder="Anna"></div>
                    <div class="col-md-6"><label class="form-label">Efternamn</label><input type="text" class="form-control" name="last_name" required placeholder="Andersson"></div>
                </div>
                <div class="row mb-3">
                    <div class="col-md-6"><label class="form-label">E-postadress</label><input type="email" class="form-control" name="email" required placeholder="anna@example.se"></div>
                    <div class="col-md-6"><label class="form-label">Telefonnummer</label><input type="text" class="form-control" name="phone" required placeholder="070-123 45 67"></div>
                </div>
                <div class="row mb-3">
                    <div class="col-md-6"><label class="form-label">Lösenord</label><input type="password" class="form-control" name="password" required placeholder="Välj ett säkert lösenord"></div>
                    <div class="col-md-6"><label class="form-label">Bekräfta lösenord</label><input type="password" class="form-control" name="confirm_password" required placeholder="Upprepa lösenordet"></div>
                </div>
                <div class="mb-3"><label class="form-label">Gatuadress</label><input type="text" class="form-control" id="addressInput" name="address" required placeholder="t.ex. Sveavägen 10"></div>
                <div class="row mb-3">
                    <div class="col-md-6"><label class="form-label">Postnummer</label><input type="text" class="form-control" id="postalCodeInput" name="postal_code" required placeholder="111 57"></div>
                    <div class="col-md-6"><label class="form-label">Stad</label><input type="text" class="form-control" id="cityInput" name="city" required placeholder="Stockholm"></div>
                </div>
                <button type="submit" class="btn btn-dark w-100 btn-lg">Skapa Mitt Konto</button>
            </form>

            <!-- Social Logins (Google, Apple, Facebook, Instagram, TikTok) pour l'inscription -->
            <div class="d-flex align-items-center my-4">
                <hr class="flex-grow-1 border-secondary">
                <span class="px-2 text-muted small fw-bold">eller registrera dig med</span>
                <hr class="flex-grow-1 border-secondary">
            </div>

            <div class="d-flex flex-column gap-2">
                <a href="/login/google" class="btn btn-outline-dark w-100 d-flex align-items-center justify-content-center gap-2 py-2 fw-semibold">
                    <svg width="18" height="18" viewBox="0 0 24 24"><path fill="currentColor" d="M12.545 10.239v3.821h5.445c-.712 2.315-2.647 3.972-5.445 3.972a6.033 6.033 0 1 1 6.033-6.033c0 .337-.027.668-.078.991h3.918A10.024 10.024 0 0 0 12.545 2C6.98 2 2.47 6.51 2.47 12.075c0 5.564 4.51 10.075 10.075 10.075 6.115 0 10.075-4.304 10.075-10.239 0-.583-.051-1.156-.145-1.672h-9.93z"/></svg>
                    Fortsätt med Google
                </a>
                <a href="/login/apple" class="btn btn-outline-dark w-100 d-flex align-items-center justify-content-center gap-2 py-2 fw-semibold">
                    <svg width="18" height="18" viewBox="0 0 24 24"><path fill="currentColor" d="M18.71 19.5c-.83 1.24-1.71 2.45-3.05 2.47-1.34.03-1.77-.79-3.29-.79-1.53 0-2 .77-3.27.82-1.31.05-2.3-1.32-3.14-2.53C4.25 17 2.94 12.45 4.7 9.39c.87-1.52 2.43-2.48 4.12-2.51 1.28-.02 2.5.87 3.29.87.78 0 2.26-1.07 3.81-.91.65.03 2.47.26 3.64 1.98-.09.06-2.17 1.28-2.15 3.81.03 3.02 2.65 4.03 2.68 4.04-.03.07-.42 1.44-1.38 2.83M15.97 6.85c.67-.82 1.13-1.96.99-3.1-.98.04-2.19.66-2.88 1.47-.62.72-1.16 1.89-.99 3.02 1.1.09 2.23-.55 2.88-1.39"/></svg>
                    Fortsätt med Apple
                </a>
                <a href="/login/facebook" class="btn btn-outline-dark w-100 d-flex align-items-center justify-content-center gap-2 py-2 fw-semibold">
                    <svg width="18" height="18" viewBox="0 0 24 24"><path fill="currentColor" d="M22 12c0-5.52-4.48-10-10-10S2 6.48 2 12c0 4.84 3.44 8.87 8 9.8V15H7.5v-3H10V9.5C10 7.01 11.49 5.6 13.78 5.6c1.1 0 2.25.2 2.25.2v2.48h-1.27c-1.23 0-1.62.77-1.62 1.56V12h2.78l-.44 3h-2.34v6.8c4.56-.93 8-4.96 8-9.8z"/></svg>
                    Fortsätt med Facebook
                </a>
                <a href="/login/instagram" class="btn btn-outline-dark w-100 d-flex align-items-center justify-content-center gap-2 py-2 fw-semibold">
                    <svg width="18" height="18" viewBox="0 0 24 24"><path fill="currentColor" d="M12 2.163c3.204 0 3.584.012 4.85.07 3.252.148 4.771 1.691 4.919 4.919.058 1.265.069 1.645.069 4.849 0 3.205-.012 3.584-.069 4.849-.149 3.225-1.664 4.771-4.919 4.919-1.266.058-1.644.07-4.85.07-3.204 0-3.584-.012-4.849-.07-3.26-.149-4.771-1.699-4.919-4.92-.058-1.265-.07-1.644-.07-4.849 0-3.204.013-3.583.07-4.849.149-3.227 1.664-4.771 4.919-4.919 1.266-.057 1.645-.069 4.849-.069zm0-2.163c-3.259 0-3.667.014-4.947.072-4.358.2-6.78 2.618-6.98 6.98-.059 1.281-.073 1.689-.073 4.948 0 3.259.014 3.668.072 4.948.2 4.358 2.618 6.78 6.98 6.98 1.281.058 1.689.072 4.948.072 3.259 0 3.668-.014 4.948-.072 4.354-.2 6.782-2.618 6.979-6.98.059-1.28.073-1.689.073-4.948 0-3.259-.014-3.667-.072-4.947-.196-4.354-2.617-6.78-6.979-6.98-1.281-.059-1.69-.073-4.949-.073zm0 5.838c-3.403 0-6.162 2.759-6.162 6.162s2.759 6.163 6.162 6.163 6.162-2.759 6.162-6.163c0-3.403-2.759-6.162-6.162-6.162zm0 10.162c-2.209 0-4-1.79-4-4 0-2.209 1.791-4 4-4s4 1.791 4 4c0 2.21-1.791 4-4 4zm6.406-11.845c-.796 0-1.441.645-1.441 1.44s.645 1.44 1.441 1.44c.795 0 1.439-.645 1.439-1.44s-.644-1.44-1.439-1.44z"/></svg>
                    Fortsätt med Instagram
                </a>
                <a href="/login/tiktok" class="btn btn-outline-dark w-100 d-flex align-items-center justify-content-center gap-2 py-2 fw-semibold">
                    <svg width="18" height="18" viewBox="0 0 24 24"><path fill="currentColor" d="M12.525.02c1.31-.02 2.61-.01 3.91-.02.08 1.53.63 3.09 1.75 4.17 1.12 1.11 2.7 1.62 4.24 1.79v4.03c-1.44-.05-2.89-.35-4.2-.97-.57-.26-1.1-.59-1.62-.93-.01 2.92.01 5.84-.02 8.75-.08 1.4-.54 2.79-1.35 3.94-1.31 1.92-3.58 3.17-5.91 3.21-1.43.08-2.86-.31-4.08-1.03-2.02-1.19-3.44-3.37-3.65-5.71-.02-.5-.03-1-.01-1.49.18-1.9 1.12-3.72 2.58-4.96 1.66-1.44 3.98-2.13 6.15-1.72.02 1.48-.04 2.96-.04 4.44-.99-.32-2.15-.23-3.02.37-.82.56-1.36 1.5-1.42 2.5-.06 1.08.38 2.16 1.17 2.87.82.73 1.98 1.05 3.07.84 1.11-.2 2.08-.94 2.56-1.96.24-.52.35-1.1.34-1.68.02-3.67.01-7.34.01-11.01z"/></svg>
                    Fortsätt med TikTok
                </a>
            </div>

            <div class="text-center mt-3"><a href="/login" class="text-dark">Har du redan ett konto? Logga in här</a></div>
            <a href="/" class="btn btn-link mt-2 text-center d-block text-dark">&larr; Tillbaka till URBAN NATION</a>
        </div>
    </div>
    """ + ADDRESS_AUTOCOMPLETE_SCRIPT + """
</body>
</html>
"""

USER_ACCOUNT_TEMPLATE = """
<!DOCTYPE html>
<html lang="sv">
<head>
    <meta charset="UTF-8">
    <title>Mitt Konto - URBAN NATION</title>
    """ + COMMON_STYLES + """
</head>
<body class="bg-light">
    <nav class="navbar navbar-dark bg-dark">
        <div class="container">
            <a class="navbar-brand text-white fw-bold d-flex align-items-center gap-2" href="/">
                <img src="{{ logo_url }}" alt="Urban Nation Logo" style="height: 32px; width: 32px; border-radius: 50%;" onerror="this.style.display='none'">
                <span>URBAN NATION</span>
            </a>
            <div>
                <a href="/" class="btn btn-outline-light btn-sm me-2">Tillbaka till Shoppen</a>
                <a href="/logout" class="btn btn-danger btn-sm">Logga ut</a>
            </div>
        </div>
    </nav>

    <div class="container my-5">
        {% with messages = get_flashed_messages(with_categories=true) %}
          {% if messages %}{% for c, m in messages %}<div class="alert alert-{{ c }} shadow-sm rounded-3">{{ m }}</div>{% endfor %}{% endif %}
        {% endwith %}

        <div class="row">
            <!-- Profil, ändring av personuppgifter & lösenord -->
            <div class="col-md-4 mb-4">
                <div class="card p-4 shadow-sm bg-white border-0">
                    <div class="text-center mb-3">
                        <div class="bg-dark text-white rounded-circle d-inline-flex align-items-center justify-content-center fw-bold" style="width: 70px; height: 70px; font-size: 28px;">
                            {{ current_user.first_name[0] if current_user.first_name else current_user.name[0] }}
                        </div>
                        <h4 class="mt-2 mb-0">{{ current_user.name }}</h4>
                        <small class="text-muted">{{ current_user.email }}</small>
                    </div>
                    <hr>
                    <h5 class="mb-3">✏️ Ändra dina uppgifter</h5>
                    <form method="POST">
                        <div class="row mb-2">
                            <div class="col-6"><label class="form-label small">Förnamn</label><input type="text" class="form-control form-control-sm" name="first_name" value="{{ current_user.first_name if current_user.first_name else current_user.name.split()[0] }}" required></div>
                            <div class="col-6"><label class="form-label small">Efternamn</label><input type="text" class="form-control form-control-sm" name="last_name" value="{{ current_user.last_name if current_user.last_name else ' '.join(current_user.name.split()[1:]) }}" required></div>
                        </div>
                        <div class="mb-2"><label class="form-label small">Telefon</label><input type="text" class="form-control form-control-sm" name="phone" value="{{ current_user.phone }}" required></div>
                        <div class="mb-2"><label class="form-label small">Adress</label><input type="text" class="form-control form-control-sm" id="addressInput" name="address" value="{{ current_user.address }}" required></div>
                        <div class="row mb-2">
                            <div class="col-6"><label class="form-label small">Postnr</label><input type="text" class="form-control form-control-sm" id="postalCodeInput" name="postal_code" value="{{ current_user.postal_code }}" required></div>
                            <div class="col-6"><label class="form-label small">Stad</label><input type="text" class="form-control form-control-sm" id="cityInput" name="city" value="{{ current_user.city }}" required></div>
                        </div>
                        <button type="submit" class="btn btn-dark btn-sm w-100 mt-2">Spara uppdateringar</button>
                    </form>
                </div>

                <!-- 🔒 FORMULAIRE DE MODIFICATION DU MOT DE PASSE -->
                <div class="card p-4 shadow-sm mt-4 bg-white border-0">
                    <h5 class="fw-bold mb-3">🔒 Ändra lösenord</h5>
                    <form action="/change-password" method="POST">
                        <div class="mb-3">
                            <label class="form-label small fw-bold">Nuvarande lösenord</label>
                            <input type="password" class="form-control form-control-sm" name="current_password" required>
                        </div>
                        <div class="mb-3">
                            <label class="form-label small fw-bold">Nytt lösenord</label>
                            <input type="password" class="form-control form-control-sm" name="new_password" required>
                        </div>
                        <button type="submit" class="btn btn-dark btn-sm fw-bold w-100">Uppdatera lösenord</button>
                    </form>
                </div>
            </div>

            <!-- Historik, Orderstatus & Eventbiljetter -->
            <div class="col-md-8">
                <!-- Section Köphistorik & Orderstatus -->
                <div class="card p-4 shadow-sm bg-white mb-4 border-0">
                    <div class="d-flex justify-content-between align-items-center mb-4">
                        <h3 class="mb-0">Köphistorik & Orderstatus</h3>
                        <span class="badge bg-dark fs-6">{{ orders|length if orders else 0 }} Beställningar</span>
                    </div>

                    {% if orders %}
                        {% for order in orders %}
                        <div class="border rounded-3 p-3 mb-4 bg-light shadow-sm">
                            <!-- En-tête de la commande -->
                            <div class="d-flex justify-content-between align-items-center flex-wrap gap-2 mb-3 pb-2 border-bottom">
                                <div>
                                    <strong class="fs-5 text-dark">Order #{{ order.id }}</strong>
                                    <span class="text-muted small ms-2">{{ order.date }}</span>
                                </div>
                                <div>
                                    {% if 'VIP' in order.status %}
                                        <span class="badge bg-warning text-dark px-3 py-2 fs-6">🎁 VIP Inbjudan</span>
                                    {% elif 'Mottagen' in order.status %}
                                        <span class="badge bg-info text-dark px-3 py-2 fs-6">🔄 Överförd</span>
                                    {% elif order.status == 'Skickad' %}
                                        <span class="badge bg-primary px-3 py-2 fs-6">Skickad</span>
                                    {% elif order.status == 'Levererad / Avslutad' %}
                                        <span class="badge bg-success px-3 py-2 fs-6">Levererad</span>
                                    {% else %}
                                        <span class="badge bg-warning text-dark px-3 py-2 fs-6">Under behandling</span>
                                    {% endif %}
                                </div>
                            </div>

                            <!-- Barre de progression du statut de la commande -->
                            <div class="mb-4 px-2">
                                <div class="progress" style="height: 8px;">
                                    {% if order.status == 'Levererad / Avslutad' or 'VIP' in order.status or 'Mottagen' in order.status %}
                                        <div class="progress-bar bg-success" style="width: 100%;"></div>
                                    {% elif order.status == 'Skickad' %}
                                        <div class="progress-bar bg-primary" style="width: 66%;"></div>
                                    {% else %}
                                        <div class="progress-bar bg-warning" style="width: 33%;"></div>
                                    {% endif %}
                                </div>
                                <div class="d-flex justify-content-between text-muted small mt-1" style="font-size: 0.75rem;">
                                    <span class="fw-bold text-dark">1. Mottagen</span>
                                    <span class="{% if order.status in ['Skickad', 'Levererad / Avslutad'] or 'VIP' in order.status or 'Mottagen' in order.status %}fw-bold text-dark{% endif %}">2. Behandlas</span>
                                    <span class="{% if order.status in ['Skickad', 'Levererad / Avslutad'] or 'VIP' in order.status or 'Mottagen' in order.status %}fw-bold text-dark{% endif %}">3. Skickad</span>
                                    <span class="{% if order.status == 'Levererad / Avslutad' or 'VIP' in order.status or 'Mottagen' in order.status %}fw-bold text-success{% endif %}">4. Levererad</span>
                                </div>
                            </div>

                            <!-- Liste des articles de la commande -->
                            <h6 class="fw-bold mb-2 text-muted">Köpta Artiklar / Inbjudningar</h6>
                            <ul class="list-group mb-3">
                                {% for item in order.order_items %}
                                <li class="list-group-item d-flex justify-content-between align-items-center py-2">
                                    <div>
                                        <span>{% if item.type == 'ticket' %}🎫{% else %}🛍️{% endif %} <strong>{{ item.name }}</strong></span>
                                        {% if item.size or item.color %}
                                            <small class="text-muted d-block" style="font-size: 0.8rem;">
                                                {% if item.size %}Storlek: {{ item.size }}{% endif %}
                                                {% if item.color %} | Färg: {{ item.color }}{% endif %}
                                            </small>
                                        {% endif %}
                                    </div>
                                    <span class="fw-bold text-dark">{{ item.price }} SEK</span>
                                </li>
                                {% endfor %}
                            </ul>

                            <!-- Récapitulatif financier et informations de livraison -->
                            <div class="d-flex justify-content-between align-items-center flex-wrap gap-2 mb-3 bg-white p-2 rounded border">
                                <div>
                                    <small class="text-muted d-block">Leveransmetod: <strong>{{ order.shipping }}</strong></small>
                                    {% if order.tracking_number %}
                                        <small class="text-dark d-block mt-1"> <strong>Spårningsnummer:</strong> <code class="bg-light px-2 py-1 rounded">{{ order.tracking_number }}</code></small>
                                    {% endif %}
                                </div>
                                <div class="text-end">
                                    <small class="text-muted d-block">Totalt belopp:</small>
                                    <strong class="fs-4 text-dark">{{ order.total }} SEK</strong>
                                </div>
                            </div>

                            <!-- Options de gestion : Téléchargement de Facture & Retur -->
                            <div class="d-flex gap-2 mt-2 flex-wrap">
                                <a href="/download_invoice/{{ order.id }}" class="btn btn-outline-dark btn-sm fw-bold">
                                    📄 Ladda ner Faktura (PDF)
                                </a>

                                {% if 'VIP' not in order.status and 'Mottagen' not in order.status %}
                                    <button class="btn btn-outline-danger btn-sm" data-bs-toggle="collapse" data-bs-target="#returnForm{{ order.id }}">
                                        🔄 Begär Retur / Reklamation
                                    </button>
                                {% endif %}
                            </div>

                            <!-- Formulaire repliable de retour -->
                            <div class="collapse mt-3" id="returnForm{{ order.id }}">
                                <form action="/request_return/{{ order.id }}" method="POST" class="card card-body bg-white p-3 border">
                                    <h6 class="mb-2 fw-bold">Begär Retur för Order #{{ order.id }}</h6>
                                    <p class="text-muted small mb-2">Välj vilken produkt du vill returnera och ange anledning.</p>
                                    <div class="mb-2">
                                        <label class="form-label small fw-bold">Välj produkt</label>
                                        <select class="form-select form-select-sm" name="item_name">
                                            {% for item in order.order_items %}
                                                <option value="{{ item.name }}">{{ item.name }} ({{ item.price }} SEK)</option>
                                            {% endfor %}
                                        </select>
                                    </div>
                                    <div class="mb-3">
                                        <label class="form-label small fw-bold">Anledning till retur</label>
                                        <input type="text" class="form-control form-control-sm" name="reason" required placeholder="t.ex. Fel storlek, ångrat köp, etc.">
                                    </div>
                                    <button type="submit" class="btn btn-dark btn-sm">Skicka Returbegäran</button>
                                </form>
                            </div>
                        </div>
                        {% endfor %}
                    {% else %}
                        <div class="text-center py-5 bg-light rounded border">
                            <p class="fs-5 text-muted mb-2">Du har inga tidigare beställningar ännu.</p>
                            <a href="/#catalog-section" class="btn btn-dark btn-sm">Utforska Shoppen & Gör Din Första Beställning</a>
                        </div>
                    {% endif %}
                </div>

                <!-- Section Eventbiljetter & QR-koder (Inklusive Transfert, VIP & Wallet) -->
                <div class="card p-4 shadow-sm bg-white border-0">
                    <h3 class="mb-3">🎫 Mina Eventbiljetter & QR-koder</h3>
                    {% set has_tickets = namespace(value=false) %}
                    {% for order in orders %}
                        {% for item in order.order_items %}
                            {% if item.type == 'ticket' %}
                                {% set has_tickets.value = true %}
                                {% set ticket_qr_data = item.ticket_code if item.ticket_code else 'TICKET-' ~ order.id ~ '-' ~ item.name %}
                                <div class="card mb-3 border-dark bg-light shadow-sm">
                                    <div class="card-body">
                                        <div class="d-flex justify-content-between align-items-center flex-wrap gap-3">
                                            <div>
                                                <h5 class="card-title text-dark fw-bold mb-1">{{ item.name }}</h5>
                                                <p class="text-muted small mb-1">Order ID: #{{ order.id }} | Gäst: {{ current_user.name }}</p>
                                                {% if 'VIP' in order.status or 'VIP' in item.name %}
                                                    <span class="badge bg-warning text-dark border border-dark">🌟 VIP-Pass / Inbjudan</span>
                                                {% elif 'Mottagen' in order.status or 'Överförd' in item.name %}
                                                    <span class="badge bg-info text-dark">🔄 Överförd Biljett</span>
                                                {% else %}
                                                    <span class="badge bg-dark text-white">Giltig Biljett</span>
                                                {% endif %}
                                                <div class="mt-3 d-flex flex-wrap gap-2">
                                                    <a href="/download_ticket/{{ order.id }}/{{ item.name }}" class="btn btn-dark btn-sm fw-bold">📄 Ladda ner PDF-biljett</a>

                                                    <!-- Bouton pour ouvrir le formulaire de transfert -->
                                                    <button class="btn btn-outline-dark btn-sm fw-bold" data-bs-toggle="collapse" data-bs-target="#transferForm{{ order.id }}{{ loop.index }}">
                                                        🔄 Överför till en vän
                                                    </button>
                                                </div>
                                            </div>
                                            <div class="text-center bg-white p-2 rounded border border-secondary shadow-sm">
                                                <img src="https://api.qrserver.com/v1/create-qr-code/?size=110x110&data={{ ticket_qr_data }}" alt="QR Code" class="img-fluid" style="max-width: 110px;">
                                                <small class="d-block text-dark fw-bold mt-1" style="font-size: 0.7rem;">Skanna i entrén</small>
                                            </div>
                                        </div>

                                        <!-- FORMULAIRE REPLIABLE DE TRANSFERT DE BILLET -->
                                        <div class="collapse mt-3" id="transferForm{{ order.id }}{{ loop.index }}">
                                            <form action="/transfer_ticket/{{ order.id }}/{{ item.name }}" method="POST" class="card card-body bg-white border border-dark p-3">
                                                <h6 class="fw-bold mb-1 text-dark">🔄 Överför biljett till en vän</h6>
                                                <p class="text-muted small mb-2">Ange e-postadressen till personen som ska få biljetten. Din nuvarande QR-kod kommer att spärras och en ny skickas till din vän.</p>
                                                <div class="input-group input-group-sm mb-2">
                                                    <input type="email" class="form-control" name="recipient_email" placeholder="van@example.com" required>
                                                    <button type="submit" class="btn btn-dark fw-bold">Skicka Biljett 🚀</button>
                                                </div>
                                            </form>
                                        </div>

                                        <!-- SECTION DE SÉLECTION D'AJOUT AU WALLET SMARTPHONE -->
                                        <div class="mt-3 pt-3 border-top d-flex flex-wrap gap-2 align-items-center">
                                            <small class="text-muted fw-bold w-100 d-block mb-1">📱 Spara i din smartphone:</small>

                                            <!-- Bouton Apple Wallet (iOS) -->
                                            <a href="/download_apple_wallet/{{ order.id }}/{{ item.name }}" class="btn btn-dark btn-sm fw-bold d-inline-flex align-items-center gap-2 px-3 py-2 shadow-sm rounded-3">
                                                <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" class="bi bi-apple" viewBox="0 0 16 16">
                                                    <path d="M11.182.008C11.148-.03 9.923.023 8.857 1.18c-1.066 1.156-.902 2.482-.878 2.516.024.034 1.52.097 2.491-1.12.97-1.217.746-2.53.712-2.568zm.14 3.695c-.492 0-1.681.3-2.313.3-.728 0-1.895-.316-2.903-.316-2.181 0-4.008 1.481-4.008 4.28 0 3.018 2.22 6.551 4.148 6.551 1.05 0 1.637-.621 2.827-.621 1.176 0 1.698.621 2.808.621 1.884 0 3.993-3.328 3.993-6.52 0-.154-.011-.3-.027-.442-1.393-.615-2.203-2.133-2.203-3.64 0-1.464.795-2.532 2.148-3.088-.808-1.126-2.093-1.815-3.473-1.815z"/>
                                                </svg>
                                                <span>Apple Wallet</span>
                                            </a>

                                            <!-- Bouton Google Wallet (Android) -->
                                            <a href="/add_google_wallet/{{ order.id }}/{{ item.name }}" target="_blank" class="btn btn-outline-dark btn-sm fw-bold d-inline-flex align-items-center gap-2 px-3 py-2 shadow-sm rounded-3 bg-white">
                                                <img src="https://upload.wikimedia.org/wikipedia/commons/f/f2/Google_Pay_Logo.svg" alt="Google Pay" style="height: 16px;">
                                                <span>Google Wallet</span>
                                            </a>
                                        </div>
                                    </div>
                                </div>
                            {% endif %}
                        {% endfor %}
                    {% endfor %}

                    {% if not has_tickets.value %}
                        <div class="text-center py-4 bg-light rounded border">
                            <p class="text-muted mb-0">Du har inga aktiva eventbiljetter i ditt konto för tillfället.</p>
                        </div>
                    {% endif %}
                </div>
            </div>
        </div>
    </div>
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
    """ + ADDRESS_AUTOCOMPLETE_SCRIPT + """
</body>
</html>
"""

ADMIN_LOGIN_TEMPLATE = """
<!DOCTYPE html>
<html lang="sv">
<head>
    <meta charset="UTF-8">
    <title>Admin Login - URBAN NATION</title>
    """ + COMMON_STYLES + """
</head>
<body class="bg-light">
    <div class="container my-5" style="max-width: 400px;">
        <div class="text-center mb-4">
            <img src="{{ logo_url }}" alt="Urban Nation Logo" style="height: 80px; width: 80px; border-radius: 50%; object-fit: cover;" class="mb-2 shadow-sm" onerror="this.style.display='none'">
            <h2 class="fw-bold text-uppercase">URBAN NATION</h2>
        </div>
        <div class="card p-4 shadow-sm">
            <h4 class="mb-3 text-center">Admin Inloggning</h4>
            {% with messages = get_flashed_messages(with_categories=true) %}
              {% if messages %}{% for c, m in messages %}<div class="alert alert-{{ c }}">{{ m }}</div>{% endfor %}{% endif %}
            {% endwith %}
            <form method="POST">
                <div class="mb-3"><label class="form-label">Lösenord</label><input type="password" class="form-control" name="password" required placeholder="Ange lösenord"></div>
                <button type="submit" class="btn btn-dark w-100">Logga in</button>
            </form>
            <a href="/" class="btn btn-link mt-3 text-center d-block text-dark">&larr; Tillbaka till URBAN NATION</a>
        </div>
    </div>
</body>
</html>
"""

ADMIN_DASHBOARD_TEMPLATE = """
<!DOCTYPE html>
<html lang="sv" style="scroll-behavior: smooth;">
<head>
    <meta charset="UTF-8">
    <title>Admin Dashboard - URBAN NATION</title>
    """ + COMMON_STYLES + """
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        .table-scroll-container { max-height: 400px; overflow-y: auto; border: 1px solid #dee2e6; border-radius: 0.375rem; }
        .table-scroll-container thead th { position: sticky; top: 0; background-color: #f8f9fa; z-index: 1; }

        /* Menu latéral coulissant en superposition (Overlay) */
        .admin-sidebar {
            height: 100%;
            width: 0;
            position: fixed;
            z-index: 1060;
            top: 0;
            right: 0;
            left: auto;
            background-color: #111111;
            overflow-x: hidden;
            transition: 0.3s ease;
            padding-top: 60px;
            box-shadow: -5px 0 15px rgba(0,0,0,0.5);
            display: flex;
            flex-direction: column;
        }

        .sidebar-overlay {
            display: none;
            position: fixed;
            top: 0;
            left: 0;
            width: 100vw;
            height: 100vh;
            background: rgba(0, 0, 0, 0.4);
            z-index: 1050;
        }
        .sidebar-overlay.active {
            display: block;
        }

        .admin-sidebar-content {
            flex-grow: 1;
            overflow-y: auto;
        }
        .admin-sidebar a {
            padding: 12px 20px;
            text-decoration: none;
            font-size: 0.95rem;
            color: #ffffff;
            display: block;
            transition: 0.2s;
            border-right: 4px solid transparent;
        }
        .admin-sidebar a:hover, .admin-sidebar a.active {
            background-color: #222222;
            color: #ffc107;
            border-right-color: #ffc107;
        }
        .admin-sidebar .close-btn {
            position: absolute;
            top: 15px;
            left: 20px;
            font-size: 24px;
            cursor: pointer;
            color: #fff;
        }
        .admin-sidebar-footer {
            padding: 20px;
            border-top: 1px solid #222222;
        }
        .admin-section { display: none; }
        .admin-section.active-section { display: block; }
    </style>
</head>
<body class="bg-light text-dark">

    <div id="sidebarOverlay" class="sidebar-overlay" onclick="closeNav()"></div>

    <div id="adminSidebar" class="admin-sidebar">
        <span class="close-btn" onclick="closeNav()">&times;</span>
        <h4 class="text-white px-4 mb-4 fw-bold text-end">URBAN NATION <span class="text-warning fs-6">Admin</span></h4>

        <div class="admin-sidebar-content">
            <a href="#" onclick="showSection('stats'); return false;" class="menu-link active text-end">📊 Statistik</a>
            <a href="#" onclick="showSection('b2b-section'); return false;" class="menu-link text-end">🏢 Fakturering</a>
            <a href="#" onclick="showSection('live-section'); return false;" class="menu-link text-end">📡 Styrning av Live Streaming</a>
            <a href="#" onclick="showSection('categories'); return false;" class="menu-link text-end">🏷️ Kategorier</a>
            <a href="#" onclick="showSection('orders'); return false;" class="menu-link text-end">🚚 Beställningar</a>
            <a href="#" onclick="showSection('returns'); return false;" class="menu-link text-end">🔄 Returer</a>
            <a href="#" onclick="showSection('promos'); return false;" class="menu-link text-end">🎟️ Rabattkoder</a>
            <a href="#" onclick="showSection('events'); return false;" class="menu-link text-end">🎉 Event</a>
            <a href="#" onclick="showSection('products'); return false;" class="menu-link text-end">📦 Produkter & Biljetter</a>
            <a href="#" onclick="showSection('customers-section'); return false;" class="menu-link text-end">⚙️ Kunder och Inställningar</a>
            <a href="#" onclick="showSection('guests-section'); return false;" class="menu-link text-end">🎟️ Inbjudna Gäster & VIP</a>
            <a href="#" onclick="showSection('transfers-section'); return false;" class="menu-link text-end">🔄 Överföringsbegäran</a>
            <a href="#" onclick="showSection('scanner-section'); return false;" class="menu-link text-end">📱 Ticket Scanner</a>
            <a href="#" onclick="showSection('checkin-report-section'); return false;" class="menu-link text-end">⏲ Real-Time Check-in</a>
            <a href="#" onclick="showSection('logs'); return false;" class="menu-link text-end">📋 Aktionslogg</a>
        </div>

        <div class="admin-sidebar-footer">
            <a href="/admin/logout" class="btn btn-danger w-100 fw-bold text-center border-0 py-2">
                🚪 Logga ut
            </a>
        </div>
    </div>

    <nav class="navbar navbar-dark bg-dark">
        <div class="container-fluid px-4">
            <div class="d-flex align-items-center gap-3">
                <a class="navbar-brand text-white fw-bold d-flex align-items-center gap-2" href="/admin">
                    <img src="{{ logo_url }}" alt="Urban Nation Logo" style="height: 36px; width: 36px; border-radius: 50%;" onerror="this.style.display='none'">
                    <span>URBAN NATION <span class="text-light">Administration</span></span>
                </a>
            </div>
            <div class="d-flex align-items-center gap-2">
                <a href="/" class="btn btn-outline-light btn-sm me-2">Visa Hemsida</a>
                <button class="btn btn-outline-warning btn-sm fw-bold" onclick="openNav()">
                    ☰ Menu
                </button>
            </div>
        </div>
    </nav>

    <div id="main-content" class="container my-5">
        {% with messages = get_flashed_messages(with_categories=true) %}
          {% if messages %}{% for c, m in messages %}<div class="alert alert-{{ c }}">{{ m }}</div>{% endfor %}{% endif %}
        {% endwith %}

        <div class="d-flex justify-content-between align-items-center mb-4 bg-white p-3 rounded shadow-sm border">
            <h4 class="mb-0">Exportera Data (Excel / CSV)</h4>
            <div class="d-flex gap-2">
                <a href="/admin/export/orders" class="btn btn-dark btn-sm">Beställningar CSV</a>
                <a href="/admin/export/customers" class="btn btn-dark btn-sm">Kunder CSV</a>
                <a href="/admin/export/event_attendees" class="btn btn-dark btn-sm">Event Deltagare</a>
            </div>
        </div>

        <div class="card p-4 shadow-sm mb-4 border-dark">
            <div class="mb-3">
                <h4 class="fw-bold mb-0">💰 Exporteringscenter & Bokföringsrapporter</h4>
                <p class="text-muted small mb-0">Filtrera försäljning och momsunnderlag per månad eller år för bokföringen.</p>
            </div>

            <form action="/admin/sales_report_pdf" method="GET" target="_blank" class="row g-3 align-items-end">
                <div class="col-md-3">
                    <label class="form-label small fw-bold">Välj År (År)</label>
                    <select class="form-select form-select-sm" name="year">
                        <option value="">Alla år</option>
                        <option value="2026" selected>2026</option>
                        <option value="2025">2025</option>
                    </select>
                </div>
                <div class="col-md-3">
                    <label class="form-label small fw-bold">Välj Månad</label>
                    <select class="form-select form-select-sm" name="month">
                        <option value="">Alla månader (Helår)</option>
                        <option value="01">Januari (01)</option>
                        <option value="02">Februari (02)</option>
                        <option value="03">Mars (03)</option>
                        <option value="04">April (04)</option>
                        <option value="05">Maj (05)</option>
                        <option value="06">Juni (06)</option>
                        <option value="07">Juli (07)</option>
                        <option value="08">Augusti (08)</option>
                        <option value="09">September (09)</option>
                        <option value="10" selected>Oktober (10)</option>
                        <option value="11">November (11)</option>
                        <option value="12">December (12)</option>
                    </select>
                </div>
                <div class="col-md-6 d-flex gap-2">
                    <button type="submit" class="btn btn-dark btn-sm fw-bold w-50">
                        📄 Visa PDF-rapport
                    </button>
                    <button type="button" class="btn btn-outline-success btn-sm fw-bold w-50" onclick="exportFilteredCSV()">
                        📊 Ladda ner CSV
                    </button>
                </div>
            </form>
        </div>

        <!-- SECTION 1: STATISTIK -->
        <section id="stats" class="admin-section active-section mb-5">
            <div class="d-flex justify-content-between align-items-center mb-3">
                <h3 class="mb-0">Försäljningsstatistik & Analys</h3>
                <button class="btn btn-dark btn-sm" data-bs-toggle="modal" data-bs-target="#editStatsModal">⚙️ Ändra statistik</button>
            </div>
            <div class="row mb-4">
                <div class="col-md-3 mb-3">
                    <div class="card p-3 shadow-sm bg-white text-center h-100 border-start border-4 border-dark">
                        <h5 class="text-muted fs-6">Total Omsättning</h5>
                        <h3 class="fw-bold text-dark mb-0">{{ total_revenue }} SEK</h3>
                    </div>
                </div>
                <div class="col-md-3 mb-3">
                    <div class="card p-3 shadow-sm bg-white text-center h-100 border-start border-4 border-secondary">
                        <h5 class="text-muted fs-6">Sålda Artiklar</h5>
                        <h3 class="fw-bold text-secondary mb-0">{{ total_items_sold }} st</h3>
                    </div>
                </div>
                <div class="col-md-3 mb-3">
                    <div class="card p-3 shadow-sm bg-white text-center h-100 border-start border-4 border-dark">
                        <h5 class="text-muted fs-6">Sålda Biljetter</h5>
                        <h3 class="fw-bold text-dark mb-0">{{ total_tickets_sold }} st</h3>
                    </div>
                </div>
                <div class="col-md-3 mb-3">
                    <div class="card p-3 shadow-sm bg-white text-center h-100 border-start border-4 border-secondary">
                        <h5 class="text-muted fs-6">Kunder</h5>
                        <h3 class="fw-bold text-secondary mb-0">{{ customers|length }} pers</h3>
                    </div>
                </div>
            </div>
            <div class="row">
                <div class="col-md-7 mb-3">
                    <div class="card p-4 shadow-sm bg-white h-100">
                        <h5>Lagersituation: Inlagda vs Sålda (Dynamisk)</h5>
                        <canvas id="barChart" height="200"></canvas>
                    </div>
                </div>
                <div class="col-md-5 mb-3">
                    <div class="card p-4 shadow-sm bg-white h-100">
                        <h5>Intäktsfördelning</h5>
                        <canvas id="pieChart" height="200"></canvas>
                    </div>
                </div>
            </div>
        </section>
        
        <!-- SECTION B2B FAKTURERING -->
        <section id="b2b-section" class="admin-section card p-4 shadow-sm mb-5">
            <div class="d-flex justify-content-between align-items-center mb-4">
                <h3 class="mb-0">🏢 B2B Fakturering & Företagssammarbeten</h3>
                <button class="btn btn-dark btn-sm" data-bs-toggle="modal" data-bs-target="#newB2BModal">➕ Skapa ny B2B-faktura</button>
            </div>
        
            <!-- Tableau des factures B2B existantes -->
            <div class="table-scroll-container">
                <table class="table table-striped align-middle mb-0">
                    <thead>
                        <tr>
                            <th>ID</th>
                            <th>Företag</th>
                            <th>Org.nummer</th>
                            <th>E-post</th>
                            <th>Beskrivning</th>
                            <th>Belopp</th>
                            <th>Datum</th>
                            <th>Status</th>
                            <th>Åtgärd</th>
                        </tr>
                    </thead>
                    <tbody>
                        {% for inv in b2b_invoices %}
                        <tr>
                            <td>#{{ inv.id }}</td>
                            <td><strong>{{ inv.company_name }}</strong></td>
                            <td><code>{{ inv.org_number }}</code></td>
                            <td>{{ inv.email }}</td>
                            <td>{{ inv.items_description }}</td>
                            <td><strong class="text-dark">{{ inv.amount }} SEK</strong></td>
                            <td>{{ inv.date }}</td>
                            <td><span class="badge bg-secondary">{{ inv.status }}</span></td>
                            <td>
                                <a href="/admin/download_b2b_invoice/{{ inv.id }}" class="btn btn-outline-dark btn-sm fw-bold">📄 PDF</a>
                            </td>
                        </tr>
                        {% endfor %}
                    </tbody>
                </table>
            </div>
        </section>
        
        <!-- MODALE DE CRÉATION DE FACTURE B2B -->
        <div class="modal fade" id="newB2BModal" tabindex="-1">
            <div class="modal-dialog">
                <div class="modal-content">
                    <form action="/admin/b2b_invoices" method="POST">
                        <div class="modal-header">
                            <h5 class="modal-title fw-bold">Skapa ny B2B-faktura</h5>
                            <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                        </div>
                        <div class="modal-body">
                            <div class="mb-3">
                                <label class="form-label small fw-bold">Företagsnamn</label>
                                <input type="text" class="form-control" name="company_name" required placeholder="Ex: Nordic Fashion AB">
                            </div>
                            <div class="mb-3">
                                <label class="form-label small fw-bold">Organisationsnummer</label>
                                <input type="text" class="form-control" name="org_number" required placeholder="556XXX-XXXX">
                            </div>
                            <div class="mb-3">
                                <label class="form-label small fw-bold">Företagets E-post</label>
                                <input type="email" class="form-control" name="email" required placeholder="faktura@foretag.se">
                            </div>
                            <div class="mb-3">
                                <label class="form-label small fw-bold">Beskrivning av varor / tjänster</label>
                                <textarea class="form-control" name="items_description" rows="2" required placeholder="Parti-leverans..."></textarea>
                            </div>
                            <div class="row">
                                <div class="col-md-6 mb-3">
                                    <label class="form-label small fw-bold">Belopp (SEK)</label>
                                    <input type="number" class="form-control" name="amount" required placeholder="15000">
                                </div>
                                <div class="col-md-6 mb-3">
                                    <label class="form-label small fw-bold">Fakturadatum</label>
                                    <input type="date" class="form-control" name="date" required value="2026-10-26">
                                </div>
                            </div>
                        </div>
                        <div class="modal-footer">
                            <button type="button" class="btn btn-outline-secondary btn-sm" data-bs-dismiss="modal">Avbryt</button>
                            <button type="submit" class="btn btn-dark btn-sm">Skicka Faktura 🚀</button>
                        </div>
                    </form>
                </div>
            </div>
        </div>
        
        <!-- SECTION LIVE STREAMING MULTI-PLATEFORMES & STATISTIQUES -->
        <section id="live-section" class="admin-section card p-4 shadow-sm mb-5 border-dark rounded-4">
            <div class="d-flex justify-content-between align-items-center mb-4">
                <div>
                    <h3 class="fw-bold mb-1">📡 Styrning av Live Streaming (Multi-plattform)</h3>
                    <p class="text-muted small mb-0">Aktivera en eller flera plattformar samtidigt för din direktsändning.</p>
                </div>
            </div>
        
            <form action="/admin/update_live" method="POST" class="bg-light p-3 rounded-3 mb-4 border">
                <div class="form-check form-switch mb-4">
                    <input class="form-check-input" type="checkbox" role="switch" name="live_active" id="liveActiveSwitch" {% if global_live.active %}checked{% endif %}>
                    <label class="form-check-label fw-bold fs-6 text-dark" for="liveActiveSwitch">🔴 Huvudbrytare: Aktivera Live-fönster på webbplatsen</label>
                </div>
        
                <div class="mb-3">
                    <label class="form-label small fw-bold">Live Titel</label>
                    <input type="text" class="form-control form-control-sm" name="live_title" value="{{ global_live.title }}">
                </div>
        
                <h6 class="fw-bold mt-4 mb-3">Välj aktiva plattformar & ange inbäddningslänkar:</h6>
        
                <div class="row g-3">
                    <!-- YOUTUBE -->
                    <div class="col-md-6">
                        <div class="p-3 border rounded bg-white shadow-sm">
                            <div class="form-check mb-2">
                                <input class="form-check-input" type="checkbox" name="active_youtube" id="checkYt" {% if global_live.platforms.youtube.active %}checked{% endif %}>
                                <label class="form-check-label fw-bold text-danger" for="checkYt">YouTube Live</label>
                            </div>
                            <input type="text" class="form-control form-control-sm" name="url_youtube" value="{{ global_live.platforms.youtube.url }}" placeholder="https://www.youtube.com/embed/...">
                        </div>
                    </div>
        
                    <!-- FACEBOOK -->
                    <div class="col-md-6">
                        <div class="p-3 border rounded bg-white shadow-sm">
                            <div class="form-check mb-2">
                                <input class="form-check-input" type="checkbox" name="active_facebook" id="checkFb" {% if global_live.platforms.facebook.active %}checked{% endif %}>
                                <label class="form-check-label fw-bold text-primary" for="checkFb">Facebook Live</label>
                            </div>
                            <input type="text" class="form-control form-control-sm" name="url_facebook" value="{{ global_live.platforms.facebook.url }}" placeholder="https://www.facebook.com/plugins/video.php?href=...">
                        </div>
                    </div>
        
                    <!-- TIKTOK -->
                    <div class="col-md-6">
                        <div class="p-3 border rounded bg-white shadow-sm">
                            <div class="form-check mb-2">
                                <input class="form-check-input" type="checkbox" name="active_tiktok" id="checkTt" {% if global_live.platforms.tiktok.active %}checked{% endif %}>
                                <label class="form-check-label fw-bold text-dark" for="checkTt">TikTok Live</label>
                            </div>
                            <input type="text" class="form-control form-control-sm" name="url_tiktok" value="{{ global_live.platforms.tiktok.url }}" placeholder="https://www.tiktok.com/embed/v2/...">
                        </div>
                    </div>
        
                    <!-- INSTAGRAM -->
                    <div class="col-md-6">
                        <div class="p-3 border rounded bg-white shadow-sm">
                            <div class="form-check mb-2">
                                <input class="form-check-input" type="checkbox" name="active_instagram" id="checkIg" {% if global_live.platforms.instagram.active %}checked{% endif %}>
                                <label class="form-check-label fw-bold text-secondary" for="checkIg">Instagram Live</label>
                            </div>
                            <input type="text" class="form-control form-control-sm" name="url_instagram" value="{{ global_live.platforms.instagram.url }}" placeholder="https://www.instagram.com/p/.../embed">
                        </div>
                    </div>
                </div>
        
                <div class="text-end mt-4">
                    <button type="submit" class="btn btn-dark btn-sm px-4 fw-bold">💾 Spara & Uppdatera Live Stream</button>
                </div>
            </form>
        
            <!-- STATISTIQUES DE PROVENANCE EN TEMPS RÉEL -->
            <div class="mt-4 pt-3 border-top">
                <div class="d-flex justify-content-between align-items-center mb-3">
                    <h5 class="fw-bold fs-6 mb-0">📊 Trafikanalys per plattform (Visningar i realtid)</h5>
                    <button type="button" class="btn btn-outline-dark btn-sm fw-bold" onclick="fetchLiveAnalytics()">🔄 Uppdatera statistik</button>
                </div>
        
                <div class="row text-center g-3">
                    <div class="col-md-3">
                        <div class="p-3 border rounded bg-white shadow-sm">
                            <small class="text-muted d-block fw-bold">YouTube</small>
                            <strong class="fs-3 text-danger" id="statYoutube">0</strong>
                            <span class="d-block text-muted small mt-1">visningar</span>
                        </div>
                    </div>
                    <div class="col-md-3">
                        <div class="p-3 border rounded bg-white shadow-sm">
                            <small class="text-muted d-block fw-bold">Facebook</small>
                            <strong class="fs-3 text-primary" id="statFacebook">0</strong>
                            <span class="d-block text-muted small mt-1">visningar</span>
                        </div>
                    </div>
                    <div class="col-md-3">
                        <div class="p-3 border rounded bg-white shadow-sm">
                            <small class="text-muted d-block fw-bold">TikTok</small>
                            <strong class="fs-3 text-dark" id="statTiktok">0</strong>
                            <span class="d-block text-muted small mt-1">visningar</span>
                        </div>
                    </div>
                    <div class="col-md-3">
                        <div class="p-3 border rounded bg-white shadow-sm">
                            <small class="text-muted d-block fw-bold">Instagram</small>
                            <strong class="fs-3 text-secondary" id="statInstagram">0</strong>
                            <span class="d-block text-muted small mt-1">visningar</span>
                        </div>
                    </div>
                </div>
            </div>
        </section>

        <!-- SECTION 2: KATEGORIER -->
        <section id="categories" class="admin-section card p-4 shadow-sm mb-5">
            <h3 class="mb-3">Hantera Produkttyper / Kategori</h3>
            <form action="/admin/add_type" method="POST" class="row g-3 mb-4">
                <div class="col-auto"><input type="text" class="form-control" name="type_name" required placeholder="Nytt typnamn"></div>
                <div class="col-auto"><button type="submit" class="btn btn-dark">Lägg till ny Typ</button></div>
            </form>
            <ul class="list-group">
                {% for t in product_types %}
                <li class="list-group-item d-flex justify-content-between align-items-center">
                    <form action="/admin/edit_type/{{ t.id }}" method="POST" class="d-flex gap-2 flex-grow-1 me-3">
                        <input type="text" class="form-control" name="type_name" value="{{ t.name }}" required>
                        <button type="submit" class="btn btn-outline-dark btn-sm text-nowrap">Byt namn</button>
                    </form>
                    <a href="/admin/delete_type/{{ t.id }}" class="btn btn-danger btn-sm" onclick="return confirm('Ta bort?')">Ta bort</a>
                </li>
                {% endfor %}
            </ul>
        </section>

        <!-- SECTION 3: BESTÄLLNINGAR -->
        <section id="orders" class="admin-section card p-4 shadow-sm mb-5">
            <h3 class="mb-3">Hantera Beställningar</h3>
            <div class="table-scroll-container">
                <table class="table table-striped align-middle mb-0">
                    <thead><tr><th>Order ID</th><th>Datum</th><th>Kund</th><th>Produkter</th><th>Totalt</th><th>Spårning</th><th>Status</th><th>Åtgärd</th></tr></thead>
                    <tbody>
                        {% for order in orders %}
                        <tr>
                            <td><strong>#{{ order.id }}</strong></td>
                            <td><small>{{ order.date }}</small></td>
                            <td>{{ order.customer_email }}</td>
                            <td>{% for item in order.order_items %}<small class="d-block">• {{ item.name }} ({{ item.price }} SEK)</small>{% endfor %}</td>
                            <td><strong>{{ order.total }} SEK</strong></td>
                            <td><code>{{ order.tracking_number if order.tracking_number else '-' }}</code></td>
                            <td><span class="badge bg-dark">{{ order.status }}</span></td>
                            <td>
                                <button class="btn btn-outline-dark btn-sm me-1" data-bs-toggle="modal" data-bs-target="#editOrderModal{{ order.id }}">Uppdatera</button>
                                <a href="/admin/order/resend_email/{{ order.id }}" class="btn btn-outline-secondary btn-sm">📧 Mejla</a>
                            </td>
                        </tr>
                        <div class="modal fade" id="editOrderModal{{ order.id }}" tabindex="-1">
                          <div class="modal-dialog"><div class="modal-content">
                            <form action="/admin/order/update/{{ order.id }}" method="POST">
                                <div class="modal-header"><h5 class="modal-title">Uppdatera Order #{{ order.id }}</h5><button type="button" class="btn-close" data-bs-dismiss="modal"></button></div>
                                <div class="modal-body">
                                    <div class="mb-3"><label class="form-label">Status</label>
                                        <select class="form-select" name="status">
                                            <option value="Under behandling" {% if order.status == 'Under behandling' %}selected{% endif %}>Under behandling</option>
                                            <option value="Skickad" {% if order.status == 'Skickad' %}selected{% endif %}>Skickad</option>
                                            <option value="Levererad / Avslutad" {% if order.status == 'Levererad / Avslutad' %}selected{% endif %}>Levererad / Avslutad</option>
                                        </select>
                                    </div>
                                    <div class="mb-3"><label class="form-label">Spårningsnummer</label><input type="text" class="form-control" name="tracking_number" value="{{ order.tracking_number if order.tracking_number else '' }}"></div>
                                </div>
                                <div class="modal-footer"><button type="submit" class="btn btn-dark">Spara</button></div>
                            </form>
                          </div></div>
                        </div>
                        {% endfor %}
                    </tbody>
                </table>
            </div>
        </section>

        <!-- SECTION 4: RETURER -->
        <section id="returns" class="admin-section card p-4 shadow-sm mb-5">
            <h3 class="mb-3">Hantera Returer</h3>
            {% if returns %}
            <div class="table-scroll-container">
                <table class="table table-striped align-middle mb-0">
                    <thead><tr><th>ID</th><th>Order</th><th>Kund</th><th>Produkt</th><th>Anledning</th><th>Belopp</th><th>Status</th><th>Åtgärd</th></tr></thead>
                    <tbody>
                        {% for r in returns %}
                        <tr>
                            <td>#{{ r.id }}</td><td>#{{ r.order_id }}</td><td>{{ r.customer_email }}</td><td>{{ r.item_name }}</td>
                            <td><small>{{ r.reason }}</small></td><td><strong>{{ r.amount }} SEK</strong></td>
                            <td><span class="badge bg-secondary">{{ r.status }}</span></td>
                            <td>
                                {% if r.status == 'Under behandling' %}
                                <a href="/admin/return/process/{{ r.id }}/approve" class="btn btn-dark btn-sm me-1">Godkänn</a>
                                <a href="/admin/return/process/{{ r.id }}/reject" class="btn btn-outline-dark btn-sm">Avslå</a>
                                {% else %}<span class="text-muted small">Hanterad</span>{% endif %}
                            </td>
                        </tr>
                        {% endfor %}
                    </tbody>
                </table>
            </div>
            {% else %}<p class="text-muted mb-0">Inga returer.</p>{% endif %}
        </section>

        <!-- SECTION 5: RABATTKODER -->
        <section id="promos" class="admin-section card p-4 shadow-sm mb-5">
            <h3 class="mb-3">Hantera Rabattkoder & Kampanjbrickor (Rea / Black Friday)</h3>

            <h5 class="mt-2 mb-3 text-muted">1. Rabattkoder (Används i kassan)</h5>
            <form action="/admin/add_promo" method="POST" class="row g-3 mb-4">
                <div class="col-auto"><input type="text" class="form-control" name="code" required placeholder="Kod (t.ex. URBAN)"></div>
                <div class="col-auto"><input type="number" class="form-control" name="discount" required placeholder="Rabatt %"></div>
                <div class="col-auto"><button type="submit" class="btn btn-dark">Skapa Rabattkod</button></div>
            </form>
            <ul class="list-group mb-4">
                {% for promo in promo_codes %}
                <li class="list-group-item d-flex justify-content-between align-items-center">
                    <div><strong>{{ promo.code }}</strong> - <span class="badge bg-dark">-{{ promo.discount_percent }}%</span></div>
                    <a href="/admin/delete_promo/{{ promo.code }}" class="btn btn-danger btn-sm" onclick="return confirm('Ta bort rabattkod?')">Ta bort</a>
                </li>
                {% endfor %}
            </ul>

            <hr class="my-4">

            <h5 class="mb-3 text-muted">2. Lägg till eller ändra Kampanjbricka & Rea på en produkt</h5>
            <form action="/admin/assign_promo_badge" method="POST" class="row g-3 mb-4 bg-light p-3 rounded border">
                <div class="col-md-5">
                    <label class="form-label small fw-bold">Välj Produkt</label>
                    <select class="form-select" name="product_id" required>
                        {% for p in products %}
                            <option value="{{ p.id }}">{{ p.name }} ({% if p.promo_badge %}{{ p.promo_badge }}{% else %}Ingen promo{% endif %})</option>
                        {% endfor %}
                    </select>
                </div>
                <div class="col-md-3">
                    <label class="form-label small fw-bold">Kampanjbricka (t.ex. BLACK FRIDAY)</label>
                    <input type="text" class="form-control" name="promo_badge" placeholder="BLACK FRIDAY / SÄSONGSREA">
                </div>
                <div class="col-md-2">
                    <label class="form-label small fw-bold">Rea Pris (SEK)</label>
                    <input type="number" class="form-control" name="discount_price" placeholder="t.ex. 499">
                </div>
                <div class="col-md-2 d-flex align-items-end">
                    <button type="submit" class="btn btn-dark w-100">Spara på produkt</button>
                </div>
            </form>

            <hr class="my-4">

            <h5 class="mb-3 text-muted">3. Aktiva Kampanjbrickor på produkter</h5>
            <ul class="list-group">
                {% set ns = namespace(has_badges=false) %}
                {% for p in products %}
                    {% if p.promo_badge or p.discount_price %}
                        {% set ns.has_badges = true %}
                        <li class="list-group-item d-flex justify-content-between align-items-center">
                            <div>
                                <strong>{{ p.name }}</strong>
                                {% if p.promo_badge %}<span class="badge bg-secondary ms-2 fw-bold">{{ p.promo_badge }}</span>{% endif %}
                                {% if p.discount_price %}<span class="badge bg-dark ms-2">Rea: {{ p.discount_price }} SEK (Ord. {{ p.price }} SEK)</span>{% endif %}
                            </div>
                            <a href="/admin/clear_promo_badge/{{ p.id }}" class="btn btn-danger btn-sm" onclick="return confirm('Ta bort kampanj/rea för denna produkt?')">Ta bort promo & rea</a>
                        </li>
                    {% endif %}
                {% endfor %}
                {% if not ns.has_badges %}
                    <li class="list-group-item text-muted small">Inga aktiva kampanjbrickor eller reapriser just nu.</li>
                {% endif %}
            </ul>
        </section>

        <!-- SECTION 6: EVENT & BILJETTYPER -->
        <section id="events" class="admin-section card p-4 shadow-sm mb-5">
        
            <!-- FORMULAIRE INDÉPENDANT POUR LE MESSAGE D'ANNONCE "EN PRÉPARATION" -->
            <div class="mb-4 bg-warning bg-opacity-10 p-3 rounded border border-warning">
                <form action="/admin/update_announcement" method="POST" enctype="multipart/form-data">
                    <div class="d-flex justify-content-between align-items-center mb-3">
                        <h5 class="text-dark fw-bold mb-0">🚧 Globalt "Under förberedelse"-meddelande</h5>
                        <!-- Bouton pour supprimer/effacer l'annonce -->
                        <a href="/admin/delete_announcement" class="btn btn-outline-danger btn-sm fw-bold" onclick="return confirm('Vill du ta bort detta meddelande?')">🗑️ Radera meddelande</a>
                    </div>
                    
                    <div class="form-check mb-3">
                        <input class="form-check-input" type="checkbox" name="announcement_active" id="checkAnnouncement" {% if global_announcement and global_announcement.active %}checked{% endif %}>
                        <label class="form-check-label fw-bold text-dark" for="checkAnnouncement">
                            Aktivera meddelande för hemsidan
                        </label>
                    </div>
                    
                    <div class="mb-3">
                        <label class="form-label small fw-bold">Meddelande till användare</label>
                        <textarea class="form-control" name="announcement_text" rows="2" placeholder="t.ex. Line-up och hemlig lokal släpps om några dagar...">{{ global_announcement.text if global_announcement else '' }}</textarea>
                    </div>
            
                    <div class="row align-items-center mb-3">
                        <div class="col-md-9">
                            <label class="form-label small fw-bold">Bild för förberedelse-meddelandet (valfritt)</label>
                            <input type="file" class="form-control form-control-sm" name="announcement_file" accept="image/*">
                        </div>
                        <div class="col-md-3 text-end">
                            <button type="submit" class="btn btn-warning fw-bold text-dark w-100 mt-4">💾 Spara meddelande</button>
                        </div>
                    </div>
                </form>
            </div>
        
            <h3 class="mb-3">Publicera nytt Evenemang</h3>
            <form action="/admin/add_event" method="POST" enctype="multipart/form-data">
                <div class="row">
                    <div class="col-md-4 mb-3"><label class="form-label">Titel</label><input type="text" class="form-control" name="title" required></div>
                    <div class="col-md-3 mb-3"><label class="form-label">Datum</label><input type="date" class="form-control" name="date" required></div>
                    <div class="col-md-3 mb-3"><label class="form-label">Tid</label><input type="text" class="form-control" name="time" required value="23:00 - 05:00"></div>
                    <div class="col-md-2 mb-3"><label class="form-label fw-bold">Åldersgräns</label><input type="number" class="form-control" name="min_age" value="18" required></div>
                </div>
                
                <div class="row mb-3">
                    <div class="col-md-6"><label class="form-label">Plats</label><input type="text" class="form-control" name="location" required placeholder="t.ex. Stockholm Club Central"></div>
                    <div class="col-md-6"><label class="form-label">Baspris Standard (SEK)</label><input type="number" class="form-control" name="price" required value="250"></div>
                </div>
        
                <!-- SÉLECTION DES BILJETTYPES PAR CASES À COCHER (CHECKBOXES) -->
                <div class="mb-4 bg-light p-3 rounded border">
                    <label class="form-label fw-bold mb-2">🏷️ Välj biljettyper och zoner som ska aktiveras för detta event:</label>
                    
                    <div class="row g-3">
                        <div class="col-md-4">
                            <div class="p-3 border bg-white rounded shadow-sm">
                                <div class="form-check mb-2">
                                    <input class="form-check-input" type="checkbox" name="ticket_types" value="Early Bird" id="checkEarlyBird" checked>
                                    <label class="form-check-label fw-bold" for="checkEarlyBird">Early Bird</label>
                                </div>
                                <div class="mb-2"><label class="form-label small text-muted">Pris (SEK)</label><input type="number" class="form-control form-control-sm" name="price_early_bird" value="200"></div>
                                <div><label class="form-label small text-muted">Antal platser</label><input type="number" class="form-control form-control-sm" name="stock_early_bird" value="50"></div>
                            </div>
                        </div>
        
                        <div class="col-md-4">
                            <div class="p-3 border bg-white rounded shadow-sm">
                                <div class="form-check mb-2">
                                    <input class="form-check-input" type="checkbox" name="ticket_types" value="Standard" id="checkStandard" checked>
                                    <label class="form-check-label fw-bold" for="checkStandard">Standard</label>
                                </div>
                                <div class="mb-2"><label class="form-label small text-muted">Pris (SEK)</label><input type="number" class="form-control form-control-sm" name="price_standard" value="250"></div>
                                <div><label class="form-label small text-muted">Antal platser</label><input type="number" class="form-control form-control-sm" name="stock_standard" value="150"></div>
                            </div>
                        </div>
        
                        <div class="col-md-4">
                            <div class="p-3 border bg-white rounded shadow-sm">
                                <div class="form-check mb-2">
                                    <input class="form-check-input" type="checkbox" name="ticket_types" value="VIP / Fast Track" id="checkVip" checked>
                                    <label class="form-check-label fw-bold" for="checkVip">VIP / Fast Track</label>
                                </div>
                                <div class="mb-2"><label class="form-label small text-muted">Pris (SEK)</label><input type="number" class="form-control form-control-sm" name="price_vip" value="375"></div>
                                <div><label class="form-label small text-muted">Antal platser</label><input type="number" class="form-control form-control-sm" name="stock_vip" value="40"></div>
                            </div>
                        </div>
                    </div>
                </div>
        
                <div class="row mb-3">
                    <div class="col-md-6"><label class="form-label">📁 Bildfil</label><input type="file" class="form-control" name="image_file" accept="image/*"></div>
                    <div class="col-md-6"><label class="form-label">🔗 Bild-URL</label><input type="text" class="form-control" name="image_url"></div>
                </div>
                <div class="mb-3"><label class="form-label">Beskrivning</label><textarea class="form-control" name="desc" rows="2" placeholder="Kort beskrivning..."></textarea></div>
                <button type="submit" class="btn btn-dark fw-bold">🚀 Publicera Event & Zoner</button>
            </form>
        
            <hr class="my-4">
        
            <!-- LISTE DES ÉVÉNEMENTS EXISTANTS -->
            <h4 class="mb-3">Befintliga Evenemang</h4>
            <div class="table-scroll-container mb-3">
                <table class="table table-striped align-middle mb-0">
                    <thead>
                        <tr>
                            <th>Bild</th>
                            <th>Titel</th>
                            <th>Datum & Tid</th>
                            <th>Plats</th>
                            <th>Ålder</th>
                            <th>Åtgärd</th>
                        </tr>
                    </thead>
                    <tbody>
                        {% if events %}
                            {% for event in events %}
                            <tr>
                                <td><img src="{{ event.image }}" style="width: 45px; height: 45px; object-fit: cover; border-radius: 6px;"></td>
                                <td><strong>{{ event.title }}</strong></td>
                                <td><small>{{ event.date }} ({{ event.time }})</small></td>
                                <td><small>{{ event.location }}</small></td>
                                <td><span class="badge bg-secondary">{{ event.min_age if event.min_age else 18 }} år</span></td>
                                <td>
                                    <div class="d-flex gap-1">
                                        <button class="btn btn-outline-dark btn-sm" data-bs-toggle="modal" data-bs-target="#editEventModal{{ event.id }}">✏️ Ändra</button>
                                        <a href="/admin/delete_event/{{ event.id }}" class="btn btn-danger btn-sm" onclick="return confirm('Vill du ta bort detta event?')">🗑️ Ta bort</a>
                                    </div>
                                </td>
                            </tr>
                            {% endfor %}
                        {% else %}
                            <tr><td colspan="6" class="text-center text-muted py-3">Inga evenemang publicerade ännu.</td></tr>
                        {% endif %}
                    </tbody>
                </table>
            </div>
        
            <!-- MODAUX HORS DU TABLEAU BASÉS SUR event.id -->
            {% if events %}
                {% for event in events %}
                <div class="modal fade" id="editEventModal{{ event.id }}" tabindex="-1">
                  <div class="modal-dialog modal-lg"><div class="modal-content">
                    <form action="/admin/edit_event/{{ event.id }}" method="POST">
                        <div class="modal-header bg-dark text-white">
                            <h5 class="modal-title">Redigera Event: {{ event.title }}</h5>
                            <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal"></button>
                        </div>
                        <div class="modal-body">
                            <div class="row mb-3">
                                <div class="col-md-6"><label class="form-label small fw-bold">Titel</label><input type="text" class="form-control" name="title" value="{{ event.title }}" required></div>
                                <div class="col-md-3 mb-3"><label class="form-label small fw-bold">Datum</label><input type="date" class="form-control" name="date" value="{{ event.date }}" required></div>
                                <div class="col-md-3 mb-3"><label class="form-label small fw-bold">Tid</label><input type="text" class="form-control" name="time" value="{{ event.time }}" required></div>
                            </div>
                            <div class="row mb-3">
                                <div class="col-md-6"><label class="form-label small fw-bold">Plats</label><input type="text" class="form-control" name="location" value="{{ event.location }}" required></div>
                                <div class="col-md-6"><label class="form-label small fw-bold">Åldersgräns</label><input type="number" class="form-control" name="min_age" value="{{ event.min_age if event.min_age else 18 }}" required></div>
                            </div>
                            <div class="mb-3"><label class="form-label small fw-bold">Beskrivning</label><textarea class="form-control" name="desc" rows="2">{{ event.desc }}</textarea></div>
                        </div>
                        <div class="modal-footer">
                            <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Avbryt</button>
                            <button type="submit" class="btn btn-dark">Spara ändringar</button>
                        </div>
                    </form>
                  </div></div>
                </div>
                {% endfor %}
            {% endif %}
        </section>

        <!-- SECTION 7: PRODUKTER & BILJETTER -->
        <section id="products" class="admin-section mb-5">
            <div class="card p-4 shadow-sm mb-4">
                <h3 class="mb-3">Lägg till ny produkt / Biljett</h3>
                <form action="/admin/add_product" method="POST" enctype="multipart/form-data">
                    <div class="row mb-3">
                        <div class="col-md-4"><label class="form-label">Namn</label><input type="text" class="form-control" name="name" required placeholder="Produktnamn eller Biljettnamn"></div>
                        <div class="col-md-2"><label class="form-label">Ord. Pris (SEK)</label><input type="number" class="form-control" name="price" required placeholder="699"></div>
                        <div class="col-md-3"><label class="form-label">Typ / Kategori</label>
                            <select class="form-select" name="type">
                                {% for t in product_types %}<option value="{{ t.id }}">{{ t.name }}</option>{% endfor %}
                            </select>
                        </div>
                        <div class="col-md-3"><label class="form-label">Lagerantal (Stock)</label><input type="number" class="form-control" name="total_stock" value="50" required></div>
                    </div>
        
                    <div class="row mb-3">
                        <div class="col-md-4"><label class="form-label">Storlekar (Komma-separerade)</label><input type="text" class="form-control" name="sizes" placeholder="S, M, L, XL,..."></div>
                        <div class="col-md-4"><label class="form-label">Färger (Komma-separerade)</label><input type="text" class="form-control" name="colors" placeholder="Svart, Vit"></div>
                        <div class="col-md-4"><label class="form-label">📁 Ladda upp bildfil</label><input type="file" class="form-control" name="image_file" accept="image/*"></div>
                    </div>
        
                    <div class="row mb-3">
                        <div class="col-md-12"><label class="form-label">🔗 Eller Bild-URL</label><input type="text" class="form-control" name="image_url" placeholder="https://..."></div>
                    </div>
        
                    <div class="mb-3"><label class="form-label">Beskrivning</label><textarea class="form-control" name="desc" rows="2" placeholder="Kort beskrivning..."></textarea></div>
                    <button type="submit" class="btn btn-dark">Lägg till produkt / Biljett</button>
                </form>
            </div>
        
            <div class="card p-4 shadow-sm">
                <h3 class="mb-3">Befintliga Produkter</h3>
                <div class="table-scroll-container">
                    <table class="table table-striped align-middle mb-0">
                        <thead><tr><th>ID</th><th>Bild</th><th>Typ</th><th>Namn</th><th>Pris / Rea</th><th>Kampanj</th><th>Stock</th><th>Sålda</th><th>Åtgärd</th></tr></thead>
                        <tbody>
                            {% for p in products %}
                            <tr>
                                <td>{{ p.id }}</td>
                                <td><img src="{{ p.image }}" style="width: 40px; height: 40px; object-fit: cover; border-radius: 4px;"></td>
                                <td><span class="badge bg-secondary">{{ p.type }}</span></td>
                                <td><strong>{{ p.name }}</strong></td>
                                <td>
                                    {% if p.discount_price %}
                                        <span class="text-decoration-line-through text-muted me-1">{{ p.price }} SEK</span>
                                        <strong class="text-dark">{{ p.discount_price }} SEK</strong>
                                    {% else %}
                                        {{ p.price }} SEK
                                    {% endif %}
                                </td>
                                <td>
                                    {% if p.promo_badge %}<span class="badge bg-dark">{{ p.promo_badge }}</span>{% else %}<span class="text-muted small">-</span>{% endif %}
                                </td>
                                <td>{{ p.total_stock }}</td>
                                <td>{{ p.sold }}</td>
                                <td><a href="/admin/delete_product/{{ p.id }}" class="btn btn-danger btn-sm" onclick="return confirm('Ta bort?')">Ta bort</a></td>
                            </tr>
                            {% endfor %}
                        </tbody>
                    </table>
                </div>
            </div>
        </section>

        <!-- SECTION 8: GESTION DES INVITÉS & VIP -->
        <section id="guests-section" class="admin-section card p-4 shadow-sm mb-5 border-dark rounded-4">
            <div class="d-flex justify-content-between align-items-center mb-4 flex-wrap gap-2">
                <div>
                    <h3 class="fw-bold mb-1">🎟️ Hantering av Inbjudna Gäster & VIP</h3>
                    <p class="text-muted small mb-0">Utfärda gratis VIP-biljetter, skicka inbjudningar och följ närvaron i realtid (med 48h arkiv).</p>
                </div>
                <div class="d-flex gap-2">
                    <a href="/admin?archive=true#guests-section" class="btn btn-outline-dark btn-sm fw-bold">📂 Visa Alla Arkiv</a>
                    <a href="/admin#guests-section" class="btn btn-dark btn-sm fw-bold">⏱️ Senaste 48h</a>
                </div>
            </div>

            <div class="bg-light p-3 rounded-3 mb-4 border">
                <h5 class="fw-bold fs-6 mb-3">➕ Utfärda ny VIP-inbjudan</h5>
                <form action="/admin/add_guest" method="POST">
                    <div class="row g-3">
                        <div class="col-md-4">
                            <label class="form-label small fw-bold">Fullständiga namn</label>
                            <input type="text" class="form-control form-control-sm" name="guest_name" placeholder="Anna Svensson" required>
                        </div>
                        <div class="col-md-4">
                            <label class="form-label small fw-bold">E-postadress</label>
                            <input type="email" class="form-control form-control-sm" name="guest_email" placeholder="anna@example.com" required>
                        </div>
                        <div class="col-md-4">
                            <label class="form-label small fw-bold">Välj Evenemang (Inbjudan)</label>
                            <div class="border rounded p-2 bg-white" style="max-height: 100px; overflow-y: auto;">
                                {% for event in events %}
                                <div class="form-check form-check-inline d-block">
                                    <input class="form-check-input" type="checkbox" name="guest_events" value="{{ event.title }}" id="evt_{{ loop.index }}">
                                    <label class="form-check-label small" for="evt_{{ loop.index }}">{{ event.title }}</label>
                                </div>
                                {% endfor %}
                            </div>
                        </div>
                    </div>
                    <div class="text-end mt-3">
                        <button type="submit" class="btn btn-dark btn-sm px-4 fw-bold">Spara & Lägg till i listan</button>
                    </div>
                </form>
            </div>

            <div class="table-responsive">
                <table class="table table-hover align-middle">
                    <thead class="table-dark" style="font-size: 0.85rem;">
                        <tr>
                            <th>Namn / E-post</th>
                            <th>Inbjudna Evenemang</th>
                            <th>Inbjudansstatus</th>
                            <th>Närvaro (Scanner)</th>
                            <th class="text-end">Åtgärder</th>
                        </tr>
                    </thead>
                    <tbody style="font-size: 0.9rem;">
                        {% if guests %}
                            {% for guest in guests %}
                            <tr>
                                <td>
                                    <strong class="d-block">{{ guest.name }}</strong>
                                    <span class="text-muted small">{{ guest.email }}</span>
                                </td>
                                <td>
                                    {% if guest.events_invited %}
                                        {% for evt in guest.events_invited %}
                                            <span class="badge bg-secondary mb-1">{{ evt }}</span>
                                        {% endfor %}
                                    {% else %}
                                        <span class="text-muted small">Inga evenemang valda</span>
                                    {% endif %}
                                </td>
                                <td>
                                    {% if guest.invitation_sent %}
                                        <span class="badge bg-success">✉️ Skickad</span>
                                    {% else %}
                                        <span class="badge bg-warning text-dark">⏳ Ej skickad</span>
                                    {% endif %}
                                </td>
                                <td>
                                    {% if guest.checked_in %}
                                        <span class="badge bg-success px-2 py-1">🟢 På plats ({{ guest.checkin_time }})</span>
                                    {% else %}
                                        <span class="badge bg-secondary px-2 py-1">🔴 Ej anländ</span>
                                    {% endif %}
                                </td>
                                <td class="text-end">
                                    <div class="d-flex justify-content-end gap-1">
                                        {% if not guest.invitation_sent %}
                                        <a href="/admin/send_invitation/{{ guest.id }}" class="btn btn-dark btn-sm">Skicka</a>
                                        {% endif %}
                                        <a href="/admin/archive_guest/{{ guest.id }}" class="btn btn-outline-secondary btn-sm">
                                            {% if guest.archived %}Återställ{% else %}Arkivera{% endif %}
                                        </a>
                                    </div>
                                </td>
                            </tr>
                            {% endfor %}
                        {% else %}
                            <tr><td colspan="5" class="text-center text-muted py-4">Inga gäster registrerade ännu.</td></tr>
                        {% endif %}
                    </tbody>
                </table>
            </div>
        </section>

        <!-- SECTION 9: ÖVERFÖRINGSBEGÄRAN -->
        <section id="transfers-section" class="admin-section card p-4 shadow-sm mb-5 border-dark">
            <div class="d-flex justify-content-between align-items-center mb-3">
                <div>
                    <h3 class="mb-0">🔄 Överföringsbegäran av biljetter (Säkerhetskontroll)</h3>
                    <p class="text-muted small mb-0">Granska och godkänn biljettoverföringar för att förhindra andrahandsförsäljning och bedrägerier.</p>
                </div>
            </div>

            <div class="table-responsive">
                <table class="table table-sm table-striped align-middle">
                    <thead class="table-dark">
                        <tr>
                            <th>Begäran ID</th>
                            <th>Datum</th>
                            <th>Avsändare (Från)</th>
                            <th>Mottagare (Till)</th>
                            <th>Biljett</th>
                            <th>Status</th>
                            <th class="text-end">Åtgärd</th>
                        </tr>
                    </thead>
                    <tbody>
                        {% if pending_transfers %}
                            {% for req in pending_transfers %}
                            <tr>
                                <td><code>#{{ req.id }}</code></td>
                                <td><small>{{ req.request_date }}</small></td>
                                <td><strong>{{ req.sender_name }}</strong><br><small class="text-muted">{{ req.sender_email }}</small></td>
                                <td><span class="badge bg-light text-dark border">{{ req.recipient_email }}</span></td>
                                <td><strong>{{ req.ticket_name }}</strong></td>
                                <td>
                                    {% if req.status == 'PENDING' %}
                                        <span class="badge bg-warning text-dark">⏳ Väntar på godkännande</span>
                                    {% elif req.status == 'APPROVED' %}
                                        <span class="badge bg-success">✅ Godkänd</span>
                                    {% else %}
                                        <span class="badge bg-danger">❌ Avslagen</span>
                                    {% endif %}
                                </td>
                                <td class="text-end">
                                    {% if req.status == 'PENDING' %}
                                    <div class="d-flex gap-1 justify-content-end">
                                        <form action="/admin/process_transfer/{{ req.id }}/approve" method="POST">
                                            <button type="submit" class="btn btn-success btn-sm fw-bold">Godkänn ✅</button>
                                        </form>
                                        <form action="/admin/process_transfer/{{ req.id }}/reject" method="POST">
                                            <button type="submit" class="btn btn-outline-danger btn-sm fw-bold">Avslå ❌</button>
                                        </form>
                                    </div>
                                    {% else %}
                                        <small class="text-muted">Hanterad</small>
                                    {% endif %}
                                </td>
                            </tr>
                            {% endfor %}
                        {% else %}
                            <tr>
                                <td colspan="7" class="text-center text-muted py-3">Inga överföringsbegäranden att granska för tillfället.</td>
                            </tr>
                        {% endif %}
                    </tbody>
                </table>
            </div>
        </section>

        <!-- SECTION 10: KUNDHANTERING -->
        <section id="customers-section" class="admin-section card p-4 shadow-sm mb-5">
            <div class="d-flex justify-content-between align-items-center mb-3">
                <h3 class="mb-0">👥 Kundhantering & Inloggningsstatistik</h3>
                <span class="badge bg-dark fs-6">{{ customers|length }} Registrerade Kunder</span>
            </div>

            {% set ns = namespace(google=0, apple=0, facebook=0, instagram=0, tiktok=0, email=0) %}
            {% for c in customers %}
                {% set provider = c.provider if c.provider else 'email' %}
                {% if provider == 'google' %}{% set ns.google = ns.google + 1 %}
                {% elif provider == 'apple' %}{% set ns.apple = ns.apple + 1 %}
                {% elif provider == 'facebook' %}{% set ns.facebook = ns.facebook + 1 %}
                {% elif provider == 'instagram' %}{% set ns.instagram = ns.instagram + 1 %}
                {% elif provider == 'tiktok' %}{% set ns.tiktok = ns.tiktok + 1 %}
                {% else %}{% set ns.email = ns.email + 1 %}
                {% endif %}
            {% endfor %}

            <div class="row my-3">
                <div class="col-md-8">
                    <div class="row g-2">
                        <div class="col-6 col-md-4">
                            <div class="p-3 border rounded text-center bg-light">
                                <small class="text-muted d-block">Google</small>
                                <strong class="fs-4 text-dark">{{ ns.google }}</strong>
                            </div>
                        </div>
                        <div class="col-6 col-md-4">
                            <div class="p-3 border rounded text-center bg-light">
                                <small class="text-muted d-block">Apple</small>
                                <strong class="fs-4 text-dark">{{ ns.apple }}</strong>
                            </div>
                        </div>
                        <div class="col-6 col-md-4">
                            <div class="p-3 border rounded text-center bg-light">
                                <small class="text-muted d-block">Facebook</small>
                                <strong class="fs-4 text-primary">{{ ns.facebook }}</strong>
                            </div>
                        </div>
                        <div class="col-6 col-md-4">
                            <div class="p-3 border rounded text-center bg-light">
                                <small class="text-muted d-block">Instagram</small>
                                <strong class="fs-4 text-dark">{{ ns.instagram }}</strong>
                            </div>
                        </div>
                        <div class="col-6 col-md-4">
                            <div class="p-3 border rounded text-center bg-light">
                                <small class="text-muted d-block">TikTok</small>
                                <strong class="fs-4 text-dark">{{ ns.tiktok }}</strong>
                            </div>
                        </div>
                        <div class="col-6 col-md-4">
                            <div class="p-3 border rounded text-center bg-light">
                                <small class="text-muted d-block">E-post</small>
                                <strong class="fs-4 text-secondary">{{ ns.email }}</strong>
                            </div>
                        </div>
                    </div>
                </div>

                <div class="col-md-4 d-flex align-items-center justify-content-center">
                    <div style="width: 100%; max-width: 220px;">
                        <canvas id="loginProvidersChart"></canvas>
                    </div>
                </div>
            </div>

            <hr class="my-4">

            <div class="table-scroll-container">
                <table class="table table-striped align-middle mb-0">
                    <thead>
                        <tr>
                            <th>ID</th>
                            <th>Namn</th>
                            <th>E-post</th>
                            <th>Inloggningsmetod</th>
                            <th>Telefon</th>
                            <th>Ort</th>
                            <th>Orderantal</th>
                            <th>Åtgärd</th>
                        </tr>
                    </thead>
                    <tbody>
                        {% for c in customers %}
                        <tr>
                            <td><strong>#{{ c.id }}</strong></td>
                            <td><strong>{{ c.name }}</strong></td>
                            <td>{{ c.email }}</td>
                            <td>
                                {% set provider = c.provider if c.provider else 'email' %}
                                {% if provider == 'google' %}
                                    <span class="badge bg-danger text-white">Google</span>
                                {% elif provider == 'apple' %}
                                    <span class="badge bg-dark text-white">Apple</span>
                                {% elif provider == 'facebook' %}
                                    <span class="badge bg-primary text-white">Facebook</span>
                                {% elif provider == 'instagram' %}
                                    <span class="badge bg-secondary text-white">Instagram</span>
                                {% elif provider == 'tiktok' %}
                                    <span class="badge bg-dark text-white">TikTok</span>
                                {% else %}
                                    <span class="badge bg-secondary text-white">E-post & Lösenord</span>
                                {% endif %}
                            </td>
                            <td><small>{{ c.phone if c.phone else '-' }}</small></td>
                            <td><small>{{ c.city if c.city else '-' }}</small></td>
                            <td><span class="badge bg-dark">{{ c.total_orders if c.total_orders else 0 }} st</span></td>
                            <td>
                                <button class="btn btn-outline-dark btn-sm" data-bs-toggle="modal" data-bs-target="#editCustomerModal{{ c.id }}">✏️ Redigera</button>
                            </td>
                        </tr>

                        <div class="modal fade" id="editCustomerModal{{ c.id }}" tabindex="-1">
                            <div class="modal-dialog modal-lg">
                                <div class="modal-content">
                                    <form action="/admin/customer/update/{{ c.id }}" method="POST">
                                        <div class="modal-header bg-dark text-white">
                                            <h5 class="modal-title">Redigera Kund #{{ c.id }} - {{ c.name }}</h5>
                                            <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal"></button>
                                        </div>
                                        <div class="modal-body">
                                            <div class="row mb-3">
                                                <div class="col-md-6">
                                                    <label class="form-label small fw-bold">Förnamn</label>
                                                    <input type="text" class="form-control" name="first_name" value="{{ c.first_name if c.first_name else c.name.split()[0] }}" required>
                                                </div>
                                                <div class="col-md-6">
                                                    <label class="form-label small fw-bold">Efternamn</label>
                                                    <input type="text" class="form-control" name="last_name" value="{{ c.last_name if c.last_name else ' '.join(c.name.split()[1:]) }}">
                                                </div>
                                            </div>
                                            <div class="row mb-3">
                                                <div class="col-md-6">
                                                    <label class="form-label small fw-bold">E-postadress</label>
                                                    <input type="email" class="form-control" name="email" value="{{ c.email }}" required>
                                                </div>
                                                <div class="col-md-6">
                                                    <label class="form-label small fw-bold">Telefonnummer</label>
                                                    <input type="text" class="form-control" name="phone" value="{{ c.phone if c.phone else '' }}">
                                                </div>
                                            </div>
                                            <div class="mb-3">
                                                <label class="form-label small fw-bold">Gatuadress</label>
                                                <input type="text" class="form-control" name="address" value="{{ c.address if c.address else '' }}">
                                            </div>
                                            <div class="row mb-3">
                                                <div class="col-md-6">
                                                    <label class="form-label small fw-bold">Postnummer</label>
                                                    <input type="text" class="form-control" name="postal_code" value="{{ c.postal_code if c.postal_code else '' }}">
                                                </div>
                                                <div class="col-md-6">
                                                    <label class="form-label small fw-bold">Stad</label>
                                                    <input type="text" class="form-control" name="city" value="{{ c.city if c.city else '' }}">
                                                </div>
                                            </div>
                                        </div>
                                        <div class="modal-footer">
                                            <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Avbryt</button>
                                            <button type="submit" class="btn btn-dark">Spara ändringar</button>
                                        </div>
                                    </form>
                                </div>
                            </div>
                        </div>
                        {% endfor %}
                    </tbody>
                </table>
            </div>
        </section>

        <!-- SECTION 11: TICKET SCANNER -->
        <section id="scanner-section" class="admin-section card p-4 shadow-sm mb-5 border-dark">
            <div class="d-flex justify-content-between align-items-center mb-3 flex-wrap gap-2">
                <div>
                    <h3 class="mb-0">📱 URBAN NATION - Ticket Scanner</h3>
                    <p class="text-muted small mb-0">Skapa tidsbegränsade länkar (max 6h) för ordningsvakter och personal i entrén.</p>
                </div>
                <form action="/admin/generate_scanner_link" method="POST">
                    <button type="submit" class="btn btn-dark fw-bold">🔗 Generera ny Scanner-länk (6h)</button>
                </form>
            </div>

            <div class="table-responsive mb-4">
                <table class="table table-sm table-striped align-middle">
                    <thead>
                        <tr>
                            <th>Token ID</th>
                            <th>Lösenord</th>
                            <th>Giltig till</th>
                            <th>Direktlänk för personal</th>
                        </tr>
                    </thead>
                    <tbody>
                        {% if scanner_tokens %}
                            {% for token, data in scanner_tokens.items() %}
                            <tr>
                                <td><code>{{ token }}</code></td>
                                <td><span class="badge bg-secondary fs-6">{{ data.password }}</span></td>
                                <td><small class="fw-bold">{{ data.expires_formatted }}</small></td>
                                <td>
                                    <a href="/scanner/{{ token }}" target="_blank" class="btn btn-warning btn-sm fw-bold">
                                        🔗 Öppna Skanner-sida ↗
                                    </a>
                                </td>
                            </tr>
                            {% endfor %}
                        {% else %}
                            <tr>
                                <td colspan="4" class="text-center text-muted py-3">
                                    Inga aktiva scanner-länkar för tillfället. Klicka på knappen ovan för att skapa en.
                                </td>
                            </tr>
                        {% endif %}
                    </tbody>
                </table>
            </div>

            <hr class="my-4">

            <div class="row justify-content-center">
                <div class="col-md-6 text-center">
                    <h5 class="fw-bold mb-2">Live Biljettskanner (Admin-vy)</h5>
                    <p class="text-muted small">Verifiera besökarens ID-kort och ålder innan godkännande.</p>

                    <div class="d-flex justify-content-center gap-2 mb-3">
                        <button id="toggleCameraBtn" class="btn btn-dark btn-sm" onclick="toggleCamera()">📷 Stäng av kamera</button>
                        <button id="toggleFlashBtn" class="btn btn-outline-dark btn-sm" onclick="toggleFlash()" disabled>⚡ Flash (Ficklampa)</button>
                    </div>

                    <div id="scanner-container" class="border rounded bg-black mb-3 position-relative shadow-sm overflow-hidden" style="height: 280px;">
                        <video id="preview" style="width: 100%; height: 100%; object-fit: cover;"></video>
                    </div>

                    <div id="scan-result" class="alert d-none text-start"></div>
                </div>
            </div>
        </section>

        <!-- SECTION 12: REAL-TIME CHECK-IN -->
        <section id="checkin-report-section" class="admin-section card p-4 shadow-sm mb-5 border-dark">
            <div class="d-flex justify-content-between align-items-center mb-3 flex-wrap gap-2">
                <div>
                    <h3 class="mb-0">📊 Real-Time Check-in</h3>
                    <p class="text-muted small mb-0">Övervaka antal insläppta besökare och tidpunkter för köbildning i entrén.</p>
                    <small id="adminLocalTime" class="text-primary fw-bold d-block mt-1">🕒 Datum & Tid: Laddar...</small>
                </div>

                <div class="d-flex align-items-center gap-3 flex-wrap">
                    <div>
                        <label class="form-label small fw-bold mb-1 d-block">Välj Evenemang</label>
                        {% set grand_total_tickets = namespace(count=0) %}
                        {% for e in events %}{% set grand_total_tickets.count = grand_total_tickets.count + (e.total_tickets if e.total_tickets else 100) %}{% endfor %}

                        <select id="eventFilterSelect" class="form-select form-select-sm" onchange="fetchCheckinData()">
                            <option value="ALL" data-tickets="{{ grand_total_tickets.count }}">Alla Evenemang (Totalt)</option>
                            {% for e in events %}
                                <option value="{{ e.title }}" data-tickets="{{ e.total_tickets if e.total_tickets else 100 }}">
                                    {{ e.title }} ({{ e.date }}) - {{ e.total_tickets if e.total_tickets else 100 }} platser
                                </option>
                            {% endfor %}
                        </select>
                    </div>

                    <div class="badge bg-white border text-dark fs-6 px-3 py-2 mt-3 shadow-sm">
                        Insläppta: <strong id="checkedInDisplay" class="text-success fs-5">0</strong> / <span id="totalTicketsDisplay" class="fs-5">{{ grand_total_tickets.count }}</span> biljetter (<span id="percentDisplay" class="text-primary fw-bold">0.0%</span>)
                    </div>
                </div>
            </div>

            <div class="mb-4">
                <div class="progress" style="height: 16px;">
                    <div id="checkinProgressBar" class="progress-bar bg-success progress-bar-striped progress-bar-animated" style="width: 0%;"></div>
                </div>
            </div>

            <div class="row">
                <div class="col-md-7 mb-3">
                    <div class="card p-3 bg-light border">
                        <h5 class="fs-6 fw-bold mb-3">📈 Antal insläpp per timme (15:00 - 07:00)</h5>
                        <canvas id="checkinChart" height="180"></canvas>
                    </div>
                </div>

                <div class="col-md-5 mb-3">
                    <div class="card p-3 bg-light border" style="max-height: 280px; overflow-y: auto;">
                        <h5 class="fs-6 fw-bold mb-3">⏱️ Historik över senaste skanningar</h5>
                        <ul id="scanHistoryList" class="list-group list-group-flush small">
                            <li class="list-group-item bg-transparent text-center text-muted py-4">Inga insläpp registrerade ännu.</li>
                        </ul>
                    </div>
                </div>
            </div>
        </section>

        <!-- SECTION 13: AKTIONSLOGG -->
        <section id="logs" class="admin-section mb-5">
            <h3 class="mb-3">Aktionslogg</h3>
            <div class="card p-3 shadow-sm bg-white">
                <div class="table-scroll-container">
                    <table class="table table-striped mb-0 align-middle">
                        <thead><tr><th>Tidpunkt</th><th>Åtgärd</th><th>Detaljer</th></tr></thead>
                        <tbody>
                            {% for log in logs %}
                            <tr>
                                <td><code>{{ log.timestamp }}</code></td>
                                <td><span class="badge bg-dark">{{ log.action }}</span></td>
                                <td>{{ log.details }}</td>
                            </tr>
                            {% endfor %}
                        </tbody>
                    </table>
                </div>
            </div>
        </section>

    </div>

    <!-- MODAL STATS -->
    <div class="modal fade" id="editStatsModal" tabindex="-1">
      <div class="modal-dialog"><div class="modal-content">
        <form action="/admin/update_stats" method="POST">
            <div class="modal-header"><h5 class="modal-title">Ändra statistik</h5><button type="button" class="btn-close" data-bs-dismiss="modal"></button></div>
            <div class="modal-body">
                <div class="mb-3"><label class="form-label">Produkt</label>
                    <select class="form-select" name="product_id">
                        {% for p in products %}<option value="{{ p.id }}">{{ p.name }} ({{ p.sold }} sålda)</option>{% endfor %}
                    </select>
                </div>
                <div class="mb-3"><label class="form-label">Lägg till sålda</label><input type="number" class="form-control" name="extra_sold" value="5" required></div>
            </div>
            <div class="modal-footer"><button type="submit" class="btn btn-dark">Uppdatera</button></div>
        </form>
      </div></div>
    </div>

    <script src="https://unpkg.com/@zxing/library@latest"></script>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <script>
        function openNav() {
            document.getElementById("adminSidebar").style.width = "280px";
            document.getElementById("sidebarOverlay").classList.add("active");
        }
    
        function closeNav() {
            document.getElementById("adminSidebar").style.width = "0";
            document.getElementById("sidebarOverlay").classList.remove("active");
        }
    
        function showSection(sectionId) {
            const sections = document.querySelectorAll('.admin-section');
            sections.forEach(sec => sec.classList.remove('active-section'));
    
            const target = document.getElementById(sectionId);
            if (target) {
                target.classList.add('active-section');
            }
    
            const links = document.querySelectorAll('.admin-sidebar a');
            links.forEach(l => l.classList.remove('active'));
            if (event && event.currentTarget) {
                event.currentTarget.classList.add('active');
            }
    
            closeNav();
        }
    
        // --- GESTION DES ARCHIVES & OUVERTURE AUTOMATIQUE DE LA SECTION INVITÉS ---
        function loadGuestsArchive(showAll) {
            // Redirige vers la route avec le paramètre d'archive tout en forçant l'ancrage sur la section
            window.location.href = "/admin?archive=" + showAll + "#guests-section";
        }
    
        window.addEventListener('DOMContentLoaded', (event) => {
            if (window.location.hash === '#guests-section') {
                showSection('guests-section');
            } else if (window.location.hash === '#live-section') {
                showSection('live-section');
            }
        });
        // -------------------------------------------------------------------------
    
        // --- ANALYTICS LIVE STREAMING EN TEMPS RÉEL ---
        function fetchLiveAnalytics() {
            fetch('/api/get_live_analytics')
                .then(res => res.json())
                .then(data => {
                    if (document.getElementById('statYoutube')) document.getElementById('statYoutube').innerText = data.youtube || 0;
                    if (document.getElementById('statFacebook')) document.getElementById('statFacebook').innerText = data.facebook || 0;
                    if (document.getElementById('statTiktok')) document.getElementById('statTiktok').innerText = data.tiktok || 0;
                    if (document.getElementById('statInstagram')) document.getElementById('statInstagram').innerText = data.instagram || 0;
                })
                .catch(err => console.error("Kunde inte hämta live-statistik:", err));
        }
    
        // Lancer au chargement et rafraîchir automatiquement toutes les 10 secondes
        fetchLiveAnalytics();
        setInterval(fetchLiveAnalytics, 10000);
        // ----------------------------------------------
    
        function updateAdminClock() {
            const now = new Date();
            const timeZone = Intl.DateTimeFormat().resolvedOptions().timeZone;
            const options = { 
                weekday: 'long', 
                year: 'numeric', 
                month: 'long', 
                day: 'numeric', 
                hour: '2-digit', 
                minute: '2-digit', 
                second: '2-digit' 
            };
            const formattedDate = now.toLocaleDateString('sv-SE', options);
            const clockElem = document.getElementById('adminLocalTime');
            if (clockElem) {
                clockElem.innerHTML = `🕒 <strong>Lokal Tid (${timeZone}):</strong> ${formattedDate}`;
            }
        }
        setInterval(updateAdminClock, 1000);
        updateAdminClock();
    
        // --- GRAPHIQUE DYNAMIQUE DES PRODUITS (BARCHART) ---
        document.addEventListener("DOMContentLoaded", function () {
            // Récupération dynamique des données produits transmises par Flask
            const productLabels = {{ products | map(attribute='name') | list | tojson }};
            const productStocks = {{ products | map(attribute='total_stock') | list | tojson }};
            const productSold = {{ products | map(attribute='sold') | list | tojson }};
    
            // Fonction pour générer des couleurs uniques et automatiques pour chaque produit
            function generateColors(count) {
                let bgColors = [];
                for (let i = 0; i < count; i++) {
                    let hue = (i * 137.5) % 360; // Distribution harmonieuse des couleurs
                    bgColors.push(`hsl(${hue}, 70%, 55%)`);
                }
                return bgColors;
            }
    
            const dynamicColors = generateColors(productLabels.length);
    
            // 1. Graphique en barres (Lagersituation: Inlagda vs Sålda)
            const ctxBar = document.getElementById('barChart').getContext('2d');
            new Chart(ctxBar, {
                type: 'bar',
                data: {
                    labels: productLabels,
                    datasets: [
                        {
                            label: 'Totalt Lager (Inlagda)',
                            data: productStocks,
                            backgroundColor: '#212529', // Noir/Dark standard Urban Nation
                            borderRadius: 4
                        },
                        {
                            label: 'Sålda',
                            data: productSold,
                            backgroundColor: dynamicColors, // Couleurs propres et automatiques par produit
                            borderRadius: 4
                        }
                    ]
                },
                options: {
                    responsive: true,
                    scales: {
                        y: { beginAtZero: true }
                    }
                }
            });
        });
        // ----------------------------------------------------
    
        const ctxPie = document.getElementById('pieChart').getContext('2d');
        new Chart(ctxPie, {
            type: 'pie',
            data: {
                labels: [{% for p in products %}"{{ p.name }}",{% endfor %}],
                datasets: [{
                    data: [{% for p in products %}{{ p.sold * (p.discount_price if p.discount_price else p.price) }},{% endfor %}],
                    backgroundColor: ['#0d6efd', '#198754', '#ffc107', '#dc3545', '#6f42c1', '#0dcaf0']
                }]
            },
            options: { responsive: true }
        });
    
        const ctxLogin = document.getElementById('loginProvidersChart').getContext('2d');
        new Chart(ctxLogin, {
            type: 'doughnut',
            data: {
                labels: ['Google', 'Apple', 'Facebook', 'Instagram', 'TikTok', 'E-post'],
                datasets: [{
                    data: [{{ ns.google }}, {{ ns.apple }}, {{ ns.facebook }}, {{ ns.instagram }}, {{ ns.tiktok }}, {{ ns.email }}],
                    backgroundColor: ['#dc3545', '#000000', '#0d6efd', '#6c757d', '#111111', '#adb5bd']
                }]
            },
            options: {
                responsive: true,
                plugins: {
                    legend: { position: 'bottom' }
                }
            }
        });
    
        const checkinHours = ['15:00', '16:00', '17:00', '18:00', '19:00', '20:00', '21:00', '22:00', '23:00', '00:00', '01:00', '02:00', '03:00', '04:00', '05:00', '06:00', '07:00'];
        const ctxCheckin = document.getElementById('checkinChart').getContext('2d');
    
        let checkinChartInstance = new Chart(ctxCheckin, {
            type: 'bar',
            data: {
                labels: checkinHours,
                datasets: [{
                    label: 'Insläppta besökare',
                    data: [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
                    backgroundColor: '#198754',
                    borderRadius: 4
                }]
            },
            options: {
                responsive: true,
                plugins: { legend: { display: false } },
                scales: { y: { beginAtZero: true, ticks: { precision: 0 } } }
            }
        });
    
        function fetchCheckinData() {
            const selectElem = document.getElementById('eventFilterSelect');
            if (!selectElem) return;
            const selectedEvent = selectElem.value;
            const selectedOption = selectElem.options[selectElem.selectedIndex];
            const eventTicketsQuota = parseInt(selectedOption.getAttribute('data-tickets')) || 100;
    
            fetch(`/api/get_checkin_stats?event=${encodeURIComponent(selectedEvent)}`)
                .then(res => {
                    if (!res.ok) throw new Error("Erreur serveur " + res.status);
                    return res.json();
                })
                .then(data => {
                    const checkedIn = data.checked_in;
                    const percent = eventTicketsQuota > 0 ? ((checkedIn / eventTicketsQuota) * 100).toFixed(1) : 0;
    
                    document.getElementById('checkedInDisplay').innerText = checkedIn;
                    document.getElementById('totalTicketsDisplay').innerText = eventTicketsQuota;
                    document.getElementById('percentDisplay').innerText = percent + '%';
                    document.getElementById('checkinProgressBar').style.width = percent + '%';
    
                    checkinChartInstance.data.datasets[0].data = data.hourly_counts;
                    checkinChartInstance.update();
    
                    const historyList = document.getElementById('scanHistoryList');
                    if (data.history.length === 0) {
                        historyList.innerHTML = '<li class="list-group-item bg-transparent text-center text-muted py-4">Inga insläpp registrerade ännu.</li>';
                    } else {
                        historyList.innerHTML = data.history.map(item => `
                            <li class="list-group-item bg-transparent d-flex justify-content-between align-items-center py-2">
                                <div>
                                    <span class="fw-bold">🎫 ${item.category}</span>
                                    <small class="text-muted d-block">${item.timestamp}</small>
                                </div>
                                <span class="badge bg-success">Insläppt</span>
                            </li>
                        `).join('');
                    }
                })
                .catch(err => console.error("Erreur lors de l'actualisation du check-in :", err));
        }
    
        fetchCheckinData();
        setInterval(fetchCheckinData, 10000);
    
        function exportFilteredCSV() {
            const yearSelect = document.querySelector('select[name="year"]');
            const monthSelect = document.querySelector('select[name="month"]');
            const year = yearSelect ? yearSelect.value : '';
            const month = monthSelect ? monthSelect.value : '';
            window.location.href = `/admin/export_sales_csv?year=${year}&month=${month}`;
        }
    
        let codeReader = null;
        let isCameraActive = true;
        let flashOn = false;
    
        window.addEventListener('load', function () {
            startScanner();
        });
    
        function startScanner() {
            codeReader = new ZXing.BrowserQRCodeReader();
            codeReader.decodeFromInputVideoDevice(undefined, 'preview').then((result) => {
                fetch('/api/scan_ticket', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({ ticket_code: result.text })
                })
                .then(res => res.json())
                .then(data => {
                    const resDiv = document.getElementById('scan-result');
                    resDiv.classList.remove('d-none', 'alert-success', 'alert-danger', 'alert-warning');
    
                    if (data.status === 'VALID') {
                        resDiv.classList.add('alert-success');
                        resDiv.innerHTML = `
                            <h5 class="fw-bold mb-1">✅ GILTIG BILJETT</h5>
                            <p class="mb-1"><strong>Kategori:</strong> ${data.category}</p>
                            <p class="mb-1"><strong>Gäst:</strong> ${data.guest_name}</p>
                            <p class="mb-0"><strong>Minimiålder:</strong> ${data.min_age} år (Kontrollera ID-kort!)</p>
                        `;
                        fetchCheckinData();
                    } else if (data.status === 'ALREADY_USED') {
                        resDiv.classList.add('alert-warning');
                        resDiv.innerHTML = `
                            <h5 class="fw-bold mb-1">⚠️ REDAN ANVÄND BILJETT</h5>
                            <p class="mb-0">${data.message}</p>
                        `;
                    } else {
                        resDiv.classList.add('alert-danger');
                        resDiv.innerHTML = `
                            <h5 class="fw-bold mb-1">❌ OGILTIG BILJETT</h5>
                            <p class="mb-0">${data.message}</p>
                        `;
                    }
                }).catch(err => console.error(err));
            }).catch(err => console.error("Kunde inte starta kameran: ", err));
        }
    
        function toggleCamera() {
            const videoElement = document.getElementById('preview');
            const btn = document.getElementById('toggleCameraBtn');
            const flashBtn = document.getElementById('toggleFlashBtn');
    
            if (isCameraActive) {
                const stream = videoElement.srcObject;
                if (stream) {
                    stream.getTracks().forEach(track => track.stop());
                }
                videoElement.srcObject = null;
                if (codeReader) codeReader.reset();
    
                btn.innerText = "📷 Sätt på kamera";
                btn.classList.replace('btn-dark', 'btn-outline-dark');
                flashBtn.disabled = true;
                isCameraActive = false;
            } else {
                startScanner();
                btn.innerText = "📷 Stäng av kamera";
                btn.classList.replace('btn-outline-dark', 'btn-dark');
                flashBtn.disabled = false;
                isCameraActive = true;
            }
        }
    
        async function toggleFlash() {
            const videoElement = document.getElementById('preview');
            const stream = videoElement.srcObject;
            if (stream) {
                const track = stream.getVideoTracks()[0];
                try {
                    flashOn = !flashOn;
                    await track.applyConstraints({
                        advanced: [{ torch: flashOn }]
                    });
                    const flashBtn = document.getElementById('toggleFlashBtn');
                    if (flashOn) {
                        flashBtn.classList.replace('btn-outline-dark', 'btn-warning');
                        flashBtn.innerText = "⚡ Stäng av Flash";
                    } else {
                        flashBtn.classList.replace('btn-warning', 'btn-outline-dark');
                        flashBtn.innerText = "⚡ Flash (Ficklampa)";
                    }
                } catch (err) {
                    alert("Flash stöds inte av denna enhet eller webbläsare.");
                }
            }
        }
    </script>
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
</body>
</html>
"""

CHECKOUT_TEMPLATE = """
<!DOCTYPE html>
<html lang="sv">
<head>
    <meta charset="UTF-8">
    <title>Kassa - URBAN NATION</title>
    """ + COMMON_STYLES + """
</head>
<body class="bg-light">
    <div class="container my-5">
        <div class="d-flex justify-content-between align-items-center mb-4">
            <a href="/" class="btn btn-secondary">&larr; Tillbaka</a>
            <div class="d-flex align-items-center gap-2">
                <img src="{{ logo_url }}" alt="Logo" style="height: 38px; width: 38px; border-radius: 50%;" onerror="this.style.display='none'">
                <span class="fw-bold fs-4">URBAN NATION</span>
            </div>
        </div>
        <form method="POST">
            <div class="row">
                <div class="col-md-7">
                    <div class="card p-4 shadow-sm mb-4">
                        <h4 class="mb-3">1. Kundinformation</h4>
                        <div class="row">
                            <div class="col-md-6 mb-3">
                                <label class="form-label">Förnamn</label>
                                <input type="text" class="form-control" name="first_name" value="{{ current_user.first_name if current_user else '' }}" required placeholder="">
                            </div>
                            <div class="col-md-6 mb-3">
                                <label class="form-label">Efternamn</label>
                                <input type="text" class="form-control" name="last_name" value="{{ current_user.last_name if current_user else '' }}" required placeholder="">
                            </div>
                        </div>
                        <div class="row">
                            <div class="col-md-6 mb-3">
                                <label class="form-label">E-postadress</label>
                                <input type="email" class="form-control" id="emailInput" name="email" value="{{ current_user.email if current_user else '' }}" required placeholder="Upprepa e-postadress">
                            </div>
                            <div class="col-md-6 mb-3">
                                <label class="form-label">Bekräfta E-postadress</label>
                                <input type="email" class="form-control" id="confirmEmailInput" name="confirm_email" value="{{ current_user.email if current_user else '' }}" required placeholder="Upprepa e-postadress">
                            </div>
                        </div>
                        <div class="mb-3">
                            <label class="form-label">Mobilnummer</label>
                            <input type="tel" class="form-control" name="phone" value="{{ current_user.phone if current_user else '' }}" required placeholder="07x xxx xx xx">
                        </div>
                    
                        {% if not current_user %}
                        <!-- Skapa Konto Lösenord (för nya kunder) -->
                        <div class="p-3 mb-3 bg-light rounded border">
                            <label class="form-label fw-bold mb-1">🔐 Skapa konto för framtida inloggning</label>
                            <p class="text-muted small mb-2">Ditt lösenord används för att komma åt dina köpta biljetter och orderhistorik.</p>
                            <div class="row">
                                <div class="col-md-6 mb-2">
                                    <label class="form-label small">Lösenord</label>
                                    <input type="password" class="form-control" id="passwordInput" name="password" required placeholder="Välj ett lösenord">
                                </div>
                                <div class="col-md-6 mb-2">
                                    <label class="form-label small">Bekräfta Lösenord</label>
                                    <input type="password" class="form-control" id="confirmPasswordInput" name="confirm_password" required placeholder="Upprepa lösenord">
                                </div>
                            </div>
                        </div>
                        {% endif %}
                    
                        <div class="mb-3 position-relative">
                            <label class="form-label">Gatuadress</label>
                            <input type="text" class="form-control" id="addressInput" name="address" value="{{ current_user.address if current_user else '' }}" autocomplete="off" required placeholder="Börja skriva din gatuadress ...">
                            <div id="addressSuggestions" class="list-group position-absolute w-100 shadow-sm" style="z-index: 1050; display: none;"></div>
                        </div>
                        <div class="row">
                            <div class="col-md-6 mb-3">
                                <label class="form-label">Postnummer</label>
                                <input type="text" class="form-control" id="postalCodeInput" name="postal_code" value="{{ current_user.postal_code if current_user else '' }}" required placeholder="xxx xx" maxlength="6">
                            </div>
                            <div class="col-md-6 mb-3">
                                <label class="form-label">Stad / Ort</label>
                                <input type="text" class="form-control" id="cityInput" name="city" value="{{ current_user.city if current_user else '' }}" required placeholder="Luleå eller Umeå">
                            </div>
                        </div>
                    </div>
                    <div class="card p-4 shadow-sm mb-4">
                        <h4 class="mb-3">2. Fraktalternativ</h4>
                        {% for s in shipping_options %}
                        <div class="form-check mb-2">
                            <input class="form-check-input" type="radio" name="shipping" id="{{ s.id }}" value="{{ s.id }}" {% if loop.first %}checked{% endif %}>
                            <label class="form-check-label" for="{{ s.id }}"><strong>{{ s.name }}</strong> - {{ s.price }} SEK</label>
                        </div>
                        {% endfor %}
                    </div>
                    <div class="card p-4 shadow-sm mb-4">
                        <h4 class="mb-3">3. Betalningsmetod</h4>
                        {% for p in payment_methods %}
                        <div class="form-check mb-3">
                            <input class="form-check-input" type="radio" name="payment" id="{{ p.id }}" value="{{ p.id }}" {% if loop.first %}checked{% endif %}>
                            <label class="form-check-label" for="{{ p.id }}"><strong>{{ p.name }}</strong><br><small class="text-muted">{{ p.desc }}</small></label>
                        </div>
                        {% endfor %}
                    </div>
                </div>
                <div class="col-md-5">
                    <div class="card p-4 shadow-sm mb-4">
                        <h4 class="mb-3">Rabattkod</h4>
                        <div class="input-group mb-3">
                            <input type="text" class="form-control" name="promo_code" value="{{ promo_code_applied }}" placeholder="KOD">
                            <button class="btn btn-dark" type="submit">Tillämpa</button>
                        </div>
                    </div>
                    <div class="card p-4 shadow-sm">
                        <div class="d-flex justify-content-between align-items-center mb-3">
                            <h4 class="mb-0">Varukorg</h4>
                            <a href="/cart/clear" class="btn btn-outline-danger btn-sm" onclick="return confirm('Vill du tömma hela varukorgen?')">🗑️ Töm allt</a>
                        </div>
                        
                        <ul class="list-group mb-3">
                            {% for item in items %}
                            <li class="list-group-item d-flex justify-content-between align-items-center">
                                <div>
                                    <span class="fw-bold">{{ item.name }}</span><br>
                                    <small class="text-muted">{{ item.price }} SEK st</small>
                                </div>
                                <div class="d-flex align-items-center gap-2">
                                    <div class="btn-group btn-group-sm" role="group">
                                        <a href="/cart/decrease/{{ loop.index0 }}" class="btn btn-outline-secondary">-</a>
                                        <span class="btn btn-light disabled border px-2 text-dark fw-bold">{{ item.quantity }}</span>
                                        <a href="/cart/increase/{{ loop.index0 }}" class="btn btn-outline-secondary">+</a>
                                    </div>
                                    <span class="fw-bold ms-2">{{ item.total_price }} SEK</span>
                                </div>
                            </li>
                            {% endfor %}

                            {% if applied_discount > 0 %}
                            <li class="list-group-item d-flex justify-content-between fw-bold bg-light">
                                <span>Rabatt ({{ promo_code_applied }})</span>
                                <span class="text-danger">-{{ applied_discount }} SEK</span>
                            </li>
                            {% endif %}
                            
                            <li class="list-group-item d-flex justify-content-between bg-light fw-bold fs-5">
                                <span>Totalt ({{ total_items_count }} st)</span>
                                <span>{{ discounted_subtotal }} SEK</span>
                            </li>
                        </ul>
                        <button type="submit" name="submit_order" value="1" class="btn btn-dark w-100 btn-lg">Slutför Köp</button>
                    </div>
                </div>
            </div>
        </form>
    </div>
    """ + ADDRESS_AUTOCOMPLETE_SCRIPT + """
</body>
</html>
"""

SUCCESS_TEMPLATE = """
<!DOCTYPE html>
<html lang="sv">
<head>
    <meta charset="UTF-8">
    <title>Bekräftelse - URBAN NATION</title>
    """ + COMMON_STYLES + """
</head>
<body class="bg-light">
    <div class="container my-5">
        <div class="card p-5 shadow-sm text-center">
            <div class="mb-3">
                <img src="{{ logo_url }}" alt="Logo" style="height: 90px; width: 90px; border-radius: 50%; object-fit: cover;" class="shadow-sm" onerror="this.style.display='none'">
            </div>
            <h1 class="mb-3 text-dark">Tack för din beställning hos URBAN NATION! 🎉</h1>
            <p class="lead">Kvitto och biljetter skickade till <strong>{{ email }}</strong>.</p>
            <div class="text-start mx-auto mt-4" style="max-width: 600px;">
                <p><strong>Ordernummer:</strong> #{{ order_id }}</p>
                <p><strong>Mottagare:</strong> {{ name }} ({{ phone }})</p>
                <p><strong>Leverans:</strong> {{ shipping.name }} ({{ shipping.price }} SEK)</p>
                <h4>Totalt att betala: {{ total }} SEK</h4>
            </div>
            <div class="mt-4">
                <a href="/account" class="btn btn-dark me-2">Gå till Mitt Konto & Se Biljetter</a>
                <a href="/" class="btn btn-outline-dark">Tillbaka till Start</a>
            </div>
        </div>
    </div>
</body>
</html>
"""

SCANNER_LOGIN_TEMPLATE = """
<!DOCTYPE html>
<html lang="sv">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>URBAN NATION - Entré Skanner</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
</head>
<body class="bg-dark text-white d-flex align-items-center justify-content-center min-vh-100">
    <div class="card p-4 bg-black text-white border-secondary shadow-lg text-center" style="max-width: 400px; width: 100%;">
        <h3 class="fw-bold mb-1">📱 URBAN NATION</h3>
        <p class="text-muted small mb-3">Entré & Biljettskanner för Ordningsvakter</p>
        <div class="alert alert-info py-1 px-2 small mb-3">
            ⏰ Giltig till: <strong>{{ expires }}</strong>
        </div>

        {% with messages = get_flashed_messages(with_categories=true) %}
          {% if messages %}{% for c, m in messages %}<div class="alert alert-{{ c }} py-2 small">{{ m }}</div>{% endfor %}{% endif %}
        {% endwith %}

        <form method="POST">
            <div class="mb-3 text-start">
                <label class="form-label small text-muted">Ange Engångslösenord</label>
                <input type="text" class="form-control text-center fw-bold fs-4 bg-dark text-white border-secondary" name="password" placeholder="XXX-XXX" required autofocus autocomplete="off">
            </div>
            <button type="submit" class="btn btn-warning w-100 fw-bold py-2">Lås upp Skanner</button>
        </form>
    </div>
</body>
</html>
"""


SCANNER_AGENT_TEMPLATE = """
<!DOCTYPE html>
<html lang="sv">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>URBAN NATION - Scanner</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
</head>
<body class="bg-dark text-white">
    <div class="container text-center my-3" style="max-width: 500px;">
        <div class="d-flex justify-content-between align-items-center mb-3 border-bottom pb-2">
            <h4 class="fw-bold mb-0">📱 Ticket Scanner</h4>
            <span class="badge bg-danger">⏰ Max 6h (Till {{ expires }})</span>
        </div>

        <div class="d-flex justify-content-center gap-2 mb-3">
            <button id="toggleCameraBtn" class="btn btn-light btn-sm fw-bold" onclick="toggleCamera()">📷 Stäng av kamera</button>
            <button id="toggleFlashBtn" class="btn btn-outline-warning btn-sm fw-bold" onclick="toggleFlash()">⚡ Flash</button>
        </div>

        <div id="scanner-container" class="border border-secondary rounded bg-black mb-3 position-relative overflow-hidden" style="height: 320px;">
            <video id="preview" style="width: 100%; height: 100%; object-fit: cover;"></video>
        </div>

        <div id="scan-result" class="alert d-none text-start"></div>
    </div>

    <script src="https://unpkg.com/@zxing/library@latest"></script>
    <script>
        let codeReader = null;
        let isCameraActive = true;
        let flashOn = false;

        window.addEventListener('load', function () { startScanner(); });

        function startScanner() {
            codeReader = new ZXing.BrowserQRCodeReader();
            codeReader.decodeFromInputVideoDevice(undefined, 'preview').then((result) => {
                fetch('/api/scan_ticket', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({ ticket_code: result.text })
                })
                .then(res => res.json())
                .then(data => {
                    const resDiv = document.getElementById('scan-result');
                    resDiv.classList.remove('d-none', 'alert-success', 'alert-danger', 'alert-warning');
                    if (data.status === 'VALID') {
                        resDiv.classList.add('alert-success');
                        resDiv.innerHTML = `<h5 class="fw-bold">✅ GILTIG BILJETT</h5><p class="mb-1"><strong>Kategori:</strong> ${data.category}</p><p class="mb-0"><strong>Gäst:</strong> ${data.guest_name}</p>`;
                    } else {
                        resDiv.classList.add('alert-danger');
                        resDiv.innerHTML = `<h5 class="fw-bold">❌ OGILTIG / ANVÄND BILJETT</h5><p class="mb-0">${data.message}</p>`;
                    }
                });
            }).catch(err => console.error(err));
        }

        function toggleCamera() {
            const videoElement = document.getElementById('preview');
            const btn = document.getElementById('toggleCameraBtn');
            if (isCameraActive) {
                const stream = videoElement.srcObject;
                if (stream) stream.getTracks().forEach(track => track.stop());
                videoElement.srcObject = null;
                if (codeReader) codeReader.reset();
                btn.innerText = "📷 Starta kamera";
                isCameraActive = false;
            } else {
                startScanner();
                btn.innerText = "📷 Stäng av kamera";
                isCameraActive = true;
            }
        }

        async function toggleFlash() {
            const stream = document.getElementById('preview').srcObject;
            if (stream) {
                const track = stream.getVideoTracks()[0];
                try {
                    flashOn = !flashOn;
                    await track.applyConstraints({ advanced: [{ torch: flashOn }] });
                } catch (err) { alert("Flash stöds inte på denna enhet."); }
            }
        }
    </script>
</body>
</html>
"""

SALES_REPORT_PDF_TEMPLATE = """
<!DOCTYPE html>
<html lang="sv">
<head>
    <meta charset="UTF-8">
    <title>Moms- & Försäljningsrapport - URBAN NATION</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <style>
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #ffffff; color: #000; }
        @media print {
            .no-print { display: none !important; }
            body { padding: 0; margin: 0; }
        }
    </style>
</head>
<body class="p-5">

    <div class="d-flex justify-content-between align-items-center mb-4 no-print border-bottom pb-3">
        <div>
            <a href="/admin" class="btn btn-outline-dark btn-sm">← Tillbaka till Admin Dashboard</a>
        </div>
        <button onclick="window.print()" class="btn btn-dark btn-lg fw-bold">🖨️ Skriv ut / Spara som PDF</button>
    </div>

    <!-- EN-TÊTE DU RAPPORT COMPTABLE -->
    <div class="row align-items-center mb-4 border-bottom pb-3">
        <div class="col-8">
            <h1 class="fw-bold mb-1">URBAN NATION</h1>
            <h4 class="text-uppercase text-muted">Moms- & Försäljningsrapport (Bokföring)</h4>
            <p class="small text-muted mb-0">Rapport genererad: <strong>{{ now_date }}</strong></p>
        </div>
        <div class="col-4 text-end">
            <div class="p-3 bg-light border rounded">
                <small class="text-muted d-block">Total Omsättning (Inkl. moms)</small>
                <h3 class="fw-bold mb-0 text-dark">{{ total_grand_incl }} SEK</h3>
            </div>
        </div>
    </div>

    <!-- RÉCAPITULATIF PAR TAUX DE TVA (MOMS-SUMMERING) -->
    <h5 class="fw-bold mb-3">📊 Momssummering per skattesats</h5>
    <div class="row mb-4">
        <div class="col-md-6 mb-2">
            <div class="p-3 border rounded bg-light">
                <div class="d-flex justify-content-between">
                    <span><strong>Kläder & Merch (25% moms)</strong></span>
                    <span class="badge bg-dark">25%</span>
                </div>
                <hr class="my-2">
                <div class="d-flex justify-content-between small">
                    <span>Brutto (Inkl. moms):</span>
                    <strong>{{ total_clothing_incl }} SEK</strong>
                </div>
                <div class="d-flex justify-content-between small text-danger">
                    <span>Beräknad Moms (25%):</span>
                    <strong>{{ total_clothing_vat }} SEK</strong>
                </div>
                <div class="d-flex justify-content-between small text-muted">
                    <span>Netto (Exkl. moms):</span>
                    <span>{{ (total_clothing_incl - total_clothing_vat)|round(2) }} SEK</span>
                </div>
            </div>
        </div>

        <div class="col-md-6 mb-2">
            <div class="p-3 border rounded bg-light">
                <div class="d-flex justify-content-between">
                    <span><strong>Eventbiljetter (6% moms)</strong></span>
                    <span class="badge bg-secondary">6%</span>
                </div>
                <hr class="my-2">
                <div class="d-flex justify-content-between small">
                    <span>Brutto (Inkl. moms):</span>
                    <strong>{{ total_ticket_incl }} SEK</strong>
                </div>
                <div class="d-flex justify-content-between small text-danger">
                    <span>Beräknad Moms (6%):</span>
                    <strong>{{ total_ticket_vat }} SEK</strong>
                </div>
                <div class="d-flex justify-content-between small text-muted">
                    <span>Netto (Exkl. moms):</span>
                    <span>{{ (total_ticket_incl - total_ticket_vat)|round(2) }} SEK</span>
                </div>
            </div>
        </div>
    </div>

    <!-- TABLEAU DÉTAILLÉ DES TRANSACTIONS -->
    <h5 class="fw-bold mb-3">📄 Transaktionsspecifikation</h5>
    <table class="table table-bordered table-sm align-middle small mb-4">
        <thead class="table-dark">
            <tr>
                <th>Order #</th>
                <th>Datum</th>
                <th>Kund</th>
                <th>Produkt / Artikel</th>
                <th>Typ</th>
                <th class="text-end">Moms %</th>
                <th class="text-end">Exkl. Moms</th>
                <th class="text-end">Moms SEK</th>
                <th class="text-end">Inkl. Moms</th>
            </tr>
        </thead>
        <tbody>
            {% for it in items %}
            <tr>
                <td>#{{ it.order_id }}</td>
                <td>{{ it.date }}</td>
                <td>{{ it.customer }}</td>
                <td><strong>{{ it.item_name }}</strong></td>
                <td>{{ it.type_label }}</td>
                <td class="text-end">{{ it.vat_rate }}%</td>
                <td class="text-end">{{ it.total_excl }} SEK</td>
                <td class="text-end text-danger">{{ it.vat_amt }} SEK</td>
                <td class="text-end fw-bold">{{ it.total_incl }} SEK</td>
            </tr>
            {% endfor %}
        </tbody>
        <tfoot class="table-light fw-bold">
            <tr>
                <td colspan="6" class="text-end">Totalt:</td>
                <td class="text-end">{{ (total_grand_incl - total_grand_vat)|round(2) }} SEK</td>
                <td class="text-end text-danger">{{ total_grand_vat }} SEK</td>
                <td class="text-end text-dark fs-6">{{ total_grand_incl }} SEK</td>
            </tr>
        </tfoot>
    </table>

    <div class="mt-5 text-center text-muted small border-top pt-3">
        <p>© 2026 URBAN NATION AB - Officiellt bokföringsunderlag genererat automatiskt.</p>
    </div>

</body>
</html>
"""

FORGOT_PASSWORD_TEMPLATE = """
<!DOCTYPE html>
<html lang="sv">
<head>
    <meta charset="UTF-8">
    <title>Glömt lösenord - URBAN NATION</title>
    """ + COMMON_STYLES + """
</head>
<body class="bg-light">
    <div class="container my-5" style="max-width: 450px;">
        <div class="text-center mb-4">
            <img src="{{ logo_url }}" alt="Urban Nation Logo" style="height: 80px; width: 80px; border-radius: 50%; object-fit: cover;" class="mb-2 shadow-sm" onerror="this.style.display='none'">
            <h2 class="fw-bold text-uppercase">URBAN <span style="color: #000;">NATION</span></h2>
        </div>
        <div class="card p-4 shadow-sm">
            <h4 class="mb-3 text-center fw-bold">Återställ lösenord</h4>
            <p class="text-muted small text-center mb-4">Ange din e-postadress så skickar vi instruktioner för att återställa ditt lösenord.</p>

            {% with messages = get_flashed_messages(with_categories=true) %}
              {% if messages %}{% for c, m in messages %}<div class="alert alert-{{ c }} small py-2">{{ m }}</div>{% endfor %}{% endif %}
            {% endwith %}

            <form method="POST">
                <div class="mb-3">
                    <label class="form-label">E-postadress</label>
                    <input type="email" class="form-control" name="email" required placeholder="namn@example.se">
                </div>
                <button type="submit" class="btn btn-dark w-100 btn-lg">Skicka återställningslänk</button>
            </form>

            <hr class="my-4">
            <div class="text-center">
                <a href="/login" class="btn btn-link text-decoration-none text-dark p-0">&larr; Tillbaka till inloggning</a>
            </div>
        </div>
    </div>
</body>
</html>
"""

RESET_PASSWORD_TEMPLATE = """
<!DOCTYPE html>
<html lang="sv">
<head>
    <meta charset="UTF-8">
    <title>Nytt lösenord - URBAN NATION</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
</head>
<body class="bg-dark text-white d-flex align-items-center justify-content-center vh-100">
    <div class="card p-4 shadow-lg bg-black border border-warning rounded-4" style="width: 400px;">
        <h3 class="fw-bold text-center mb-3 text-warning">Skapa nytt lösenord</h3>

        <form method="POST">
            <div class="mb-3">
                <label class="form-label small fw-bold">Nytt lösenord</label>
                <input type="password" class="form-control form-control-sm bg-dark text-white border-secondary" name="new_password" required>
            </div>
            <button type="submit" class="btn btn-warning w-100 fw-bold btn-sm py-2">Spara nytt lösenord</button>
        </form>
    </div>
</body>
</html>
"""


if __name__ == '__main__':
    app.run(debug=True)