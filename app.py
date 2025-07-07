
from flask import Flask, render_template, request, redirect
import smtplib
import os
import json
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from email.mime.text import MIMEText, MIMEMultipart
from email.mime.application import MIMEApplication
from fpdf import FPDF

app = Flask(__name__)

# Configuración de Google Sheets desde variable de entorno
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds_dict = json.loads(os.environ["GOOGLE_CREDS"])
creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
client = gspread.authorize(creds)
sheet = client.open("Leads Comparador Hipotecario").sheet1

EMAIL_SENDER = os.environ.get("EMAIL_SENDER")
EMAIL_PASS = os.environ.get("EMAIL_PASS")
EMAIL_DEST = os.environ.get("EMAIL_DEST")

@app.route('/')
def index():
    return render_template("formulario.html")

@app.route('/enviar', methods=['POST'])
def enviar():
    datos_lead = {
        "Nombre": request.form['nombre'],
        "Precio": request.form['precio'],
        "Aportacion": request.form['aportacion'],
        "Ciudad": request.form['ciudad'],
        "Correo": request.form['correo'],
        "Telefono": request.form['telefono'],
        "Ingresos": request.form['ingresos'],
        "Contrato": request.form['contrato'],
        "Edad": request.form['edad'],
        "Finalidad": request.form['finalidad']
    }

    try:
        precio = float(datos_lead['Precio'])
        aportacion = float(datos_lead['Aportacion'])
        porcentaje = round((1 - aportacion / precio) * 100)
        datos_lead["% Financiación"] = f"{porcentaje}%"
    except:
        datos_lead["% Financiación"] = "N/A"

    sheet.append_row(list(datos_lead.values()))

    # Crear PDF con logotipo
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    pdf.image("static/logo.png", x=10, y=8, w=33)
    pdf.ln(40)

    for k, v in datos_lead.items():
        pdf.cell(0, 10, f"{k}: {v}", ln=True)

    pdf_file = "/tmp/lead.pdf"
    pdf.output(pdf_file)

    # Email
    mensaje = MIMEMultipart()
    mensaje["Subject"] = "Nuevo lead hipotecario"
    mensaje["From"] = EMAIL_SENDER
    mensaje["To"] = EMAIL_DEST
    mensaje.attach(MIMEText("\n".join([f"{k}: {v}" for k, v in datos_lead.items()]), "plain"))

    with open(pdf_file, "rb") as f:
        adjunto = MIMEApplication(f.read(), _subtype="pdf")
        adjunto.add_header("Content-Disposition", "attachment", filename="lead.pdf")
        mensaje.attach(adjunto)

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(EMAIL_SENDER, EMAIL_PASS)
        server.send_message(mensaje)

    return redirect("/gracias")

@app.route('/gracias')
def gracias():
    return render_template("gracias.html")

if __name__ == "__main__":
    app.run(debug=True)
