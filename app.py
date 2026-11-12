import io
import pandas as pd
import plotly.express as px
import streamlit as st

st.set_page_config(
    page_title="다이소 품질 및 불합격 분석 대시보드", page_icon="📊", layout="wide"
)

st.title("📦 다이소 품질 검사 및 불합격 분석 대시보드")
st.markdown(
    "엑셀 파일을 업로드하면 **D열 납품업체 그룹핑(3개사 통합)** 및 **불합격 항목/업체별 불합격률**을 실시간으로 분석합니다."
)

# 1. 파일 업로드 섹션
uploaded_file = st.file_uploader(
    "검사/시험 결과 마스터 엑셀 파일(.xlsx)을 업로드하세요", type=["xlsx", "xls"]
)

if uploaded_file is not None:
  # 엑셀 데이터 로드
  df = pd.read_excel(uploaded_file)

  st.success("엑셀 파일이 성공적으로 업로드되었습니다!")

  with st.expander("📄 업로드된 데이터 미리보기"):
    st.dataframe(df.head(10))

  # 컬럼 확인 및 매핑 (필요시 조정 가능)
  columns = df.columns.tolist()

  st.sidebar.header("⚙️ 데이터 컬럼 매핑 설정")
  # 기본적으로 4번째 열(인덱스 3, D열)을 납품업체로 지정
  default_vendor_col = columns[3] if len(columns) > 3 else columns[0]
  vendor_col = st.sidebar.selectbox(
      "납품업체 컬럼 (D열 매칭)", columns, index=columns.index(default_vendor_col)
  )

  item_col = st.sidebar.selectbox(
      "시험/검사 항목 컬럼", columns, index=1 if len(columns) > 1 else 0
  )
  result_col = st.sidebar.selectbox(
      "판정 결과 컬럼 (예: 합격/불합격)",
      columns,
      index=2 if len(columns) > 2 else 0,
  )
  applicant_col = st.sidebar.selectbox(
      "신청업체 컬럼", columns, index=0 if len(columns) > 0 else 0
  )

  # 2. D열 납품업체 3가지 통합 로직 (사용자 정의 매핑)
  st.sidebar.markdown("---")
  st.sidebar.subheader("🔗 D열 납품업체 3개사 통합 설정")
  st.sidebar.info(
      "지정된 3개의 납품업체명을 하나의 통합 그룹명으로 묶습니다."
  )

  unique_vendors = df[vendor_col].dropna().unique().tolist()
  selected_vendors = st.sidebar.multiselect(
      "통합할 3개의 납품업체 선택", unique_vendors
  )
  group_name = st.sidebar.text_input(
      "통합 그룹 바이어명 입력", value="다이소 통합 그룹"
  )

  # 데이터 복사본 생성 후 그룹핑 적용
  analysis_df = df.copy()
  if selected_vendors:
    analysis_df["통합_납품업체"] = analysis_df[vendor_col].apply(
        lambda x: group_name if x in selected_vendors else x
    )
  else:
    analysis_df["통합_납품업체"] = analysis_df[vendor_col]

  # 3. 불합격 데이터 필터링
  # 불합격 키워드 정의 (불합격, FAIL, 부적합 등)
  fail_keywords = ["불합격", "FAIL", "fail", "부적합", "불가"]
  analysis_df["is_fail"] = analysis_df[result_col].astype(str).str.contains(
      "|".join(fail_keywords), na=False
  )

  # 상단 주요 지표 (KPI) 요약
  total_tests = len(analysis_df)
  total_fails = analysis_df["is_fail"].sum()
  overall_fail_rate = (
      (total_fails / total_tests) * 100 if total_tests > 0 else 0
  )

  col1, col2, col3 = st.columns(3)
  col1.metric("총 검사 건수", f"{total_tests:,} 건")
  col2.metric("총 불합격 건수", f"{total_fails:,} 건", delta_color="inverse")
  col3.metric("전체 불합격률", f"{overall_fail_rate:.2f}%")

  st.markdown("---")

  # 4. 시각화 대시보드 구성
  col_a, col_b = st.columns(2)

  with col_a:
    st.subheader("❌ 주요 불합격 항목 순위 (Top Items)")
    fail_df = analysis_df[analysis_df["is_fail"]]
    if not fail_df.empty:
      fail_item_counts = (
          fail_df[item_col].value_counts().reset_index()
      )  # pandas 2.0+ 호환
      fail_item_counts.columns = ["시험항목", "불합격건수"]

      fig_item = px.bar(
          fail_item_counts.head(10),
          x="불합격건수",
          y="시험항목",
          orientation="h",
          title="항목별 불합격 빈도수",
          text="불합격건수",
      )
      fig_item.update_layout(yaxis={"categoryorder": "total ascending"})
      st.plotly_chart(fig_item, use_container_width=True)
    else:
      st.info("불합격 데이터가 없습니다.")

  with col_b:
    st.subheader("🏢 신청업체별 불합격 현황")
    if not fail_df.empty:
      applicant_fail_counts = (
          fail_df[applicant_col].value_counts().reset_index()
      )
      applicant_fail_counts.columns = ["신청업체", "불합격건수"]

      fig_app = px.pie(
          applicant_fail_counts.head(10),
          names="신청업체",
          values="불합격건수",
          title="신청업체별 불합격 비중",
          hole=0.4,
      )
      st.plotly_chart(fig_app, use_container_width=True)
    else:
      st.info("불합격 데이터가 없습니다.")

  # 5. 통합 납품업체(D열 그룹)별 품질 분석 테이블
  st.subheader("📋 통합 납품업체별 품질 및 불합격률 분석")
  summary_table = (
      analysis_df.groupby("통합_납품업체")
      .agg(
          총검사건수=(result_col, "count"),
          불합격건수=("is_fail", "sum"),
      )
      .reset_index()
  )
  summary_table["합격건수"] = (
      summary_table["총검사건수"] - summary_table["불합격건수"]
  )
  summary_table["불합격률(%)"] = (
      (summary_table["불합격건수"] / summary_table["총검사건수"]) * 100
  ).round(2)
  summary_table = summary_table.sort_values(by="불합격건수", ascending=False)

  st.dataframe(summary_table, use_container_width=True)

  # 다운로드 버튼
  buffer = io.BytesIO()
  with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
    summary_table.to_excel(writer, sheet_name="업체별_품질통계", index=False)
    analysis_df.to_excel(writer, sheet_name="전체_분석데이터", index=False)
  buffer.seek(0)

  st.download_button(
      label="📥 분석 결과 보고서 엑셀 다운로드",
      data=buffer,
      file_name="Daiso_Quality_Analysis_Report.xlsx",
      mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
  )

else:
  st.info(
      "💡 상단의 **'Browse files'** 버튼을 클릭하여 다이소 검사 결과 엑셀 파일을"
      " 업로드해 주세요."
  )