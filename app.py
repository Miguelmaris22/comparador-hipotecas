from flask import Flask, render_template, request, redirect
import smtplib
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from datetime import datetime
from fpdf import FPDF
import os

app = Flask(__name__)

# Configuración de Google Sheets
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds_json = os.getenv("GOOGLE_CREDS", "client_secret.json")
creds = ServiceAccountCredentials.from_json_keyfile_name(creds_json, scope)
client = gspread.authorize(creds)
sheet = client.open("Leads Comparador Hipotecario").sheet1

# Configura estos valores con tu cuenta
EMAIL_SENDER = "miguel.maris.mm@gmail.com"
EMAIL_PASS = "bqhh aoxf ohxz oedg"
EMAIL_DEST = "miguel.maris.mm@gmail.com"

@app.route('/')
def index():
    return render_template("formulario.html")

@app.route('/gracias')
def gracias():
    return render_template("gracias.html")

@app.route('/enviar', methods=['POST'])
def enviar():
    datos = {
        "Nombre": request.form['nombre'],
        "Precio": request.form['precio'],
        "Aportacion": request.form['aportacion'],
        "Ciudad": request.form['ciudad'],
        "Correo": request.form['correo'],
        "Telefono": request.form['telefono'],
        "Ingresos": request.form['ingresos'],
        "Contrato": request.form['contrato'],
        "Edad": request.form['edad'],
        "Finalidad": request.form['finalidad'],
        "Fecha": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "IP": request.remote_addr,
        "User-Agent": request.headers.get("User-Agent"),
        "Empresa": ""
    }

    # Guardar en Google Sheets
    fila = list(datos.values())
    sheet.append_row(fila)

    # Crear PDF
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    for k, v in datos.items():
        pdf.cell(200, 10, txt=f"{k}: {v}", ln=True)
    pdf.output("lead.pdf")

    # Enviar email
    mensaje = MIMEMultipart()
    mensaje["Subject"] = "Nuevo lead hipotecario"
    mensaje["From"] = EMAIL_SENDER
    mensaje["To"] = EMAIL_DEST
    cuerpo = "\n".join([f"{k}: {v}" for k, v in datos.items()])
    mensaje.attach(MIMEText(cuerpo, "plain"))
    with open("lead.pdf", "rb") as f:
        adjunto = MIMEApplication(f.read(), _subtype="pdf")
        adjunto.add_header("Content-Disposition", "attachment", filename="lead.pdf")
        mensaje.attach(adjunto)

    # Enviar copia a empresa también (mismo contenido)
    mensaje_emp = MIMEMultipart()
    mensaje_emp["Subject"] = "Nuevo lead hipotecario"
    mensaje_emp["From"] = EMAIL_SENDER
    mensaje_emp["To"] = datos["Correo"]
    mensaje_emp.attach(MIMEText("Gracias por enviar tu solicitud. Un asesor se pondrá en contacto contigo."))

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(EMAIL_SENDER, EMAIL_PASS)
        server.sendmail(EMAIL_SENDER, EMAIL_DEST, mensaje.as_string())
        server.sendmail(EMAIL_SENDER, datos["Correo"], mensaje_emp.as_string())

    return redirect('/gracias')

if __name__ == "__main__":
    app.run(debug=True)
