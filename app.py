%%writefile app.py
import streamlit as st
import pandas as pd

# Cấu hình trang
st.set_page_config(page_title="SME Credit Decision Engine", page_icon="🏢", layout="wide")

# ==========================================
# 1. SETUP & MOCK MODEL (DÀNH CHO DOANH NGHIỆP)
# ==========================================

def mock_predict_sme_score(years_operation, cic_score, profit_margin, de_ratio, collateral_coverage):
    """
    Mô phỏng Scorecard cho Doanh nghiệp (SME).
    Input:
        - years_operation: Số năm hoạt động (float)
        - cic_score: Điểm CIC doanh nghiệp (int: 300-1000)
        - profit_margin: Biên lợi nhuận ròng (%) (float)
        - de_ratio: Tỷ lệ Nợ/Vốn chủ sở hữu (%) (float)
        - collateral_coverage: Tỷ lệ giá trị TSĐB/Khoản vay (%) (float)
    """
    base_score = 300 # Điểm sàn
    
    # --- LOGIC TÍNH ĐIỂM (WEIGHT OF EVIDENCE MÔ PHỎNG) ---
    
    # 1. Thâm niên: Càng lâu càng tốt (Max 100 điểm)
    # Ví dụ: 10 năm * 10 = 100 điểm
    p_years = int(min(100, years_operation * 10))
    
    # 2. Uy tín lịch sử: Quan trọng nhất (Max 250 điểm)
    # Mapping điểm CIC sang điểm Scorecard
    p_cic = int((cic_score - 300) * 0.4) 
    
    # 3. Hiệu quả hoạt động: Profit Margin (Max 150 điểm)
    # Margin 20% -> 100 điểm. Margin âm -> 0 điểm.
    p_profit = int(max(0, profit_margin * 5))
    
    # 4. Đòn bẩy tài chính: D/E Ratio (Nghịch biến - Max 100 điểm)
    # D/E càng thấp càng tốt. Nếu D/E > 300% thì 0 điểm.
    # Công thức: 100 - (D/E * 0.3)
    p_de = int(max(0, 100 - (de_ratio * 0.3)))
    
    # 5. Bảo đảm: Tài sản thế chấp (Max 100 điểm)
    # Coverage 100% -> 50 điểm, 200% -> 100 điểm
    p_collateral = int(min(100, collateral_coverage * 0.5))
    
    # Tổng điểm
    total_score = base_score + p_years + p_cic + p_profit + p_de + p_collateral
    final_score = max(0, min(1000, total_score))
    
    # Chi tiết điểm (để vẽ biểu đồ)
    breakdown = {
        "Base Score (Sàn)": base_score,
        "Thâm niên hoạt động": p_years,
        "Lịch sử tín dụng (CIC)": p_cic,
        "Hiệu quả KD (Profit)": p_profit,
        "Cấu trúc vốn (D/E)": p_de,
        "Tài sản đảm bảo": p_collateral
    }
    
    return final_score, breakdown

def map_sme_rating(score):
    # Thang điểm xếp hạng doanh nghiệp (Ví dụ chuẩn Moody's/S&P mapping)
    if score >= 800: return 'AAA (Excellent)'
    elif score >= 700: return 'AA (Very Good)'
    elif score >= 600: return 'A (Good)'
    elif score >= 500: return 'BBB (Average)'
    elif score >= 400: return 'BB (Speculative)'
    else: return 'C (High Risk)'

# ==========================================
# 2. SESSION STATE
# ==========================================
if 'config_sme_rules' not in st.session_state:
    st.session_state['config_sme_rules'] = {
        'max_dpd_threshold': 10,       # Chặn nếu nợ quá hạn > 10 ngày
        'min_capital_req': 2,          # Vốn điều lệ tối thiểu 2 tỷ
        'restricted_industries': True, # Bật rule ngành hạn chế
        'auto_reject_ratings': ['C (High Risk)', 'BB (Speculative)']
    }

if 'sme_result' not in st.session_state:
    st.session_state['sme_result'] = None

# ==========================================
# 3. UI LAYOUT
# ==========================================
st.title("Enterprise Credit Scoring Demo")
st.caption("Hệ thống chấm điểm tín dụng & Phê duyệt tự động cho Khách hàng Doanh nghiệp (SME)")
st.markdown("---")

tab1, tab2, tab3 = st.tabs(["📝 Nhập liệu Hồ sơ", "📊 Phân tích Scorecard", "⚙️ Chính sách Rủi ro"])

# --- TAB 3: CONFIGURATION (POLICY) ---
with tab3:
    st.header("Cấu hình Chính sách Tín dụng (Credit Policy)")
    col_c1, col_c2 = st.columns(2)
    with col_c1:
        st.subheader("Hard Rules (Điều kiện Cần)")
        rule_dpd = st.number_input("Ngưỡng chặn Nợ quá hạn (DPD)", 
                                  value=st.session_state['config_sme_rules']['max_dpd_threshold'],
                                  help="Từ chối ngay nếu khách đang có nợ quá hạn vượt mức này.")
        
        rule_capital = st.number_input("Vốn điều lệ tối thiểu (Tỷ VND)", 
                                      value=st.session_state['config_sme_rules']['min_capital_req'])
        
        rule_industry = st.checkbox("Kích hoạt Blacklist Ngành nghề", 
                                   value=st.session_state['config_sme_rules']['restricted_industries'],
                                   help="Ví dụ: Bất động sản nghỉ dưỡng, Karaoke, Bar...")
        
    with col_c2:
        st.subheader("Risk Appetite (Khẩu vị Rủi ro)")
        all_ratings = ['AAA (Excellent)', 'AA (Very Good)', 'A (Good)', 'BBB (Average)', 'BB (Speculative)', 'C (High Risk)']
        rule_ratings = st.multiselect("Từ chối tự động với Hạng:", 
                                     all_ratings,
                                     default=st.session_state['config_sme_rules']['auto_reject_ratings'])

    if st.button("💾 Lưu cấu hình chính sách", type="primary"):
        st.session_state['config_sme_rules'] = {
            'max_dpd_threshold': rule_dpd, 
            'min_capital_req': rule_capital, 
            'restricted_industries': rule_industry, 
            'auto_reject_ratings': rule_ratings
        }
        st.success("Đã cập nhật chính sách phê duyệt!")

# --- TAB 1: SIMULATOR (INPUT) ---
with tab1:
    col1, col2 = st.columns([1, 1.5])
    
    with col1:
        with st.form("sme_input_form"):
            st.markdown("### 1. Thông tin Tài chính & Phi tài chính")
            
            in_x1 = st.number_input("Số năm hoạt động", min_value=0.5, max_value=50.0, value=3.0, step=0.5)
            in_x2 = st.slider("Điểm tín dụng CIC/PCB (300-1000)", 300, 1000, 650)
            in_x3 = st.slider("Biên lợi nhuận ròng (%)", -20.0, 50.0, 10.0)
            in_x4 = st.slider("Tỷ lệ Nợ / Vốn chủ sở hữu (D/E %)", 0, 500, 120, help="Càng cao càng rủi ro")
            in_x5 = st.slider("Tỷ lệ bao phủ TSĐB (%)", 0, 200, 80, help="Giá trị TSĐB / Giá trị khoản vay")
            
            st.markdown("---")
            st.markdown("### 2. Thông tin Thẩm định (Policy Check)")
            
            in_x6 = st.number_input("Số ngày quá hạn cao nhất (Max DPD)", value=0)
            in_x7 = st.number_input("Vốn điều lệ đăng ký (Tỷ VND)", value=5.0)
            in_x8 = st.selectbox("Ngành nghề kinh doanh", ["Sản xuất", "Thương mại", "Dịch vụ", "BĐS Kinh doanh", "Ngành hạn chế (Karaoke/Bar)"])
            
            submitted = st.form_submit_button("🚀 Chạy Mô hình & Phê duyệt", use_container_width=True)

    with col2:
        if submitted:
            # 1. Tính toán Score
            model_score, score_breakdown = mock_predict_sme_score(in_x1, in_x2, in_x3, in_x4, in_x5)
            model_rating = map_sme_rating(model_score)
            
            # 2. Chạy Rule Engine (Chính sách)
            rules = st.session_state['config_sme_rules']
            reasons = []
            decision = "APPROVE" # Mặc định là duyệt
            
            # Rule 1: DPD
            if in_x6 > rules['max_dpd_threshold']: 
                reasons.append(f"❌ Vi phạm chính sách nợ quá hạn (DPD {in_x6} > {rules['max_dpd_threshold']})")
            
            # Rule 2: Vốn
            if in_x7 < rules['min_capital_req']: 
                reasons.append(f"❌ Vốn điều lệ không đủ điều kiện ({in_x7} < {rules['min_capital_req']} tỷ)")
            
            # Rule 3: Ngành nghề
            if rules['restricted_industries'] and in_x8 == "Ngành hạn chế (Karaoke/Bar)":
                reasons.append(f"❌ Ngành nghề nằm trong danh sách hạn chế ({in_x8})")
            
            # Rule 4: Rating Cut-off
            if model_rating in rules['auto_reject_ratings']:
                reasons.append(f"❌ Hạng tín dụng {model_rating} dưới chuẩn cho vay")
            
            if reasons: 
                decision = "REJECT"

            # 3. Lưu kết quả
            st.session_state['sme_result'] = {
                "score": model_score,
                "rating": model_rating,
                "breakdown": score_breakdown,
                "decision": decision,
                "reasons": reasons
            }
            
            # 4. Hiển thị kết quả (UI Card)
            if decision == "APPROVE":
                st.success(f"## ✅ PHÊ DUYỆT (APPROVE)")
                st.metric("Total Score", f"{model_score}/1000", delta="Đạt chuẩn")
                st.info(f"**Hạng tín dụng:** {model_rating}")
            else:
                st.error(f"## 🚫 TỪ CHỐI (REJECT)")
                st.metric("Total Score", f"{model_score}/1000", delta="-Dưới chuẩn", delta_color="inverse")
                st.warning(f"**Hạng tín dụng:** {model_rating}")
                with st.expander("Xem lý do từ chối", expanded=True):
                    for r in reasons:
                        st.write(r)

# --- TAB 2: EXPLAINABILITY (XAI) ---
with tab2:
    st.header("📊 Giải trình Mô hình (White-box Explanation)")
    
    if st.session_state['sme_result']:
        res = st.session_state['sme_result']
        breakdown = res['breakdown']
        
        col_x1, col_x2 = st.columns([1, 1])
        
        with col_x1:
            st.subheader("Chi tiết điểm thành phần")
            df_b = pd.DataFrame(list(breakdown.items()), columns=['Yếu tố rủi ro', 'Điểm đóng góp'])
            st.dataframe(df_b.style.background_gradient(cmap="Blues"), use_container_width=True)
            
        with col_x2:
            st.subheader("Tác động vào tổng điểm")
            st.bar_chart(data=pd.DataFrame(breakdown, index=[0]).T)
            
        st.markdown("""
        ### 💡 Nhận định nhanh (Automated Insights):
        """)
        
        if breakdown['Cấu trúc vốn (D/E)'] < 30:
            st.write("- ⚠️ **Cấu trúc vốn:** Doanh nghiệp đang sử dụng đòn bẩy tài chính quá cao (D/E Ratio lớn).")
        else:
            st.write("- ✅ **Cấu trúc vốn:** Tỷ lệ nợ ở mức an toàn.")
            
        if breakdown['Hiệu quả KD (Profit)'] > 80:
            st.write("- ✅ **Hiệu quả:** Doanh nghiệp có biên lợi nhuận rất tốt, khả năng trả nợ từ dòng tiền cao.")
            
    else:
        st.info("👈 Vui lòng nhập thông tin doanh nghiệp ở Tab 1 và nhấn 'Chạy Mô hình'")
