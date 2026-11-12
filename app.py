import streamlit as st
import pandas as pd
import plotly.express as px
from supabase import create_client, Client

# 1. 페이지 기본 설정 (와이드 레이아웃 적용 및 테마 설정)
st.set_page_config(
    page_title="다이소 품질 관리 대시보드",
    page_icon="📦",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- 🎨 커스텀 CSS 적용 (KPI 카드 스타일링) ---
st.markdown("""
<style>
div[data-testid="metric-container"] {
    background-color: #ffffff;
    border: 1px solid #e0e4e8;
    padding: 15px 20px;
    border-radius: 10px;
    box-shadow: 2px 4px 10px rgba(0,0,0,0.05);
}
h1 {
    color: #1f2937;
    font-weight: 700;
}
</style>
""", unsafe_allow_html=True)

# 2. Supabase 연결 설정
@st.cache_resource
def init_supabase():
    try:
        url = st.secrets["SUPABASE_URL"]
        key = st.secrets["SUPABASE_KEY"]
        return create_client(url, key)
    except Exception as e:
        return None

supabase = init_supabase()

# --- ⬅️ 사이드바 (설정 및 업로드 영역) ---
with st.sidebar:
    st.title("⚙️ 대시보드 설정")
    
    if supabase is None:
        st.error("⚠️ Supabase 연결 실패 (Secrets 확인)")
    else:
        st.success("🟢 Supabase 연결 활성화")
        
    st.divider()
    st.subheader("📁 데이터 업로드")
    uploaded_file = st.file_uploader("검사 결과 엑셀 (.xlsx, .xls)", type=["xlsx", "xls"])

# --- 🖥️ 메인 화면 영역 ---
st.title("📦 다이소 협력사 품질(QA) 통합 대시보드")
st.markdown("업로드된 검사 성적 데이터를 기반으로 불합격 원인을 분석하고 품질 개선 지표를 도출합니다.")

if uploaded_file is not None:
    try:
        # 파일 확장자에 따른 엔진 선택
        file_name = uploaded_file.name.lower()
        if file_name.endswith('.xls'):
            df = pd.read_excel(uploaded_file, engine='xlrd')
        else:
            df = pd.read_excel(uploaded_file, engine='openpyxl')
            
        total_rows = len(df)
        columns_list = list(df.columns)
        
        # UI 레이아웃 분리 (탭 생성)
        tab_dashboard, tab_data = st.tabs(["📊 핵심 품질 지표 (Dashboard)", "📋 상세 원본 데이터 (Data)"])
        
        # --- 탭 1: 핵심 품질 지표 대시보드 ---
        with tab_dashboard:
            st.markdown("#### 🔍 분석 기준 설정")
            c1, c2 = st.columns(2)
            with c1:
                default_status_idx = next((i for i, col in enumerate(columns_list) if any(k in str(col).lower() for k in ['판정', 'result', 'status', '합격'])), 0)
                status_col = st.selectbox("판정 결과 기준 컬럼", columns_list, index=default_status_idx)
            with c2:
                default_reason_idx = next((i for i, col in enumerate(columns_list) if any(k in str(col).lower() for k in ['사유', '불합격', '항목', 'reason', 'fail'])), min(1, len(columns_list)-1))
                reason_col = st.selectbox("불합격 사유 기준 컬럼", columns_list, index=default_reason_idx)

            if status_col and reason_col:
                # 불합격 데이터 필터링
                fail_keywords = ['불합격', 'fail', '不合格', 'x', 'n', '부적합']
                mask = df[status_col].astype(str).str.lower().apply(lambda x: any(kw in x for kw in fail_keywords))
                df_fail = df[mask]
                
                fail_count = len(df_fail)
                pass_count = total_rows - fail_count
                fail_rate = (fail_count / total_rows * 100) if total_rows > 0 else 0
                pass_rate = 100 - fail_rate

                # 상단 KPI 메트릭 카드
                st.markdown("<br>", unsafe_allow_html=True)
                m1, m2, m3, m4 = st.columns(4)
                with m1:
                    st.metric(label="총 검사 진행 건수", value=f"{total_rows:,} 건")
                with m2:
                    st.metric(label="✅ 최종 합격 건수", value=f"{pass_count:,} 건", delta=f"{pass_rate:.1f}%")
                with m3:
                    st.metric(label="🚨 최종 불합격 건수", value=f"{fail_count:,} 건", delta=f"-{fail_rate:.1f}%", delta_color="inverse")
                with m4:
                    st.metric(label="📉 종합 불합격률(Defect Rate)", value=f"{fail_rate:.2f}%")

                st.divider()

                # 시각화 영역
                if fail_count > 0:
                    st.markdown("#### 🔎 주요 품질 결함 분석")
                    
                    # 결함 항목 집계
                    fail_summary = df_fail[reason_col].value_counts().reset_index()
                    fail_summary.columns = ['불합격 항목', '발생 건수']
                    fail_summary['점유율(%)'] = (fail_summary['발생 건수'] / fail_count * 100).round(1)
                    
                    chart_col1, chart_col2 = st.columns([1, 1.2])
                    
                    with chart_col1:
                        # 1. 도넛 차트 (비중 파악용)
                        fig_pie = px.pie(
                            fail_summary, 
                            names='불합격 항목', 
                            values='발생 건수', 
                            hole=0.45,
                            color_discrete_sequence=px.colors.qualitative.Pastel
                        )
                        fig_pie.update_traces(textposition='inside', textinfo='percent+label')
                        fig_pie.update_layout(title_text="결함 항목별 점유율", margin=dict(t=40, b=20, l=0, r=0), height=350)
                        st.plotly_chart(fig_pie, use_container_width=True)
                        
                    with chart_col2:
                        # 2. 바 차트 (빈도 파악용)
                        fig_bar = px.bar(
                            fail_summary, 
                            x='발생 건수', 
                            y='불합격 항목', 
                            orientation='h',
                            text='발생 건수',
                            color='발생 건수',
                            color_continuous_scale='Reds'
                        )
                        fig_bar.update_layout(
                            title_text="결함 항목별 발생 빈도", 
                            yaxis={'categoryorder':'total ascending'},
                            margin=dict(t=40, b=20, l=0, r=0), height=350,
                            coloraxis_showscale=False
                        )
                        st.plotly_chart(fig_bar, use_container_width=True)
                        
                    # 결함 상세 테이블
                    st.markdown("##### 📋 세부 결함 통계 테이블")
                    st.dataframe(fail_summary, use_container_width=True)
                else:
                    st.success("🎉 분석 결과 모든 제품이 품질 기준을 통과했습니다 (불합격 건수: 0)")

        # --- 탭 2: 원본 데이터 조회 ---
        with tab_data:
            st.markdown("#### 📂 엑셀 원본 데이터")
            st.dataframe(df, use_container_width=True, height=600)

    except Exception as e:
        st.error(f"데이터 처리 중 오류가 발생했습니다: {e}")
else:
    # 파일이 업로드되지 않았을 때의 랜딩 화면
    st.info("👈 좌측 사이드바에서 다이소 품질 관리 엑셀 파일을 업로드해 주세요.")
    st.image("https://images.unsplash.com/photo-1551288049-bebda4e38f71?auto=format&fit=crop&w=1200&q=80", use_column_width=True, caption="Data Driven Quality Control")
