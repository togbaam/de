import streamlit as st
import pandas as pd
import time
import random

st.set_page_config(page_title="Credit Decision Engine", page_icon="🛡️", layout="wide")

# ==========================================
# 1. SETUP & MOCK MODEL (CÓ SCORE BREAKDOWN)
# ==========================================

# Hàm này giờ trả về 2 thứ: Tổng điểm VÀ Chi tiết điểm thành phần
def mock_predict_score_detailed(x1, x2, x3, x4, x5):
    base_score = 200 # Điểm cơ bản (Intercept)
    
    # Tính điểm thành phần (Partial Scores)
    # Trong thực tế, đây là logic: Weight of Evidence (WoE) * Coefficient
    p_x1 = int(x1 * 0.5)   # Tuổi càng cao điểm càng tăng nhẹ
    p_x2 = int(x2 * 0.5)   # Điểm cũ (Credit History) ảnh hưởng lớn
    p_x3 = int(x3 / 100)   # Số dư (chia tỷ lệ)
    p_x4 = int((100 - x4) * 2) # Tỷ lệ nợ càng thấp điểm càng cao
    p_x5 = int((5 - x5) * 10)  # Càng ít thẻ tín dụng càng tốt (ví dụ)
    
    # Tổng điểm
    total_score = base_score + p_x1 + p_x2 + p_x3 + p_x4 + p_x5
    
    # Clip score 0-1000
    final_score = max(0, min(1000, total_score))
    
    # Đóng gói chi tiết để giải trình
    breakdown = {
        "Base Score (Điểm sàn)": base_score,
        "X1 - Tuổi": p_x1,
        "X2 - Lịch sử tín dụng": p_x2,
        "X3 - Số dư trung bình": p_x3,
        "X4 - Tỷ lệ Nợ/Thu nhập": p_x4,
        "X5 - Số thẻ sở hữu": p_x5
    }
    
    return final_score, breakdown

def map_rating(score):
    if score >= 750: return 'A'
    elif score >= 650: return 'B'
    elif score >= 550: return 'C'
    elif score >= 450: return 'D'
    else: return 'E'

# ==========================================
# 2. SESSION STATE
# ==========================================
if 'config_rules' not in st.session_state:
    st.session_state['config_rules'] = {
        'x6_max': 50, 'x7_min': 5000, 'x8_blacklist': True, 'fail_ratings': ['E']
    }

if 'last_result' not in st.session_state:
    st.session_state['last_result'] = None

# ==========================================
# 3. UI LAYOUT
# ==========================================
st.title("🛡️ Enterprise Credit Decision Engine")
st.markdown("---")

tab1, tab2, tab3 = st.tabs(["🚀 Thông tin đầu vào", "🔍 Giải thích mô hình", "⚙️ Tùy chỉnh chính sách"])

# --- TAB 3: CONFIGURATION ---
with tab3:
    st.header("Cấu hình Hard Rules")
    col_c1, col_c2 = st.columns(2)
    with col_c1:
        rule_x6 = st.number_input("Ngưỡng chặn Max DPD", value=st.session_state['config_rules']['x6_max'])
        rule_x7 = st.number_input("Ngưỡng chặn Min Income", value=st.session_state['config_rules']['x7_min'])
        rule_x8 = st.checkbox("Rule Blacklist", value=st.session_state['config_rules']['x8_blacklist'])
    with col_c2:
        rule_ratings = st.multiselect("Reject Ratings", ['A', 'B', 'C', 'D', 'E'], default=st.session_state['config_rules']['fail_ratings'])

    if st.button("Lưu Cấu Hình"):
        st.session_state['config_rules'] = {'x6_max': rule_x6, 'x7_min': rule_x7, 'x8_blacklist': rule_x8, 'fail_ratings': rule_ratings}
        st.success("Updated!")

# --- TAB 1: SIMULATOR ---
with tab1:
    col1, col2 = st.columns([1, 2])
    with col1:
        with st.form("input_form"):
            st.markdown("### Nhập liệu hồ sơ (Giả lập API Request)")
            st.markdown("**Biến Mô hình**")
            in_x1 = st.slider("Tuổi", 18, 70, 35)
            in_x2 = st.slider("Credit Score cũ", 300, 850, 650)
            in_x3 = st.number_input("Số dư TB (USD)", value=2000)
            in_x4 = st.slider("Tỷ lệ Nợ/Thu nhập (%)", 0, 100, 30)
            in_x5 = st.slider("Số lượng thẻ tín dụng", 0, 10, 2)
            st.markdown("---")
            st.markdown("**Biến Chính sách**")
            in_x6 = st.number_input("DPD hiện tại", value=0)
            in_x7 = st.number_input("Thu nhập (USD)", value=8000)
            in_x8 = st.checkbox("Blacklist?", value=False)
            submitted = st.form_submit_button("Chấm điểm ngay")

    with col2:
        if submitted:
            # GỌI MODEL MỚI (DETAILED)
            model_score, score_breakdown = mock_predict_score_detailed(in_x1, in_x2, in_x3, in_x4, in_x5)
            model_rating = map_rating(model_score)
            
            # Logic Rule Engine
            rules = st.session_state['config_rules']
            reasons = []
            decision = "APPROVE"
            
            if in_x6 > rules['x6_max']: reasons.append(f"X6 ({in_x6}) > {rules['x6_max']}")
            if in_x7 < rules['x7_min']: reasons.append(f"X7 ({in_x7}) < {rules['x7_min']}")
            if rules['x8_blacklist'] and in_x8: reasons.append("Blacklisted")
            if model_rating in rules['fail_ratings']: reasons.append(f"Rating {model_rating} bị chặn")
            
            if reasons: decision = "REJECT"

            # Lưu session
            st.session_state['last_result'] = {
                "input": [in_x1, in_x2, in_x3, in_x4, in_x5],
                "score": model_score,
                "rating": model_rating,
                "breakdown": score_breakdown, # <--- DỮ LIỆU MỚI QUAN TRỌNG
                "decision": decision,
                "reasons": reasons
            }
            
            # Hiển thị Kết quả tóm tắt ngay tại đây
            if decision == "APPROVE":
                st.success(f"## ✅ APPROVE - Rating {model_rating} ({model_score} điểm)")
            else:
                st.error(f"## ❌ REJECT - Rating {model_rating} ({model_score} điểm)")
                st.write("Lý do:", ", ".join(reasons))

# --- TAB 2: EXPLAINABILITY (XAI) - PHẦN MỚI ---
with tab2:
    st.header("🔍 Giải trình kết quả chấm điểm (Scorecard View)")
    
    if st.session_state['last_result']:
        res = st.session_state['last_result']
        breakdown = res['breakdown']
        
        # 1. Hiển thị bảng chi tiết (Scorecard Table)
        st.subheader("Bảng điểm chi tiết từng biến")
        
        # Tạo DataFrame từ breakdown dict
        df_breakdown = pd.DataFrame(list(breakdown.items()), columns=['Tên biến số', 'Điểm đóng góp'])
        
        # Thêm cột giá trị đầu vào (Input Value) để đối chiếu
        # Lưu ý: Base Score không có input, ta xử lý khéo 1 chút
        input_vals = ["-"] + [str(v) for v in res['input']] # Thêm "-" cho dòng Base Score
        df_breakdown.insert(1, "Giá trị đầu vào", input_vals)
        
        # Style cho bảng: Tô màu điểm đóng góp
        st.dataframe(
            df_breakdown.style.background_gradient(subset=['Điểm đóng góp'], cmap="Greens"),
            use_container_width=True
        )
        
        # 2. Trực quan hóa (Waterfall Chart - Biểu đồ thác nước)
        # Biểu đồ này cực kỳ phổ biến trong Credit Risk để giải thích điểm
        st.subheader("Tác động của từng biến đến tổng điểm")
        
        # Dùng Bar chart đơn giản để mô phỏng Waterfall
        chart_data = pd.DataFrame({
            'Biến số': list(breakdown.keys()),
            'Điểm': list(breakdown.values())
        })
        st.bar_chart(chart_data, x='Biến số', y='Điểm')
        
        st.info("""
        **Cách đọc:**
        - **Base Score:** Điểm khởi đầu của mọi hồ sơ.
        - **Cột cao:** Biến số đó đang giúp tăng điểm tín dụng mạnh.
        - **Cột thấp/âm:** Biến số đó đang kéo tụt điểm của khách hàng.
        """)
    else:
        st.warning("Vui lòng chạy Simulator ở Tab 1 trước.")
