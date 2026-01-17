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

# --- CONFIG ---
gmail_user = os.environ.get("GMAIL_USER")
gmail_password = os.environ.get("GMAIL_PASSWORD")
url_suscriptores = os.environ.get("URL_SUSCRIPTORES")
webhook_make = os.environ.get("MAKE_WEBHOOK_URL")

# PEGA AQUÍ EL ENLACE DE TU LOGO EN GITHUB (Que ya tenías)
URL_LOGO = "https://raw.githubusercontent.com/TuUsuario/TuRepo/main/logo.jpg" 

# PEGA AQUÍ LA URL DE TU NUEVA PÁGINA DE WIX (Donde pusiste el formulario)
URL_SUSCRIPCION = "https://analyzingbasketball.wixsite.com/home/newsletter"
URL_HOME = "https://analyzingbasketball.wixsite.com/home"

if not gmail_user or not gmail_password: sys.exit("❌ Faltan credenciales.")

# --- LEER INFORME ---
if not os.path.exists("newsletter_borrador.md"): sys.exit("❌ No hay informe.")
with open("newsletter_borrador.md", "r", encoding="utf-8") as f: md_content = f.read()

titulo_redes = md_content.split('\n')[0].replace('#', '').strip()
texto_post = f"🏀 {titulo_redes}\n📊 Nuevo análisis. Link en bio.\n#ACB #AnalyzingBasketball"

# --- LINKEDIN ---
if webhook_make:
    try: requests.post(webhook_make, json={"texto": texto_post})
    except: pass

# --- INSTAGRAM ---
img = Image.new('RGB', (1080, 1080), color=(10, 10, 10))
draw = ImageDraw.Draw(img)
try: font = ImageFont.load_default()
except: font = ImageFont.load_default()
draw.text((100, 500), "NUEVO INFORME\nDISPONIBLE", fill=(255, 255, 255), font=font)
img.save("post_ig.jpg")

msg_admin = MIMEMultipart()
msg_admin['From'] = gmail_user
msg_admin['To'] = gmail_user
msg_admin['Subject'] = "📸 Pack Instagram"
msg_admin.attach(MIMEText(texto_post, 'plain'))
with open("post_ig.jpg", 'rb') as f: msg_admin.attach(MIMEImage(f.read(), name="ig.jpg"))
server = smtplib.SMTP_SSL('smtp.gmail.com', 465)
server.login(gmail_user, gmail_password)
server.sendmail(gmail_user, gmail_user, msg_admin.as_string())

# --- NEWSLETTER (DISEÑO FINAL) ---
html_content = markdown.markdown(md_content)

plantilla = f"""
<html><body style='font-family:Arial, sans-serif; background:#f4f4f4; padding:20px; margin:0;'>
<div style='background:#fff; max-width:600px; margin:0 auto; border:1px solid #ddd;'>
    
    <div style='background:#000; padding:20px; text-align:center;'>
        <img src="{URL_LOGO}" style="max-width:120px; display:block; margin:0 auto;">
    </div>

    <div style='padding:40px 30px; color:#333; line-height:1.6;'>
        {html_content}
    </div>

    <div style='background:#fff; padding:20px; text-align:center; padding-bottom: 40px;'>
        <a href="{URL_SUSCRIPCION}" style='display:inline-block; background:#000; color:#fff; padding:12px 30px; text-decoration:none; font-weight:bold; font-size:14px; letter-spacing:1px;'>RECOMENDAR</a>
    </div>

    <div style='background:#f9f9f9; padding:20px; text-align:center; border-top:1px solid #eee;'>
        <a href='{URL_HOME}' style='color:#000; font-weight:bold; text-decoration:none; font-size:14px; text-transform:uppercase;'>Analyzing Basketball</a>
        <p style='color:#999; font-size:11px; margin-top:5px;'>&copy; 2026 AB</p>
    </div>

</div>
</body></html>
"""

# ENVÍO
lista_emails = []
if url_suscriptores:
    try:
        df = pd.read_csv(url_suscriptores, on_bad_lines='skip', engine='python')
        col = next((c for c in df.columns if "@" in str(df[c].iloc[0])), None)
        if col: lista_emails = df[col].dropna().unique().tolist()
    except: pass
if gmail_user not in lista_emails: lista_emails.append(gmail_user)

for email in lista_emails:
    msg = MIMEMultipart()
    msg['From'] = f"Analyzing Basketball <{gmail_user}>"
    msg['To'] = email.strip()
    msg['Subject'] = f"🏀 Informe: {titulo_redes}"
    msg.attach(MIMEText(plantilla, 'html'))
    server.sendmail(gmail_user, email.strip(), msg.as_string())

server.quit()
print("✅ TODO COMPLETADO.")
