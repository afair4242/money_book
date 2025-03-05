import streamlit as st
import openpyxl as op
import io
import pandas as pd
import requests


HEADERS = {
    "Authorization": "Bearer AmMcKixHW5WauWQYrgdHg8mK35tL2cJJ18mryClN",
    "Content-Type": "application/json"
}


# D1에서 카테고리 키워드 가져오기
def fetch_categories():
    query = {"sql": "SELECT category, keyword FROM categories"}
    response = requests.post(D1_API_URL, headers=HEADERS, json=query)

    if response.status_code == 200:
        data = response.json()
        result = data.get("result", [])
        if result and isinstance(result, list) and "results" in result[0]:
            results = result[0]["results"]
        else:
            st.error("올바른 데이터 형식이 아닙니다.")
            return {}

        category_keywords = {item.get("category", "").strip(): item.get("keyword", "").strip().split(",") for item in results}
        return category_keywords
    else:
        st.error(f"카테고리 데이터를 불러오는 중 오류 발생 (HTTP {response.status_code})")
        return {}

# D1에 카테고리 키워드 업데이트
def update_category_data(category_data):
    success = True
    for category, keywords in category_data.items():
        keyword_str = ", ".join(keywords)
        query = {
            "sql": "INSERT INTO categories (category, keyword) VALUES (?, ?) ON CONFLICT(category) DO UPDATE SET keyword = ?",
            "params": [category, keyword_str, keyword_str]
        }
        response = requests.post(D1_API_URL, headers=HEADERS, json=query)
        if response.status_code != 200:
            success = False
    return success

# D1에서 카테고리 삭제
def delete_category(category):
    query = {
        "sql": "DELETE FROM categories WHERE category = ?",
        "params": [category]
    }
    response = requests.post(D1_API_URL, headers=HEADERS, json=query)
    return response.status_code == 200

# 페이지 설정
st.set_page_config(page_title="엑셀가계부", page_icon="💰")

st.title("엑셀 정산 프로그램")
st.write("홈페이지 제작 또는 기타 개인수익과 카드에 포함되지 않는 항목은 수동입력해야 합니다.")

tab1, tab2, tab3 = st.tabs(["호스팅수입(회사)", "배달수입(개인)", "신용카드 지출정산"])


with tab1:
    #st.subheader("회사수익(호스팅) 정산")
    uploaded_file = st.file_uploader("회사엑셀 파일을 업로드 하세요.", type=["xlsx"],key="file_uploader_1")
    st.write('---')
    if uploaded_file is not None:
        try:
            # 업로드된 파일을 메모리에서 읽기
            wb = op.load_workbook(io.BytesIO(uploaded_file.getvalue()), data_only=True)
            ws = wb.active  # 활성화된 시트 선택

            # 합산할 값 목록
            target_values = {66000, 88000, 385000}
            total_sum = 0
            included_items = []  # 포함된 항목 리스트

            # E열(금액)과 G열(설명) 탐색
            for row in ws.iter_rows(min_row=2, max_row=ws.max_row, min_col=5, max_col=7):  # E, F 컬럼 탐색
                amount = row[0].value  # E열: 금액
                description = row[1].value  # F열: 설명

                if isinstance(amount, (int, float)) and amount in target_values:
                    total_sum += amount
                    included_items.append({"항목": description, "금액": amount})

            # 결과 출력
            st.subheader(f"호스팅 합산: {total_sum} 원")

            # 포함된 항목 테이블 출력
            if included_items:
                st.caption("📌 포함된 항목 목록")
                df = pd.DataFrame(included_items)
                st.table(df)

        except Exception as e:
            st.error(f"파일을 읽는 중 오류가 발생했습니다: {e}")

with tab2:
    #st.subheader("배달수입(개인) 정산")
    # 엑셀 파일 업로드 UI
    uploaded_file = st.file_uploader("개인엑셀 파일을 업로드하세요", type=["xlsx"], key="file_uploader_2")
    st.write('---')
    if uploaded_file is not None:
        try:
            # 업로드된 파일을 메모리에서 읽기
            wb = op.load_workbook(io.BytesIO(uploaded_file.getvalue()), data_only=True)
            ws = wb.active  # 활성화된 시트 선택

            # 정산 금액 초기화
            coupang_total = 0
            baemin_total = 0

            # 정산 내역 저장 리스트
            coupang_details = []
            baemin_details = []

            # 데이터 탐색 (C열: 날짜, E열: 금액, F열: 내용)
            for row in ws.iter_rows(min_row=2, max_row=ws.max_row, min_col=3, max_col=6):  # C, E, F 컬럼 탐색
                date = row[0].value  # C열: 날짜
                amount = row[2].value  # E열: 금액
                description = row[3].value  # F열: 내용

                # 값이 숫자인 경우만 처리
                if isinstance(amount, (int, float)):
                    if description == "쿠팡이츠정산":
                        coupang_total += amount
                        coupang_details.append({"날짜": date, "금액": amount, "내용": description})
                    elif description == "우아한청년들":
                        baemin_total += amount
                        baemin_details.append({"날짜": date, "금액": amount, "내용": description})

            # 전체 합계 계산
            overall_total = coupang_total + baemin_total

            # 결과 출력
            st.subheader(f"쿠팡정산 합계: {coupang_total} 원")
            if coupang_details:
                st.caption("📌 쿠팡이츠정산 내역")
                df_coupang = pd.DataFrame(coupang_details)
                st.table(df_coupang)

            st.subheader(f"배민정산 합계: {baemin_total} 원")
            if baemin_details:
                st.caption("📌 배민정산 내역")
                df_baemin = pd.DataFrame(baemin_details)
                st.table(df_baemin)

            # 전체 합계 출력
            st.markdown("---")
            st.subheader(f"💰 전체 합계: {overall_total} 원")

        except Exception as e:
            st.error(f"파일을 읽는 중 오류가 발생했습니다: {e}")


with tab3:

    # 엑셀 파일 업로드
    uploaded_file = st.file_uploader("신용카드 엑셀 파일을 업로드하세요", type=["xlsx"], key="file_uploader_3")
    st.write('---')
    # 카테고리 로드
    category_keywords = fetch_categories()
    edited_category_keywords = category_keywords.copy()

    # 카테고리 추가 UI
    new_category = st.text_input("새로운 카테고리 추가")
    if new_category and new_category not in edited_category_keywords:
        edited_category_keywords[new_category] = []

    # 카테고리 키워드 수정 및 삭제 UI
    for category in list(edited_category_keywords.keys()):
        col1, col2 = st.columns([4, 1])
        with col1:
            keywords = st.text_input(f"{category} 카테고리 키워드 (쉼표로 구분)", ", ".join(edited_category_keywords[category]))
            edited_category_keywords[category] = [kw.strip() for kw in keywords.split(",") if kw.strip()]
        with col2:
            if st.button("삭제", key=f"delete_{category}"):
                del edited_category_keywords[category]
                delete_category(category)
                st.rerun()

    # 모든 변경 사항 저장
    if st.button("저장"):
        success = update_category_data(edited_category_keywords)
        if success:
            st.success("카테고리가 저장되었습니다.")
            st.rerun()
        else:
            st.error("카테고리 저장 중 오류가 발생했습니다.")


    
    if uploaded_file is not None:
        try:
            wb = op.load_workbook(io.BytesIO(uploaded_file.getvalue()), data_only=True)
            ws = wb.active

            category_totals = {category: 0 for category in edited_category_keywords.keys()}
            category_details = {category: [] for category in edited_category_keywords.keys()}
            unclassified_items = []
            unclassified_total = 0
            overall_total = 0

            for row in ws.iter_rows(min_row=2, max_row=ws.max_row, min_col=5, max_col=6):
                description = row[0].value
                amount = row[1].value

                if isinstance(amount, (int, float)) and isinstance(description, str):
                    matched = False
                    overall_total += amount

                    for category, keywords in edited_category_keywords.items():
                        if any(keyword in description for keyword in keywords):
                            category_totals[category] += amount
                            category_details[category].append({"항목": description, "금액": amount})
                            matched = True
                            break

                    if not matched:
                        unclassified_items.append({"항목": description, "금액": amount})
                        unclassified_total += amount

            for category, total in category_totals.items():
                st.subheader(f"{category} 합계: {total} 원")
                if category_details[category]:
                    df = pd.DataFrame(category_details[category])
                    st.table(df)

            if unclassified_items:
                st.subheader(f"❗ 미분류 항목 합계: {unclassified_total} 원")
                df_unclassified = pd.DataFrame(unclassified_items)
                st.table(df_unclassified)

            st.markdown("---")
            st.subheader(f"💰 전체 합계: {overall_total} 원")

        except Exception as e:
            st.error(f"파일을 읽는 중 오류가 발생했습니다: {e}")
