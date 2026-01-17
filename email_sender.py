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

# --- 1. TUS ENLACES (¡RELLÉNALOS!) ---
# Pega aquí el enlace de tu logo (el de GitHub que acaba en .jpg o .png)
URL_LOGO = "https://github.com/AnalyzingBasketball/acb-newsletter-bot/blob/main/logo.png?raw=true" 

# Pega aquí el enlace de tu página de Wix que acabas de encontrar
URL_SUSCRIPCION = "https://analyzingbasketball.wixsite.com/home/newsletter"
URL_HOME = "https://analyzingbasketball.wixsite.com/home"

# --- 2. CONFIGURACIÓN SEGURA ---
gmail_user = os.environ.get("GMAIL_USER")
gmail_password = os.environ.get("GMAIL_PASSWORD")
url_suscriptores = os.environ.get("URL_SUSCRIPTORES")
webhook_make = os.environ.get("MAKE_WEBHOOK_URL")

if not gmail_user or not gmail_password:
    sys.exit("❌ Error: Faltan credenciales de Gmail.")

# --- 3. LEER EL INFORME GENERADO ---
if not os.path.exists("newsletter_borrador.md"):
    sys.exit("❌ No hay informe generado.")

with open("newsletter_borrador.md", "r", encoding="utf-8") as f:
    md_content = f.read()

# Preparamos los textos
titulo_redes = md_content.split('\n')[0].replace('#', '').strip()

# Texto específico para LinkedIn (con enlace clicable)
texto_linkedin = f"🏀 {titulo_redes}\n\n📊 Nuevo análisis de datos disponible.\nLee el informe completo y suscríbete aquí: {URL_SUSCRIPCION}\n\n#ACB #DataScouting #AnalyzingBasketball"

# Texto para Instagram (más corto, link en bio)
texto_instagram = f"🏀 {titulo_redes}\n📊 Nuevo análisis disponible. Link en bio.\n#ACB #AnalyzingBasketball"

# --- 4. AUTOMATIZACIÓN LINKEDIN (VÍA MAKE) ---
if webhook_make:
    print("📡 Enviando datos a Make para LinkedIn...")
    try:
        # Enviamos el texto con el enlace bueno a Make
        requests.post(webhook_make, json={"texto": texto_linkedin})
        print("✅ Publicado en LinkedIn automáticamente.")
    except Exception as e:
        print(f"⚠️ Error conectando con Make: {e}")

# --- 5. GENERAR IMAGEN PARA INSTAGRAM ---
print("🎨 Generando imagen para Instagram...")
nombre_imagen = "post_ig.jpg"
img = Image.new('RGB', (1080, 1080), color=(15, 15, 15)) # Fondo casi negro
draw = ImageDraw.Draw(img)

try:
    font = ImageFont.load_default()
except:
    font = ImageFont.load_default()

# Dibujamos el texto en la imagen
draw.text((100, 450), "ANALYZING\nBASKETBALL", fill=(0, 120, 255), font=font)
draw.text((100, 600), "NUEVO INFORME\nDISPONIBLE", fill=(255, 255, 255), font=font)
draw.text((100, 750), datetime.now().strftime("%d/%m/%Y"), fill=(150, 150, 150), font=font)

img.save(nombre_imagen)

# --- 6. ENVIAR PACK INSTAGRAM AL ADMIN (A TI) ---
msg_admin = MIMEMultipart()
msg_admin['From'] = gmail_user
msg_admin['To'] = gmail_user
msg_admin['Subject'] = "📸 Pack Instagram (LinkedIn ya publicado)"
msg_admin.attach(MIMEText(f"LinkedIn se ha publicado solo.\n\nAquí tienes la foto para Instagram:\n\n{texto_instagram}", 'plain'))

with open(nombre_imagen, 'rb') as f:
    msg_admin.attach(MIMEImage(f.read(), name="instagram_post.jpg"))

server = smtplib.SMTP_SSL('smtp.gmail.com', 465)
server.login(gmail_user, gmail_password)
server.sendmail(gmail_user, gmail_user, msg_admin.as_string())

# --- 7. ENVIAR NEWSLETTER A SUSCRIPTORES ---
print("📥 Preparando Newsletter...")
html_content = markdown.markdown(md_content)

plantilla = f"""
<html><body style='font-family: Helvetica, Arial, sans-serif; background-color: #f4f4f4; margin: 0; padding: 20px;'>
<div style='background-color: #ffffff; max-width: 600px; margin: 0 auto; border: 1px solid #dddddd;'>
    
    <div style='background-color: #000000; padding: 30px 20px; text-align: center;'>
        <img src="{URL_LOGO}" alt="Analyzing Basketball" style="max-width: 150px; height: auto; display: block; margin: 0 auto;">
    </div>

    <div style='padding: 40px 30px; color: #333333; line-height: 1.6; font-size: 16px;'>
        {html_content}
    </div>

    <div style='background-color: #ffffff; padding: 20px; text-align: center; padding-bottom: 40px;'>
        <a href="{URL_SUSCRIPCION}" style='display: inline-block; background-color: #000000; color: #ffffff; padding: 14px 30px; text-decoration: none; font-weight: bold; font-size: 14px; letter-spacing: 1px;'>RECOMENDAR</a>
    </div>

    <div style='background-color: #f9f9f9; padding: 30px; text-align: center; border-top: 1px solid #eeeeee;'>
        <a href='{URL_HOME}' style='color: #000000; font-weight: bold; text-decoration: none; font-size: 14px; text-transform: uppercase;'>Analyzing Basketball</a>
        <p style='color: #999999; font-size: 11px; margin-top: 10px;'>&copy; 2026 AB</p>
    </div>

</div>
</body></html>
"""

# Obtener lista de emails (con protección anti-errores)
lista_emails = []
if url_suscriptores:
    try:
        # engine='python' y on_bad_lines='skip' evitan que falle si hay comas raras
        df = pd.read_csv(url_suscriptores, on_bad_lines='skip', engine='python')
        
        # Buscamos automáticamente la columna que tiene emails
        col = next((c for c in df.columns if "@" in str(df[c].iloc[0])), None)
        if col:
            lista_emails = df[col].dropna().unique().tolist()
    except Exception as e:
        print(f"⚠️ Nota: No se pudo leer la lista de suscriptores ({e}). Se enviará solo al admin.")

# Aseguramos que tú siempre recibes una copia
if gmail_user not in lista_emails:
    lista_emails.append(gmail_user)

print(f"📧 Enviando newsletter a {len(lista_emails)} personas...")

for email in lista_emails:
    try:
        msg = MIMEMultipart()
        msg['From'] = f"Analyzing Basketball <{gmail_user}>"
        msg['To'] = email.strip()
        msg['Subject'] = f"🏀 Informe: {titulo_redes}"
        msg.attach(MIMEText(plantilla, 'html'))
        server.sendmail(gmail_user, email.strip(), msg.as_string())
    except:
        continue # Si un email falla, seguimos con el siguiente

server.quit()
print("✅ TODO COMPLETADO CON ÉXITO.")
