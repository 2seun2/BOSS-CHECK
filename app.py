import streamlit as st
import pandas as pd
import numpy as np
import math

# --- 페이지 설정 ---
st.set_page_config(page_title="Boss Design Simulator", layout="wide")

# --- 데이터 정의 ---
# 1. 아세아볼트 표준 규격 (M2~M5)
SCREW_SPECS = {
    "M2": {"d": 2.0, "pitch": 0.4},
    "M2.5": {"d": 2.5, "pitch": 0.45},
    "M3": {"d": 3.0, "pitch": 0.5},
    "M4": {"d": 4.0, "pitch": 0.7},
    "M5": {"d": 5.0, "pitch": 0.8}
}

# 2. 롯데케미칼 EP 물성치 (단위: MPa)
# 인장항복강도는 일반적인 TDS 값을 기준으로 함
MATERIAL_SPECS = {
    "PC (INFINO - High Impact)": {"yield": 62, "desc": "내충격용 PC"},
    "PC/ABS (INFINO)": {"yield": 55, "desc": "PC+ABS 합금"},
    "ABS (STAREX)": {"yield": 45, "desc": "범용 ABS"},
    "POM (KOCETAL)": {"yield": 65, "desc": "내마모/고강성"},
    "PP (Composite)": {"yield": 30, "desc": "복합 PP"}
}

# --- 사이드바 UI ---
st.sidebar.header("🛠️ 설계 파라미터 입력")

# 스크류 및 재질 선택
selected_screw = st.sidebar.selectbox("스크류 종류 (아세아볼트)", list(SCREW_SPECS.keys()), index=2)
selected_mat = st.sidebar.selectbox("보스 재질 (롯데케미칼)", list(MATERIAL_SPECS.keys()))

st.sidebar.subheader("📐 보스 치수 (mm)")
b_od = st.sidebar.slider("보스 외경 (OD)", 3.0, 15.0, 6.0, 0.1)
b_id = st.sidebar.slider("보스 내경 (ID)", 1.5, 6.0, 2.6, 0.1)
b_height = st.sidebar.slider("전체 체결 깊이 (L)", 2.0, 20.0, 8.0, 0.5)
b_chamfer = st.sidebar.slider("보스 챔퍼 깊이 (C)", 0.0, 2.0, 0.5, 0.1)

st.sidebar.subheader("🔩 체결 조건")
torque = st.sidebar.number_input("체결 토크 (kgf·cm)", value=4.0, step=0.5)

# --- 계산 로직 ---
d = SCREW_SPECS[selected_screw]["d"]
sy = MATERIAL_SPECS[selected_mat]["yield"]
ss = sy * 0.577  # Von Mises 기준 전단강도

# 유효 체결 길이 계산 (챔퍼 제외)
eff_l = b_height - b_chamfer

# 1. 축력 계산 (T = K * D * F)
# K: 토크계수 (플라스틱 체결 시 약 0.25 적용)
k_factor = 0.25
torque_nm = torque * 0.0980665 # kgf.cm -> N.m 변환
axial_force = torque_nm / (k_factor * d * 0.001)

# 2. 파손모드 A: 나사산 전단 (Stripping)
# 전단 면적 (나사산 맞물림을 고려한 유효 면적)
shear_area = math.pi * b_id * eff_l * 0.5
applied_shear = axial_force / shear_area if shear_area > 0 else 999
sf_stripping = ss / applied_shear

# 3. 파손모드 B: 보스 터짐 (Bursting - Hoop Stress)
# 쐐기 효과(30도)에 의한 방사형 압력 산출
p_internal = (axial_force * math.tan(math.radians(30))) / (math.pi * b_id * eff_l)
# 두꺼운 원통 공식 (Lame's equation)
hoop_stress = p_internal * ((b_od**2 + b_id**2) / (b_od**2 - b_id**2)) if b_od > b_id else 999
sf_bursting = sy / hoop_stress

# --- 메인 화면 출력 ---
st.title("🔩 Screw Boss Safety Simulator")
st.markdown(f"**현재 설정:** {selected_screw} / {selected_mat} ({MATERIAL_SPECS[selected_mat]['desc']})")

if b_od <= b_id:
    st.error("❌ 오류: 보스 외경이 내경보다 커야 합니다.")
else:
    col1, col2, col3 = st.columns(3)
    col1.metric("발생 축력", f"{axial_force:.1f} N")
    
    # 안전율 표시 및 색상 결정
    def get_status(sf):
        if sf > 2.0: return "✅ 안전", "green"
        if sf > 1.2: return "⚠️ 주의", "orange"
        return "🚨 파손 위험", "red"

    status_s, color_s = get_status(sf_stripping)
    status_b, color_b = get_status(sf_bursting)

    with col2:
        st.subheader("나산 전단 (Stripping)")
        st.write(f"안전율: **{sf_stripping:.2f}**")
        st.markdown(f"<span style='color:{color_s}'>{status_s}</span>", unsafe_allow_html=True)

    with col3:
        st.subheader("보스 터짐 (Bursting)")
        st.write(f"안전율: **{sf_bursting:.2f}**")
        st.markdown(f"<span style='color:{color_b}'>{status_b}</span>", unsafe_allow_html=True)

st.markdown("---")
st.subheader("📚 공학적 참고사항")
st.write("""
- **유효 체결 길이:** 챔퍼는 초기 진입을 돕지만 유효한 나사산 길이를 감소시켜 전단 파손 위험을 높입니다.
- **후프 응력(Hoop Stress):** 스크류가 벌어지려는 힘에 의해 보스 외벽이 터지는 응력입니다. 외경(OD)이 내경(ID)의 2배 이상일 때 안정적입니다.
""")
