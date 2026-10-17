from flask import Flask, render_template_string, request, redirect, url_for, flash, session, Response, send_file
from flask_mail import Mail, Message
import os
import random
from datetime import datetime, timedelta
import csv
import io
import qrcode

# Importation pour la génération PDF des billets
from reportlab.lib.pagesizes import A6
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

app = Flask(__name__)
app.secret_key = "secret_key_suede_ecommerce_admin"

# Configuration Flask-Mail
app.config['MAIL_SERVER'] = os.environ.get('MAIL_SERVER', 'smtp.gmail.com')
app.config['MAIL_PORT'] = int(os.environ.get('MAIL_PORT', 587))
app.config['MAIL_USE_TLS'] = os.environ.get('MAIL_USE_TLS', 'true').lower() in ['true', 'on', '1']
app.config['MAIL_USERNAME'] = os.environ.get('MAIL_USERNAME', 'support@urbannation.se')
app.config['MAIL_PASSWORD'] = os.environ.get('MAIL_PASSWORD', 'votre_mot_de_passe')
app.config['MAIL_DEFAULT_SENDER'] = os.environ.get('MAIL_DEFAULT_SENDER',
                                                   ('URBAN NATION Stockholm', 'no-reply@urbannation.se'))

mail = Mail(app)

UPLOAD_FOLDER = 'static/uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# URL du logo officiel Urban Nation
LOGO_URL = "/static/uploads/image1.jpeg"
# Image Hero Banner avec la photo des platines DJ / concert (provenant de votre capture)
# HERO_DJ_BG = "https://images.unsplash.com/photo-1516450360452-9312f5e86fc7?auto=format&fit=crop&w=1600&q=80"
HERO_DJ_BG = "/static/uploads/image2.png"


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
        "title": "Urban Nation Techno Rave - Winter Edition",
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


# --- EXPORTATION CSV ---

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


# --- ROUTES GESTION ---

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


@app.route('/request_return/<int:order_id>', methods=['POST'])
def request_return(order_id):
    current_user = get_current_user()
    if not current_user: return redirect(url_for('user_login'))
    reason = request.form.get('reason')
    item_name = request.form.get('item_name')
    order = next((o for o in ORDERS if o['id'] == order_id), None)
    if order:
        ret_id = max([r['id'] for r in RETURNS]) + 1 if RETURNS else 101
        RETURNS.append({
            "id": ret_id, "order_id": order_id, "customer_email": current_user['email'],
            "reason": reason, "item_name": item_name, "amount": order['total'], "status": "Under behandling"
        })
        flash("Din returbegäran har skickats till kundtjänst!", "success")
    return redirect(url_for('user_account'))


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
    return render_template_string(HOME_TEMPLATE, products=PRODUCTS, top_products=top_products, events=EVENTS,
                                  product_types=PRODUCT_TYPES, cart_count=cart_count, current_user=current_user,
                                  logo_url=LOGO_URL, hero_bg=HERO_DJ_BG)


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
def user_login():
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password')
        customer = next((c for c in CUSTOMERS if c['email'].lower() == email and c['password'] == password), None)
        if customer:
            session['user_email'] = customer['email']
            flash(f"Välkommen tillbaka, {customer['name']}!", "success")
            return redirect(url_for('user_account'))
        else:
            flash("Felaktig e-postadress eller lösenord.", "danger")
    return render_template_string(USER_LOGIN_TEMPLATE, logo_url=LOGO_URL)


@app.route('/register', methods=['GET', 'POST'])
def user_register():
    if request.method == 'POST':
        first_name = request.form.get('first_name', '').strip()
        last_name = request.form.get('last_name', '').strip()
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        phone = request.form.get('phone')
        address = request.form.get('address')
        postal_code = request.form.get('postal_code')
        city = request.form.get('city')

        if password != confirm_password:
            flash("Lösenorden matchar inte.", "danger")
        elif any(c['email'].lower() == email for c in CUSTOMERS):
            flash("Det finns redan ett konto registrerat med denna e-postadress.", "warning")
        else:
            full_name = f"{first_name} {last_name}".strip()
            new_id = max([c['id'] for c in CUSTOMERS]) + 1 if CUSTOMERS else 1
            CUSTOMERS.append({
                "id": new_id, "name": full_name, "first_name": first_name, "last_name": last_name,
                "email": email, "phone": phone, "address": address, "postal_code": postal_code,
                "city": city, "password": password, "total_orders": 0
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


@app.route('/logout')
def user_logout():
    session.pop('user_email', None)
    flash("Du har loggats ut.", "info")
    return redirect(url_for('index'))


@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        if request.form.get('password') == "suisse2026":
            session['admin_logged'] = True
            log_admin_action("Inloggning i adminpanelen", "Admin anslöt till systemet.")
            return redirect(url_for('admin_dashboard'))
        else:
            flash("Fel lösenord.", "danger")
    return render_template_string(ADMIN_LOGIN_TEMPLATE, logo_url=LOGO_URL)


@app.route('/admin', methods=['GET', 'POST'])
def admin_dashboard():
    if not session.get('admin_logged'): return redirect(url_for('admin_login'))
    total_revenue = sum(p['sold'] * (p['discount_price'] if p.get('discount_price') else p['price']) for p in PRODUCTS)
    total_items_sold = sum(p['sold'] for p in PRODUCTS)
    total_tickets_sold = sum(p['sold'] for p in PRODUCTS if p['type'] == 'ticket')
    ticket_revenue = sum(
        p['sold'] * (p['discount_price'] if p.get('discount_price') else p['price']) for p in PRODUCTS if
        p['type'] == 'ticket')
    return render_template_string(ADMIN_DASHBOARD_TEMPLATE,
                                  products=PRODUCTS, events=EVENTS, product_types=PRODUCT_TYPES,
                                  customers=CUSTOMERS, logs=ADMIN_LOGS, orders=ORDERS, returns=RETURNS,
                                  promo_codes=PROMO_CODES,
                                  total_revenue=total_revenue, total_items_sold=total_items_sold,
                                  total_tickets_sold=total_tickets_sold, ticket_revenue=ticket_revenue,
                                  logo_url=LOGO_URL)


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


@app.route('/admin/add_event', methods=['POST'])
def admin_add_event():
    if not session.get('admin_logged'): return redirect(url_for('admin_login'))
    title = request.form.get('title')
    date = request.form.get('date')
    time = request.form.get('time')
    location = request.form.get('location')
    price = int(request.form.get('price'))
    desc = request.form.get('desc')
    image_url = request.form.get('image_url')
    file = request.files.get('image_file')

    if file and file.filename != '':
        filename = f"event_{random.randint(1000, 9999)}_{file.filename}"
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        image_path = f"/{filepath}"
    elif image_url:
        image_path = image_url
    else:
        image_path = "https://images.unsplash.com/photo-1516450360452-9312f5e86fc7?auto=format&fit=crop&w=500&q=60"

    new_id = max([e['id'] for e in EVENTS]) + 1 if EVENTS else 1
    EVENTS.append({"id": new_id, "title": title, "date": date, "time": time, "location": location, "price": price,
                   "image": image_path, "desc": desc})

    prod_id = max([p['id'] for p in PRODUCTS]) + 1 if PRODUCTS else 1
    PRODUCTS.append({
        "id": prod_id, "type": "ticket", "name": f"{title} - Biljett", "price": price,
        "discount_price": None, "promo_badge": "", "total_stock": 100, "sold": 0,
        "date": datetime.now().strftime("%Y-%m-%d"), "sizes": [], "colors": [], "image": image_path,
        "images": [image_path],
        "desc": f"Biljett till {title} på {location} ({date})."
    })
    log_admin_action("Event publicerat", f"Event '{title}' publicerades med tillhörande biljetter.")
    flash("Eventet har publicerats och biljetter har lagts till i shoppen!", "success")
    return redirect(url_for('admin_dashboard') + '#events')


@app.route('/admin/delete_event/<int:event_id>')
def admin_delete_event(event_id):
    if not session.get('admin_logged'): return redirect(url_for('admin_login'))
    global EVENTS
    ev = next((e for e in EVENTS if e['id'] == event_id), None)
    t_title = ev['title'] if ev else f"ID {event_id}"
    EVENTS = [e for e in EVENTS if e['id'] != event_id]
    log_admin_action("Event borttaget", f"Event '{t_title}' raderades.")
    flash("Eventet har tagits bort.", "info")
    return redirect(url_for('admin_dashboard') + '#events')


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

    # Indexation et groupement par produit
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

        if email != confirm_email:
            flash("E-postadresserna matchar inte.", "danger")
            return redirect(url_for('checkout'))

        if not current_user and password != confirm_password:
            flash("Lösenorden matchar inte.", "danger")
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

        # Mettre à jour les ventes par unité
        for item in cart_items:
            target_p = next((p for p in PRODUCTS if p['id'] == item['id']), None)
            if target_p: target_p['sold'] += item['quantity']

        new_order = {
            "id": order_id, "customer_email": email, "customer_name": name,
            "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "order_items": [{"id": i['id'], "name": i['name'], "price": i['price'], "quantity": i['quantity'], "type": i['type']} for i in
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

# --- STYLES HARMONISÉS NOIR & BLANC (SANS JAUNE, TEXTES LISIBLES) ---

COMMON_STYLES = """
    <link href="https://fonts.googleapis.com/css2?family=Montserrat:wght@400;600;800&family=Inter:wght@300;400;600;700&display=swap" rel="stylesheet">
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <style>
        :root {
            --primary-black: #0d0d0d;
            --border-color: #e5e5e5;
        }

        /* Mode Clair par défaut : Fond Blanc avec multi-logos répétés Urban Nation */
        body {
            font-family: 'Inter', sans-serif;
            background-color: #ffffff !important;
            color: #111111 !important;
            position: relative;
        }

        /* Multiples petits logos répétés en arrière-plan (Pattern / Wallpaper) */
        body::before {
            content: "";
            position: fixed;
            top: 0;
            left: 0;
            width: 100vw;
            height: 100vh;
            background-image: url('/static/uploads/image1.jpeg');
            background-repeat: repeat; /* Répète le logo partout sur la page */
            background-position: 0 0;
            background-size: 80px 80px; /* Taille de chaque petit logo */
            opacity: 0.025; /* Très discret et élégant */
            pointer-events: none;
            z-index: -1;
        }

        /* Mode Sombre (Dark Mode) */
        body.dark-mode {
            background-color: #0f0f12 !important;
            color: #ffffff !important;
        }
        body.dark-mode::before {
            filter: invert(1) brightness(2); /* Inverse les logos en blanc sur fond sombre */
            opacity: 0.035;
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

        .badge.bg-dark, 
        body.dark-mode .badge.bg-dark {
            background-color: #0d0d0d !important;
            color: #ffffff !important;
            border: 1px solid #444444 !important;
        }

        .badge.bg-danger, 
        body.dark-mode .badge.bg-danger {
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

        body.dark-mode h1, body.dark-mode h2, body.dark-mode h3, body.dark-mode h4, body.dark-mode h5 {
            color: #ffffff !important;
        }

        body.dark-mode .card, body.dark-mode .bg-white, body.dark-mode .bg-light {
            background-color: #18181c !important;
            color: #ffffff !important;
            border-color: #2a2a30 !important;
        }

        body.dark-mode .card .card-title, body.dark-mode .card h5, body.dark-mode .card h4, body.dark-mode .card p, body.dark-mode .card span {
            color: #ffffff !important;
        }

        body.dark-mode .btn-link, 
        body.dark-mode .card .btn-link {
            color: #ffffff !important;
        }

        body.dark-mode .text-decoration-line-through,
        body.dark-mode .card .text-muted, 
        body.dark-mode .text-muted { 
            color: #bbbbbb !important; 
        }

        body.dark-mode .btn-outline-dark {
            color: #ffffff !important;
            border-color: #ffffff !important;
        }

        body.dark-mode select.form-select {
            background-color: #2b2b36 !important;
            color: #ffffff !important;
            border-color: #444455 !important;
        }

        .gallery-thumb { width: 44px; height: 44px; object-fit: cover; cursor: pointer; border: 2px solid transparent; border-radius: 6px; }
        .gallery-thumb:hover, .gallery-thumb.active { border-color: #111111; }

        .countdown-timer,
        .countdown-timer *,
        body.dark-mode .countdown-timer,
        body.dark-mode .countdown-timer * {
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
            color: rgba(255, 255, 255, 0.04); /* Très subtil en Dark Mode */
            white-space: nowrap;
            pointer-events: none;
            z-index: 0;
            font-family: 'Montserrat', sans-serif;
            letter-spacing: 4px;
        }
        body:not(.dark-mode) .bg-urban-watermark::before {
            color: rgba(0, 0, 0, 0.04); /* Très subtil en Light Mode */
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
                    <button id="themeToggleBtn" class="btn btn-outline-light btn-sm me-2" onclick="toggleDarkMode()">🌙 Dark</button>
                    {% if current_user %}
                        <a href="/account" class="btn btn-outline-light btn-sm">👤 Konto ({{ current_user.first_name if current_user.first_name else current_user.name.split()[0] }})</a>
                        <a href="/logout" class="btn btn-outline-danger btn-sm">Logga ut</a>
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
                                    </div>
                                    <h4 class="card-title h5">{{ event.title }}</h4>
                                    <p class="text-muted small mb-2">📍 {{ event.location }} (⏰ {{ event.time }})</p>
                                    <p class="card-text text-muted small flex-grow-1">{{ event.desc }}</p>

                                    <div class="mt-3">
                                        {% set match_id = 3 %}
                                        {% for p in products %}
                                            {% if event.title in p.name %}{% set match_id = p.id %}{% endif %}
                                        {% endfor %}

                                        <form action="/add/{{ match_id }}" method="POST">
                                            <div class="input-group input-group-sm mb-2">
                                                <label class="input-group-text bg-secondary text-white">Biljettyp</label>
                                                <select class="form-select form-select-sm" name="ticket_category">
                                                    <option value="early">Early Bird (-20%): {{ (event.price * 0.8)|int }} SEK</option>
                                                    <option value="standard" selected>Standard: {{ event.price }} SEK</option>
                                                    <option value="vip">VIP / Fast Track (+50%): {{ (event.price * 1.5)|int }} SEK</option>
                                                </select>
                                            </div>
                                            <button type="submit" class="btn btn-dark btn-sm w-100">Boka Biljett Nu</button>
                                        </form>
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

    <!-- Modals, footer et scripts conservés -->
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
        function toggleDarkMode() {
            document.body.classList.toggle('dark-mode');
            const isDark = document.body.classList.contains('dark-mode');
            localStorage.setItem('theme', isDark ? 'dark' : 'light');
            document.getElementById('themeToggleBtn').innerText = isDark ? '☀️ Light' : '🌙 Dark';
        }

        document.addEventListener('DOMContentLoaded', function() {
            const savedTheme = localStorage.getItem('theme');
            if (savedTheme === 'dark') {
                document.body.classList.add('dark-mode');
                const btn = document.getElementById('themeToggleBtn');
                if (btn) btn.innerText = '☀️ Light';
            } else {
                document.body.classList.remove('dark-mode');
                const btn = document.getElementById('themeToggleBtn');
                if (btn) btn.innerText = '🌙 Dark';
            }
        });

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
                <div class="mb-3"><label class="form-label">E-postadress</label><input type="email" class="form-control" name="email" required placeholder="namn@example.se"></div>
                <div class="mb-3"><label class="form-label">Lösenord</label><input type="password" class="form-control" name="password" required placeholder="Ditt lösenord"></div>
                <button type="submit" class="btn btn-dark w-100 btn-lg">Logga in</button>
            </form>
            <hr class="my-4">
            <div class="text-center"><p class="text-muted mb-1">Har du inget konto än?</p><a href="/register" class="btn btn-outline-dark btn-sm">Skapa ett konto här</a></div>
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
          {% if messages %}{% for c, m in messages %}<div class="alert alert-{{ c }}">{{ m }}</div>{% endfor %}{% endif %}
        {% endwith %}

        <div class="row">
            <div class="col-md-4 mb-4">
                <div class="card p-4 shadow-sm bg-white">
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
            </div>

            <div class="col-md-8">
                <div class="card p-4 shadow-sm bg-white mb-4">
                    <h3 class="mb-3">🛍️ Mina Beställningar & Spårning</h3>
                    {% if orders %}
                        {% for order in orders %}
                        <div class="border rounded-3 p-3 mb-3 bg-light">
                            <div class="d-flex justify-content-between align-items-center mb-2">
                                <div>
                                    <strong>Order #{{ order.id }}</strong>
                                    <span class="text-muted small ms-2">📅 {{ order.date }}</span>
                                </div>
                                <span class="badge bg-dark text-white">{{ order.status }}</span>
                            </div>
                            <ul class="list-group mb-2">
                                {% for item in order.order_items %}
                                <li class="list-group-item d-flex justify-content-between align-items-center py-2">
                                    <span>{% if item.type == 'ticket' %}🎫{% else %}👕{% endif %} <strong>{{ item.name }}</strong></span>
                                    <span>{{ item.price }} SEK</span>
                                </li>
                                {% endfor %}
                            </ul>
                            <div class="d-flex justify-content-between align-items-center mb-2">
                                <small class="text-muted">Leverans: {{ order.shipping }}</small>
                                <strong class="fs-5 text-dark">Totalt: {{ order.total }} SEK</strong>
                            </div>
                            {% if order.tracking_number %}
                            <div class="alert alert-secondary p-2 mb-2 small border">
                                📦 <strong>Spårningsnummer:</strong> <code>{{ order.tracking_number }}</code>
                            </div>
                            {% endif %}
                            <button class="btn btn-outline-dark btn-sm" data-bs-toggle="collapse" data-bs-target="#returnForm{{ order.id }}">🔄 Begär Retur</button>
                            <div class="collapse mt-2" id="returnForm{{ order.id }}">
                                <form action="/request_return/{{ order.id }}" method="POST" class="card card-body bg-white p-3">
                                    <h6 class="mb-2">Begär Retur för Order #{{ order.id }}</h6>
                                    <div class="mb-2">
                                        <label class="form-label small">Välj produkt</label>
                                        <select class="form-select form-select-sm" name="item_name">
                                            {% for item in order.order_items %}<option value="{{ item.name }}">{{ item.name }}</option>{% endfor %}
                                        </select>
                                    </div>
                                    <div class="mb-2"><label class="form-label small">Anledning</label><input type="text" class="form-control form-control-sm" name="reason" required placeholder="t.ex. Fel storlek"></div>
                                    <button type="submit" class="btn btn-dark btn-sm">Skicka Returbegäran</button>
                                </form>
                            </div>
                        </div>
                        {% endfor %}
                    {% else %}
                        <p class="text-muted">Du har inga tidigare beställningar ännu.</p>
                    {% endif %}
                </div>

                <div class="card p-4 shadow-sm bg-white">
                    <h3 class="mb-3">🎫 Mina Eventbiljetter & QR-koder</h3>
                    {% set has_tickets = false %}
                    {% for order in orders %}
                        {% for item in order.order_items %}
                            {% if item.type == 'ticket' %}
                                {% set has_tickets = true %}
                                <div class="card mb-3 border-dark">
                                    <div class="card-body d-flex justify-content-between align-items-center">
                                        <div>
                                            <h5 class="card-title text-dark mb-1">{{ item.name }}</h5>
                                            <p class="text-muted small mb-0">Order ID: #{{ order.id }} | Köpt av: {{ current_user.name }}</p>
                                            <span class="badge bg-secondary text-white mt-2">Giltig Biljett</span>
                                            <div class="mt-3">
                                                <a href="/download_ticket/{{ order.id }}/{{ item.name }}" class="btn btn-dark btn-sm">📄 Ladda ner PDF-biljett</a>
                                            </div>
                                        </div>
                                        <div class="text-center">
                                            <img src="https://api.qrserver.com/v1/create-qr-code/?size=90x90&data=TICKET-{{ order.id }}-{{ item.name }}" alt="QR Code" class="img-thumbnail">
                                            <small class="d-block text-muted mt-1" style="font-size: 0.7rem;">Skanna i entrén</small>
                                        </div>
                                    </div>
                                </div>
                            {% endif %}
                        {% endfor %}
                    {% endfor %}
                    {% if not has_tickets %}
                        <p class="text-muted mb-0">Du har inga aktiva eventbiljetter i ditt konto.</p>
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
        .admin-nav-sticky { position: sticky; top: 0; z-index: 1020; background-color: #111111; padding: 10px 0; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }
        .admin-nav-sticky .nav-link { color: #ffffff; font-weight: 500; font-size: 0.9rem; padding: 6px 12px; border-radius: 4px; transition: background 0.2s; }
        .admin-nav-sticky .nav-link:hover, .admin-nav-sticky .nav-link.active { background-color: #ffffff; color: #000 !important; }
        section { scroll-margin-top: 80px; }
    </style>
</head>
<body class="bg-light">
    <nav class="navbar navbar-dark bg-dark">
        <div class="container">
            <a class="navbar-brand text-white fw-bold d-flex align-items-center gap-2" href="/admin">
                <img src="{{ logo_url }}" alt="Urban Nation Logo" style="height: 36px; width: 36px; border-radius: 50%;" onerror="this.style.display='none'">
                <span>URBAN NATION <span class="text-light">Administration</span></span>
            </a>
            <div>
                <a href="/" class="btn btn-outline-light btn-sm me-2">Visa Hemsida</a>
                <a href="/admin/logout" class="btn btn-danger btn-sm">Logga ut</a>
            </div>
        </div>
    </nav>

    <div class="admin-nav-sticky">
        <div class="container">
            <ul class="nav nav-pills justify-content-center gap-1 flex-wrap">
                <li class="nav-item"><a class="nav-link" href="#stats">📊 Statistik</a></li>
                <li class="nav-item"><a class="nav-link" href="#categories">🏷️ Kategorier</a></li>
                <li class="nav-item"><a class="nav-link" href="#orders">🚚 Beställningar</a></li>
                <li class="nav-item"><a class="nav-link" href="#returns">🔄 Returer</a></li>
                <li class="nav-item"><a class="nav-link" href="#promos">🎟️ Rabattkoder</a></li>
                <li class="nav-item"><a class="nav-link" href="#events">🎉 Event</a></li>
                <li class="nav-item"><a class="nav-link" href="#products">📦 Produkter</a></li>
                <li class="nav-item"><a class="nav-link" href="#logs">📋 Loggar</a></li>
            </ul>
        </div>
    </div>

    <div class="container my-5">
        {% with messages = get_flashed_messages(with_categories=true) %}
          {% if messages %}{% for c, m in messages %}<div class="alert alert-{{ c }}">{{ m }}</div>{% endfor %}{% endif %}
        {% endwith %}

        <div class="d-flex justify-content-between align-items-center mb-4 bg-white p-3 rounded shadow-sm">
            <h4 class="mb-0">Exportera Data (Excel / CSV)</h4>
            <div class="d-flex gap-2">
                <a href="/admin/export/orders" class="btn btn-dark btn-sm">Beställningar CSV</a>
                <a href="/admin/export/customers" class="btn btn-dark btn-sm">Kunder CSV</a>
                <a href="/admin/export/event_attendees" class="btn btn-dark btn-sm">Event Deltagare</a>
            </div>
        </div>

        <section id="stats" class="mb-5">
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
                        <h5>Lagersituation: Inlagda vs Sålda</h5>
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

        <section id="categories" class="card p-4 shadow-sm mb-5">
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

        <section id="orders" class="card p-4 shadow-sm mb-5">
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

        <section id="returns" class="card p-4 shadow-sm mb-5">
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

        <section id="promos" class="card p-4 shadow-sm mb-5">
            <h3 class="mb-3">Hantera Rabattkoder & Kampanjbrickor (Rea / Black Friday)</h3>
            
            <!-- Section 1 : Rabattkoder i kassan -->
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

            <!-- Section 2 : Koppla Kampanjbricka / Rea till valt produkt -->
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

            <!-- Section 3 : Aktiva Kampanjbrickor lista -->
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

        <section id="events" class="card p-4 shadow-sm mb-5">
            <h3 class="mb-3">Publicera nytt Evenemang</h3>
            <form action="/admin/add_event" method="POST" enctype="multipart/form-data">
                <div class="row">
                    <div class="col-md-6 mb-3"><label class="form-label">Titel</label><input type="text" class="form-control" name="title" required></div>
                    <div class="col-md-3 mb-3"><label class="form-label">Datum</label><input type="date" class="form-control" name="date" required></div>
                    <div class="col-md-3 mb-3"><label class="form-label">Tid</label><input type="text" class="form-control" name="time" required placeholder="23:00 - 05:00"></div>
                </div>
                <div class="row">
                    <div class="col-md-6 mb-3"><label class="form-label">Plats</label><input type="text" class="form-control" name="location" required></div>
                    <div class="col-md-6 mb-3"><label class="form-label">Pris (SEK)</label><input type="number" class="form-control" name="price" required></div>
                </div>
                <div class="row mb-3">
                    <div class="col-md-6"><label class="form-label">📁 Bildfil</label><input type="file" class="form-control" name="image_file" accept="image/*"></div>
                    <div class="col-md-6"><label class="form-label">🔗 Bild-URL</label><input type="text" class="form-control" name="image_url"></div>
                </div>
                <div class="mb-3"><label class="form-label">Beskrivning</label><textarea class="form-control" name="desc" rows="2"></textarea></div>
                <button type="submit" class="btn btn-dark">Publicera Event</button>
            </form>
        </section>

        <section id="products" class="mb-5">
            <div class="card p-4 shadow-sm mb-4">
                <h3 class="mb-3">Lägg till ny produkt / Biljett</h3>
                <form action="/admin/add_product" method="POST" enctype="multipart/form-data">
                    <div class="row mb-3">
                        <div class="col-md-4"><label class="form-label">Namn</label><input type="text" class="form-control" name="name" required placeholder="Produktnamn"></div>
                        <div class="col-md-2"><label class="form-label">Ord. Pris (SEK)</label><input type="number" class="form-control" name="price" required placeholder="699"></div>
                        <div class="col-md-2"><label class="form-label">Typ / Kategori</label>
                            <select class="form-select" name="type">
                                {% for t in product_types %}<option value="{{ t.id }}">{{ t.name }}</option>{% endfor %}
                            </select>
                        </div>
                    </div>
                    <div class="row mb-3">
                        <div class="col-md-2"><label class="form-label">Lagerantal (Stock)</label><input type="number" class="form-control" name="total_stock" value="50" required></div>
                        <div class="col-md-3"><label class="form-label">Storlekar (Komma-separerade)</label><input type="text" class="form-control" name="sizes" placeholder="S, M, L, XL,..."></div>
                        <div class="col-md-3"><label class="form-label">Färger (Komma-separerade)</label><input type="text" class="form-control" name="colors" placeholder="Svart, Vit"></div>
                        <div class="col-md-4"><label class="form-label">Bild URL</label><input type="text" class="form-control" name="image_url" placeholder="https://..."></div>
                    </div>
                    <div class="mb-3"><label class="form-label">Beskrivning</label><textarea class="form-control" name="desc" rows="2" placeholder="Kort beskrivning av produkten..."></textarea></div>
                    <button type="submit" class="btn btn-dark">Lägg till produkt</button>
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

        <section id="logs" class="mb-5">
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

    <script>
        const ctxBar = document.getElementById('barChart').getContext('2d');
        new Chart(ctxBar, {
            type: 'bar',
            data: {
                labels: [{% for p in products %}"{{ p.name }}",{% endfor %}],
                datasets: [
                    { label: 'Totalt Inlagda (Stock)', data: [{% for p in products %}{{ p.total_stock }},{% endfor %}], backgroundColor: '#0d6efd' },
                    { label: 'Sålda', data: [{% for p in products %}{{ p.sold }},{% endfor %}], backgroundColor: '#198754' }
                ]
            },
            options: { responsive: true, scales: { y: { beginAtZero: true } } }
        });

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

if __name__ == '__main__':
    app.run(debug=True)