import streamlit as st
import pandas as pd
from datetime import datetime
from google import genai
import json
import os
import tempfile

st.set_page_config(page_title="AI 비상장주식 1주당 평가액 산출", layout="wide")

st.title("🤖 AI 비상장주식 1주당 평가액 산출 플랫폼")
st.markdown("""
재무제표, 세무조정계산서 등 **재무자료(PDF 또는 이미지)**를 업로드하면 AI가 자동으로 숫자를 추출하여 1주당 평가액을 산출합니다.
(수기 입력도 가능합니다.)
""")

# --- AI 추출을 위한 Session State 초기화 ---
if "extracted_data" not in st.session_state:
    st.session_state.extracted_data = {
        "total_assets": 950000000,
        "total_liabilities": 420000000,
        "inc1_corp": 74185899,
        "inc1_add": 0,
        "inc1_sub": 7615459,
        "inc2_corp": 175500704,
        "inc2_add": 0,
        "inc2_sub": 19305077,
        "inc3_corp": 127790231,
        "inc3_add": 0,
        "inc3_sub": 15462618
    }

# --- 사이드바: AI 업로드 기능 ---
with st.sidebar:
    st.header("📄 AI 재무자료 자동 추출")
    
    # Secrets에서 API 키를 먼저 찾음
    secret_api_key = ""
    try:
        secret_api_key = st.secrets.get("GEMINI_API_KEY", "")
    except Exception:
        pass

    if secret_api_key:
        api_key = secret_api_key
        st.success("✅ 시스템 API 키가 연동되어 있습니다.")
    else:
        api_key = st.text_input("Google Gemini API 키 입력", type="password", help="AI 기능을 사용하려면 API 키가 필요합니다.")
        
    uploaded_file = st.file_uploader("재무자료 업로드 (PDF, JPG, PNG)", type=["pdf", "jpg", "jpeg", "png"])
    
    if st.button("🚀 AI로 재무정보 자동 추출하기"):
        if not api_key:
            st.error("API 키를 입력해주세요.")
        elif not uploaded_file:
            st.error("파일을 업로드해주세요.")
        else:
            with st.spinner("AI가 문서를 읽고 숫자를 추출 중입니다... (약 10~20초 소요)"):
                try:
                    # 새로운 google-genai SDK 클라이언트 초기화
                    client = genai.Client(api_key=api_key)
                    
                    # 임시 파일로 저장 (업로드를 위함)
                    with tempfile.NamedTemporaryFile(delete=False, suffix=f".{uploaded_file.name.split('.')[-1]}") as tmp:
                        tmp.write(uploaded_file.getvalue())
                        tmp_path = tmp.name

                    # Gemini에 파일 업로드
                    myfile = client.files.upload(file=tmp_path)
                    
                    # 프롬프트 작성 (강력한 추출 지시)
                    prompt = """
                    당신은 전문 회계사 및 세무사입니다. 업로드된 문서는 기업의 재무제표(재무상태표, 손익계산서 등) 또는 세무조정계산서입니다.
                    문서를 꼼꼼히 분석하여 다음 항목들의 금액(원 단위)을 찾아내어 정확히 JSON 형식으로만 출력해주세요. 
                    찾을 수 없는 값은 0으로 처리하세요.
                    
                    [추출 대상 항목]
                    1. total_assets: 자산총계
                    2. total_liabilities: 부채총계
                    3. inc1_corp: 직전 1년전(최근) 사업연도 소득금액 (또는 당기순이익)
                    4. inc1_add: 직전 1년전 세무조정 가산액 (익금산입 등, 없으면 0)
                    5. inc1_sub: 직전 1년전 세무조정 차감액 (손금산입 등, 없으면 0)
                    6. inc2_corp: 2년전 사업연도 소득금액
                    7. inc2_add: 2년전 세무조정 가산액
                    8. inc2_sub: 2년전 세무조정 차감액
                    9. inc3_corp: 3년전 사업연도 소득금액
                    10. inc3_add: 3년전 세무조정 가산액
                    11. inc3_sub: 3년전 세무조정 차감액

                    # 반드시 다음 JSON 형태만 출력하세요 (마크다운 ```json 안 붙여도 됨).
                    {"total_assets": 0, "total_liabilities": 0, "inc1_corp": 0, "inc1_add": 0, "inc1_sub": 0, "inc2_corp": 0, "inc2_add": 0, "inc2_sub": 0, "inc3_corp": 0, "inc3_add": 0, "inc3_sub": 0}
                    """
                    
                    # 여러 모델을 순차적으로 시도 (구글 서버 업데이트 대응)
                    models_to_try = [
                        'gemini-1.5-flash-latest',
                        'gemini-1.5-pro-latest',
                        'gemini-2.0-flash',
                        'gemini-2.5-flash'
                    ]
                    
                    response = None
                    last_error = None
                    for m_name in models_to_try:
                        try:
                            response = client.models.generate_content(
                                model=m_name,
                                contents=[myfile, prompt]
                            )
                            break # 성공하면 루프 탈출
                        except Exception as e:
                            last_error = e
                            continue
                            
                    if not response:
                        raise last_error
                    
                    # 응답 파싱
                    result_text = response.text.replace("```json", "").replace("```", "").strip()
                    extracted = json.loads(result_text)
                    
                    # Session state 업데이트
                    for key in st.session_state.extracted_data.keys():
                        if key in extracted:
                            st.session_state.extracted_data[key] = int(extracted[key])
                            
                    st.success("데이터 추출 완료! 우측 입력칸에 자동 반영되었습니다.")
                    
                    # 정리
                    client.files.delete(name=myfile.name)
                    os.remove(tmp_path)
                    
                except Exception as e:
                    st.error(f"오류가 발생했습니다: {e}")

# --- 레이아웃: 2단 구성 ---
col_input, col_result = st.columns([1, 1])

with col_input:
    st.header("📝 1. 평가 기본정보 및 재무정보 입력")
    
    with st.expander("기본 정보", expanded=True):
        eval_date = st.date_input("평가기준일", value=datetime(2026, 8, 31))
        face_value = st.number_input("1주당 액면가액 (원)", value=5000, step=100)
        total_shares = st.number_input("발행주식총수 (주)", min_value=1, value=40000, step=1000)
        
        real_estate_flag = st.radio("부동산과다보유법인 여부 (자산 중 부동산 50% 이상)", ["아니오 (N) - 3:2 비율 적용", "예 (Y) - 2:3 비율 적용"])
        asset_only_flag = st.checkbox("순자산가치로만 평가 (설립 3년 미만, 휴폐업, 계속결손법인 등)", value=False)
        
    with st.expander("순자산 가치 산정 자료", expanded=True):
        st.info("평가기준일 현재의 자산 및 부채를 입력합니다.")
        total_assets = st.number_input("자산총계 (원)", value=st.session_state.extracted_data["total_assets"], step=10000000, format="%d")
        total_liabilities = st.number_input("부채총계 (원)", value=st.session_state.extracted_data["total_liabilities"], step=10000000, format="%d")

    with st.expander("최근 3년간 손익 자료 (순손익가치 산정용)", expanded=True):
        st.info("평가기준일 이전 1년, 2년, 3년의 법인세법상 각 사업연도 소득금액 및 세무조정 사항을 입력합니다.")
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.markdown("**이전 1년 (최근)**")
            inc1_corp = st.number_input("소득금액 (1년전)", value=st.session_state.extracted_data["inc1_corp"], step=1000000)
            inc1_add = st.number_input("세무 가산액 (1년전)", value=st.session_state.extracted_data["inc1_add"], step=1000000)
            inc1_sub = st.number_input("세무 차감액 (1년전)", value=st.session_state.extracted_data["inc1_sub"], step=1000000)
            inc1_net = inc1_corp + inc1_add - inc1_sub
            st.caption(f"순손익액: {inc1_net:,.0f} 원")

        with col2:
            st.markdown("**이전 2년**")
            inc2_corp = st.number_input("소득금액 (2년전)", value=st.session_state.extracted_data["inc2_corp"], step=1000000)
            inc2_add = st.number_input("세무 가산액 (2년전)", value=st.session_state.extracted_data["inc2_add"], step=1000000)
            inc2_sub = st.number_input("세무 차감액 (2년전)", value=st.session_state.extracted_data["inc2_sub"], step=1000000)
            inc2_net = inc2_corp + inc2_add - inc2_sub
            st.caption(f"순손익액: {inc2_net:,.0f} 원")

        with col3:
            st.markdown("**이전 3년**")
            inc3_corp = st.number_input("소득금액 (3년전)", value=st.session_state.extracted_data["inc3_corp"], step=1000000)
            inc3_add = st.number_input("세무 가산액 (3년전)", value=st.session_state.extracted_data["inc3_add"], step=1000000)
            inc3_sub = st.number_input("세무 차감액 (3년전)", value=st.session_state.extracted_data["inc3_sub"], step=1000000)
            inc3_net = inc3_corp + inc3_add - inc3_sub
            st.caption(f"순손익액: {inc3_net:,.0f} 원")

# --- 계산 로직 ---
discount_rate = 0.10

net_asset = total_assets - total_liabilities
per_share_net_asset = net_asset / total_shares if total_shares > 0 else 0

weighted_net_income = (inc1_net * 3 + inc2_net * 2 + inc3_net * 1) / 6
per_share_net_income = weighted_net_income / total_shares if total_shares > 0 else 0
per_share_net_income_value = per_share_net_income / discount_rate if per_share_net_income > 0 else 0

if "예 (Y)" in real_estate_flag:
    weighted_value = (per_share_net_income_value * 2 + per_share_net_asset * 3) / 5
else:
    weighted_value = (per_share_net_income_value * 3 + per_share_net_asset * 2) / 5

if asset_only_flag:
    weighted_value = per_share_net_asset

limit_value = per_share_net_asset * 0.8
final_value = max(weighted_value, limit_value)
is_limit_applied = final_value == limit_value and not asset_only_flag

# --- 결과 출력 ---
with col_result:
    st.header("📄 2. 자동 산출 평가 결과")
    
    st.subheader("1주당 가치 요약")
    mcol1, mcol2, mcol3 = st.columns(3)
    mcol1.metric("1주당 순손익가치", f"{per_share_net_income_value:,.0f} 원")
    mcol2.metric("1주당 순자산가치", f"{per_share_net_asset:,.0f} 원")
    mcol3.metric("최종 1주당 평가액", f"{final_value:,.0f} 원", delta="순자산가치만 적용" if asset_only_flag else ("하한선(80%) 적용" if is_limit_applied else "정상 가중평균"))

    st.divider()
    
    st.markdown("### 🔍 단계별 산출 내역")
    st.markdown(f"""
    **[STEP 1] 순손익가치 산출**
    * 이전 1년 순손익: {inc1_net:,.0f}원 (가중치 3)
    * 이전 2년 순손익: {inc2_net:,.0f}원 (가중치 2)
    * 이전 3년 순손익: {inc3_net:,.0f}원 (가중치 1)
    * 3년간 가중평균 순손익액 = **{weighted_net_income:,.0f} 원**
    * 1주당 가중평균 순손익액 = **{per_share_net_income:,.0f} 원**
    * **1주당 순손익가치** = {per_share_net_income:,.0f}원 ÷ 10% = **{per_share_net_income_value:,.0f} 원**

    **[STEP 2] 순자산가치 산출**
    * 순자산액(자산-부채) = {total_assets:,.0f} - {total_liabilities:,.0f} = **{net_asset:,.0f} 원**
    * **1주당 순자산가치** = {net_asset:,.0f}원 ÷ {total_shares:,.0f}주 = **{per_share_net_asset:,.0f} 원**

    **[STEP 3] 최종 1주당 평가가액 산출**
    * 순자산가치로만 평가 여부: **{'예' if asset_only_flag else '아니오'}**
    * 가중평균액 산정: **{weighted_value:,.0f} 원**
    * 하한선 (순자산가치의 80%): **{limit_value:,.0f} 원**
    * **최종 1주당 평가가액 = {final_value:,.0f} 원**
    """)
