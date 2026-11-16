import streamlit as st
import pandas as pd
import plotly.express as px
from supabase import create_client, Client

# 1. 페이지 기본 설정
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
        df_fail[company_col] = df_fail[company_col].astype(str).str.strip()

        # 메인 분석 탭과 원본 데이터 탭
        tab1, tab2 = st.tabs(["📊 1. 불합격 종합 분석 (항목 및 업체별)", "📋 2. 상세원본데이터"])
        
        with tab1:
            # --- 상단 KPI 카드 ---
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

                # 5% 이하 '기타' 병합 및 정렬
                cond_others = fail_summary['점유율(%)'] <= 5.0
                if cond_others.any():
                    others_count = fail_summary.loc[cond_others, '발생 건수'].sum()
                    fail_summary_pie = fail_summary[~cond_others].copy()
                    fail_summary_pie = fail_summary_pie.sort_values('발생 건수', ascending=False)
                    others_df = pd.DataFrame([{'불합격 항목': '기타', '발생 건수': others_count, '점유율(%)': round((others_count/fail_count)*100, 1)}])
                    fail_summary_pie = pd.concat([fail_summary_pie, others_df], ignore_index=True)
                else:
                    fail_summary_pie = fail_summary.sort_values('발생 건수', ascending=False)

                premium_colors = ['#3B82F6', '#10B981', '#F59E0B', '#EF4444', '#8B5CF6', '#EC4899', '#06B6D4', '#F97316', '#14B8A6', '#6366F1']
                unique_items = fail_summary_pie['불합격 항목'].tolist()
                color_map = {item: premium_colors[i % len(premium_colors)] for i, item in enumerate(unique_items) if item != '기타'}
                color_map['기타'] = '#4B5563'

                # ==========================================
                # 1-1. 불합격 항목별 점유율 (도너츠 차트)
                # ==========================================
                st.markdown("### 📊 불합격 항목별 점유율")
                col_left1, _ = st.columns([2.2, 0.8])
                
                with col_left1:
                    fig_pie = px.pie(
                        fail_summary_pie, 
                        names='불합격 항목', 
                        values='발생 건수', 
                        hole=0.5,
                        color='불합격 항목',
                        color_discrete_map=color_map
                    )
                    fig_pie.update_traces(
                        textposition='inside', 
                        textinfo='percent+label',
                        textfont=dict(size=18, color='white', family="Arial Black"),
                        marker=dict(line=dict(color='#0E1117', width=2)),
                        sort=False 
                    )
                    fig_pie.update_layout(
                        template='plotly_dark',
                        paper_bgcolor='rgba(0,0,0,0)',
                        plot_bgcolor='rgba(0,0,0,0)',
                        title=None,
                        legend=dict(
                            orientation="v",       
                            yanchor="middle", y=0.5, 
                            xanchor="left", x=1.02,   
                            font=dict(size=22, color="#F9FAFB"),
                            itemsizing="constant",
                            tracegroupgap=10
                        ),
                        margin=dict(t=20, b=20, l=0, r=200), 
                        height=550
                    )
                    st.plotly_chart(fig_pie, use_container_width=True)

                st.divider()

                # ==========================================
                # 1-2. 주요 불합격 빈도 순위 (1번 최다 ~ 10번 최소)
                # ==========================================
                st.markdown("### 📈 주요 불합격 빈도 순위 (1위 ~ 10위)")
                
                top10_reasons = fail_summary.head(10).sort_values('발생 건수', ascending=False).reset_index(drop=True)
                top10_reasons['순위_항목'] = [f"{i+1}. {row['불합격 항목']}" for i, row in top10_reasons.iterrows()]
                bar_color_map = {f"{i+1}. {row['불합격 항목']}": color_map.get(row['불합격 항목'], '#3B82F6') for i, row in top10_reasons.iterrows()}
                
                fig_bar = px.bar(
                    top10_reasons, 
                    x='발생 건수', 
                    y='순위_항목', 
                    orientation='h',
                    text='발생 건수',
                    color='순위_항목',
                    color_discrete_map=bar_color_map
                )
                fig_bar.update_traces(
                    textfont=dict(size=18, color="#F9FAFB", family="Arial Black"), 
                    textposition="outside"
                )
                fig_bar.update_layout(
                    template='plotly_dark',
                    paper_bgcolor='rgba(0,0,0,0)',
                    plot_bgcolor='rgba(0,0,0,0)',
                    showlegend=False,
                    xaxis_title="",
                    yaxis_title="",
                    yaxis=dict(
                        categoryorder="array",
                        categoryarray=top10_reasons['순위_항목'].tolist()[::-1],
                        tickfont=dict(size=18, color="#F9FAFB")
                    ),
                    margin=dict(t=20, b=20, l=10, r=60),
                    height=600
                )
                st.plotly_chart(fig_bar, use_container_width=True)

                st.divider()

                # ==========================================
                # 1-3. 신청업체별 불합격 발생 현황 (도넛 차트)
                # ==========================================
                st.markdown("### 🏢 신청업체별 불합격 발생 현황 (Top 6 및 기타)")
                
                company_fails = df_fail.groupby(company_col).size().reset_index(name='불합격 건수')
                company_fails = company_fails.sort_values('불합격 건수', ascending=False).reset_index(drop=True)
                
                if len(company_fails) > 6:
                    top6_comp = company_fails.iloc[:6].copy()
                    others_comp_count = company_fails.iloc[6:]['불합격 건수'].sum()
                    others_comp_df = pd.DataFrame([{company_col: '기타', '불합격 건수': others_comp_count}])
                    comp_pie_df = pd.concat([top6_comp, others_comp_df], ignore_index=True)
                else:
                    comp_pie_df = company_fails.copy()

                comp_pie_df['도넛_라벨'] = comp_pie_df[company_col].apply(lambda x: str(x).split()[0] if str(x).strip() else str(x))

                comp_unique = comp_pie_df[company_col].tolist()
                comp_color_map = {comp: premium_colors[i % len(premium_colors)] for i, comp in enumerate(comp_unique) if comp != '기타'}
                comp_color_map['기타'] = '#4B5563'
                
                col_left2, _ = st.columns([2.5, 0.5])
                
                with col_left2:
                    fig_comp_pie = px.pie(
                        comp_pie_df,
                        names=company_col,
                        values='불합격 건수',
                        hole=0.5,
                        color=company_col,
                        color_discrete_map=comp_color_map,
                        custom_data=['도넛_라벨']
                    )
                    fig_comp_pie.update_traces(
                        textposition='inside',
                        texttemplate='%{customdata[0]}<br>%{percent}',
                        textfont=dict(size=16, color='white', family="Arial Black"),
                        marker=dict(line=dict(color='#0E1117', width=2)),
                        sort=False
                    )
                    fig_comp_pie.update_layout(
                        template='plotly_dark',
                        paper_bgcolor='rgba(0,0,0,0)',
                        plot_bgcolor='rgba(0,0,0,0)',
                        title=None,
                        legend=dict(
                            orientation="v",
                            yanchor="middle", y=0.5,
                            xanchor="left", x=1.02,
                            font=dict(size=20, color="#F9FAFB"),
                            itemsizing="constant",
                            tracegroupgap=12
                        ),
                        margin=dict(t=20, b=20, l=0, r=320),
                        height=600
                    )
                    st.plotly_chart(fig_comp_pie, use_container_width=True)

                st.markdown("<br>", unsafe_allow_html=True)
                
                # ==========================================
                # 1-4. 전체 업체 불합격 순위 및 사유별 상세 내역 (검색창 삭제, 전체 리스트 표시)
                # ==========================================
                st.markdown("#### 📋 전체 신청업체 불합격 순위 및 사유별 상세 내역")
                
                # 업체별-사유별 교차표 생성 후 총 불합격 건수 기준 내림차순(등수순) 정렬
                cross_tab = pd.crosstab(df_fail[company_col], df_fail[reason_col])
                cross_tab['총 불합격 건수'] = cross_tab.sum(axis=1)
                cross_tab = cross_tab.sort_values(by='총 불합격 건수', ascending=False)
                
                # 등수 컬럼 및 '총 불합격 건수'를 테이블 맨 앞으로 이동
                cross_tab.insert(0, '순위', [f"{i+1}위" for i in range(len(cross_tab))])
                cols = ['순위', '총 불합격 건수'] + [c for c in cross_tab.columns if c not in ['순위', '총 불합격 건수']]
                cross_tab = cross_tab[cols]
                
                # 인덱스(업체명)를 일반 컬럼으로 변환하여 가독성 극대화
                cross_tab_display = cross_tab.reset_index().rename(columns={company_col: '신청업체명'})
                
                # 전체 데이터가 한눈에 펼쳐지도록 높이를 항목 수에 맞춰 자동 계산
                table_height = (len(cross_tab_display) + 1) * 35 + 10
                st.dataframe(
                    cross_tab_display, 
                    use_container_width=True, 
                    hide_index=True,
                    height=table_height
                )
            else:
                st.success("불합격 데이터가 존재하지 않습니다.")

        # ==========================================
        # TAB 2: 상세원본데이터
        # ==========================================
        with tab2:
            st.markdown("#### 📂 엑셀 원본 전체 데이터")
            st.dataframe(df, use_container_width=True, height=700)

    except Exception as e:
        st.error(f"데이터 처리 중 오류가 발생했습니다: {e}")
else:
    st.info("👈 좌측 상단의 사이드바를 열어 다이소 품질 관리 엑셀 파일을 업로드해 주세요.")
