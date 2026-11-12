import streamlit as st
import pandas as pd
import plotly.express as px
from supabase import create_client, Client

# 1. 페이지 기본 설정 (와이드 레이아웃 적용)
st.set_page_config(
    page_title="다이소 품질 관리 대시보드",
    page_icon="📦",
    layout="wide"
)

st.title("📦 다이소 협력사 품질 관리 대시보드")
st.markdown("엑셀 품질 검사 데이터를 업로드하고 불합격 항목별 비중 및 통계를 전문적인 시각화 지표로 확인하세요.")

# 2. Supabase 연결 설정 (안전한 예외 처리)
@st.cache_resource
def init_supabase():
    try:
        url = st.secrets["SUPABASE_URL"]
        key = st.secrets["SUPABASE_KEY"]
        return create_client(url, key)
    except Exception as e:
        return None

supabase = init_supabase()

if supabase is None:
    st.error("⚠️ Streamlit Cloud의 Secrets 설정에 SUPABASE_URL 또는 SUPABASE_KEY가 등록되지 않았습니다.")
else:
    st.success("✨ Supabase 데이터베이스와 성공적으로 연결되었습니다!")

# 3. 엑셀 파일 업로드 및 분석 영역
st.divider()
st.subheader("📊 품질 검사 엑셀 데이터 업로드 및 불합격 분석")
uploaded_file = st.file_uploader("품질 관리 엑셀 파일(.xlsx, .xls)을 업로드하세요", type=["xlsx", "xls"])

if uploaded_file is not None:
    try:
        # 파일 확장자에 따른 엔진 자동 선택 (.xls -> xlrd, .xlsx -> openpyxl)
        file_name = uploaded_file.name.lower()
        if file_name.endswith('.xls'):
            df = pd.read_excel(uploaded_file, engine='xlrd')
        else:
            df = pd.read_excel(uploaded_file, engine='openpyxl')
        
        st.write("### 📋 업로드된 데이터 미리보기")
        st.dataframe(df.head(10), use_container_width=True)
        
        # 데이터 기본 집계
        total_rows = len(df)
        
        # 컬럼 선택 UI (판정 및 불합격 사유 컬럼 자동 매칭)
        columns_list = list(df.columns)
        
        c1, c2 = st.columns(2)
        with c1:
            default_status_idx = next((i for i, col in enumerate(columns_list) if any(k in str(col).lower() for k in ['판정', 'result', 'status', '합격'])), 0)
            status_col = st.selectbox("판정 결과 컬럼 선택 (합격/불합격)", columns_list, index=default_status_idx)
            
        with c2:
            default_reason_idx = next((i for i, col in enumerate(columns_list) if any(k in str(col).lower() for k in ['사유', '불합격', '항목', 'reason', 'fail'])), min(1, len(columns_list)-1))
            reason_col = st.selectbox("불합격 사유/항목 컬럼 선택", columns_list, index=default_reason_idx)

        if status_col and reason_col:
            # 불합격 데이터 필터링
            fail_keywords = ['불합격', 'fail', '不合格', 'x', 'n', '부적합']
            mask = df[status_col].astype(str).str.lower().apply(lambda x: any(kw in x for kw in fail_keywords))
            df_fail = df[mask]
            
            fail_count = len(df_fail)
            pass_count = total_rows - fail_count
            fail_rate = (fail_count / total_rows * 100) if total_rows > 0 else 0
            pass_rate = 100 - fail_rate

            # --- 상단 요약 메트릭 카드 영역 ---
            st.divider()
            st.subheader("📌 [종합] 품질 검사 요약 지표")
            
            m1, m2, m3, m4 = st.columns(4)
            with m1:
                st.metric(label="총 검사 건수", value=f"{total_rows:,} 건")
            with m2:
                st.metric(label="합격 건수", value=f"{pass_count:,} 건", delta=f"{pass_rate:.1f}%")
            with m3:
                st.metric(label="불합격 건수", value=f"{fail_count:,} 건", delta=f"-{fail_rate:.1f}%", delta_color="inverse")
            with m4:
                st.metric(label="종합 불합격률", value=f"{fail_rate:.2f}%")

            if fail_count > 0:
                st.divider()
                st.subheader("📊 불합격 항목별 비중 및 세부 통계")
                
                # 불합격 항목별 집계 데이터프레임 생성
                fail_summary = df_fail[reason_col].value_counts().reset_index()
                fail_summary.columns = ['불합격 항목', '건수']
                fail_summary['퍼센트(%)'] = (fail_summary['건수'] / fail_count * 100).round(2)
                
                # 좌우 레이아웃 분할 (왼쪽: 도넛 차트, 오른쪽: 상세 테이블)
                col_chart, col_table = st.columns([1.2, 1])
                
                with col_chart:
                    # Plotly 도넛 차트 생성 (보여주신 레퍼런스 스타일)
                    fig = px.pie(
                        fail_summary, 
                        names='불합격 항목', 
                        values='건수', 
                        hole=0.5,
                        title="불합격 항목별 점유율(%)"
                    )
                    fig.update_traces(textposition='inside', textinfo='percent+label')
                    fig.update_layout(height=450, margin=dict(t=40, b=20, l=20, r=20))
                    st.plotly_chart(fig, use_container_width=True)
                    
                with col_table:
                    st.write("#### 📋 불합격 항목 상세 내역")
                    st.dataframe(fail_summary, use_container_width=True, height=400)
                    
            else:
                st.success("🎉 선택한 판정 기준에 따른 불합격 데이터가 없습니다. 모든 제품이 합격입니다!")

    except Exception as e:
        st.error(f"엑셀 파일을 읽는 과정에서 오류가 발생했습니다: {e}")
else:
    st.info("💡 시작하려면 상단의 'Browse files' 버튼을 눌러 품질 관리 엑셀 파일을 업로드해 주세요.")
