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
st.markdown("엑셀 품질 검사 데이터를 업로드하고 불합격 항목별 퍼센트 및 Supabase 연동 상태를 관리하세요.")

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
        
        # 기본 요약 지표
        total_rows = len(df)
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric(label="총 검사 건수", value=total_rows)
        with col2:
            st.metric(label="총 컬럼 수", value=len(df.columns))

        # 4. 불합격 항목별 퍼센트 분석 로직
        st.divider()
        st.subheader("🚨 불합격 항목별 분석 및 퍼센트")
        
        # 컬럼 선택 UI (사용자가 직접 판정 및 불합격 사유 컬럼을 고를 수 있도록 제공)
        columns_list = list(df.columns)
        
        c1, c2 = st.columns(2)
        with c1:
            # '판정'이나 'Result'가 포함된 컬럼을 기본값으로 추천
            default_status_idx = next((i for i, col in enumerate(columns_list) if any(k in str(col).lower() for k in ['판정', 'result', 'status', '합격'])), 0)
            status_col = st.selectbox("판정 결과 컬럼 선택 (합격/불합격)", columns_list, index=default_status_idx)
            
        with c2:
            # '사유', '불합격', '항목', 'Reason' 등이 포함된 컬럼을 기본값으로 추천
            default_reason_idx = next((i for i, col in enumerate(columns_list) if any(k in str(col).lower() for k in ['사유', '불합격', '항목', 'reason', 'fail'])), min(1, len(columns_list)-1))
            reason_col = st.selectbox("불합격 사유/항목 컬럼 선택", columns_list, index=default_reason_idx)

        if status_col and reason_col:
            # 불합격 데이터 필터링 (텍스트에 '불합격', 'Fail', '不合格', 'X', 'N' 등이 포함된 행 추출)
            fail_keywords = ['불합격', 'fail', '不合格', 'x', 'n', '부적합']
            
            # 대소문자 구문 없이 판정 컬럼에서 불합격 키워드가 포함된 데이터 추출
            mask = df[status_col].astype(str).str.lower().apply(lambda x: any(kw in x for kw in fail_keywords))
            df_fail = df[mask]
            
            fail_count = len(df_fail)
            pass_count = total_rows - fail_count
            fail_rate = (fail_count / total_rows * 100) if total_rows > 0 else 0
            
            with col3:
                st.metric(label="전체 불합격률", value=f"{fail_rate:.2f}%", delta=f"불합격 {fail_count}건")

            if fail_count > 0:
                st.write(f"#### 🔍 불합격 항목 세부 통계 (총 {fail_count}건)")
                
                # 불합격 항목별 건수 및 퍼센트 계산
                fail_summary = df_fail[reason_col].value_counts().reset_index()
                fail_summary.columns = ['불합격 항목', '건수']
                fail_summary['퍼센트(%)'] = (fail_summary['건수'] / fail_count * 100).round(2)
                
                # 화면에 테이블과 바 차트로 시각화 출력
                st.dataframe(fail_summary, use_container_width=True)
                st.bar_chart(fail_summary.set_index('불합격 항목')['퍼센트(%)'])
            else:
                st.success("🎉 선택한 판정 기준에 따른 불합격 데이터가 없습니다. 모두 합격입니다!")

    except Exception as e:
        st.error(f"엑셀 파일을 읽는 과정에서 오류가 발생했습니다: {e}")
else:
    st.info("💡 시작하려면 상단의 'Browse files' 버튼을 눌러 품질 관리 엑셀 파일을 업로드해 주세요.")
