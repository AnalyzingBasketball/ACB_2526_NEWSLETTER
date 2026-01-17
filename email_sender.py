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
url_suscriptores = os.environ.get("URL_SUSCRIPTORES") # TU HOJA DE TALLY
webhook_make = os.environ.get("MAKE_WEBHOOK_URL")

if not gmail_user or not gmail_password:
    sys.exit("❌ Error: Faltan credenciales de Gmail en Secrets.")

# --- 2. LEER INFORME ---
if not os.path.exists("newsletter_borrador.md"):
    sys.exit("❌ No hay informe generado (newsletter_borrador.md).")

with open("newsletter_borrador.md", "r", encoding="utf-8") as f:
    md_content = f.read()

# Título para redes
titulo_redes = md_content.split('\n')[0].replace('#', '').strip()
texto_post = f"🏀 {titulo_redes}\n\n📊 Nuevo análisis de datos disponible. Link en bio.\n\n#ACB #BigData #AnalyzingBasketball"

# --- 3. PUBLICAR EN LINKEDIN (VÍA MAKE) ---
if webhook_make:
    print("📡 Contactando con Make (LinkedIn)...")
    try:
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
    # Usamos fuente por defecto si no encuentra una pro
    font = ImageFont.load_default()
except:
    font = ImageFont.load_default()

# Dibujamos texto simple
draw.text((100, 400), "ANALYZING\nBASKETBALL", fill=(0, 150, 255), font=font)
draw.text((100, 600), "INFORME TÉCNICO", fill=(255, 255, 255), font=font)
draw.text((100, 650), datetime.now().strftime("%d/%m/%Y"), fill=(200, 200, 200), font=font)

img.save(nombre_imagen)

# --- 5. ENVIAR AL ADMIN (TÚ) ---
print(f"📩 Enviando pack Instagram a {gmail_user}...")
msg_admin = MIMEMultipart()
msg_admin['From'] = gmail_user
msg_admin['To'] = gmail_user
msg_admin['Subject'] = "📸 Pack Instagram + LinkedIn Confirmado"

body_admin = f"LinkedIn publicado vía Make.\nAqui tienes la foto para Instagram:\n\n{texto_post}"
msg_admin.attach(MIMEText(body_admin, 'plain'))

with open(nombre_imagen, 'rb') as f:
    img_data = f.read()
    image = MIMEImage(img_data, name="instagram.jpg")
    msg_admin.attach(image)

server = smtplib.SMTP_SSL('smtp.gmail.com', 465)
server.login(gmail_user, gmail_password)
server.sendmail(gmail_user, gmail_user, msg_admin.as_string())

# --- 6. NEWSLETTER A SUSCRIPTORES (TALLY) ---
print("📥 Leyendo suscriptores de Tally...")
html_content = markdown.markdown(md_content)
link_share = f"mailto:?subject=Informe Basket&body=Mira esto: https://analyzingbasketball.wixsite.com/home"

plantilla = f"""
<html><body style='font-family:Arial;background:#f4f4f4;padding:20px'>
<div style='background:#fff;padding:20px;max-width:600px;margin:auto;border-radius:5px'>
<h1 style='text-align:center;color:#000'>ANALYZING BASKETBALL</h1>
{html_content}
<div style='background:#e0f7fa;padding:15px;text-align:center;margin-top:20px'>
<p>¿Te gusta? <strong>Compártelo</strong></p>
<a href="{link_share}" style='background:#000;color:#fff;padding:10px 20px;text-decoration:none'>⏩ REENVIAR A UN AMIGO</a>
</div>
<div style='text-align:center;margin-top:20px'>
<a href='https://analyzingbasketball.wixsite.com/home' style='color:#0056b3'>Ver en la Web</a>
</div></div></body></html>
"""

lista_emails = []
if url_suscriptores:
    try:
        # Leemos el CSV ignorando líneas rotas para que no falle
        df = pd.read_csv(url_suscriptores, on_bad_lines='skip', engine='python')
        
        # BUSCAMOS LA COLUMNA DE EMAILS (Columna D o la que tenga @)
        columna_emails = None
        for col in df.columns:
            # Miramos el primer valor de cada columna para ver si parece un email
            primer_valor = str(df[col].iloc[0]) if not df.empty else ""
            if "@" in primer_valor:
                columna_emails = col
                break
        
        if columna_emails:
            lista_raw = df[columna_emails].dropna().unique().tolist()
            lista_emails = [x.strip() for x in lista_raw if "@" in str(x)]
        else:
            print("⚠️ No encontré columna con emails en el Excel. Revisa que haya al menos un dato.")

    except Exception as e:
        print(f"⚠️ Error leyendo Excel Tally: {e}")

# Añadirte a ti mismo para asegurar que recibes copia
if gmail_user not in lista_emails:
    lista_emails.append(gmail_user)

print(f"📧 Enviando a {len(lista_emails)} personas...")

for email in lista_emails:
    msg = MIMEMultipart()
    msg['From'] = f"Analyzing Basketball <{gmail_user}>"
    msg['To'] = email
    msg['Subject'] = f"🏀 Informe: {titulo_redes}"
    msg.attach(MIMEText(plantilla, 'html'))
    server.sendmail(gmail_user, email, msg.as_string())
    print(f"   -> Enviado a: {email}")

server.quit()
print("✅ TODO COMPLETADO.")
