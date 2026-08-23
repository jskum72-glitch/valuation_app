import streamlit as st
import pandas as pd
from datetime import datetime

st.set_page_config(page_title="비상장주식 1주당 평가액 간편 산출 (상증세법)", layout="wide")

st.title("📊 비상장주식 1주당 평가액 산출 앱 (2026.08 기준)")
st.markdown("""
본 앱은 제공해주신 **비상장주식 1주당 평가액 간편서식 및 주식평가프로그램** 엑셀 파일을 참조하여 작성되었습니다. 
상속세 및 증여세법(제63조, 시행령 제54조~59조)에 근거한 보충적 평가방법을 사용하여 비상장기업의 1주당 주식가치를 산출합니다.
""")

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
        total_assets = st.number_input("자산총계 (원)", value=950000000, step=10000000, format="%d")
        total_liabilities = st.number_input("부채총계 (원)", value=420000000, step=10000000, format="%d")

    with st.expander("최근 3년간 손익 자료 (순손익가치 산정용)", expanded=True):
        st.info("평가기준일 이전 1년, 2년, 3년의 법인세법상 각 사업연도 소득금액 및 세무조정 사항을 입력합니다.")
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.markdown("**이전 1년 (최근)**")
            inc1_corp = st.number_input("소득금액 (1년전)", value=74185899, step=1000000)
            inc1_add = st.number_input("세무 가산액 (1년전)", value=0, step=1000000)
            inc1_sub = st.number_input("세무 차감액 (1년전)", value=7615459, step=1000000)
            inc1_net = inc1_corp + inc1_add - inc1_sub
            st.caption(f"순손익액: {inc1_net:,.0f} 원")

        with col2:
            st.markdown("**이전 2년**")
            inc2_corp = st.number_input("소득금액 (2년전)", value=175500704, step=1000000)
            inc2_add = st.number_input("세무 가산액 (2년전)", value=0, step=1000000)
            inc2_sub = st.number_input("세무 차감액 (2년전)", value=19305077, step=1000000)
            inc2_net = inc2_corp + inc2_add - inc2_sub
            st.caption(f"순손익액: {inc2_net:,.0f} 원")

        with col3:
            st.markdown("**이전 3년**")
            inc3_corp = st.number_input("소득금액 (3년전)", value=127790231, step=1000000)
            inc3_add = st.number_input("세무 가산액 (3년전)", value=0, step=1000000)
            inc3_sub = st.number_input("세무 차감액 (3년전)", value=15462618, step=1000000)
            inc3_net = inc3_corp + inc3_add - inc3_sub
            st.caption(f"순손익액: {inc3_net:,.0f} 원")

# --- 계산 로직 ---
discount_rate = 0.10  # 상증세법상 고시 이자율 10% (순손익가치환원율)

# 1. 순자산가치
net_asset = total_assets - total_liabilities
per_share_net_asset = net_asset / total_shares if total_shares > 0 else 0

# 2. 순손익가치
weighted_net_income = (inc1_net * 3 + inc2_net * 2 + inc3_net * 1) / 6
per_share_net_income = weighted_net_income / total_shares if total_shares > 0 else 0
per_share_net_income_value = per_share_net_income / discount_rate if per_share_net_income > 0 else 0

# 3. 1주당 평가가액 (가중평균)
if "예 (Y)" in real_estate_flag:
    # 부동산과다보유법인: 순손익 2, 순자산 3
    weighted_value = (per_share_net_income_value * 2 + per_share_net_asset * 3) / 5
else:
    # 일반법인: 순손익 3, 순자산 2
    weighted_value = (per_share_net_income_value * 3 + per_share_net_asset * 2) / 5

# 순자산가치로만 평가하는 경우 예외 처리
if asset_only_flag:
    weighted_value = per_share_net_asset

# 하한선: 순자산가치의 80% (법 개정 반영)
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
    * 가중평균액 산정 (부동산과다 여부: {real_estate_flag.split(' ')[0]}): **{weighted_value:,.0f} 원**
    * 하한선 (순자산가치의 80%): **{limit_value:,.0f} 원**
    * **최종 1주당 평가가액 = {final_value:,.0f} 원**
    """)
    
    st.info("""
    **💡 참조 데이터 및 법령 (2026.08 기준)**
    * 본 산출은 참조하신 엑셀파일(`비상장주식1주당평가액간편서식`, `주식평가프로그램`)의 로직을 파이썬으로 구현한 것입니다.
    * '각 사업연도 소득금액'에서 시작하여 세무조정 가산/차감액을 반영한 '순손익액' 도출 로직을 반영하였습니다.
    * 중소기업의 최대주주 할증평가는 현재 조세특례제한법 등에 따라 배제되는 추세이므로 간편 평가에서 제외하였습니다. (필요시 추가 가능)
    """)
