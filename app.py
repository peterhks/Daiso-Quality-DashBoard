import streamlit as st
import pandas as pd
import plotly.express as px
from supabase import create_client, Client

# 1. 페이지 기본 설정 (와이드 레이아웃)
st.set_page_config(
    page_title="다이소 품질 관리 대시보드",
    page_icon="📦",
    layout="wide",
    initial_sidebar_state="collapsed"
)

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

# 3. 사이드바 - 파일 업로드
with st.sidebar:
    st.title("⚙️ 데이터 업로드")
    uploaded_file = st.file_uploader("검사 결과 엑셀 (.xlsx, .xls)", type=["xlsx", "xls"])
    st.divider()
    if supabase is None:
        st.error("⚠️ Supabase 연결 실패")
    else:
        st.success("🟢 Supabase 연동 완료")

# 4. 메인 대시보드 타이틀
st.title("📦 다이소 협력사 품질(QA) 통합 대시보드")
st.markdown("<br>", unsafe_allow_html=True)

if uploaded_file is not None:
    try:
        # 데이터 읽기
        file_name = uploaded_file.name.lower()
        engine = 'xlrd' if file_name.endswith('.xls') else 'openpyxl'
        df = pd.read_excel(uploaded_file, engine=engine)
        
        total_rows = len(df)
        
        # --- 컬럼 자동 매칭 로직 (드롭다운 삭제) ---
        status_col = next((c for c in df.columns if any(k in str(c).lower() for k in ['판정', 'result', 'status', '합격'])), df.columns[0])
        reason_col = next((c for c in df.columns if any(k in str(c).lower() for k in ['시험항목', '사유', '불합격', '항목', 'reason', 'fail'])), df.columns[1] if len(df.columns) > 1 else df.columns[0])
        company_col = next((c for c in df.columns if any(k in str(c).lower() for k in ['업체', '신청인', '협력사', 'client', 'company'])), df.columns[2] if len(df.columns) > 2 else df.columns[0])

        # 불합격 데이터 추출
        fail_keywords = ['불합격', 'fail', '不合格', 'x', 'n', '부적합']
        mask = df[status_col].astype(str).str.lower().apply(lambda x: any(kw in x for kw in fail_keywords))
        df_fail = df[mask].copy()
        
        fail_count = len(df_fail)
        pass_count = total_rows - fail_count
        fail_rate = (fail_count / total_rows * 100) if total_rows > 0 else 0
        
        # --- 요청하신 텍스트 자동 정제 로직 ---
        df_fail[reason_col] = df_fail[reason_col].astype(str) \
            .str.replace('일광견뢰도 : 제논아크법', '일광견뢰도', regex=False) \
            .str.replace('폼알데하이드 함유량=본원', '폼알데하이드', regex=False) \
            .str.replace('납(Pb) 함유량=본원', '납(Pb) 함유량', regex=False)

        # 3개의 탭으로 구조 변경
        tab1, tab2, tab3 = st.tabs(["📊 1. 불합격 항목 분석", "🏢 2. 신청업체별 불합격 항목", "📋 3. 상세원본데이터"])
        
        # ==========================================
        # TAB 1: 불합격 항목 분석
        # ==========================================
        with tab1:
            # 아름다운 HTML/CSS 커스텀 KPI 카드 렌더링
            st.markdown(f"""
            <div style="display: flex; gap: 20px; margin-bottom: 30px;">
                <div style="flex: 1; background: #ffffff; padding: 25px; border-radius: 12px; box-shadow: 0 4px 15px rgba(0,0,0,0.05); border-left: 6px solid #3B82F6;">
                    <div style="color: #6B7280; font-size: 15px; font-weight: 700; margin-bottom: 8px;">총 검사 진행 건수</div>
                    <div style="color: #111827; font-size: 32px; font-weight: 900;">{total_rows:,} <span style="font-size: 16px; font-weight: normal; color: #6B7280;">건</span></div>
                </div>
                <div style="flex: 1; background: #ffffff; padding: 25px; border-radius: 12px; box-shadow: 0 4px 15px rgba(0,0,0,0.05); border-left: 6px solid #10B981;">
                    <div style="color: #6B7280; font-size: 15px; font-weight: 700; margin-bottom: 8px;">최종 합격 건수</div>
                    <div style="color: #10B981; font-size: 32px; font-weight: 900;">{pass_count:,} <span style="font-size: 16px; font-weight: normal; color: #6B7280;">건</span></div>
                </div>
                <div style="flex: 1; background: #ffffff; padding: 25px; border-radius: 12px; box-shadow: 0 4px 15px rgba(0,0,0,0.05); border-left: 6px solid #EF4444;">
                    <div style="color: #6B7280; font-size: 15px; font-weight: 700; margin-bottom: 8px;">최종 불합격 건수</div>
                    <div style="color: #EF4444; font-size: 32px; font-weight: 900;">{fail_count:,} <span style="font-size: 16px; font-weight: normal; color: #6B7280;">건</span></div>
                </div>
                <div style="flex: 1; background: #ffffff; padding: 25px; border-radius: 12px; box-shadow: 0 4px 15px rgba(0,0,0,0.05); border-left: 6px solid #8B5CF6;">
                    <div style="color: #6B7280; font-size: 15px; font-weight: 700; margin-bottom: 8px;">종합 불합격률(Defect Rate)</div>
                    <div style="color: #8B5CF6; font-size: 32px; font-weight: 900;">{fail_rate:.1f}%</div>
                </div>
            </div>
            """, unsafe_allow_html=True)

            if fail_count > 0:
                # 결함 통계 계산
                fail_summary = df_fail[reason_col].value_counts().reset_index()
                fail_summary.columns = ['불합격 항목', '발생 건수']
                fail_summary['점유율(%)'] = (fail_summary['발생 건수'] / fail_count * 100).round(1)

                # --- 5% 이하 항목 '기타'로 묶기 ---
                cond_others = fail_summary['점유율(%)'] <= 5.0
                if cond_others.any():
                    others_count = fail_summary.loc[cond_others, '발생 건수'].sum()
                    fail_summary_pie = fail_summary[~cond_others].copy()
                    others_df = pd.DataFrame([{'불합격 항목': '기타', '발생 건수': others_count, '점유율(%)': round((others_count/fail_count)*100, 1)}])
                    fail_summary_pie = pd.concat([fail_summary_pie, others_df], ignore_index=True)
                else:
                    fail_summary_pie = fail_summary.copy()

                col_chart1, col_chart2 = st.columns(2)
                
                with col_chart1:
                    # 고해상도 시안성 도넛 차트
                    fig_pie = px.pie(
                        fail_summary_pie, 
                        names='불합격 항목', 
                        values='발생 건수', 
                        hole=0.45,
                        color_discrete_sequence=px.colors.qualitative.Set2
                    )
                    fig_pie.update_traces(
                        textposition='inside', 
                        textinfo='percent+label',
                        textfont=dict(size=14, color='white', family="Arial Black"),
                        marker=dict(line=dict(color='#FFFFFF', width=2))
                    )
                    fig_pie.update_layout(
                        title=dict(text="📊 불합격 항목별 점유율 (5% 이하 기타 통합)", font=dict(size=18, color="#1F2937")),
                        legend=dict(orientation="h", yanchor="top", y=-0.1, xanchor="center", x=0.5),
                        margin=dict(t=50, b=20, l=10, r=10),
                        height=450
                    )
                    st.plotly_chart(fig_pie, use_container_width=True)

                with col_chart2:
                    # 가독성 높은 Bar 차트 (기타 묶기 전 전체 데이터용)
                    fig_bar = px.bar(
                        fail_summary.head(10).sort_values('발생 건수', ascending=True), 
                        x='발생 건수', 
                        y='불합격 항목', 
                        orientation='h',
                        text='발생 건수',
                        color='발생 건수',
                        color_continuous_scale='Reds'
                    )
                    fig_bar.update_traces(
                        textfont=dict(size=14, color="black", family="Arial Black"), 
                        textposition="outside"
                    )
                    fig_bar.update_layout(
                        title=dict(text="📈 주요 불합격 빈도 순위 (Top 10)", font=dict(size=18, color="#1F2937")),
                        xaxis_title="",
                        yaxis_title="",
                        coloraxis_showscale=False,
                        margin=dict(t=50, b=20, l=10, r=10),
                        height=450
                    )
                    st.plotly_chart(fig_bar, use_container_width=True)

        # ==========================================
        # TAB 2: 신청업체별 불합격 항목
        # ==========================================
        with tab2:
            st.markdown("#### 🏢 신청업체별 불합격 발생 현황")
            if fail_count > 0:
                company_fails = df_fail.groupby(company_col).size().reset_index(name='불합격 건수')
                company_fails = company_fails.sort_values('불합격 건수', ascending=False)
                
                # 업체별 바 차트
                fig_comp = px.bar(
                    company_fails, 
                    x=company_col, 
                    y='불합격 건수',
                    text='불합격 건수',
                    color='불합격 건수',
                    color_continuous_scale='Blues'
                )
                fig_comp.update_traces(textposition='outside', textfont=dict(size=14, family="Arial Black"))
                fig_comp.update_layout(
                    xaxis_title="신청 업체명", 
                    yaxis_title="불합격 발생 건수",
                    coloraxis_showscale=False,
                    height=500
                )
                st.plotly_chart(fig_comp, use_container_width=True)
                
                # 업체별-사유별 상세 크로스 테이블
                st.markdown("##### 📋 업체 및 사유별 상세 내역")
                cross_tab = pd.crosstab(df_fail[company_col], df_fail[reason_col], margins=True, margins_name="총계")
                st.dataframe(cross_tab, use_container_width=True)
            else:
                st.success("불합격 데이터가 존재하지 않습니다.")

        # ==========================================
        # TAB 3: 상세원본데이터
        # ==========================================
        with tab3:
            st.markdown("#### 📂 엑셀 원본 전체 데이터")
            st.dataframe(df, use_container_width=True, height=600)

    except Exception as e:
        st.error(f"데이터 처리 중 오류가 발생했습니다: {e}")
else:
    st.info("👈 좌측 상단의 사이드바를 열어 다이소 품질 관리 엑셀 파일을 업로드해 주세요.")
