import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime
import io

# Configuración de página
st.set_page_config(page_title="Agente IA - Planificación Financiera | UCEMA", page_icon="📈", layout="wide")

# Estilos visuales
st.markdown("""
<style>
    .main-header {font-size: 2rem; font-weight: 700; color: #1B365D; margin-bottom: 0.2rem;}
    .sub-header {font-size: 1.05rem; color: #4A5568; margin-bottom: 1.5rem;}
    .step-box {background-color: #F7FAFC; border-left: 4px solid #1B365D; padding: 12px 16px; margin-bottom: 12px; border-radius: 4px;}
    .guardrail-ok {background-color: #F0FFF4; border-left: 4px solid #38A169; padding: 10px 14px; margin-bottom: 8px; border-radius: 4px; color: #22543D;}
    .guardrail-warn {background-color: #FFFBEB; border-left: 4px solid #D97706; padding: 10px 14px; margin-bottom: 8px; border-radius: 4px; color: #78350F;}
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="main-header">Agente de Diagnóstico y Rebalanceo Patrimonial con IA</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-header">Trabajo Práctico Final — Planificación Financiera y Finanzas Corporativas con IA</div>', unsafe_allow_html=True)

# ------------------------------------------------------------------------------
# BASE DE DATOS MAESTRA DE ACTIVOS (Mercado)
# ------------------------------------------------------------------------------
# Esta base de datos evita que el cliente/asesor tenga que calcular TIR, duration y pesos.
datos_mercado = {
    "Ticker": ["FCI-MM", "YMCXO", "MGCMO", "PN32O", "BPOD4", "SPY", "QQQ", "VIST"],
    "Activo": ["FCI Money Market USD", "ON YPF 2031 HD", "ON Pampa Energía 2031 HD", "ON PAE 2032 HD", "BOPREAL Serie 4", "CEDEAR S&P 500", "CEDEAR Nasdaq 100", "CEDEAR Vista Energy"],
    "Clase": ["Liquidez", "Renta Fija Corporativa", "Renta Fija Corporativa", "Renta Fija Corporativa", "Renta Fija Soberana", "Renta Variable", "Renta Variable", "Renta Variable"],
    "Emisor": ["FCI Liquidez", "YPF S.A.", "Pampa Energía", "Pan American Energy", "BCRA", "ETF S&P 500", "ETF Nasdaq 100", "Vista Energy"],
    "Es_Corporativo": [False, True, True, True, False, False, False, True],
    "TIR_USD": [2.50, 8.40, 8.20, 8.00, 9.60, 9.50, 10.50, 11.50],
    "Mod_Duration": [0.05, 4.20, 4.10, 4.50, 2.30, 0.00, 0.00, 0.00],
    "Peso_Moderado": [0.05, 0.15, 0.15, 0.15, 0.20, 0.15, 0.10, 0.05],
    "Peso_Conservador": [0.20, 0.10, 0.15, 0.15, 0.25, 0.15, 0.0, 0.0],
    "Peso_Agresivo": [0.0, 0.15, 0.10, 0.10, 0.15, 0.20, 0.20, 0.10]
}
df_master = pd.DataFrame(datos_mercado)

# ------------------------------------------------------------------------------
# BARRA LATERAL
# ------------------------------------------------------------------------------
with st.sidebar:
    st.header("📂 1. Cargar Cartera Cliente")
    st.caption("Subí un Excel con solo 2 columnas: Ticker y Tenencia_Actual_USD")
    archivo_cliente = st.file_uploader("Subir posiciones (.xlsx)", type=["xlsx"])
    
    st.divider()
    st.header("⚙️ 2. Configuración del Agente")
    modo_ia = st.radio("Motor de Redacción:", ["Simulación Determinística", "API Google Gemini (En Vivo)"])
    api_key = ""
    if modo_ia == "API Google Gemini (En Vivo)":
        default_key = st.secrets.get("GEMINI_API_KEY", "") if hasattr(st, "secrets") else ""
        api_key = st.text_input("Ingresar Gemini API Key:", value=default_key, type="password")

    st.divider()
    st.header("👤 3. Política de Inversión")
    cliente_nombre = st.text_input("Nombre del Cliente", value="Caso Testigo UCEMA")
    perfil_riesgo = st.selectbox("Perfil de Riesgo", ["Moderado", "Conservador", "Agresivo"], index=0)

    # Restricciones
    if perfil_riesgo == "Conservador":
        t_min, md_max, max_emi, max_rv = 6.5, 2.5, 15.0, 15.0
    elif perfil_riesgo == "Moderado":
        t_min, md_max, max_emi, max_rv = 8.0, 3.5, 20.0, 35.0
    else:
        t_min, md_max, max_emi, max_rv = 9.0, 5.0, 25.0, 60.0

    tir_objetivo = st.number_input("TIR / Retorno Mínimo (%)", value=t_min, step=0.25)
    md_maxima = st.number_input("Duration Máxima (Años)", value=md_max, step=0.25)
    limite_emisor = st.number_input("Máx. por Emisor Corp. (%)", value=max_emi, step=1.0)
    limite_rv = st.number_input("Tope Renta Variable (%)", value=max_rv, step=5.0)
    liquidez_min = st.number_input("Liquidez Mínima (%)", value=5.0, step=1.0)

# ------------------------------------------------------------------------------
# PANTALLA INICIAL / DESCARGA DE PLANTILLA MINIMALISTA
# ------------------------------------------------------------------------------
if archivo_cliente is None:
    st.info("👋 **¡Bienvenido!** Por favor subí el Excel del cliente. El sistema cruzará automáticamente los Tickers con nuestra base de mercado (TIR, Duration y Modelos) para calcular la propuesta.")
    
    @st.cache_data
    def get_minimal_template():
        # Plantilla simplificada: Solo Ticker y Monto
        df_t = pd.DataFrame({
            "Ticker": ["FCI-MM", "YMCXO", "MGCMO", "PN32O", "BPOD4", "SPY", "QQQ", "VIST"],
            "Tenencia_Actual_USD": [90000.0, 80000.0, 0.0, 0.0, 0.0, 30000.0, 0.0, 0.0]
        })
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
            df_t.to_excel(writer, index=False, sheet_name="Posiciones")
        return output.getvalue()
    
    st.download_button("📥 Descargar Plantilla Simple de Excel", data=get_minimal_template(), file_name="Cartera_Simple.xlsx")
    st.stop()

# ------------------------------------------------------------------------------
# PROCESAMIENTO INTELIGENTE DEL EXCEL
# ------------------------------------------------------------------------------
try:
    df_upload = pd.read_excel(archivo_cliente)
    # Validar columnas
    if "Ticker" not in df_upload.columns or "Tenencia_Actual_USD" not in df_upload.columns:
        st.error("❌ El archivo debe contener exactamente las columnas: 'Ticker' y 'Tenencia_Actual_USD'")
        st.stop()
        
    # Agrupar por ticker por si hay repetidos
    df_upload = df_upload.groupby("Ticker", as_index=False)["Tenencia_Actual_USD"].sum()
    
    # Merge con la base maestra de mercado (LEFT JOIN desde la base maestra para tener todos los activos del modelo)
    df_calc = pd.merge(df_master, df_upload, on="Ticker", how="left")
    df_calc["Tenencia_Actual_USD"] = df_calc["Tenencia_Actual_USD"].fillna(0.0)
    
    # Asignar peso objetivo según perfil
    col_peso = f"Peso_{perfil_riesgo}"
    df_calc["Peso_Objetivo_Sugerido"] = df_calc[col_peso]
    
except Exception as e:
    st.error(f"Error procesando el archivo: {e}")
    st.stop()

def calcular_metricas(df, col_monto):
    total = df[col_monto].sum()
    pesos = df[col_monto] / total if total > 0 else 0
    return {
        "capital": total,
        "suma_pesos": float(pesos.sum() * 100),
        "tir": float((pesos * df["TIR_USD"]).sum()),
        "duration": float((pesos * df["Mod_Duration"]).sum()),
        "ingreso": float((df[col_monto] * (df["TIR_USD"] / 100)).sum()),
        "max_corp": float((pesos[df["Es_Corporativo"]]).max() * 100) if any(df["Es_Corporativo"]) else 0,
        "liq": float((pesos[df["Clase"].str.contains("Liquidez", case=False)]).sum() * 100),
        "rv": float((pesos[df["Clase"].str.contains("Renta Variable", case=False)]).sum() * 100)
    }

tab1, tab2, tab3 = st.tabs(["🤖 1. Ejecución del Agente", "🛡️ 2. Consistencia y Guardrails", "📊 3. ROI"])

with tab1:
    st.markdown('<div class="step-box"><b>Arquitectura:</b> 1) Carga simplificada &rarr; 2) Cruce automático con Base de Mercado &rarr; 3) Diagnóstico y Propuesta &rarr; 4) Aprobación Asesor &rarr; 5) IA Memo</div>', unsafe_allow_html=True)
    
    cap_ini = df_calc["Tenencia_Actual_USD"].sum()
    if cap_ini <= 0:
        st.error("El capital total de la cartera inicial debe ser mayor a 0.")
        st.stop()
        
    met_ini = calcular_metricas(df_calc, "Tenencia_Actual_USD")
    
    st.subheader("Paso 1 y 2: Diagnóstico Cuantitativo")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Capital", f"USD {met_ini['capital']:,.0f}")
    c2.metric("TIR Actual", f"{met_ini['tir']:.2f}%", f"{met_ini['tir'] - tir_objetivo:+.2f}% vs Obj")
    c3.metric("Duration", f"{met_ini['duration']:.2f}a", f"RV: {met_ini['rv']:.0f}%", delta_color="off")
    c4.metric("Máx Concentración", f"{met_ini['max_corp']:.1f}%", f"Límite {limite_emisor:.0f}%", delta_color="inverse" if met_ini['max_corp'] > limite_emisor else "normal")

    st.divider()
    st.subheader("Paso 3 y 4: Motor de Rebalanceo e Intervención Humana")
    
    col1, col2 = st.columns([1, 2])
    pesos_aj = []
    with col1:
        st.markdown("**Ajuste Dinámico (%)**")
        for i, r in df_calc.iterrows():
            val = st.slider(f"{r['Ticker']}", 0.0, 100.0, float(r["Peso_Objetivo_Sugerido"]*100), 1.0)
            pesos_aj.append(val / 100)
            
    df_calc["Peso_Prop_%"] = [p * 100 for p in pesos_aj]
    df_calc["Tenencia_Prop_USD"] = df_calc["Peso_Prop_%"] / 100 * cap_ini
    df_calc["Orden_USD"] = df_calc["Tenencia_Prop_USD"] - df_calc["Tenencia_Actual_USD"]
    df_calc["Accion"] = df_calc["Orden_USD"].apply(lambda x: "COMPRAR" if x>1 else ("VENDER" if x<-1 else "MANTENER"))
    
    met_prop = calcular_metricas(df_calc, "Tenencia_Prop_USD")
    flujo = float(df_calc["Orden_USD"].sum())
    
    with col2:
        st.markdown("**Cuadro de Órdenes y Mercado**")
        st.dataframe(df_calc[["Ticker", "TIR_USD", "Mod_Duration", "Tenencia_Actual_USD", "Orden_USD", "Peso_Prop_%"]].style.format({
            "TIR_USD":"{:.2f}%", "Mod_Duration":"{:.2f}", "Tenencia_Actual_USD":"USD {:,.0f}", "Orden_USD":"USD {:+,.0f}", "Peso_Prop_%":"{:.1f}%"
        }), hide_index=True)
        
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("TIR Propuesta", f"{met_prop['tir']:.2f}%")
        m2.metric("Duration", f"{met_prop['duration']:.2f}a")
        m3.metric("Flujo Neto Caja", f"USD {abs(flujo):.0f}")
        m4.metric("CEDEARs", f"{met_prop['rv']:.1f}%")

    # Controles
    ok = (abs(met_prop["suma_pesos"] - 100) < 0.1) and (abs(flujo) < 1) and (met_prop["max_corp"] <= limite_emisor) and (met_prop["duration"] <= md_maxima) and (met_prop["tir"] >= tir_objetivo) and (met_prop["liq"] >= liquidez_min) and (met_prop["rv"] <= limite_rv)
    
    if not ok:
        st.error(f"⛔ BLOQUEO: Suma {met_prop['suma_pesos']:.1f}% | Máx Emisor {met_prop['max_corp']:.1f}% | RV {met_prop['rv']:.1f}% | TIR {met_prop['tir']:.2f}% | Dur {met_prop['duration']:.2f}")
    else:
        st.success("✅ Controles Superados (100%).")
        
    notas = st.text_input("Comentarios del Asesor:")
    aprob = st.checkbox("Autorizo generar Investment Memo.", disabled=not ok)
    
    if st.button("🚀 Ejecutar Paso 5", disabled=not (aprob and ok)):
        ords = "\n".join([f"- {r['Accion']} USD {abs(r['Orden_USD']):,.0f} en {r['Ticker']} -> {r['Peso_Prop_%']:.1f}%" for _, r in df_calc.iterrows() if r["Accion"] != "MANTENER"])
        memo = ""
        if modo_ia == "API Google Gemini (En Vivo)" and api_key:
            try:
                import google.generativeai as genai
                genai.configure(api_key=api_key)
                model = genai.GenerativeModel("gemini-pro")
                memo = model.generate_content(f"Sos un Asesor Senior. Redactá un Memo Ejecutivo para '{cliente_nombre}' (Perfil {perfil_riesgo}). Usa: TIR {met_prop['tir']:.2f}%, Duration {met_prop['duration']:.2f}a, CEDEARs {met_prop['rv']:.1f}%. Órdenes: {ords}. Notas: {notas}").text
            except:
                st.warning("Fallo API. Usando motor de respaldo.")
        if not memo:
            memo = f"### REBALANCEO - {cliente_nombre}\n**TIR:** {met_prop['tir']:.2f}% | **Duration:** {met_prop['duration']:.2f}a\n{ords}\n**Notas:** {notas}"
        st.info(memo)

with tab2:
    st.table(pd.DataFrame([
        {"Control": "Suma Ponderaciones", "Estado": "✅" if abs(met_prop["suma_pesos"] - 100) < 0.1 else "❌"},
        {"Control": f"TIR Mínima ({tir_objetivo}%)", "Estado": "✅" if met_prop["tir"] >= tir_objetivo else "❌"},
        {"Control": f"Duration Máx ({md_maxima} a)", "Estado": "✅" if met_prop["duration"] <= md_maxima else "❌"},
        {"Control": f"Max Emisor ({limite_emisor}%)", "Estado": "✅" if met_prop["max_corp"] <= limite_emisor else "❌"},
        {"Control": f"Max CEDEARs ({limite_rv}%)", "Estado": "✅" if met_prop["rv"] <= limite_rv else "❌"}
    ]))
with tab3:
    st.metric("Ahorro de Tiempo", "85%", "-57 minutos")
