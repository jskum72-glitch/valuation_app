import streamlit as st
import pandas as pd
from datetime import datetime
from google import genai
import json
import os
import tempfile

st.set_page_config(page_title="AI 기업가치평가 종합 플랫폼", layout="wide")

st.title("🤖 AI 비상장주식 & 기업가치평가 종합 플랫폼 (2026.08 세법반영)")
st.markdown("재무자료 업로드를 통해 비상장주식 평가, 영업권, FCF/EVA, 과점주주 취득세 산출 등을 원스톱으로 처리합니다.")

# --- AI 추출을 위한 Session State 초기화 ---
def init_state(key, default):
    if key not in st.session_state:
        st.session_state[key] = default

init_state("extracted_data", {
    "total_assets": 1000000000,
    "total_liabilities": 400000000,
    "real_estate_assets": 0,
    "stock_assets": 0,
    "inc1_corp": 100000000, "inc1_add": 0, "inc1_sub": 0,
    "inc2_corp": 80000000,  "inc2_add": 0, "inc2_sub": 0,
    "inc3_corp": 50000000,  "inc3_add": 0, "inc3_sub": 0,
    "op_profit": 50000000,
    "depreciation": 10000000,
    "capex": 5000000,
    "nwc_change": 2000000
})
init_state("goodwill_value", 0)

# --- 사이드바: AI 업로드 기능 ---
with st.sidebar:
    st.header("📄 AI 재무자료 종합 추출")
    
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
                    client = genai.Client(api_key=api_key)
                    
                    with tempfile.NamedTemporaryFile(delete=False, suffix=f".{uploaded_file.name.split('.')[-1]}") as tmp:
                        tmp.write(uploaded_file.getvalue())
                        tmp_path = tmp.name

                    myfile = client.files.upload(file=tmp_path)
                    
                    prompt = """
                    업로드된 재무제표(대차대조표, 손익계산서 등) 및 세무조정계산서에서 아래의 항목들을 추출해주세요. 
                    단위는 모두 '원' 단위로 변환해서 출력하세요. (예: 1백만원 -> 1000000). 
                    없거나 모호한 항목은 0으로 처리하세요.

                    추출 항목:
                    1. total_assets: 총자산
                    2. total_liabilities: 총부채
                    3. real_estate_assets: 부동산(토지,건물 등) 자산 가액
                    4. stock_assets: 타법인 주식 자산 가액
                    5. inc1_corp: 직전 1년(가장 최근) 당기순이익 (또는 각사업연도소득금액)
                    6. inc1_add: 직전 1년 세무조정 가산액
                    7. inc1_sub: 직전 1년 세무조정 차감액
                    8. inc2_corp: 2년전 당기순이익
                    9. inc2_add: 2년전 세무조정 가산액
                    10. inc2_sub: 2년전 세무조정 차감액
                    11. inc3_corp: 3년전 당기순이익
                    12. inc3_add: 3년전 세무조정 가산액
                    13. inc3_sub: 3년전 세무조정 차감액
                    14. op_profit: 직전 1년 영업이익
                    15. depreciation: 감가상각비
                    16. capex: 자본적 지출(유형자산 취득액 등)
                    17. nwc_change: 순운전자본 증감액

                    # 반드시 다음 JSON 형태만 출력하세요 (마크다운 ```json 안 붙여도 됨).
                    {"total_assets": 0, "total_liabilities": 0, "real_estate_assets": 0, "stock_assets": 0, "inc1_corp": 0, "inc1_add": 0, "inc1_sub": 0, "inc2_corp": 0, "inc2_add": 0, "inc2_sub": 0, "inc3_corp": 0, "inc3_add": 0, "inc3_sub": 0, "op_profit": 0, "depreciation": 0, "capex": 0, "nwc_change": 0}
                    """
                    
                    models_to_try = ['gemini-3.6-flash', 'gemini-3.6-pro']
                    
                    response = None
                    last_error = None
                    for m_name in models_to_try:
                        try:
                            response = client.models.generate_content(
                                model=m_name,
                                contents=[myfile, prompt]
                            )
                            break 
                        except Exception as e:
                            last_error = e
                            continue
                            
                    if not response:
                        raise last_error
                    
                    result_text = response.text.replace("```json", "").replace("```", "").strip()
                    extracted = json.loads(result_text)
                    
                    for key in st.session_state.extracted_data.keys():
                        if key in extracted:
                            st.session_state.extracted_data[key] = int(extracted[key])
                            
                    st.success("데이터 추출 완료! 각 탭에 자동 반영되었습니다.")
                    
                    client.files.delete(name=myfile.name)
                    os.remove(tmp_path)
                    
                except Exception as e:
                    st.error(f"오류가 발생했습니다: {e}")

# --- 탭 구성 ---
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "1. 비상장주식 평가 (상증세법)", 
    "2. 영업권 평가", 
    "3. FCF/EVA 기업가치평가", 
    "4. 과점주주 취득세 산출", 
    "5. 주주이동 명세서"
])

ed = st.session_state.extracted_data

with tab1:
    st.header("비상장주식 1주당 평가액 산출 (2026.08 세법 적용)")
    st.info("💡 2026년 개정 반영: 부동산 또는 주식 비중이 80% 이상인 경우, 순자산가치의 100%를 하한선으로 적용합니다.")
    
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("평가 기본정보")
        eval_date = st.date_input("평가기준일", value=datetime.today())
        face_value = st.number_input("1주당 액면가액", value=5000, step=100)
        total_shares = st.number_input("발행주식총수", value=40000, step=1000)
        
    with col2:
        st.subheader("재무 상태 입력 (AI 연동)")
        total_assets = st.number_input("총자산", value=ed["total_assets"], step=1000000)
        total_liab = st.number_input("총부채", value=ed["total_liabilities"], step=1000000)
        real_estate = st.number_input("부동산 자산", value=ed["real_estate_assets"], step=1000000)
        stock_asset = st.number_input("주식 자산", value=ed["stock_assets"], step=1000000)
        
    st.subheader("최근 3년간 순손익액")
    cols = st.columns(3)
    inc_corp = [0]*3; inc_add = [0]*3; inc_sub = [0]*3; inc_net = [0]*3
    weights = [3, 2, 1]
    
    for i in range(3):
        with cols[i]:
            st.markdown(f"**직전 {i+1}년**")
            inc_corp[i] = st.number_input(f"당기순이익 ({i+1}년전)", value=ed[f"inc{i+1}_corp"])
            inc_add[i] = st.number_input(f"가산액 ({i+1}년전)", value=ed[f"inc{i+1}_add"])
            inc_sub[i] = st.number_input(f"차감액 ({i+1}년전)", value=ed[f"inc{i+1}_sub"])
            inc_net[i] = inc_corp[i] + inc_add[i] - inc_sub[i]
            st.write(f"👉 **순손익액: {inc_net[i]:,.0f} 원**")

    # 가치 계산 로직
    # 1. 1주당 순손익가치
    weighted_income = (inc_net[0]*3 + inc_net[1]*2 + inc_net[2]*1) / 6
    if weighted_income < 0: weighted_income = 0
    per_share_income_val = (weighted_income / total_shares) / 0.1  # 10% 이자율 가정
    
    # 2. 1주당 순자산가치
    goodwill = st.session_state.goodwill_value
    net_asset = (total_assets - total_liab) + goodwill
    per_share_asset_val = net_asset / total_shares if total_shares > 0 else 0
    
    # 3. 비중 평가 및 가중평균 비율 결정
    real_estate_ratio = real_estate / total_assets if total_assets > 0 else 0
    stock_ratio = stock_asset / total_assets if total_assets > 0 else 0
    
    ratio_text = "일반 법인 (손익 3 : 자산 2)"
    weight_income = 0.6
    weight_asset = 0.4
    
    if real_estate_ratio >= 0.5:
        ratio_text = "부동산 과다 법인 (손익 2 : 자산 3)"
        weight_income = 0.4
        weight_asset = 0.6
        
    weighted_avg_val = (per_share_income_val * weight_income) + (per_share_asset_val * weight_asset)
    
    # 2026년 개정 세법 하한선 결정 로직
    if real_estate_ratio >= 0.8 or stock_ratio >= 0.8:
        floor_limit = per_share_asset_val * 1.0  # 100% 하한선 적용
        floor_reason = "순자산가치 100% 하한 적용 (부동산 또는 주식 80% 이상)"
    else:
        floor_limit = per_share_asset_val * 0.8  # 80% 하한선 적용
        floor_reason = "순자산가치 80% 하한 적용 (일반)"
        
    final_val = max(weighted_avg_val, floor_limit)
    
    st.divider()
    st.subheader("📊 1주당 평가 결과")
    st.write(f"- 1주당 순손익가치: **{per_share_income_val:,.0f} 원**")
    st.write(f"- 1주당 순자산가치: **{per_share_asset_val:,.0f} 원** (영업권 {goodwill:,.0f} 원 반영)")
    st.write(f"- 적용비율: **{ratio_text}**")
    st.write(f"- 가중평균액: **{weighted_avg_val:,.0f} 원**")
    st.write(f"- 하한선 방어: **{floor_limit:,.0f} 원** ({floor_reason})")
    
    st.success(f"### 🏆 최종 1주당 평가액 : {final_val:,.0f} 원")

with tab2:
    st.header("영업권(Goodwill) 평가 (2026.08 기준)")
    st.markdown("최근 3년간 가중평균 순손익액의 50%가 순자산가액의 10%를 초과하는 경우, 초과액을 5년간 현가 할인하여 영업권을 산출합니다.")
    
    st.write(f"- 3년 가중평균 순손익액: **{weighted_income:,.0f} 원**")
    st.write(f"- 영업권 차감 전 순자산가액: **{total_assets - total_liab:,.0f} 원**")
    
    goodwill_base = (weighted_income * 0.5) - ((total_assets - total_liab) * 0.1)
    if goodwill_base > 0:
        # 현가계수 (10% 5년 = 약 3.79079)
        pv_factor = 3.79079
        calculated_goodwill = goodwill_base * pv_factor
    else:
        calculated_goodwill = 0
        
    st.write(f"- 영업권 평가 대상액 (초과수익): **{max(0, goodwill_base):,.0f} 원**")
    st.metric(label="산출된 영업권 가액", value=f"{calculated_goodwill:,.0f} 원")
    
    if st.button("순자산가치에 영업권 반영하기"):
        st.session_state.goodwill_value = calculated_goodwill
        st.rerun()

with tab3:
    st.header("FCF / EVA 기업가치평가")
    st.write("잉여현금흐름(FCF) 기반의 본질적 가치(Intrinsic Value)를 산출합니다.")
    
    col1, col2 = st.columns(2)
    with col1:
        op_profit = st.number_input("영업이익", value=ed["op_profit"])
        tax_rate = st.number_input("법인세율 (%)", value=19.0, step=1.0) / 100
        depreciation = st.number_input("감가상각비", value=ed["depreciation"])
    with col2:
        capex = st.number_input("CAPEX (자본적지출)", value=ed["capex"])
        nwc_change = st.number_input("순운전자본 증감", value=ed["nwc_change"])
        wacc = st.number_input("WACC (가중평균자본비용, %)", value=10.0) / 100
        g = st.number_input("영구성장률 (%)", value=2.0) / 100
        
    nopat = op_profit * (1 - tax_rate)
    fcf = nopat + depreciation - capex - nwc_change
    
    st.write(f"- **세후영업이익(NOPAT):** {nopat:,.0f} 원")
    st.write(f"- **잉여현금흐름(FCF):** {fcf:,.0f} 원")
    
    if wacc > g:
        terminal_value = fcf * (1 + g) / (wacc - g)
        st.success(f"### 📈 계속기업가치 (Terminal Value): {terminal_value:,.0f} 원")
    else:
        st.error("WACC는 영구성장률(g)보다 커야 가치를 산출할 수 있습니다.")

with tab4:
    st.header("과점주주 간주취득세 산출 (2026.08 기준)")
    st.write("비상장법인의 주식을 취득하여 특수관계인 합산 지분율이 50%를 초과(과점주주)하게 된 경우 취득세를 납부해야 합니다.")
    
    c1, c2 = st.columns(2)
    with c1:
        total_s = st.number_input("발행주식총수 (회사전체)", value=total_shares, key="t4_ts")
        book_value = st.number_input("법인의 취득세 과세대상 장부가액 합계", value=500000000, step=10000000)
    with c2:
        before_shares = st.number_input("취득 전 특수관계인 합산 주식수", value=20000)
        after_shares = st.number_input("취득 후 특수관계인 합산 주식수", value=21000)
        
    before_ratio = before_shares / total_s if total_s > 0 else 0
    after_ratio = after_shares / total_s if total_s > 0 else 0
    
    st.write(f"취득 전 지분율: {before_ratio*100:.2f}% ➡️ 취득 후 지분율: **{after_ratio*100:.2f}%**")
    
    if after_ratio > 0.5:
        st.warning("⚠️ 과점주주 요건(50% 초과)을 충족하여 간주취득세 납부 대상입니다.")
        increase_ratio = after_ratio - before_ratio if before_ratio >= 0.5 else after_ratio
        if before_ratio < 0.5:
            st.info("최초 과점주주 성립: 전체 지분율에 대해 과세")
        else:
            st.info("기존 과점주주의 지분 증가: 증가분에 대해서만 과세")
            
        tax_base = book_value * increase_ratio
        acq_tax = tax_base * 0.02
        rural_tax = acq_tax * 0.1
        
        st.write(f"- 과세표준: {tax_base:,.0f} 원")
        st.error(f"**총 납부세액: {acq_tax + rural_tax:,.0f} 원** (취득세 {acq_tax:,.0f}원 + 농특세 {rural_tax:,.0f}원)")
    else:
        st.success("지분율 50% 이하로 과점주주 취득세 납부 대상이 아닙니다.")

with tab5:
    st.header("주식 및 주주이동 명세서 (2026.08 서식)")
    
    default_df = pd.DataFrame([
        {"주주명": "홍길동", "관계": "본인", "기초주식수": 10000, "당기취득": 2000, "당기양도": 0, "기말주식수": 12000},
        {"주주명": "김철수", "관계": "타인", "기초주식수": 5000, "당기취득": 0, "당기양도": 2000, "기말주식수": 3000},
    ])
    
    st.write("아래 표를 직접 클릭하여 주주 이동 내역을 수정하고 추가할 수 있습니다.")
    edited_df = st.data_editor(default_df, num_rows="dynamic", use_container_width=True)
    
    current_total = edited_df["기말주식수"].sum()
    if current_total == total_shares:
        st.success(f"기말주식수 합계({current_total})가 발행주식총수({total_shares})와 일치합니다.")
    else:
        st.error(f"오류: 기말주식수 합계({current_total})가 발행주식총수({total_shares})와 일치하지 않습니다.")
