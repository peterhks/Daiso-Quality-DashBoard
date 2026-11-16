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

# --- ★ 다크 모드 강제 적용 CSS ---
st.markdown("""
<style>
    /* 전체 배경을 블랙/다크 그레이 톤으로 변경 */
    .stApp {
        background-color: #0E1117;
        color: #F9FAFB;
    }
    /* 탭 메뉴 및 기본 텍스트 색상 변경 */
    .stMarkdown, .stText, h1, h2, h3, h4, h5, h6, p, label {
        color: #F9FAFB !important;
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

# 3. 사이드바
with st.sidebar:
    st.title("⚙️ 데이터 업로드")
    uploaded_file = st.file_uploader("검사 결과 엑셀 (.xlsx, .xls)", type=["xlsx", "xls"])
    st.divider()
    if supabase is None:
        st.error("⚠️ Supabase 연결 실패")
    else:
        st.success("🟢 Supabase 연동 완료")

# 4. 메인 타이틀
st.title("📦 다이소 협력사 품질(QA) 통합 대시보드")
st.markdown("<br>", unsafe_allow_html=True)

if uploaded_file is not None:
    try:
        file_name = uploaded_file.name.lower()
        engine = 'xlrd' if file_name.endswith('.xls') else 'openpyxl'
        df = pd.read_excel(uploaded_file, engine=engine)
        
        total_rows = len(df)
        
        # 컬럼 자동 매칭
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
        
        # 텍스트 자동 정제
        df_fail[reason_col] = df_fail[reason_col].astype(str) \
            .str.replace('일광견뢰도 : 제논아크법', '일광견뢰도', regex=False) \
            .str.replace('폼알데하이드 함유량=본원', '폼알데하이드', regex=False) \
            .str.replace('납(Pb) 함유량=본원', '납(Pb) 함유량', regex=False)
        df_fail[company_col] = df_fail[company_col].astype(str)

        tab1, tab2, tab3 = st.tabs(["📊 1. 불합격 항목 분석", "🏢 2. 신청업체별 불합격 항목", "📋 3. 상세원본데이터"])
        
        with tab1:
            # 다크 모드용 KPI 카드 스타일
            st.markdown(f"""
            <div style="display: flex; gap: 20px; margin-bottom: 40px;">
                <div style="flex: 1; background: #1F2937; padding: 25px; border-radius: 12px; border: 1px solid #374151; border-left: 6px solid #3B82F6;">
                    <div style="color: #9CA3AF; font-size: 15px; font-weight: 700; margin-bottom: 8px;">총 검사 진행 건수</div>
                    <div style="color: #F9FAFB; font-size: 32px; font-weight: 900;">{total_rows:,} <span style="font-size: 16px; font-weight: normal; color: #9CA3AF;">건</span></div>
                </div>
                <div style="flex: 1; background: #1F2937; padding: 25px; border-radius: 12px; border: 1px solid #374151; border-left: 6px solid #10B981;">
                    <div style="color: #9CA3AF; font-size: 15px; font-weight: 700; margin-bottom: 8px;">최종 합격 건수</div>
                    <div style="color: #10B981; font-size: 32px; font-weight: 900;">{pass_count:,} <span style="font-size: 16px; font-weight: normal; color: #9CA3AF;">건</span></div>
                </div>
                <div style="flex: 1; background: #1F2937; padding: 25px; border-radius: 12px; border: 1px solid #374151; border-left: 6px solid #EF4444;">
                    <div style="color: #9CA3AF; font-size: 15px; font-weight: 700; margin-bottom: 8px;">최종 불합격 건수</div>
                    <div style="color: #EF4444; font-size: 32px; font-weight: 900;">{fail_count:,} <span style="font-size: 16px; font-weight: normal; color: #9CA3AF;">건</span></div>
                </div>
                <div style="flex: 1; background: #1F2937; padding: 25px; border-radius: 12px; border: 1px solid #374151; border-left: 6px solid #8B5CF6;">
                    <div style="color: #9CA3AF; font-size: 15px; font-weight: 700; margin-bottom: 8px;">종합 불합격률(Defect Rate)</div>
                    <div style="color: #8B5CF6; font-size: 32px; font-weight: 900;">{fail_rate:.1f}%</div>
                </div>
            </div>
            """, unsafe_allow_html=True)

            if fail_count > 0:
                fail_summary = df_fail[reason_col].value_counts().reset_index()
                fail_summary.columns = ['불합격 항목', '발생 건수']
                fail_summary['점유율(%)'] = (fail_summary['발생 건수'] / fail_count * 100).round(1)

                # 5% 이하 '기타' 병합 및 정렬 (기타는 무조건 가장 마지막으로)
                cond_others = fail_summary['점유율(%)'] <= 5.0
                if cond_others.any():
                    others_count = fail_summary.loc[cond_others, '발생 건수'].sum()
                    fail_summary_pie = fail_summary[~cond_others].copy()
                    fail_summary_pie = fail_summary_pie.sort_values('발생 건수', ascending=False)
                    others_df = pd.DataFrame([{'불합격 항목': '기타', '발생 건수': others_count, '점유율(%)': round((others_count/fail_count)*100, 1)}])
                    fail_summary_pie = pd.concat([fail_summary_pie, others_df], ignore_index=True)
                else:
                    fail_summary_pie = fail_summary.sort_values('발생 건수', ascending=False)

                # --- ★ 동일 색상 매칭을 위한 Color Map 생성 ---
                premium_colors = ['#3B82F6', '#10B981', '#F59E0B', '#EF4444', '#8B5CF6', '#EC4899', '#06B6D4', '#F97316', '#14B8A6']
                unique_items = fail_summary_pie['불합격 항목'].tolist()
                color_map = {item: premium_colors[i % len(premium_colors)] for i, item in enumerate(unique_items) if item != '기타'}
                color_map['기타'] = '#4B5563' # 기타는 다크 모드에 어울리는 짙은 회색 지정

                st.markdown("### 📊 불합격 항목별 점유율")
                
                # ★ 도너츠 차트를 완전 왼쪽으로 밀착시키기 위해 컬럼 분할 (좌측 60%, 우측 여백 40%)
                col_left, col_right = st.columns([1.5, 1])
                
                with col_left:
                    fig_pie = px.pie(
                        fail_summary_pie, 
                        names='불합격 항목', 
                        values='발생 건수', 
                        hole=0.5,
                        color='불합격 항목',         # 색상 매칭 기준
                        color_discrete_map=color_map  # 매칭된 컬러맵 적용
                    )
                    fig_pie.update_traces(
                        textposition='inside', 
                        textinfo='percent+label',
                        textfont=dict(size=18, color='white', family="Arial Black"),
                        marker=dict(line=dict(color='#0E1117', width=2)), # 다크 테두리
                        sort=False 
                    )
                    fig_pie.update_layout(
                        template='plotly_dark',
                        paper_bgcolor='rgba(0,0,0,0)',
                        plot_bgcolor='rgba(0,0,0,0)',
                        title=None, # 타이틀은 st.markdown으로 위로 뺌
                        legend=dict(
                            orientation="h",       
                            yanchor="top", y=-0.1, 
                            xanchor="left", x=0,   
                            font=dict(size=24, color="#F9FAFB") # ★ 범례 글씨 크기 2배 이상 대폭 확대
                        ),
                        margin=dict(t=10, b=120, l=0, r=0), 
                        height=600
                    )
                    st.plotly_chart(fig_pie, use_container_width=True)

                st.divider()

                # 2. 바 차트 (도너츠와 100% 동일한 색상 적용)
                st.markdown("### 📈 주요 불합격 빈도 순위 (Top 10)")
                
                fig_bar = px.bar(
                    fail_summary.head(10).sort_values('발생 건수', ascending=True), 
                    x='발생 건수', 
                    y='불합격 항목', 
                    orientation='h',
                    text='발생 건수',
                    color='불합격 항목',          # ★ 도너츠와 동일한 기준
                    color_discrete_map=color_map   # ★ 도너츠와 동일한 컬러맵 강제 적용
                )
                fig_bar.update_traces(
                    textfont=dict(size=18, color="#F9FAFB", family="Arial Black"), 
                    textposition="outside"
                )
                fig_bar.update_layout(
                    template='plotly_dark',
                    paper_bgcolor='rgba(0,0,0,0)',
                    plot_bgcolor='rgba(0,0,0,0)',
                    showlegend=False, # 바 차트에서는 항목에 텍스트가 있으므로 범례 숨김
                    xaxis_title="",
                    yaxis_title="",
                    yaxis=dict(tickfont=dict(size=18, color="#F9FAFB")),
                    margin=dict(t=20, b=20, l=10, r=40),
                    height=600
                )
                st.plotly_chart(fig_bar, use_container_width=True)

        with tab2:
            st.markdown("#### 🏢 신청업체별 불합격 발생 현황")
            if fail_count > 0:
                company_fails = df_fail.groupby(company_col).size().reset_index(name='불합격 건수')
                company_fails = company_fails.sort_values('불합격 건수', ascending=False)
                
                st.markdown("##### 📈 주요 불합격 발생 업체 (Top 10)")
                top10_fails = company_fails.head(10)
                
                fig_comp = px.bar(
                    top10_fails, 
                    x=company_col, 
                    y='불합격 건수',
                    text='불합격 건수',
                    color='불합격 건수',
                    color_continuous_scale='Blues'
                )
                fig_comp.update_traces(textposition='outside', textfont=dict(size=18, color='#F9FAFB', family="Arial Black"))
                fig_comp.update_layout(
                    template='plotly_dark',
                    paper_bgcolor='rgba(0,0,0,0)',
                    plot_bgcolor='rgba(0,0,0,0)',
                    xaxis_title="", 
                    yaxis_title="불합격 발생 건수",
                    xaxis=dict(tickfont=dict(size=16, color="#F9FAFB")),
                    coloraxis_showscale=False,
                    margin=dict(t=30, b=20, l=20, r=20),
                    height=500
                )
                st.plotly_chart(fig_comp, use_container_width=True)
                
                st.divider()
                
                st.markdown("##### 🔍 업체명 검색 및 사유별 상세 내역")
                search_term = st.text_input("찾으시는 업체명을 입력하세요 (일부만 입력해도 검색됩니다) 🔎", "")
                
                if search_term:
                    filtered_df = df_fail[df_fail[company_col].str.contains(search_term, case=False, na=False)]
                else:
                    filtered_df = df_fail
                
                if not filtered_df.empty:
                    cross_tab = pd.crosstab(filtered_df[company_col], filtered_df[reason_col], margins=True, margins_name="총계")
                    st.dataframe(cross_tab, use_container_width=True)
                else:
                    st.warning("해당 이름으로 검색된 업체가 없습니다. 다시 입력해 주세요.")
            else:
                st.success("불합격 데이터가 존재하지 않습니다.")

        with tab3:
            st.markdown("#### 📂 엑셀 원본 전체 데이터")
            # 다크 모드 테이블 적용
            st.dataframe(df, use_container_width=True, height=700)

    except Exception as e:
        st.error(f"데이터 처리 중 오류가 발생했습니다: {e}")
else:
    st.info("👈 좌측 상단의 사이드바를 열어 다이소 품질 관리 엑셀 파일을 업로드해 주세요.")
