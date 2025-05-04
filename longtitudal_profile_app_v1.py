# longtitudal_profile_app.py(matplotlibからインタラクティブなplotly.graph_objects に差し替え)

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go

# ===============================
# Section 0: Page Setup
# ===============================
st.set_page_config(layout="wide")
# CSS: latexの左寄せ
st.markdown("""
    <style>
    .stMarkdown .katex {
        text-align: left !important;
        margin-left: 0 !important;
    }
    </style>
""", unsafe_allow_html=True)

st.markdown("""
    <style>
        html, body, [class*="css"]  {
            font-size: 12px !important;
            line-height: 1.2em !important;
        }
    </style>
""", unsafe_allow_html=True)

st.title("Pipeline Profile Viewer with Hydraulic Grade Line")

# ===============================
# Section 1: Upload Input CSV (Optional)
# ===============================
st.subheader("⬆️ First: (Optional) Upload Input CSV")

uploaded_input = st.file_uploader("Upload input CSV", type="csv", key="input_csv")
if uploaded_input is not None and "_input_loaded" not in st.session_state:
    loaded_df = pd.read_csv(uploaded_input)
    loaded_df.columns = loaded_df.columns.str.strip()
    st.session_state["flow_value"] = loaded_df.get("flow_m3_s", pd.Series([0.0])).iloc[0] * 3600
    st.session_state["diameter_mm"] = max(1.0, loaded_df.get("diameter_m", pd.Series([0.0])).iloc[0] * 1000)
    st.session_state["C"] = loaded_df.get("c_value", pd.Series([100])).iloc[0]
    st.session_state["LWL_suc"] = loaded_df.get("suction_lwl", pd.Series([0.0])).iloc[0]
    st.session_state["DWL_suc"] = loaded_df.get("suction_dwl", pd.Series([0.0])).iloc[0]
    st.session_state["HWL_suc"] = loaded_df.get("suction_hwl", pd.Series([0.0])).iloc[0]
    st.session_state["LWL_dis"] = loaded_df.get("discharge_lwl", pd.Series([0.0])).iloc[0]
    st.session_state["DWL_dis"] = loaded_df.get("discharge_dwl", pd.Series([0.0])).iloc[0]
    st.session_state["HWL_dis"] = loaded_df.get("discharge_hwl", pd.Series([0.0])).iloc[0]
    st.session_state["_input_loaded"] = True
    st.rerun()

# Defaults
defaults = {
    "flow_value": 0.0, "diameter_mm": 100.0, "C": 100,
    "LWL_suc": 0.0, "DWL_suc": 0.0, "HWL_suc": 0.0,
    "LWL_dis": 0.0, "DWL_dis": 0.0, "HWL_dis": 0.0,
    "run_calculation": False
}
for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

# ===============================
# Section 2: Flow and Pipe Input
# ===============================
st.header("1. Flow Rate, Diameter, and Water Level Input")

unit_options = {"m3/h": 1/3600, "m3/min": 1/60, "m3/s": 1.0}

col1a, col1b = st.columns(2)

with col1a:
    st.subheader("Flow Settings")
    flow_unit = st.selectbox("Flow rate unit", list(unit_options.keys()), key="flow_unit")
    flow_value = st.number_input("Flow rate", value=st.session_state.get("flow_value", 0.0), key="flow_value_input")

with col1b:
    st.subheader("Pipe Settings")
    diameter_mm = st.number_input("Pipe diameter [mm]", min_value=1.0, value=st.session_state.get("diameter_mm", 100.0), key="diameter_mm_input")
    diameter_m = diameter_mm / 1000
    C = st.number_input("Hazen-Williams C value", min_value=1, value=st.session_state.get("C", 100), key="C_input")

Q_m3s = flow_value * unit_options[flow_unit]
st.markdown(
    f"**Converted Flow Rate**: "
    f"{Q_m3s*3600:.2f} m³/h, {Q_m3s*60:.2f} m³/min, {Q_m3s:.4f} m³/s"
)
col2a, col2b = st.columns(2)
with col2a:
    st.subheader("Suction water level [m]")
    HWL_suc = st.number_input("Suction HWL", value=st.session_state["HWL_suc"])
    DWL_suc = st.number_input("Suction DWL", value=st.session_state["DWL_suc"])
    LWL_suc = st.number_input("Suction LWL", value=st.session_state["LWL_suc"])
with col2b:
    st.subheader("Discharge water level [m]")
    HWL_dis = st.number_input("Discharge HWL", value=st.session_state["HWL_dis"])
    DWL_dis = st.number_input("Discharge DWL", value=st.session_state["DWL_dis"])
    LWL_dis = st.number_input("Discharge LWL", value=st.session_state["LWL_dis"])

file_name_input = st.text_input("Filename for input values", value="input_conditions.csv")
col_save = st.columns(2)
with col_save[0]:
    if st.button("Save input values"):
        input_df = pd.DataFrame({
            "flow_m3_s": [Q_m3s],
            "diameter_m": [diameter_m],
            "c_value": [C],
            "suction_lwl": [LWL_suc], "suction_dwl": [DWL_suc], "suction_hwl": [HWL_suc],
            "discharge_lwl": [LWL_dis], "discharge_dwl": [DWL_dis], "discharge_hwl": [HWL_dis],
        })
        input_df.to_csv(file_name_input, index=False)
        st.download_button("Download input file", data=input_df.to_csv(index=False), file_name=file_name_input, mime="text/csv")
        st.success(f"Saved: {file_name_input}")

# ===============================
# Section 3: Run Calculation
# ===============================
st.header("2. Run Calculation")
if st.button("Run Calculation"):
    st.session_state["run_calculation"] = True

# ===============================
# Section 4–5: Profile CSV & Calculation
# ===============================
if st.session_state["run_calculation"]:
    st.header("3. Pipeline Profile Data")
    profile_file = st.file_uploader("Upload pipeline profile CSV", type="csv")
    
    if profile_file is not None:
        profile_df = pd.read_csv(profile_file)
        profile_df.columns = profile_df.columns.str.strip()

        if "Distance_m" in profile_df.columns and "Elevation_m" in profile_df.columns:
            st.dataframe(profile_df, use_container_width=True)

            # ===============================
            # Section 4: Head Loss Calculation
            # ===============================
            st.header("4. Head Loss Calculation")

            # 入力と定義
            L_total = profile_df["Distance_m"].max()
            Q = Q_m3s
            D = diameter_m

            hf = 10.67 * (L_total * Q**1.852) / (C**1.852 * D**4.87)
            HT_total = DWL_dis + hf - DWL_suc
            Ha_design = DWL_dis - DWL_suc
            Ha_min = LWL_dis - HWL_suc
            Ha_max = HWL_dis - LWL_suc

            # ⬇️ LaTeX左揃えは Section 0 にCSS済み前提
            
            def fmt(value: float) -> str:
                return f"({value:.2f})" if value < 0 else f"{value:.2f}"         
                     
            # Ha_design
            st.latex(
                rf"Ha_{{design}} = DWL_{{dis}} - DWL_{{suc}} = {fmt(DWL_dis)} - {fmt(DWL_suc)} = {Ha_design:.2f}\,m"
            )    

            # Ha_max
            st.latex(
                rf"Ha_{{max}} = HWL_{{dis}} - LWL_{{suc}} = {fmt(HWL_dis)} - {fmt(LWL_suc)} = {Ha_max:.2f}\,m"
            )            
            # Ha_min
            st.latex(
                rf"Ha_{{min}} = LWL_{{dis}} - HWL_{{suc}} = {fmt(LWL_dis)} - {fmt(HWL_suc)} = {Ha_min:.2f}\,m"
            )
            
            # hf（定義式・代入式・結果）
            st.latex(
                rf"""
                h_f = 10.67 \cdot \frac{{L \cdot Q^{{1.852}}}}{{C^{{1.852}} \cdot D^{{4.87}}}} 
                = 10.67 \cdot \frac{{{L_total:.1f} \cdot {Q:.4f}^{{1.852}}}}{{{C:.1f}^{{1.852}} \cdot {D:.3f}^{{4.87}}}} 
                = {hf:.2f}\,m
                """
            )
            # HT_design
            st.latex(
                 rf"HT_{{design}} = DWL_{{dis}} - DWL_{{suc}} + h_f = {fmt(DWL_dis)} - {fmt(DWL_suc)} + {hf:.2f} = {HT_total:.2f}\,m"
            )
            # ===============================
            # Section 5: Profile and HGL Plot
            # ===============================
            st.header("5. Profile and HGL Plot")

            fig = go.Figure()

            # Pipe Elevation Line
            fig.add_trace(go.Scatter(
                x=profile_df["Distance_m"],
                y=profile_df["Elevation_m"],
                mode="lines+markers",
                name="Pipe Elevation",
                line=dict(color="black", width=2),
                marker=dict(color="yellow", size=1, symbol="circle"),
                hovertemplate="Distance: %{x:.2f} m<br>Elevation: %{y:.2f} m",
            ))

            # HGL Line
            fig.add_trace(go.Scatter(
                x=[0, L_total],
                y=[DWL_dis + hf, DWL_dis],
                mode="lines",
                name="Hydraulic Grade Line",
                line=dict(color="red", width=2),
                hoverinfo="skip"
            ))

            # 水位マーカー追加関数
            def add_water_level_marker(x, y, color, name):
                fig.add_trace(go.Scatter(
                    x=[x],
                    y=[y],
                    mode="markers+text",
                    marker=dict(symbol='line-ew', size=15, color=color, line=dict(width=2)),
                    name=name,
                    text=[f"{y:.2f} m"],
                    textposition="top right",
                    hovertemplate=f"{name}: {y:.2f} m<br>Distance: {x} m",
                    showlegend=True
                ))

            # 吸込み側
            add_water_level_marker(-10, HWL_suc, "red", "HWL")
            add_water_level_marker(-10, LWL_suc, "blue", "LWL")
            add_water_level_marker(-10, DWL_suc, "black", "DWL")

            # 吐出側
            add_water_level_marker(L_total + 10, HWL_dis, "red", "HWL")
            add_water_level_marker(L_total + 10, LWL_dis, "blue", "LWL")
            add_water_level_marker(L_total + 10, DWL_dis, "black", "DWL")

            # レイアウト設定
            fig.update_layout(
                title="Interactive Pipeline Profile and Hydraulic Grade Line",
                xaxis=dict(
                    title=dict(text="Distance [m]", font=dict(size=16)),
                    showline=True,
                    linewidth=2,
                    linecolor='black',
                    mirror=True,
                    showgrid=True,
                    gridcolor='lightgray',
                    tickfont=dict(size=14),
                    dtick=1000  # ✅ カンマ追加済み
                ),
                yaxis=dict(
                    title=dict(text="Elevation [m]", font=dict(size=16)),
                    showline=True,
                    linewidth=2,
                    linecolor='black',
                    mirror=True,
                    showgrid=True,
                    gridcolor='lightgray',
                    tickfont=dict(size=14),
                    dtick=5  # ✅ カンマ追加済み
                ),
                legend=dict(  # ✅ 正しい位置へ移動
                    x=0.98, y=0.02,
                    xanchor='right', yanchor='bottom',
                    bgcolor='rgba(255,255,255,0.7)',
                    bordercolor='gray',
                    borderwidth=1,
                    font=dict(size=12),
                ),
                margin=dict(l=60, r=30, t=60, b=60),
                template="simple_white",
                hovermode="closest"
            )

            # 凡例重複削除
            fig.for_each_trace(lambda t: t.update(showlegend=False)
                            if t.name in [s.name for s in fig.data if s != t] else None)

            # 描画
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.error("Profile CSV must contain 'Distance_m' and 'Elevation_m' columns.")
          
# python -m streamlit run longtitudal_profile_app_v1.py

