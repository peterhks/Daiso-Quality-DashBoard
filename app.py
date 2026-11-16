import streamlit as st
import pandas as pd
import plotly.express as px
import textwrap
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

# 시험항목 헤더 2줄 줄바꿈 헬퍼 함수
def wrap_header_2lines(text):
    t = str(text).strip()
    if t in ['신청업체명', '순위', '총 불합격 건수']:
        if t == '총 불합격 건수':
            return '총 불합격<br>건수'
        return t
    if ' ' in t:
        parts = t.split(' ', 1)
        return f"{parts[0]}<br>{parts[1]}"
    if len(t) >= 5:
        mid = (len(t) + 1) // 2
        return f"{t[:mid]}<br>{t[mid:]}"
    return t

# 시험항목별 전문 품질 개선 솔루션 매칭 함수
def get_improvement_guide(item_name):
    guides = {
        "땀견뢰도": {
            "cause": "염색 후 수세(Soaping) 불충분으로 인한 미고착 잔류 염료 존재 및 고착제(Fixing Agent) 처리 미흡",
            "action": "① 염색 완료 후 충분한 열탕 수세(Soaping) 공정 강화 ② 원단 소재(면·폴리에스터·혼방)에 적합한 전용 고착제(Fixing Agent) 후처리 적용 ③ 농색(Dark Color) 원단의 경우 승화 견뢰도가 우수한 염료로 교체"
        },
        "pH": {
            "cause": "정련·표백·염색 공정에서 사용된 강산 또는 강알칼리(가성소다 등) 약품의 중화 및 수세 부족",
            "action": "① 최종 수세 단계에서 유기산(초산·구연산 등)을 활용한 정확한 중화 공정(Neutralization) 실시 ② 건조 전 습윤 상태 원단의 간이 pH 체크리스트 의무화(중성 범위 pH 4.0~7.5 유지)"
        },
        "필링": {
            "cause": "단섬유(Staple Fiber) 방적사의 꼬임(연수) 부족, 조직 밀도 저하 및 표면 마찰 저항성 미흡",
            "action": "① 원사 연수(Twist) 상향 조정 및 코마사(Combed Yarn) 등 장섬유 비율 확대 ② 편직·제직 밀도(Gauge) 상향 설계 ③ 항필링(Anti-Pilling) 특수 유연제 후가공 및 모소(Singeing)·효소 감량 처리 병행"
        },
        "세탁견뢰도": {
            "cause": "원단 섬유 조성과 맞지 않는 염료 선정, 열처리(열고정) 온도 미달 및 이염(Staining) 방지 처리 부족",
            "action": "① 반응성 염료 또는 분산 염료의 고착 온도·시간 표준 준수 ② 배색 원단(흰색+농색) 조합 시 사전 이염 테스트 및 고착제 농도 상향 ③ 나일론·폴리 혼방 소재는 환원세정(Reduction Clearing) 필수 진행"
        },
        "마찰견뢰도": {
            "cause": "원단 표면에 과도하게 잔류한 미고착 염료 및 나염(프린트) 바인더 경화 불량",
            "action": "① 습마찰 및 건마찰 개선용 특수 실리콘·우레탄계 마찰견뢰도 증진제 패딩(Padding) 처리 ② 안료 나염 시 바인더 배합 비율 상향 및 큐어링(열경화) 온도·시간 엄수"
        },
        "세탁치수변화율": {
            "cause": "편직·제직 및 텐터(Tenter) 가공 시 과도한 장력(Over-feeding 부족)으로 인한 잔류 응력 발생",
            "action": "① 텐터 가공 시 오버피드(Over-feed) 비율을 높여 원단 수축 여유분 확보 ② 방축가공(Sanforizing) 또는 텀블 건조(Pre-shrinking) 공정 추가 ③ 재단 전 최소 24시간 이상 원단 자연 방치(Relaxation) 실시"
        },
        "일광견뢰도": {
            "cause": "자외선(UV)에 취약한 형광증백제 또는 저견뢰도 염료 사용(특히 파스텔·형광·연한 색상)",
            "action": "① 일광 견뢰도 등급(4급 이상)이 검증된 내광성 전용 염료로 처방 변경 ② 염색 후처리 단계에서 자외선 흡수제(UV Absorber) 동시 처리"
        },
        "폼알데하이드": {
            "cause": "구김 방지(수지 가공), 나염 바인더, 접착 심지 및 포장재에서 유래한 잔류 유리 폼알데하이드",
            "action": "① 논포르말린(Non-Formalin) 또는 초저포르말린 인증 수지·바인더·접착제 사용 ② 가공 후 열풍 건조 및 충분한 수세·환기 공정 거친 후 밀폐 포장"
        },
        "납(Pb) 함유량": {
            "cause": "금속 부자재(단추·지퍼·리벳), PVC 코팅 원단, 도료(페인트) 및 안료 내 중금속 기준치 초과",
            "action": "① 무연(Lead-Free) 인증을 받은 검증된 부자재 협력사 원료로 즉시 교체 ② 도금·코팅 전 원재료 단계에서 XRF(형광X선분석기) 사전 스크리닝 검사 의무화"
        },
        "굽힘강도": {
            "cause": "제품 구조 설계상 하중 집중 부위의 두께 부족, 재질 강성 미달 및 사출 성형 조건 불량",
            "action": "① 하중이 가해지는 연결부·프레임의 리브(Rib) 보강 설계 및 살두께 증대 ② 내충격성·강성이 우수한 엔지니어링 플라스틱 또는 고강도 합금 소재로 변경"
        },
        "손잡이와 대의 강도": {
            "cause": "손잡이와 본체(대) 결합부의 용접·리벳·나사 체결 강도 부족 및 접합 면적 협소",
            "action": "① 접합부 이중 리벳 체결 또는 용접 비드 두께 강화 ② 손잡이 삽입 깊이 연장 및 연결 브라켓 보강 구조 적용"
        },
        "손세탁 후 외관": {
            "cause": "심지 박리, 부자재 탈락·변색, 봉제선 울음(Puckering) 및 원단 표면 보풀·변형 발생",
            "action": "① 접착 심지 프레스 온도·압력·시간 표준화 및 세탁 내구성 테스트 ② 봉제 장력 완화 및 번수 조정으로 봉제선 울음 방지"
        }
    }
    
    # 정확히 일치하거나 핵심 키워드가 포함된 경우 매칭
    for key, val in guides.items():
        if key in item_name or item_name in key:
            return val
            
    # 기본 가이드 (목록 외 신규 항목용)
    return {
        "cause": "원부자재 물성 기준 미달, 가공 공정 조건 편차 또는 완제품 출고 전 사전 품질 검증 누락",
        "action": "① 불합격 로트(Lot) 즉시 격리 및 전수 선별 작업 실시 ② 원부자재 입고 단계 시험성적서(COA) 검증 강화 및 생산 공정 표준(SOP) 재정비"
    }

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
                # 1-4. 전체 신청업체 불합격 순위 및 사유별 상세 내역
                # ==========================================
                st.markdown("#### 📋 전체 신청업체 불합격 순위 및 사유별 상세 내역")
                
                cross_tab = pd.crosstab(df_fail[company_col], df_fail[reason_col])
                cross_tab['총 불합격 건수'] = cross_tab.sum(axis=1)
                cross_tab = cross_tab.sort_values(by='총 불합격 건수', ascending=False)
                
                cross_tab.insert(0, '순위', [f"{i+1}위" for i in range(len(cross_tab))])
                cols = ['순위', '총 불합격 건수'] + [c for c in cross_tab.columns if c not in ['순위', '총 불합격 건수']]
                cross_tab = cross_tab[cols]
                cross_tab_display = cross_tab.reset_index().rename(columns={company_col: '신청업체명'})
                
                html_table = """
                <style>
                    .qa-full-table {
                        width: 100%;
                        border-collapse: collapse;
                        background-color: #111827;
                        color: #F9FAFB;
                        font-size: 13px;
                        border: 1px solid #374151;
                        table-layout: auto;
                    }
                    .qa-full-table th {
                        background-color: #1F2937;
                        color: #F3F4F6;
                        font-weight: 700;
                        padding: 10px 4px;
                        border: 1px solid #374151;
                        text-align: center;
                        vertical-align: middle;
                        line-height: 1.3;
                        word-break: keep-all;
                    }
                    .qa-full-table td {
                        padding: 8px 4px;
                        border: 1px solid #374151;
                        text-align: center;
                        vertical-align: middle;
                    }
                    .qa-full-table td.comp-col {
                        text-align: left;
                        padding-left: 10px;
                        font-weight: 600;
                        white-space: nowrap;
                    }
                    .qa-full-table td.rank-col {
                        font-weight: 700;
                        color: #60A5FA;
                        white-space: nowrap;
                    }
                    .qa-full-table td.total-col {
                        font-weight: 800;
                        color: #F87171;
                        background-color: rgba(239, 68, 68, 0.08);
                    }
                    .qa-full-table tr:hover td {
                        background-color: #1E293B;
                    }
                    .zero-val {
                        color: #4B5563;
                    }
                    .nonzero-val {
                        color: #F9FAFB;
                        font-weight: 700;
                    }
                </style>
                <div style="width: 100%;">
                <table class="qa-full-table">
                    <thead>
                        <tr>
                """
                
                for col in cross_tab_display.columns:
                    wrapped_col = wrap_header_2lines(col)
                    html_table += f"<th>{wrapped_col}</th>"
                
                html_table += "</tr></thead><tbody>"
                
                for _, row in cross_tab_display.iterrows():
                    html_table += "<tr>"
                    for col in cross_tab_display.columns:
                        val = row[col]
                        if col == '신청업체명':
                            html_table += f"<td class='comp-col'>{val}</td>"
                        elif col == '순위':
                            html_table += f"<td class='rank-col'>{val}</td>"
                        elif col == '총 불합격 건수':
                            html_table += f"<td class='total-col'>{val}</td>"
                        else:
                            if val == 0:
                                html_table += f"<td class='zero-val'>0</td>"
                            else:
                                html_table += f"<td class='nonzero-val'>{val}</td>"
                    html_table += "</tr>"
                
                html_table += "</tbody></table></div>"
                st.markdown(html_table, unsafe_allow_html=True)

                st.divider()

                # ==========================================
                # 1-5. 주요 불합격 빈도 순위(Top 10) 항목별 품질 개선 가이드
                # ==========================================
                st.markdown("### 🛠️ 주요 불합격 항목별 품질 개선 가이드 (Top 10 기준)")
                st.markdown("<p style='color: #9CA3AF; font-size: 14px; margin-bottom: 20px;'>상위 불합격 빈도 순위에 집계된 시험항목별 주요 발생 원인 및 생산·공정 개선 대책입니다.</p>", unsafe_allow_html=True)
                
                guide_cards_html = '<div style="display: flex; flex-direction: column; gap: 14px;">'
                
                for i, row in top10_reasons.iterrows():
                    item_name = row['불합격 항목']
                    count = row['발생 건수']
                    share = row['점유율(%)']
                    guide = get_improvement_guide(item_name)
                    badge_color = color_map.get(item_name, '#3B82F6')
                    
                    guide_cards_html += f"""
                    <div style="background: #1F2937; border: 1px solid #374151; border-left: 6px solid {badge_color}; border-radius: 10px; padding: 18px 22px;">
                        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px;">
                            <div style="font-size: 18px; font-weight: 800; color: #F9FAFB;">
                                <span style="color: {badge_color}; margin-right: 6px;">{i+1}위.</span> {item_name}
                            </div>
                            <div style="background: rgba(239, 68, 68, 0.15); color: #F87171; padding: 4px 12px; border-radius: 20px; font-size: 13px; font-weight: 700;">
                                불합격 {count}건 ({share}%)
                            </div>
                        </div>
                        <div style="font-size: 14px; color: #D1D5DB; margin-bottom: 6px; line-height: 1.5;">
                            <strong style="color: #FBBF24;">▪ 주요 원인:</strong> {guide['cause']}
                        </div>
                        <div style="font-size: 14px; color: #E5E7EB; line-height: 1.6;">
                            <strong style="color: #34D399;">▪ 개선 대책:</strong> {guide['action']}
                        </div>
                    </div>
                    """
                
                guide_cards_html += '</div>'
                st.markdown(guide_cards_html, unsafe_allow_html=True)

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
