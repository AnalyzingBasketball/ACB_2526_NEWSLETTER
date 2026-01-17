import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.image import MIMEImage
import os
import markdown
import sys
import pandas as pd
import requests
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont

# --- 1. CONFIGURACIÓN ---
gmail_user = os.environ.get("GMAIL_USER")
gmail_password = os.environ.get("GMAIL_PASSWORD")
url_suscriptores = os.environ.get("URL_SUSCRIPTORES")
webhook_make = os.environ.get("MAKE_WEBHOOK_URL")

if not gmail_user or not gmail_password:
    sys.exit("❌ Error: Faltan credenciales de Gmail.")

# --- 2. LEER INFORME ---
if not os.path.exists("newsletter_borrador.md"):
    sys.exit("❌ No hay informe generado.")

with open("newsletter_borrador.md", "r", encoding="utf-8") as f:
    md_content = f.read()

# Título para redes (primera línea del MD)
titulo_redes = md_content.split('\n')[0].replace('#', '').strip()
texto_post = f"🏀 {titulo_redes}\n\n📊 Nuevo análisis de datos disponible. Link en bio.\n\n#ACB #BigData #AnalyzingBasketball"

# --- 3. PUBLICAR EN LINKEDIN (VÍA MAKE) ---
if webhook_make:
    print("📡 Contactando con Make (LinkedIn)...")
    try:
        # Enviamos el texto a Make. Make lo pondrá en LinkedIn.
        requests.post(webhook_make, json={"texto": texto_post})
        print("✅ Señal enviada a Make.")
    except Exception as e:
        print(f"⚠️ Error conectando con Make: {e}")

# --- 4. GENERAR IMAGEN (PACK INSTAGRAM) ---
print("🎨 Generando imagen...")
nombre_imagen = "post_instagram.jpg"
img = Image.new('RGB', (1080, 1080), color=(10, 10, 10))
draw = ImageDraw.Draw(img)

try:
    font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 70)
except:
    font = ImageFont.load_default()

draw.text((100, 400), "ANALYZING\nBASKETBALL", fill=(0, 150, 255), font=font)
draw.text((100, 600), "INFORME TÉCNICO", fill=(255, 255, 255), font=font)
draw.text((100, 700), datetime.now().strftime("%d/%m/%Y"), fill=(150, 150, 150), font=font)

img.save(nombre_imagen)

# --- 5. ENVIAR AL ADMIN (TÚ) ---
print(f"📩 Enviando pack Instagram a {gmail_user}...")
msg_admin = MIMEMultipart()
msg_admin['From'] = gmail_user
msg_admin['To'] = gmail_user
msg_admin['Subject'] = "📸 Pack Instagram + LinkedIn Confirmado"

body_admin = f"LinkedIn se ha publicado automático.\nAqui tienes la foto para Instagram:\n\n{texto_post}"
msg_admin.attach(MIMEText(body_admin, 'plain'))

with open(nombre_imagen, 'rb') as f:
    img_data = f.read()
    image = MIMEImage(img_data, name="instagram.jpg")
    msg_admin.attach(image)

server = smtplib.SMTP_SSL('smtp.gmail.com', 465)
server.login(gmail_user, gmail_password)
server.sendmail(gmail_user, gmail_user, msg_admin.as_string())

# --- 6. NEWSLETTER A SUSCRIPTORES ---
print("📥 Enviando Newsletter a suscriptores...")
html_content = markdown.markdown(md_content)
plantilla = f"""
<html><body>
<div style='background:#f4f4f4;padding:20px'>
<div style='background:#fff;padding:20px;max-width:600px;margin:auto'>
<h1 style='text-align:center;color:#000'>ANALYZING BASKETBALL</h1>
{html_content}
<div style='text-align:center;margin-top:20px'>
<a href='https://analyzingbasketball.wixsite.com/home' style='background:#000;color:#fff;padding:10px 20px;text-decoration:none'>VER WEB</a>
</div></div></div></body></html>
"""

lista_emails = []
if url_suscriptores:
    try:
        df = pd.read_csv(url_suscriptores)
        col = next((c for c in df.columns if "@" in str(df[c].iloc[0])), None)
        if col: lista_emails = df[col].dropna().unique().tolist()
    except: pass

for email in lista_emails:
    if "@" in str(email):
        msg = MIMEMultipart()
        msg['From'] = f"Analyzing Basketball <{gmail_user}>"
        msg['To'] = email.strip()
        msg['Subject'] = f"🏀 Informe: {titulo_redes}"
        msg.attach(MIMEText(plantilla, 'html'))
        server.sendmail(gmail_user, email.strip(), msg.as_string())

server.quit()
print("✅ TODO COMPLETADO.")
