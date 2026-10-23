import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime
import io

# Configuración de página
st.set_page_config(
    page_title="Agente IA - Planificación Financiera | UCEMA",
    page_icon="📈",
    layout="wide"
)

# Estilos visuales personalizados
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
# BARRA LATERAL: CONFIGURACIÓN DEL AGENTE Y CARGA DE EXCEL
# ------------------------------------------------------------------------------
with st.sidebar:
    st.header("📂 1. Cargar Cartera Cliente")
    archivo_cliente = st.file_uploader("Subir tenencia del cliente (.xlsx)", type=["xlsx"])
    
    st.divider()
    st.header("⚙️ 2. Configuración del Agente")
    modo_ia = st.radio(
        "Motor de Redacción del Agente:",
        ["Simulación Determinística (Demo en Vivo)", "API Google Gemini (En Vivo)"],
        help="El modo Simulación garantiza ejecución instantánea sin requerir API Key."
    )
    api_key = ""
    if modo_ia == "API Google Gemini (En Vivo)":
        default_key = st.secrets.get("GEMINI_API_KEY", "") if hasattr(st, "secrets") else ""
        api_key = st.text_input("Ingresar Gemini API Key:", value=default_key, type="password")

    st.divider()
    st.header("👤 3. Política de Inversión")
    cliente_nombre = st.text_input("Nombre del Cliente", value="Caso Testigo UCEMA")
    perfil_riesgo = st.selectbox("Perfil de Riesgo", ["Moderado", "Conservador", "Agresivo"], index=0)

    # Restricciones duras según perfil
    if perfil_riesgo == "Conservador":
        tir_min_default, md_max_default, max_emisor_default, max_rv_default = 6.5, 2.5, 15.0, 15.0
    elif perfil_riesgo == "Moderado":
        tir_min_default, md_max_default, max_emisor_default, max_rv_default = 8.0, 3.5, 20.0, 35.0
    else:
        tir_min_default, md_max_default, max_emisor_default, max_rv_default = 9.0, 5.0, 25.0, 60.0

    tir_objetivo = st.number_input("TIR / Retorno Mínimo Objetivo (% USD)", value=tir_min_default, step=0.25)
    md_maxima = st.number_input("Modified Duration Máxima Cartera (Años)", value=md_max_default, step=0.25)
    limite_emisor = st.number_input("Límite Máximo por Emisor Corp. (%)", value=max_emisor_default, step=1.0)
    limite_rv = st.number_input("Tope Máximo Renta Variable / CEDEARs (%)", value=max_rv_default, step=5.0)
    liquidez_min = st.number_input("Liquidez Mínima Requerida (%)", value=5.0, step=1.0)

# ------------------------------------------------------------------------------
# PANTALLA DE BIENVENIDA SI NO HAY ARCHIVO
# ------------------------------------------------------------------------------
if archivo_cliente is None:
    st.info("👋 **¡Bienvenido a la plataforma!** Para comenzar, por favor subí el archivo Excel con la cartera del cliente desde la barra lateral izquierda.")
    st.write("Si no tenés un archivo a mano para la demostración, podés descargar la plantilla de caso de prueba acá abajo, modificar los montos si querés, y luego subirla:")
    
    # Generar el archivo excel en memoria para descarga
    @st.cache_data
    def get_template_excel():
        data_temp = [
            {"Ticker": "FCI-MM", "Activo": "FCI Money Market USD", "Clase": "Liquidez", "Emisor": "FCI Liquidez", "Es_Corporativo": False, "TIR_USD": 2.50, "Mod_Duration": 0.05, "Tenencia_Actual_USD": 90000.0, "Peso_Objetivo_Sugerido": 0.05},
            {"Ticker": "YMCXO", "Activo": "ON YPF 2031 Hard Dollar (Tramo Largo)", "Clase": "Renta Fija Corporativa", "Emisor": "YPF S.A.", "Es_Corporativo": True, "TIR_USD": 8.40, "Mod_Duration": 4.20, "Tenencia_Actual_USD": 80000.0, "Peso_Objetivo_Sugerido": 0.15},
            {"Ticker": "MGCMO", "Activo": "ON Pampa Energía 2031 HD (Tramo Largo)", "Clase": "Renta Fija Corporativa", "Emisor": "Pampa Energía S.A.", "Es_Corporativo": True, "TIR_USD": 8.20, "Mod_Duration": 4.10, "Tenencia_Actual_USD": 0.0, "Peso_Objetivo_Sugerido": 0.15},
            {"Ticker": "PN32O", "Activo": "ON Pan American Energy 2032 HD (Tramo Largo)", "Clase": "Renta Fija Corporativa", "Emisor": "Pan American Energy", "Es_Corporativo": True, "TIR_USD": 8.00, "Mod_Duration": 4.50, "Tenencia_Actual_USD": 0.0, "Peso_Objetivo_Sugerido": 0.15},
            {"Ticker": "BPOD4", "Activo": "BOPREAL Serie 4 (BCRA)", "Clase": "Renta Fija Soberana/BCRA", "Emisor": "BCRA", "Es_Corporativo": False, "TIR_USD": 9.60, "Mod_Duration": 2.30, "Tenencia_Actual_USD": 0.0, "Peso_Objetivo_Sugerido": 0.20},
            {"Ticker": "SPY", "Activo": "CEDEAR S&P 500 ETF (Core US)", "Clase": "Renta Variable (CEDEAR)", "Emisor": "ETF S&P 500 Diversificado", "Es_Corporativo": False, "TIR_USD": 9.50, "Mod_Duration": 0.00, "Tenencia_Actual_USD": 30000.0, "Peso_Objetivo_Sugerido": 0.15},
            {"Ticker": "QQQ", "Activo": "CEDEAR Nasdaq 100 ETF (Growth Tech)", "Clase": "Renta Variable (CEDEAR)", "Emisor": "ETF Nasdaq 100", "Es_Corporativo": False, "TIR_USD": 10.50, "Mod_Duration": 0.00, "Tenencia_Actual_USD": 0.0, "Peso_Objetivo_Sugerido": 0.10},
            {"Ticker": "VIST", "Activo": "CEDEAR Vista Energy (Equity Energía)", "Clase": "Renta Variable (CEDEAR)", "Emisor": "Vista Energy S.A.B.", "Es_Corporativo": True, "TIR_USD": 11.50, "Mod_Duration": 0.00, "Tenencia_Actual_USD": 0.0, "Peso_Objetivo_Sugerido": 0.05}
        ]
        df_t = pd.DataFrame(data_temp)
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
            df_t.to_excel(writer, index=False, sheet_name="Cartera")
        return output.getvalue()
    
    st.download_button(
        label="📥 Descargar Plantilla Excel de Ejemplo",
        data=get_template_excel(),
        file_name="Cartera_Inicial_Cliente.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    st.stop()

# ------------------------------------------------------------------------------
# LECTURA DE DATOS DESDE EL EXCEL SUBIDO
# ------------------------------------------------------------------------------
try:
    df_base = pd.read_excel(archivo_cliente)
    # Rellenar nulos
    df_base.fillna({'Tenencia_Actual_USD': 0.0, 'Peso_Objetivo_Sugerido': 0.0}, inplace=True)
except Exception as e:
    st.error(f"Error al leer el archivo Excel. Asegurate de usar el formato correcto. Detalle: {e}")
    st.stop()

# ------------------------------------------------------------------------------
# HERRAMIENTA 1 Y 2 DEL AGENTE: MOTOR FINANCIERO DETERMINÍSTICO
# ------------------------------------------------------------------------------
def calcular_metricas_cartera(df, col_monto):
    total_usd = df[col_monto].sum()
    pesos = df[col_monto] / total_usd if total_usd > 0 else 0
    tir_pond = float((pesos * df["TIR_USD"]).sum())
    md_pond = float((pesos * df["Mod_Duration"]).sum())
    ingreso_anual = float((df[col_monto] * (df["TIR_USD"] / 100.0)).sum())
    max_corp_peso = float((pesos[df["Es_Corporativo"]]).max() * 100.0) if any(df["Es_Corporativo"]) else 0.0
    liq_peso = float((pesos[df["Clase"].astype(str).str.contains("Liquidez", case=False)]).sum() * 100.0)
    rv_peso = float((pesos[df["Clase"].astype(str).str.contains("Renta Variable", case=False)]).sum() * 100.0)
    return {
        "capital_total": total_usd,
        "suma_pesos_pct": float(pesos.sum() * 100.0),
        "tir_ponderada": tir_pond,
        "md_ponderada": md_pond,
        "ingreso_anual_usd": ingreso_anual,
        "max_emisor_corp_pct": max_corp_peso,
        "liquidez_pct": liq_peso,
        "renta_variable_pct": rv_peso
    }

tab1, tab2, tab3 = st.tabs([
    "🤖 1. Ejecución del Agente y Supervisión Humana",
    "🛡️ 2. Verificación de Consistencia y Guardrails",
    "📊 3. Caso de Negocio, ROI y Valor Adicional"
])

with tab1:
    st.markdown("""
    <div class="step-box">
        <b>Arquitectura del Proceso:</b> 1) Carga de tenencia Excel &rarr; 2) Diagnóstico cuantitativo (Herramienta 1) &rarr;
        3) Optimización de órdenes de rebalanceo (Herramienta 2) &rarr; <b>4) Intervención y validación del Asesor</b> &rarr;
        5) Redacción del Investment Memo por el Agente.
    </div>
    """, unsafe_allow_html=True)

    # PASO 1 y 2: Diagnóstico
    st.subheader("Paso 1 y 2: Diagnóstico Cuantitativo de la Cartera Inicial")
    df_calc = df_base.copy()
    cap_inicial = df_calc["Tenencia_Actual_USD"].sum()
    df_calc["Peso_Actual_%"] = (df_calc["Tenencia_Actual_USD"] / cap_inicial) * 100.0 if cap_inicial > 0 else 0
    metricas_ini = calcular_metricas_cartera(df_calc, "Tenencia_Actual_USD")

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Capital Total en Custodia", f"USD {metricas_ini['capital_total']:,.0f}")
    c2.metric("TIR / Retorno Esp. Actual", f"{metricas_ini['tir_ponderada']:.2f}%", delta=f"{metricas_ini['tir_ponderada'] - tir_objetivo:+.2f}% vs Objetivo ({tir_objetivo:.1f}%)")
    c3.metric("Modified Duration Actual", f"{metricas_ini['md_ponderada']:.2f} años", delta=f"Peso CEDEARs actual: {metricas_ini['renta_variable_pct']:.0f}%", delta_color="off")
    c4.metric("Máx. Concentración Corporativa", f"{metricas_ini['max_emisor_corp_pct']:.1f}%", delta=f"Límite {limite_emisor:.0f}%", delta_color="inverse" if metricas_ini['max_emisor_corp_pct'] > limite_emisor else "normal")

    if metricas_ini["max_emisor_corp_pct"] > limite_emisor or metricas_ini["tir_ponderada"] < tir_objetivo:
        st.markdown(f"""
        <div class="guardrail-warn">
            <b>⚠️ Hallazgos del Diagnóstico Automático (Perfil {perfil_riesgo}):</b><br>
            • La cartera actual presenta desvíos respecto a su política de inversión (exceso de concentración o sub-optimización de rendimiento).
        </div>
        """, unsafe_allow_html=True)

    st.divider()

    st.subheader("Paso 3 y 4: Propuesta del Motor e Intervención Humana (Human-in-the-Loop)")
    st.info("👨‍💼 **Instancia de Supervisión del Asesor:** Ajustá las ponderaciones desde los controles. El Agente sólo redactará el informe si los números verifican todas las reglas financieras.")

    col_sliders, col_tabla = st.columns([1, 2])
    pesos_ajustados = []
    with col_sliders:
        st.markdown("**Ajuste Dinámico de Ponderaciones (%)**")
        for idx, row in df_calc.iterrows():
            val_pct = st.slider(
                f"{row['Ticker']} ({row['Activo']})",
                min_value=0.0,
                max_value=100.0,
                value=float(row["Peso_Objetivo_Sugerido"] * 100.0),
                step=1.0,
                key=f"slider_{row['Ticker']}"
            )
            pesos_ajustados.append(val_pct / 100.0)

    df_calc["Peso_Propuesto_%"] = [p * 100.0 for p in pesos_ajustados]
    df_calc["Tenencia_Propuesta_USD"] = df_calc["Peso_Propuesto_%"] / 100.0 * cap_inicial
    df_calc["Orden_Rebalanceo_USD"] = df_calc["Tenencia_Propuesta_USD"] - df_calc["Tenencia_Actual_USD"]
    df_calc["Accion"] = df_calc["Orden_Rebalanceo_USD"].apply(
        lambda x: "COMPRAR" if x > 1e-2 else ("VENDER" if x < -1e-2 else "MANTENER")
    )

    metricas_prop = calcular_metricas_cartera(df_calc, "Tenencia_Propuesta_USD")
    flujo_neto_caja = float(df_calc["Orden_Rebalanceo_USD"].sum())

    with col_tabla:
        st.markdown("**Cuadro de Órdenes Calculadas**")
        df_vista = df_calc[[
            "Ticker", "Activo", "TIR_USD", "Mod_Duration",
            "Tenencia_Actual_USD", "Orden_Rebalanceo_USD", "Peso_Propuesto_%"
        ]].copy()
        st.dataframe(
            df_vista.style.format({
                "TIR_USD": "{:.2f}%", "Mod_Duration": "{:.2f}",
                "Tenencia_Actual_USD": "USD {:,.0f}", "Orden_Rebalanceo_USD": "USD {:+,.0f}",
                "Peso_Propuesto_%": "{:.1f}%"
            }),
            use_container_width=True, hide_index=True
        )

        m1, m2, m3, m4 = st.columns(4)
        m1.metric("TIR / Retorno Propuesto", f"{metricas_prop['tir_ponderada']:.2f}%")
        m2.metric("Duration Propuesta", f"{metricas_prop['md_ponderada']:.2f} años")
        m3.metric("Retorno Anual", f"USD {metricas_prop['ingreso_anual_usd']:,.0f}")
        m4.metric("Exposición CEDEARs", f"{metricas_prop['renta_variable_pct']:.1f}%", delta="En límite" if metricas_prop['renta_variable_pct'] <= limite_rv else "Excedido", delta_color="normal" if metricas_prop['renta_variable_pct'] <= limite_rv else "inverse")

    # VALIDACIÓN DE GUARDRAILS
    suma_100_ok = abs(metricas_prop["suma_pesos_pct"] - 100.0) < 0.01
    caja_cero_ok = abs(flujo_neto_caja) < 0.01
    emisor_ok = metricas_prop["max_emisor_corp_pct"] <= limite_emisor
    duration_ok = metricas_prop["md_ponderada"] <= md_maxima
    tir_ok = metricas_prop["tir_ponderada"] >= tir_objetivo
    liquidez_ok = metricas_prop["liquidez_pct"] >= liquidez_min
    rv_ok = metricas_prop["renta_variable_pct"] <= limite_rv

    todos_los_controles_ok = suma_100_ok and caja_cero_ok and emisor_ok and duration_ok and tir_ok and liquidez_ok and rv_ok

    if not todos_los_controles_ok:
        st.error(
            f"⛔ BLOQUEO DE GUARDRAIL FINANCIERO: La propuesta actual no supera las validaciones duras "
            f"(Suma de pesos: {metricas_prop['suma_pesos_pct']:.1f}% | Máx Emisor: {metricas_prop['max_emisor_corp_pct']:.1f}% | "
            f"CEDEARs: {metricas_prop['renta_variable_pct']:.1f}% | TIR: {metricas_prop['tir_ponderada']:.2f}% | Duration: {metricas_prop['md_ponderada']:.2f}a). "
            f"Ajustá los controles deslizantes para cumplir la política."
        )
    else:
        st.markdown("""
        <div class="guardrail-ok">
            <b>✅ Controles de Consistencia Financiera Superados (100%):</b> La cartera cumple todas las normativas del perfil.
        </div>
        """, unsafe_allow_html=True)

    st.markdown("### ✍️ Confirmación del Asesor Financiero (Human-in-the-Loop)")
    notas_asesor = st.text_input("Comentarios del Asesor para el Memo (opcional):", value="Rebalanceo estratégico de cartera.")
    aprobacion_humana = st.checkbox("He revisado la consistencia financiera de las órdenes y autorizo al Agente a generar el Investment Memo.", disabled=not todos_los_controles_ok)

    if st.button("🚀 Ejecutar Paso 5: Generar Investment Memo con el Agente", type="primary", disabled=not (aprobacion_humana and todos_los_controles_ok)):
        ordenes_texto = "\n".join([
            f"- {r['Accion']} USD {abs(r['Orden_Rebalanceo_USD']):,.0f} en {r['Activo']} ({r['Ticker']}) -> Nuevo peso: {r['Peso_Propuesto_%']:.1f}%"
            for _, r in df_calc.iterrows() if r["Accion"] != "MANTENER"
        ])

        memo_generado = ""
        if modo_ia == "API Google Gemini (En Vivo)" and api_key:
            try:
                import google.generativeai as genai
                genai.configure(api_key=api_key)
                model = genai.GenerativeModel("gemini-pro") # Versión robusta para texto
                prompt = f"""
                Actuá como un Asesor Financiero Senior de Banca Privada en Argentina.
                Redactá un Investment Memo ejecutivo para el cliente '{cliente_nombre}' (Perfil {perfil_riesgo}).
                Utilizá EXCLUSIVAMENTE estas cifras:
                - Capital: USD {cap_inicial:,.0f}
                - Retorno Esperado: de {metricas_ini['tir_ponderada']:.2f}% a {metricas_prop['tir_ponderada']:.2f}%
                - Duration: de {metricas_ini['md_ponderada']:.2f} años a {metricas_prop['md_ponderada']:.2f} años
                - Flujo Anual: de USD {metricas_ini['ingreso_anual_usd']:,.0f} a USD {metricas_prop['ingreso_anual_usd']:,.0f}
                - CEDEARs: {metricas_prop['renta_variable_pct']:.1f}%
                - Órdenes: {ordenes_texto}
                - Notas: {notas_asesor}
                """
                with st.spinner("Redactando Investment Memo verificado..."):
                    respuesta = model.generate_content(prompt)
                    memo_generado = respuesta.text
            except Exception as e:
                st.warning(f"Error con la API ({e}). Utilizando motor de respaldo.")

        if not memo_generado:
            memo_generado = f"""### PROPUESTA DE REBALANCEO PATRIMONIAL
**Destinatario:** {cliente_nombre} | **Perfil:** {perfil_riesgo}  
**Fecha:** {datetime.now().strftime('%d/%m/%Y')}

#### 1. Plan de Acción y Órdenes
Se propone un rebalanceo hacia una TIR ponderada del **{metricas_prop['tir_ponderada']:.2f}%** y una duration de **{metricas_prop['md_ponderada']:.2f} años**.
{ordenes_texto}

**Notas del Asesor:** {notas_asesor}
"""
        st.success("✅ Investment Memo generado con éxito.")
        st.markdown(memo_generado)

with tab2:
    st.subheader("Auditoría de Guardrails")
    st.table(pd.DataFrame([
        {"Control": "1. Suma Ponderaciones (100%)", "Estado": "✅ APROBADO" if suma_100_ok else "❌ FALLO"},
        {"Control": f"2. TIR Mínima ({tir_objetivo}%)", "Estado": "✅ APROBADO" if tir_ok else "❌ FALLO"},
        {"Control": f"3. Duration Máxima ({md_maxima} a)", "Estado": "✅ APROBADO" if duration_ok else "❌ FALLO"},
        {"Control": f"4. Max Emisor ({limite_emisor}%)", "Estado": "✅ APROBADO" if emisor_ok else "❌ FALLO"},
        {"Control": f"5. Max CEDEARs ({limite_rv}%)", "Estado": "✅ APROBADO" if rv_ok else "❌ FALLO"},
    ]))

with tab3:
    st.subheader("Simulador de ROI del Agente")
    t_manual, t_ia = st.columns(2)
    min_manual = t_manual.number_input("Tiempo Manual (min)", value=65)
    min_ia = t_ia.number_input("Tiempo con Agente (min)", value=8)
    st.metric("Ahorro Operativo por Propuesta", f"{(min_manual - min_ia) / min_manual * 100:.1f}%", delta=f"-{min_manual - min_ia} min")
