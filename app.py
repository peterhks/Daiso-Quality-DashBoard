import streamlit as st
import pandas as pd
from supabase import create_client, Client

# 1. 페이지 기본 설정 (와이드 레이아웃 적용)
st.set_page_config(
    page_title="다이소 품질 관리 대시보드",
    page_icon="📦",
    layout="wide"
)

st.title("📦 다이소 협력사 품질 관리 대시보드")
st.markdown("엑셀 품질 검사 데이터를 업로드하고 Supabase 데이터베이스와 연동하여 관리하세요.")

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

# Supabase 연결 상태 안내
if supabase is None:
    st.error("⚠️ Streamlit Cloud의 Secrets 설정에 SUPABASE_URL 또는 SUPABASE_KEY가 등록되지 않았습니다. 설정을 확인해주세요.")
else:
    st.success("✨ Supabase 데이터베이스와 성공적으로 연결되었습니다!")

# 3. 엑셀 파일 업로드 및 분석 영역
st.divider()
st.subheader("📊 품질 검사 엑셀 데이터 업로드")
uploaded_file = st.file_uploader("품질 관리 엑셀 파일(.xlsx, .xls)을 업로드하세요", type=["xlsx", "xls"])

if uploaded_file is not None:
    try:
        # openpyxl 엔진을 명시하여 엑셀 파일 읽기
        df = pd.read_excel(uploaded_file, engine='openpyxl')
        
        st.write("### 📋 업로드된 데이터 미리보기")
        st.dataframe(df.head(10), use_container_width=True)
        
        # 기본 요약 지표 표시
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric(label="총 데이터 행(Row) 수", value=len(df))
        with col2:
            st.metric(label="총 컬럼 수", value=len(df.columns))
        with col3:
            st.metric(label="주요 항목", value=df.columns[0] if len(df.columns) > 0 else "없음")

        # 데이터베이스 저장 버튼 (필요 시 확장하여 활용)
        if st.button("Supabase에 데이터 저장하기"):
            st.info("데이터 저장을 위한 테이블 연동 로직을 이곳에 추가하여 사용할 수 있습니다.")
            
    except Exception as e:
        st.error(f"엑셀 파일을 읽는 과정에서 오류가 발생했습니다: {e}")
else:
    st.info("💡 시작하려면 상단의 'Browse files' 버튼을 눌러 품질 관리 엑셀 파일을 업로드해 주세요.")
