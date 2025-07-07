from flask import Flask, render_template, request
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
import json  # Solo una vez
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds_dict = json.loads(os.environ["GOOGLE_CREDENTIALS_JSON"])
creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
client = gspread.authorize(creds)
sheet = client.open("Leads Comparador Hipotecario").sheet1


# Configuración de correo
EMAIL_SENDER = "miguel.maris.mm@gmail.com"
EMAIL_PASS = "bqhh aoxf ohxz oedg"
EMAIL_DEST = "miguel.maris.mm@gmail.com"

# Correos de empresas receptoras
EMPRESAS_EMAIL = {
    "Broker Madrid S.L.": "broker.madrid@example.com",
    "Hipotecas Costa Levante": "hipotecas.levante@example.com"
}

# Clase PDF personalizada
class LeadPDF(FPDF):
    def header(self):
        self.image('A_vector-based_digital_illustration_logo_features_.png', 10, 8, 33)
        self.set_font('Arial', 'B', 14)
        self.cell(80)
        self.cell(30, 10, 'Resumen del Lead Hipotecario', 0, 0, 'C')
        self.ln(20)

    def add_lead_info(self, data: dict):
        self.set_font('Arial', '', 12)
        for key, value in data.items():
            safe_value = str(value).replace("€", "EUR")
            self.cell(0, 10, f"{key}: {safe_value}", ln=True)

def generar_pdf_lead(datos: dict, nombre_archivo: str) -> str:
    pdf = LeadPDF()
    pdf.add_page()
    pdf.add_lead_info(datos)
    pdf.output(nombre_archivo)
    return nombre_archivo

@app.route('/')
def index():
    return render_template("formulario.html")

@app.route('/politica-privacidad')
def politica_privacidad():
    return render_template("politica-privacidad.html")

@app.route('/enviar', methods=['POST'])
def enviar():
    # Recoger datos del formulario
    nombre = request.form['nombre']
    precio = float(request.form['precio'])
    aportacion = float(request.form['aportacion'])
    ciudad = request.form['ciudad']
    correo = request.form['correo']
    telefono = request.form['telefono']
    ingresos = request.form['ingresos']
    contrato = request.form['contrato']
    edad = request.form['edad']
    finalidad = request.form['finalidad']

    porcentaje = round(((precio - aportacion) / precio) * 100)
    fecha_envio = datetime.now().strftime("%d/%m/%Y %H:%M")
    ip = request.headers.get('X-Forwarded-For', request.remote_addr)
    user_agent = request.headers.get('User-Agent')

    ciudad_lower = ciudad.lower()
    if ciudad_lower in ["madrid", "rivas", "alcobendas"]:
        empresa = "Broker Madrid S.L."
    elif ciudad_lower in ["valencia", "alicante"]:
        empresa = "Hipotecas Costa Levante"
    else:
        empresa = "Lead sin asignar"

    # 🔍 Mostrar en consola los datos críticos
    print("==== DATOS DE ENVÍO ====")
    print("Fecha:", fecha_envio)
    print("IP:", ip)
    print("User-Agent:", user_agent)
    print("Empresa:", empresa)
    print("========================")

    # Guardar en Google Sheets
    fila = [
        fecha_envio,
        nombre,
        precio,
        aportacion,
        f"{porcentaje}%",
        ciudad,
        correo,
        telefono,
        ingresos,
        contrato,
        edad,
        finalidad,
        ip,
        user_agent,
        empresa
    ]
    sheet.append_row(fila)


    # Datos para PDF y correos
    datos_lead = {
        "Nombre": nombre,
        "Precio": f"{precio} EUR",
        "Aportación": f"{aportacion} EUR",
        "Porcentaje financiado": f"{porcentaje}%",
        "Ciudad": ciudad,
        "Correo": correo,
        "Teléfono": telefono,
        "Ingresos": f"{ingresos} EUR",
        "Contrato": contrato,
        "Edad": edad,
        "Finalidad": finalidad,
        "IP": ip,
        "User-Agent": user_agent,
        "Empresa receptora": empresa
    }

    pdf_path = f"lead_{nombre.replace(' ', '_')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
    generar_pdf_lead(datos_lead, pdf_path)

    # Enviar correo a ti
    mensaje = MIMEMultipart()
    mensaje["Subject"] = "Nuevo lead hipotecario"
    mensaje["From"] = EMAIL_SENDER
    mensaje["To"] = EMAIL_DEST
    mensaje.attach(MIMEText("\n".join([f"{k}: {v}" for k, v in datos_lead.items()]), "plain"))

    with open(pdf_path, "rb") as f:
        adjunto = MIMEApplication(f.read(), _subtype="pdf")
        adjunto.add_header("Content-Disposition", "attachment", filename=os.path.basename(pdf_path))
        mensaje.attach(adjunto)

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(EMAIL_SENDER, EMAIL_PASS)
            server.sendmail(EMAIL_SENDER, EMAIL_DEST, mensaje.as_string())
    except Exception as e:
        print("Error al enviar correo a administrador:", e)

    # Enviar correo a empresa receptora si tiene email
    correo_empresa = EMPRESAS_EMAIL.get(empresa)
    if correo_empresa:
        mensaje_emp = MIMEMultipart()
        mensaje_emp["Subject"] = "Lead hipotecario asignado"
        mensaje_emp["From"] = EMAIL_SENDER
        mensaje_emp["To"] = correo_empresa
        mensaje_emp.attach(MIMEText("\n".join([f"{k}: {v}" for k, v in datos_lead.items()]), "plain"))

        with open(pdf_path, "rb") as f:
            adjunto_emp = MIMEApplication(f.read(), _subtype="pdf")
            adjunto_emp.add_header("Content-Disposition", "attachment", filename=os.path.basename(pdf_path))
            mensaje_emp.attach(adjunto_emp)

        try:
            with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
                server.login(EMAIL_SENDER, EMAIL_PASS)
                server.sendmail(EMAIL_SENDER, correo_empresa, mensaje_emp.as_string())
        except Exception as e:
            print(f"Error al enviar correo a empresa {empresa}:", e)

    # Eliminar el PDF temporal si no lo necesitas guardar
    os.remove(pdf_path)

    return render_template("gracias.html")


if __name__ == "__main__":
    app.run(debug=True)
