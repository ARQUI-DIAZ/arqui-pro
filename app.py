import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
from io import BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader

# ---------------------------
# CONFIGURACIÓN GENERAL
# ---------------------------
st.set_page_config(
    page_title="Presupuestos - Arqui-Pro",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Tema oscuro + acentos verde claro + botón ayuda amarillo
def inject_theme(dark=True):
    if dark:
        st.markdown("""
            <style>
            html, body, [class*="css"]  {
              background-color: #121212 !important;
              color: #FFFFFF !important;
              font-family: Inter, system-ui, -apple-system, Segoe UI, Roboto, "Helvetica Neue", Arial;
            }
            .stButton>button {
              border-radius: 12px;
              border: 2px solid #7CFFB2;
              background: #1E1E1E;
              color: #FFFFFF;
            }
            .stButton>button:hover {
              border-color: #B5FFD4;
              background: #2A2A2A;
            }
            .help-btn button{
              background: #FFD400 !important;
              color: #000 !important;
              border: 0 !important;
              font-weight: 700 !important;
            }
            .accent{
              border: 1px solid #7CFFB2 !important;
              border-radius: 12px;
              padding: 8px 12px;
            }
            </style>
        """, unsafe_allow_html=True)
    else:
        st.markdown("""
            <style>
            html, body, [class*="css"]  {
              background-color: #FAFAFA !important;
              color: #111 !important;
              font-family: Inter, system-ui, -apple-system, Segoe UI, Roboto, "Helvetica Neue", Arial;
            }
            .stButton>button {
              border-radius: 12px;
              border: 2px solid #2ecc71;
              background: #FFFFFF;
              color: #111;
            }
            .stButton>button:hover {
              border-color: #35d47a;
              background: #F3FFF8;
            }
            .help-btn button{
              background: #FFD400 !important;
              color: #000 !important;
              border: 0 !important;
              font-weight: 700 !important;
            }
            .accent{
              border: 1px solid #2ecc71 !important;
              border-radius: 12px;
              padding: 8px 12px;
            }
            </style>
        """, unsafe_allow_html=True)

inject_theme(dark=True)

# Branding fijo (solo en la app, NO va al PDF)
st.title("🏠 Presupuestos – Arqui-Pro")
st.caption("Sistema profesional de presupuestos para construcción y remodelación – by Arqui-Díaz")

# ---------------------------
# CONEXIÓN GOOGLE SHEETS (REGISTRO)
# ---------------------------
SHEET_URL = "https://docs.google.com/spreadsheets/d/1FzV4o3uQafKohDbil0kzfJBHaxmH2QKvOL2MC6gxGE0/edit?usp=sharing"
SCOPE = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]

def get_gsheet():
    try:
        creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=SCOPE)
        client = gspread.authorize(creds)
        sh = client.open_by_url(SHEET_URL)
        ws = sh.sheet1  # Hoja 1: "Usuarios registrados" con columnas: Nombre y Apellido | WhatsApp | Email | Fecha/Hora
        return ws
    except Exception as e:
        st.error("❌ Error conectando a Google Sheets. Revisa `Secrets` y comparte la hoja con el Service Account.")
        st.stop()

# ---------------------------
# ESTADO INICIAL
# ---------------------------
if "registered" not in st.session_state:
    st.session_state.registered = False
if "view" not in st.session_state:
    st.session_state.view = None
if "rubros" not in st.session_state:
    # Plantilla inicial vivienda media-baja (Quito) con cantidades=0
    data = [
        # CODIGO, DESCRIPCION, UNIDAD, PRECIO_UNITARIO_USD, CATEGORIA, INCERTIDUMBRE, SUPUESTO_NOTAS, FUENTE, FECHA_ACTUALIZACION
        ["DEM-001","Limpieza y trazo de terreno","m²",0.80,"Demoliciones/Preparación","Baja","Terreno accesible, sin escombros previos","Ref. local","2025-08-31"],
        ["MOV-001","Excavación manual zanjas cimentación","m³",10.50,"Cimentación","Media","Suelo tipo II, sin agua","Ref. local","2025-08-31"],
        ["CIM-001","Cimentación corrida hormigón ciclópeo","m³",85.00,"Cimentación","Media","Dosificación 120 kg, piedra disponible","Ref. local","2025-08-31"],
        ["EST-001","Columna de hormigón armado f'c=210 kg/cm²","m³",165.00,"Estructura","Media","Acero #3-#5, cimbras reutilizables","Ref. local","2025-08-31"],
        ["EST-002","Viga/Cadena de amarre f'c=210 kg/cm²","m³",160.00,"Estructura","Media","Longitudes regulares","Ref. local","2025-08-31"],
        ["EST-003","Losa maciza de hormigón armado 12 cm","m²",24.00,"Estructura","Media","Espesor 12 cm, malla 6-6/10-10","Ref. local","2025-08-31"],
        ["MAN-001","Muro bloque cemento 15 cm","m²",18.50,"Mampostería","Media","Bloque estándar, mortero 1:4","Ref. local","2025-08-31"],
        ["MAN-002","Tabique interior bloque 10 cm","m²",16.00,"Mampostería","Media","Altura ≤ 2.6 m","Ref. local","2025-08-31"],
        ["INS-001","Instalación sanitaria baño completo","ud",320.00,"Instalaciones","Alta","Incluye tuberías y aparatos básicos","Ref. local","2025-08-31"],
        ["INS-002","Instalación eléctrica vivienda tipo (hasta 60 m²)","ud",380.00,"Instalaciones","Alta","Canalización y tablero básico","Ref. local","2025-08-31"],
        ["ACB-001","Piso cerámico económico","m²",11.50,"Acabados","Media","Incluye adhesivo, junta","Ref. local","2025-08-31"],
        ["ACB-002","Revestimiento cerámico pared (baño/cocina)","m²",13.50,"Acabados","Media","Altura 1.50 m","Ref. local","2025-08-31"],
        ["ACB-003","Enlucido y pintura interior","m²",6.80,"Acabados","Media","Pintura látex estándar","Ref. local","2025-08-31"],
        ["ACB-004","Pintura exterior","m²",7.50,"Acabados","Media","Sellador + 2 manos","Ref. local","2025-08-31"],
        ["CAR-001","Puerta metálica simple","ud",140.00,"Carpintería/Cerrajería","Alta","Incluye bisagras y cerradura simple","Ref. local","2025-08-31"],
        ["CAR-002","Ventana metálica c/vidrio 1.20x1.00","ud",120.00,"Carpintería/Cerrajería","Media","Perfilería liviana","Ref. local","2025-08-31"],
        ["CBT-001","Estructura metálica para cubierta liviana","m²",18.00,"Cubierta","Media","Luz corta","Ref. local","2025-08-31"],
        ["CBT-002","Cubierta teja fibrocemento","m²",12.00,"Cubierta","Media","Incluye fijaciones","Ref. local","2025-08-31"],
        ["IMP-001","Impermeabilización losa expuesta","m²",9.50,"Impermeabilización","Alta","Membrana asfáltica 3 mm","Ref. local","2025-08-31"],
        ["EXT-001","Cerramiento perimetral en bloque","m²",19.00,"Exteriores","Media","Altura 2.00 m","Ref. local","2025-08-31"],
        ["EXT-002","Acceso peatonal hormigón simple","m²",10.00,"Exteriores","Baja","Espesor 8 cm","Ref. local","2025-08-31"],
    ]
    df = pd.DataFrame(data, columns=[
        "CODIGO","DESCRIPCION","UNIDAD","PRECIO_UNITARIO_USD","CATEGORIA","INCERTIDUMBRE","SUPUESTO_NOTAS","FUENTE","FECHA_ACTUALIZACION"
    ])
    df["CANTIDAD"] = 0.0
    st.session_state.rubros = df

if "materiales" not in st.session_state:
    st.session_state.materiales = pd.DataFrame(columns=["CODIGO","DESCRIPCION","UNIDAD","PRECIO_UNITARIO_USD","FUENTE","FECHA_ACTUALIZACION"])

if "mano_obra" not in st.session_state:
    st.session_state.mano_obra = pd.DataFrame(columns=["CODIGO","DESCRIPCION","UNIDAD","COSTO_UNITARIO_USD","RENDIMIENTO","FUENTE","FECHA_ACTUALIZACION"])

if "herramientas" not in st.session_state:
    st.session_state.herramientas = pd.DataFrame(columns=["CODIGO","DESCRIPCION","UNIDAD","TARIFA_USO_USD","FUENTE","FECHA_ACTUALIZACION"])

if "presupuestos" not in st.session_state:
    st.session_state.presupuestos = {}  # nombre -> DataFrame de rubros


# ---------------------------
# FORMULARIO DE REGISTRO
# ---------------------------
def show_register():
    st.markdown("### Registro de acceso (obligatorio)")
    with st.form("registro_form"):
        nombre = st.text_input("Nombre y Apellido *")
        whatsapp = st.text_input("WhatsApp *")
        email = st.text_input("Email (opcional)")
        submitted = st.form_submit_button("Ingresar")

        if submitted:
            if not nombre.strip() or not whatsapp.strip():
                st.error("⚠️ Nombre y WhatsApp son obligatorios.")
                st.stop()
            ws = get_gsheet()
            fecha = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            ws.append_row([nombre, whatsapp, email, fecha])
            st.session_state.registered = True
            st.success("✅ Registro exitoso. Bienvenido a Arqui-Pro.")

if not st.session_state.registered:
    show_register()

# ---------------------------
# MENÚ PRINCIPAL
# ---------------------------
if st.session_state.registered:
    # Modo claro/oscuro (opcional)
    with st.sidebar:
        st.markdown("### Apariencia")
        modo = st.radio("Tema", ["Oscuro", "Claro"], index=0)
        if modo == "Oscuro":
            inject_theme(dark=True)
        else:
            inject_theme(dark=False)

    st.markdown("## 📌 Menú Principal")
    c1, c2, c3 = st.columns(3)
    c4, c5, c6 = st.columns(3)

    if c1.button("📋 Rubros", use_container_width=True):
        st.session_state.view = "rubros"
    if c2.button("🧱 Materiales", use_container_width=True):
        st.session_state.view = "materiales"
    if c3.button("👷 Mano de Obra", use_container_width=True):
        st.session_state.view = "mano"
    if c4.button("🛠️ Herramientas", use_container_width=True):
        st.session_state.view = "herr"
    if c5.button("➕ Crear Presupuesto", use_container_width=True):
        st.session_state.view = "presu"
    c6.markdown('<div class="help-btn">', unsafe_allow_html=True)
    if c6.button("❓ Ayuda", use_container_width=True):
        st.session_state.view = "ayuda"
    c6.markdown('</div>', unsafe_allow_html=True)

    st.markdown("---")

    # ------------ VISTAS ------------
    def vista_rubros():
        st.subheader("📋 Rubros (globales)")
        st.info("Edita cantidades y precios. Cantidades iniciales = 0.")
        df = st.session_state.rubros.copy()
        df["SUBTOTAL"] = (df["CANTIDAD"] * df["PRECIO_UNITARIO_USD"]).round(2)
        edited = st.data_editor(df, num_rows="dynamic", use_container_width=True)
        st.session_state.rubros = edited.drop(columns=["SUBTOTAL"])
        st.success("Cambios guardados en tu sesión.")

        with st.expander("➕ Crear rubro nuevo"):
            colA, colB, colC = st.columns(3)
            codigo = colA.text_input("Código")
            desc = colB.text_input("Descripción")
            unidad = colC.text_input("Unidad (m², m³, ud, ml)")
            colD, colE, colF = st.columns(3)
            precio = colD.number_input("Precio unitario (USD)", min_value=0.0, step=0.1)
            categoria = colE.text_input("Categoría")
            incertid = colF.selectbox("Incertidumbre", ["Baja","Media","Alta"], index=1)
            colG, colH, colI = st.columns(3)
            supuesto = colG.text_input("Supuesto/Notas")
            fuente = colH.text_input("Fuente")
            fecha = colI.date_input("Fecha actualización")
            if st.button("Agregar rubro"):
                if not codigo or not desc or not unidad:
                    st.error("Código, descripción y unidad son obligatorios.")
                else:
                    new = {
                        "CODIGO":codigo,"DESCRIPCION":desc,"UNIDAD":unidad,
                        "PRECIO_UNITARIO_USD":precio,"CATEGORIA":categoria or "Otros",
                        "INCERTIDUMBRE":incertid,"SUPUESTO_NOTAS":supuesto,
                        "FUENTE":fuente,"FECHA_ACTUALIZACION":str(fecha),"CANTIDAD":0.0
                    }
                    st.session_state.rubros = pd.concat([st.session_state.rubros, pd.DataFrame([new])], ignore_index=True)
                    st.success("Rubro agregado.")

    def vista_materiales():
        st.subheader("🧱 Materiales")
        df = st.session_state.materiales.copy()
        edited = st.data_editor(df, num_rows="dynamic", use_container_width=True)
        st.session_state.materiales = edited
        with st.expander("➕ Crear material"):
            colA, colB, colC = st.columns(3)
            codigo = colA.text_input("Código mat.")
            desc = colB.text_input("Descripción mat.")
            unidad = colC.text_input("Unidad mat.")
            colD, colE = st.columns(2)
            precio = colD.number_input("Precio unitario (USD)", min_value=0.0, step=0.1)
            fuente = colE.text_input("Fuente")
            fecha = st.date_input("Fecha actualización")
            if st.button("Agregar material"):
                if not codigo or not desc or not unidad:
                    st.error("Código, descripción y unidad son obligatorios.")
                else:
                    new = {"CODIGO":codigo,"DESCRIPCION":desc,"UNIDAD":unidad,
                           "PRECIO_UNITARIO_USD":precio,"FUENTE":fuente,"FECHA_ACTUALIZACION":str(fecha)}
                    st.session_state.materiales = pd.concat([st.session_state.materiales, pd.DataFrame([new])], ignore_index=True)
                    st.success("Material agregado.")

    def vista_mano():
        st.subheader("👷 Mano de Obra")
        df = st.session_state.mano_obra.copy()
        edited = st.data_editor(df, num_rows="dynamic", use_container_width=True)
        st.session_state.mano_obra = edited
        with st.expander("➕ Crear mano de obra"):
            colA, colB, colC = st.columns(3)
            codigo = colA.text_input("Código MO")
            desc = colB.text_input("Descripción MO")
            unidad = colC.text_input("Unidad MO (jornal, h, m², etc.)")
            colD, colE = st.columns(2)
            costo = colD.number_input("Costo unitario (USD)", min_value=0.0, step=0.1)
            rend = colE.text_input("Rendimiento (opcional)")
            fuente = st.text_input("Fuente")
            fecha = st.date_input("Fecha actualización")
            if st.button("Agregar MO"):
                if not codigo or not desc or not unidad:
                    st.error("Código, descripción y unidad son obligatorios.")
                else:
                    new = {"CODIGO":codigo,"DESCRIPCION":desc,"UNIDAD":unidad,
                           "COSTO_UNITARIO_USD":costo,"RENDIMIENTO":rend,
                           "FUENTE":fuente,"FECHA_ACTUALIZACION":str(fecha)}
                    st.session_state.mano_obra = pd.concat([st.session_state.mano_obra, pd.DataFrame([new])], ignore_index=True)
                    st.success("Mano de obra agregada.")

    def vista_herr():
        st.subheader("🛠️ Herramientas / Equipos")
        df = st.session_state.herramientas.copy()
        edited = st.data_editor(df, num_rows="dynamic", use_container_width=True)
        st.session_state.herramientas = edited
        with st.expander("➕ Crear herramienta"):
            colA, colB, colC = st.columns(3)
            codigo = colA.text_input("Código eq.")
            desc = colB.text_input("Descripción eq.")
            unidad = colC.text_input("Unidad eq.")
            colD, colE = st.columns(2)
            tarifa = colD.number_input("Tarifa de uso (USD)", min_value=0.0, step=0.1)
            fuente = colE.text_input("Fuente")
            fecha = st.date_input("Fecha actualización")
            if st.button("Agregar herramienta"):
                if not codigo or not desc or not unidad:
                    st.error("Código, descripción y unidad son obligatorios.")
                else:
                    new = {"CODIGO":codigo,"DESCRIPCION":desc,"UNIDAD":unidad,
                           "TARIFA_USO_USD":tarifa,"FUENTE":fuente,"FECHA_ACTUALIZACION":str(fecha)}
                    st.session_state.herramientas = pd.concat([st.session_state.herramientas, pd.DataFrame([new])], ignore_index=True)
                    st.success("Herramienta agregada.")

    def make_pdf(budget_df, cliente_nombre, constructor_nombre, constructor_cel, constructor_dir, leyenda, logo_bytes):
        buffer = BytesIO()
        c = canvas.Canvas(buffer, pagesize=A4)
        width, height = A4

        # Logo opcional
        if logo_bytes is not None:
            try:
                img = ImageReader(logo_bytes)
                c.drawImage(img, width-140, height-100, width=120, height=60, preserveAspectRatio=True, mask='auto')
            except:
                pass

        # Encabezado simple
        c.setFont("Helvetica-Bold", 14)
        c.drawString(40, height-50, "Presupuesto de Obra")
        c.setFont("Helvetica", 10)
        c.drawString(40, height-70, f"Cliente: {cliente_nombre}")
        c.drawString(40, height-85, f"Fecha: {datetime.now().strftime('%Y-%m-%d')}")

        # Tabla
        y = height - 120
        headers = ["Código","Descripción","Unidad","Cant.","P.Unit (USD)","Subtotal (USD)"]
        colw = [60, 220, 50, 50, 80, 80]
        c.setFont("Helvetica-Bold", 9)
        x = 40
        for i, htxt in enumerate(headers):
            c.drawString(x, y, htxt)
            x += colw[i]
        y -= 12
        c.line(40, y, 40+sum(colw), y)
        y -= 8
        c.setFont("Helvetica", 8)

        total = 0.0
        for _, r in budget_df.iterrows():
            if y < 120:
                c.showPage()
                y = height - 80
            sub = float(r["CANTIDAD"]) * float(r["PRECIO_UNITARIO_USD"])
            total += sub
            vals = [
                r["CODIGO"],
                (r["DESCRIPCION"][:55] + "...") if len(r["DESCRIPCION"])>58 else r["DESCRIPCION"],
                r["UNIDAD"],
                f'{r["CANTIDAD"]:.2f}',
                f'{float(r["PRECIO_UNITARIO_USD"]):.2f}',
                f'{sub:.2f}'
            ]
            x = 40
            for i, v in enumerate(vals):
                c.drawString(x, y, str(v))
                x += colw[i]
            y -= 12

        # Resumen (los % ya vienen calculados afuera)
        y -= 10
        c.line(40, y, 40+sum(colw), y); y -= 6
        c.setFont("Helvetica-Bold", 10)
        c.drawRightString(40+sum(colw), y, f"Total: {total:.2f} USD"); y -= 20

        # Pie - datos constructor
        c.setFont("Helvetica", 9)
        c.drawString(40, 60, f"Constructor: {constructor_nombre}  |  Cel.: {constructor_cel}")
        if constructor_dir:
            c.drawString(40, 46, f"Dirección: {constructor_dir}")
        if leyenda:
            c.drawString(40, 32, f"Leyenda: {leyenda}")

        c.showPage()
        c.save()
        buffer.seek(0)
        return buffer

    def vista_presu():
        st.subheader("➕ Crear/Editar Presupuesto")
        # crear nuevo
        colA, colB = st.columns([2,1])
        nuevo = colA.text_input("Nombre del presupuesto (ej: Vivienda 60 m² – Cliente Pérez)")
        if colB.button("Crear presupuesto"):
            if not nuevo.strip():
                st.error("Pon un nombre.")
            else:
                st.session_state.presupuestos[nuevo] = st.session_state.rubros.copy()
                st.success(f"Presupuesto '{nuevo}' creado.")

        # seleccionar existente
        if st.session_state.presupuestos:
            nombres = list(st.session_state.presupuestos.keys())
            sel = st.selectbox("Presupuestos existentes", nombres)
            bcol1, bcol2 = st.columns(2)
            if bcol1.button("Eliminar presupuesto seleccionado"):
                st.session_state.presupuestos.pop(sel, None)
                st.warning("Presupuesto eliminado.")
                st.stop()

            st.markdown("#### Editar rubros del presupuesto")
            dfp = st.session_state.presupuestos[sel].copy()
            dfp["SUBTOTAL"] = (dfp["CANTIDAD"] * dfp["PRECIO_UNITARIO_USD"]).round(2)
            dfp = st.data_editor(dfp, num_rows="dynamic", use_container_width=True)
            # guardar cambios
            st.session_state.presupuestos[sel] = dfp.drop(columns=["SUBTOTAL"])

            # parámetros
            st.markdown("#### Parámetros de cálculo")
            col1, col2, col3, col4 = st.columns(4)
            pct_indirectos = col1.number_input("Indirectos (%)", 0.0, 100.0, 0.0, 0.5)
            pct_descuento  = col2.number_input("Descuento (%)", 0.0, 100.0, 0.0, 0.5)
            pct_iva        = col3.number_input("IVA (%)", 0.0, 100.0, 15.0, 0.5)
            pct_anticipo   = col4.number_input("Anticipo (%)", 0.0, 100.0, 0.0, 0.5)

            base = float((dfp["CANTIDAD"] * dfp["PRECIO_UNITARIO_USD"]).sum())
            indirectos = base * pct_indirectos/100
            subtotal = base + indirectos
            descuento = subtotal * pct_descuento/100
            neto = subtotal - descuento
            iva = neto * pct_iva/100
            total = neto + iva
            anticipo = total * pct_anticipo/100

            st.markdown("#### Totales")
            st.metric("Base (USD)", f"{base:,.2f}")
            st.metric("Indirectos (USD)", f"{indirectos:,.2f}")
            st.metric("Subtotal (USD)", f"{subtotal:,.2f}")
            st.metric("Descuento (USD)", f"{descuento:,.2f}")
            st.metric("Neto (USD)", f"{neto:,.2f}")
            st.metric("IVA (USD)", f"{iva:,.2f}")
            st.metric("TOTAL (USD)", f"{total:,.2f}")
            st.metric("Anticipo (USD)", f"{anticipo:,.2f}")

            st.markdown("---")
            st.markdown("#### Datos para PDF (cliente/constructor)")
            colA, colB = st.columns(2)
            cliente_nombre = colA.text_input("Nombre y Apellido del cliente (obligatorio en PDF)", "")
            constructor_nombre = colB.text_input("Nombre y Apellido del constructor *", "")
            constructor_cel = st.text_input("Celular del constructor *", "")
            colC, colD = st.columns(2)
            constructor_dir = colC.text_input("Dirección del constructor (opcional)", "")
            leyenda = colD.text_input("Leyenda corta (opcional, ej: Presupuesto válido 30 días)", "")
            logo = st.file_uploader("Logo opcional para PDF (png/jpg)", type=["png","jpg","jpeg"])

            if st.button("🖨️ Exportar PDF"):
                if not constructor_nombre.strip() or not constructor_cel.strip():
                    st.error("Nombre y Celular del constructor son obligatorios.")
                elif not cliente_nombre.strip():
                    st.error("Nombre del cliente es obligatorio.")
                else:
                    pdf = make_pdf(st.session_state.presupuestos[sel], cliente_nombre, constructor_nombre, constructor_cel, constructor_dir, leyenda, logo.read() if logo else None)
                    st.download_button("Descargar PDF", data=pdf, file_name=f"{sel.replace(' ','_')}.pdf", mime="application/pdf")
        else:
            st.info("Crea tu primer presupuesto usando el cuadro superior.")

        with st.expander("Si te falta un material/MO/herramienta, créalo aquí rápidamente"):
            t = st.tabs(["Material", "Mano de Obra", "Herramienta"])
            with t[0]:
                codigo = st.text_input("Código mat. (rápido)")
                desc = st.text_input("Descripción mat. (rápido)")
                unidad = st.text_input("Unidad mat. (rápido)")
                precio = st.number_input("Precio unitario (USD)", 0.0, step=0.1)
                if st.button("Guardar material"):
                    if codigo and desc and unidad:
                        new = {"CODIGO":codigo,"DESCRIPCION":desc,"UNIDAD":unidad,"PRECIO_UNITARIO_USD":precio,"FUENTE":"","FECHA_ACTUALIZACION":datetime.now().date().isoformat()}
                        st.session_state.materiales = pd.concat([st.session_state.materiales, pd.DataFrame([new])], ignore_index=True)
                        st.success("Material creado (base personal).")
                    else:
                        st.error("Completa código, descripción y unidad.")
            with t[1]:
                codigo = st.text_input("Código MO (rápido)")
                desc = st.text_input("Descripción MO (rápido)")
                unidad = st.text_input("Unidad MO (rápido)")
                costo = st.number_input("Costo unitario (USD)", 0.0, step=0.1, key="mo_costo")
                if st.button("Guardar MO"):
                    if codigo and desc and unidad:
                        new = {"CODIGO":codigo,"DESCRIPCION":desc,"UNIDAD":unidad,"COSTO_UNITARIO_USD":costo,"RENDIMIENTO":"","FUENTE":"","FECHA_ACTUALIZACION":datetime.now().date().isoformat()}
                        st.session_state.mano_obra = pd.concat([st.session_state.mano_obra, pd.DataFrame([new])], ignore_index=True)
                        st.success("Mano de obra creada (base personal).")
                    else:
                        st.error("Completa código, descripción y unidad.")
            with t[2]:
                codigo = st.text_input("Código eq. (rápido)")
                desc = st.text_input("Descripción eq. (rápido)")
                unidad = st.text_input("Unidad eq. (rápido)")
                tarifa = st.number_input("Tarifa uso (USD)", 0.0, step=0.1, key="eq_tarifa")
                if st.button("Guardar herramienta"):
                    if codigo and desc and unidad:
                        new = {"CODIGO":codigo,"DESCRIPCION":desc,"UNIDAD":unidad,"TARIFA_USO_USD":tarifa,"FUENTE":"","FECHA_ACTUALIZACION":datetime.now().date().isoformat()}
                        st.session_state.herramientas = pd.concat([st.session_state.herramientas, pd.DataFrame([new])], ignore_index=True)
                        st.success("Herramienta creada (base personal).")
                    else:
                        st.error("Completa código, descripción y unidad.")

    def vista_ayuda():
        st.subheader("📖 Ayuda rápida")
        st.markdown("""
        1) Regístrate con **Nombre + WhatsApp** (Email opcional).  
        2) Usa los **5 botones** para gestionar Rubros, Materiales, Mano de Obra, Herramientas y **Crear Presupuesto**.  
        3) En **Crear Presupuesto**, edita cantidades y precios. Los totales se calculan solos.  
        4) Exporta a **PDF** y agrega **tu logo** si quieres.  
        """)
        st.download_button("Descargar guía PDF (próxima versión)", data=b"Proximamente", file_name="Guia_ArquiPro.pdf")

    if st.session_state.view == "rubros":
        vista_rubros()
    elif st.session_state.view == "materiales":
        vista_materiales()
    elif st.session_state.view == "mano":
        vista_mano()
    elif st.session_state.view == "herr":
        vista_herr()
    elif st.session_state.view == "presu":
        vista_presu()
    elif st.session_state.view == "ayuda":
        vista_ayuda()
    else:
        st.info("Usa los botones de arriba para comenzar.")
  
