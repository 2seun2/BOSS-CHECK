import streamlit as st
import pandas as pd
import numpy as np
import math
import matplotlib.pyplot as plt
import matplotlib.patches as patches

# --- 페이지 설정 ---
st.set_page_config(page_title="Boss Design Simulator v2", layout="wide", page_icon="🔩")

# 폰트 설정 (matplotlib 한글 깨짐 방지 - 나눔고딕 등 설치 필요 시)
# 현재는 영문으로 표기하여 호환성을 높임

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
# 인장항복강도는 일반적인 TDS 값을 기준으로 함 (Grade에 따라 다를 수 있음)
MATERIAL_SPECS = {
    "PC (INFINO - High Impact)": {"yield": 62, "desc": "내충격용 PC"},
    "PC/ABS (INFINO)": {"yield": 55, "desc": "PC+ABS 합금"},
    "ABS (STAREX)": {"yield": 45, "desc": "범용 ABS"},
    "POM (KOCETAL)": {"yield": 65, "desc": "내마모/고강성"},
    "PP (Composite)": {"yield": 30, "desc": "복합 PP"}
}

# --- 보스 형상 시각화 함수 ---
def draw_boss_diagram(od, id, height, chamfer, d_screw):
    fig, ax = plt.subplots(figsize=(6, 8))
    
    # 설정
    boss_color = '#d3d3d3' # 회색
    screw_color = '#555555' # 진한 회색
    line_color = 'black'
    
    # 1. 보스 외곽 (OD)
    # 아래쪽 사각형 (챔퍼 아래)
    h_body = height - chamfer
    boss_body = patches.Rectangle((-od/2, 0), od, h_body, linewidth=2, edgecolor=line_color, facecolor=boss_color)
    ax.add_patch(boss_body)
    
    # 2. 보스 챔퍼 (Chamfer) - 사다리꼴 모양
    if chamfer > 0:
        chamfer_pts = np.array([
            [-od/2, h_body],          # 바깥 아래
            [od/2, h_body],           # 바깥 아래
            [id/2 + chamfer, height],  # 바깥 위 (내경 + 챔퍼폭만큼 바깥)
            [-(id/2 + chamfer), height] # 바깥 위
        ])
        # 단순화를 위해 OD에서 ID로 수직으로 떨어지는 챔퍼로 가정
        chamfer_pts = np.array([
            [-od/2, h_body],
            [od/2, h_body],
            [id/2, height],
            [-id/2, height]
        ])
        boss_chamfer_patch = patches.Polygon(chamfer_pts, linewidth=2, edgecolor=line_color, facecolor=boss_color)
        ax.add_patch(boss_chamfer_patch)

    # 3. 보스 내경 (ID) - 점선 표기
    ax.plot([-id/2, -id/2], [0, h_body], color=line_color, linestyle='--', linewidth=1)
    ax.plot([id/2, id/2], [0, h_body], color=line_color, linestyle='--', linewidth=1)

    # 4. 스크류 (Screw) - 단순화된 형상 (유효 체결 깊이까지만 표시)
    screw_width = d_screw * 0.95 # 약간 작게 그림
    # 유효 체결 깊이 (L - C)
    eff_l = height - chamfer
    if eff_l > 0:
        screw_rect = patches.Rectangle((-screw_width/2, chamfer), screw_width, eff_l, linewidth=1, edgecolor=screw_color, facecolor=screw_color, alpha=0.7)
        ax.add_patch(screw_rect)
        ax.text(0, chamfer + eff_l/2, f'Screw\n(Leff={eff_l:.1f})', color='white', ha='center', va='center', fontsize=10)

    # 5. 치수선 추가 (Dimensions)
    def add_dim_h(y, x_start, x_end, text):
        ax.annotate('', xy=(x_start, y), xytext=(x_end, y), arrowprops=dict(arrowstyle='<->', color='blue'))
        ax.text((x_start+x_end)/2, y, text, color='blue', ha='center', va='bottom', fontsize=11)

    def add_dim_v(x, y_start, y_end, text):
        ax.annotate('', xy=(x, y_start), xytext=(x, y_end), arrowprops=dict(arrowstyle='<->', color='green'))
        ax.text(x, (y_start+y_end)/2, text, color='green', ha='left', va='center', fontsize=11, rotation=90)

    # OD, ID
    add_dim_h(-1, -od/2, od/2, f'OD {od:.1f}')
    add_dim_h(height+1, -id/2, id/2, f'ID {id:.1f}')
    
    # Height, Chamfer
    add_dim_v(-(od/2 + 1), 0, height, f'L {height:.1f}')
    if chamfer > 0:
        add_dim_v((od/2 + 1), 0, chamfer, f'C {chamfer:.1f}')

    # 플롯 설정
    ax.set_xlim(-(od/2 + 3), (od/2 + 3))
    ax.set_ylim(-2, height + 3)
    ax.set_aspect('equal') # 비율 유지
    ax.axis('off') # 축 숨기기
    plt.title("Boss Design Cross-section (Unit: mm)", fontsize=14, pad=20)
    
    return fig

# --- 사이드바 UI ---
st.sidebar.header("🛠️ 설계 파라미터 입력")

# 스크류 및 재질 선택
selected_screw = st.sidebar.selectbox("스크류 종류 (아세아볼트)", list(SCREW_SPECS.keys()), index=2)
selected_mat = st.sidebar.selectbox("보스 재질 (롯데케미칼)", list(MATERIAL_SPECS.keys()))

st.sidebar.subheader("📐 보스 치수 (mm)")
# 입력 변수를 세션 상태로 저장하기 위해 key 추가
b_od = st.sidebar.number_input("보스 외경 (OD)", value=6.0, min_value=1.0, step=0.1, format="%.1f")
b_id = st.sidebar.number_input("보스 내경 (ID)", value=2.6, min_value=0.5, step=0.1, format="%.1f")
b_height = st.sidebar.number_input("전체 체결 깊이 (L)", value=8.0, min_value=1.0, step=0.5, format="%.1f")
b_chamfer = st.sidebar.number_input("보스 챔퍼 깊이 (C)", value=0.5, min_value=0.0, step=0.1, format="%.1f")

st.sidebar.subheader("🔩 체결 조건")
torque = st.sidebar.number_input("체결 토크 (kgf·cm)", value=4.0, step=0.5)

# --- 메인 화면 출력 ---
st.title("🔩 Screw Boss Safety Simulator v2")
st.markdown(f"**설정 재질:** {selected_mat} ({MATERIAL_SPECS[selected_mat]['desc']})")

# 화면을 두 컬럼으로 나눔 (왼쪽: 도면, 오른쪽: 결과)
col_diag, col_res = st.columns([1, 1])

with col_diag:
    st.subheader("👨‍🎨 보스 설계 도면")
    d_screw = SCREW_SPECS[selected_screw]["d"]
    # 도면 그리기
    fig = draw_boss_diagram(b_od, b_id, b_height, b_chamfer, d_screw)
    st.pyplot(fig)

with col_res:
    st.subheader("📊 체결 해석 결과")
    st.write("왼쪽에서 파라미터를 설정한 후 아래 버튼을 눌러주세요.")
    
    # --- 체결 버튼 ---
    st.markdown("---")
    # center_btn = st.columns([1,2,1])[1] # 가운데 정렬
    calc_btn = st.button("🔩 스크류 체결 시작", type="primary", use_container_width=True)
    st.markdown("---")

    # 버튼이 눌렸을 때만 계산 및 결과 출력
    if calc_btn:
        # 데이터 가져오기
        d = SCREW_SPECS[selected_screw]["d"]
        sy = MATERIAL_SPECS[selected_mat]["yield"]
        ss = sy * 0.577  # Von Mises 기준 전단강도

        # 유효 체결 길이 계산 (챔퍼 제외)
        eff_l = b_height - b_chamfer

        # 에러 체크
        if b_od <= b_id:
            st.error("❌ 오류: 보스 외경(OD)이 내경(ID)보다 커야 합니다.")
        elif eff_l <= 0:
            st.error("❌ 오류: 유효 체결 길이(L-C)가 0보다 커야 합니다. 전체 깊이(L) 또는 챔퍼(C)를 조정하세요.")
        else:
            # --- 계산 로직 ---
            # 1. 축력 계산 (T = K * D * F)
            # K: 토크계수 (플라스틱 체결 시 약 0.25 적용, 윤활 상태에 따라 다름)
            k_factor = 0.25
            torque_nm = torque * 0.0980665 # kgf.cm -> N.m 변환
            # d는 mm이므로 m로 변환
            axial_force = torque_nm / (k_factor * d * 0.001)

            # 2. 파손모드 A: 나사산 전단 (Stripping)
            # 전단 면적 (플라스틱 보스 내벽 나사산의 유효 전단 면적)
            # 단순화를 위해 ID 기준 원통 면적의 50% 적용
            shear_area = math.pi * b_id * eff_l * 0.5
            applied_shear = axial_force / shear_area if shear_area > 0 else 9999
            sf_stripping = ss / applied_shear

            # 3. 파손모드 B: 보스 터짐 (Bursting - Hoop Stress)
            # 스크류 나사산 각도(60도 -> 반각 30도)에 의한 쐐기 효과 압력 산출
            radial_force = axial_force * math.tan(math.radians(30))
            p_internal = radial_force / (math.pi * b_id * eff_l)
            # 두꺼운 원통 공식 (Lame's equation) - 최댓값인 내벽 응력 계산
            hoop_stress = p_internal * ((b_od**2 + b_id**2) / (b_od**2 - b_id**2)) if b_od > b_id else 9999
            sf_bursting = sy / hoop_stress

            # --- 결과 출력 ---
            st.success("✅ 체결 완료! 안전율을 확인하세요.")
            
            # 메트릭 표시
            m_col1, m_col2 = st.columns(2)
            m_col1.metric("발생 축력 (Axial Force)", f"{axial_force:.1f} N")
            m_col2.metric("유효 체결 깊이 (Leff)", f"{eff_l:.1f} mm")

            st.markdown("#### 파손 모드별 안전율 (Safety Factor)")
            
            # 안전율 표시 및 색상 결정 함수
            def get_status_md(sf):
                if sf > 2.0: return f"**<span style='color:green'>안전 (SF={sf:.2f})</span>**"
                if sf > 1.2: return f"**<span style='color:orange'>주의 (SF={sf:.2f})</span>**"
                return f"**<span style='color:red'>파손 위험 (SF={sf:.2f})</span>**"

            # 나산 전단 결과
            st.markdown(f"1. **나사산 뭉개짐 (Stripping):** {get_status_md(sf_stripping)}", unsafe_allow_html=True)
            st.caption(f"(발생 전단응력: {applied_shear:.1f} MPa / 재질 전단강도: {ss:.1f} MPa)")

            # 보스 터짐 결과
            st.markdown(f"2. **보스 터짐 (Bursting):** {get_status_md(sf_bursting)}", unsafe_allow_html=True)
            st.caption(f"(발생 후프응력: {hoop_stress:.1f} MPa / 재질 항복강도: {sy:.1f} MPa)")

st.markdown("---")
st.subheader("📚 설계 가이드 (Rule of Thumb)")
st.write("""
- **보스 외경 (OD):** 일반적으로 스크류 직경(D)의 **2.0 ~ 2.5배**를 권장합니다.
- **보스 내경 (ID):** 스크류 직경(D) 대비 **약 80~85%** 수준으로 설계하여 나사산이 충분히 박히도록 합니다. (탭핑 스크류 기준)
- **체결 깊이:** 플라스틱의 경우 최소 스크류 직경의 **2.0배 이상** 유효 체결 길이를 확보하는 것이 좋습니다.
- **챔퍼 (Chamfer):** 챔퍼는 초기 체결 가이드를 돕지만, 너무 깊으면 유효 체결 길이를 줄이므로 주의해야 합니다. (통상 0.5mm 이하)
""")
