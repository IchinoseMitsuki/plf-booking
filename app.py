import streamlit as st
import pandas as pd
import hashlib
import gspread
import pytz
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime, timedelta

# --- 1. 基础配置与 Google Sheets 连接 ---
st.set_page_config(page_title="PLF 预约系统", layout="wide", initial_sidebar_state="expanded")

# 自定义 CSS 保持原样并优化
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&display=swap');
    html, body, [class*="css"] { font-family: 'Inter', -apple-system, sans-serif; }
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    .stDataFrame div[data-testid="stTable"] {
        min-width: 850px;
        border-radius: 12px;
        overflow: hidden;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
    }
    div.stButton > button {
        width: 100%;
        border-radius: 10px !important;
        font-weight: 600 !important;
        transition: all 0.2s ease;
    }
    </style>
    """, unsafe_allow_html=True)

@st.cache_resource
def init_spreadsheet():
    scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
    try:
        creds_info = st.secrets["gcp_service_account"]
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_info, scope)
        client = gspread.authorize(creds)
        # 确保你的 Google 表格列名为：日期, 时段, 姓名, 目的, 显示姓名, 显示目的
        sheet = client.open("PLF_Booking").sheet1 
        return sheet
    except Exception as e:
        st.error(f"无法连接到 Google Sheets: {e}")
        return None

sheet = init_spreadsheet()
ADMIN_PASSWORD = "123456" 

def generate_time_ranges():
    ranges = []
    curr = datetime.strptime("08:00", "%H:%M")
    end = datetime.strptime("22:00", "%H:%M")
    while curr < end:
        next_slot = curr + timedelta(minutes=30)
        range_str = f"{curr.strftime('%H:%M')}-{next_slot.strftime('%H:%M')}"
        ranges.append(range_str)
        curr = next_slot
    return ranges

TIME_RANGES = generate_time_ranges()
DAYS = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]

def load_data():
    if sheet:
        data = sheet.get_all_records()
        if data:
            temp_df = pd.DataFrame(data)
            temp_df['日期'] = temp_df['日期'].astype(str)
            # 兼容旧数据：如果列不存在则创建默认值
            if '显示姓名' not in temp_df.columns: temp_df['显示姓名'] = "是"
            if '显示目的' not in temp_df.columns: temp_df['显示目的'] = "是"
            return temp_df
    return pd.DataFrame(columns=['日期', '时段', '姓名', '目的', '显示姓名', '显示目的'])

df = load_data()

def get_morandi_color(name):
    if name == "空闲": return "#f8f9fa", "#adb5bd"
    h_hex = hashlib.sha256((name + "plf_v3_privacy").encode()).hexdigest()
    h_int = int(h_hex[:8], 16)
    hue = (h_int * 157.3) % 360
    return f"hsl({hue}, 35%, 70%)", "#334155"

# --- 3. 侧边栏与身份认证 ---
with st.sidebar:
    st.markdown("# 🎸 PLF 后台")
    role = st.radio("🔑 身份切换", ["同学", "管理员"], horizontal=True)
    is_admin = False
    if role == "管理员":
        pwd = st.text_input("管理密码", type="password")
        if pwd == ADMIN_PASSWORD: is_admin = True

# --- 4. 核心显示逻辑 (隐私处理) ---
shanghai_tz = pytz.timezone('Asia/Shanghai')
now_sh = datetime.now(shanghai_tz)
weekday = now_sh.weekday()
start_date = now_sh - timedelta(days=weekday) if weekday < 5 else now_sh

week_dates = []
for i in range(7):
    d = start_date + timedelta(days=i)
    week_dates.append(f"{d.strftime('%Y-%m-%d')} ({DAYS[d.weekday()]})")

# 构建矩阵
real_matrix = pd.DataFrame(index=TIME_RANGES, columns=DAYS)
for i, d_str in enumerate(week_dates):
    pure_date = d_str[:10]
    for r_str in TIME_RANGES:
        start_point = r_str.split("-")[0]
        match = df[(df['日期'] == pure_date) & (df['时段'] == start_point)]
        
        if match.empty:
            real_matrix.iloc[TIME_RANGES.index(r_str), i] = "空闲"
        else:
            row = match.iloc[0]
            # 隐私拼接逻辑实现
            # 如果是管理员，直接看原名，否则根据隐私设置显示
            if is_admin:
                real_matrix.iloc[TIME_RANGES.index(r_str), i] = f"{row['姓名']} ({row['目的']})"
            else:
                display_parts = ["已预约"]
                if str(row['显示姓名']) == "是":
                    display_parts.append(row['姓名'])
                if str(row['显示目的']) == "是":
                    display_parts.append(row['目的'])
                
                # 连接字符串：已预约-姓名-目的
                real_matrix.iloc[TIME_RANGES.index(r_str), i] = "-".join(display_parts)

# --- 5. 表格渲染 ---
display_matrix = real_matrix.copy()
display_matrix.columns = [d.replace(" (", "\n(") for d in week_dates]

def style_fn(data):
    s = pd.DataFrame('', index=data.index, columns=data.columns)
    for col_idx in range(len(data.columns)):
        for row_idx in range(len(data.index)):
            val = real_matrix.iloc[row_idx, col_idx]
            bg, txt = get_morandi_color(val)
            s.iloc[row_idx, col_idx] = f'background-color:{bg};color:{txt};text-align:center;font-size:12px;border:0.5px solid #f1f5f9;'
    return s

st.markdown(f"### 🎸 PLF 预约周表 (隐私保护模式)")
st.dataframe(display_matrix.style.apply(style_fn, axis=None), use_container_width=True, height=600)

# --- 6. 交互功能 ---
t1, t2, t3 = st.tabs(["📝 提交预约", "❌ 取消预约", "🔍 管理面板" if is_admin else "🔍 详情"])

with t1:
    with st.form("booking_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        u_name = col1.text_input("乐队名/姓名", placeholder="必填")
        u_aim = col2.text_input("使用目的", placeholder="必填")
        
        st.markdown("##### 🔒 隐私设置 (决定在公开课表中显示哪些信息)")
        c_p1, c_p2 = st.columns(2)
        show_name = c_p1.checkbox("在表格中公开显示【乐队名/姓名】", value=True)
        show_aim = c_p2.checkbox("在表格中公开显示【使用目的】", value=True)
        
        c1, c2, c3 = st.columns(3)
        d_sel = c1.selectbox("日期", week_dates)
        all_pts = [datetime.strptime("08:00", "%H:%M") + timedelta(minutes=30*i) for i in range(29)]
        all_pts_str = [t.strftime("%H:%M") for t in all_pts]
        s_t = c2.selectbox("开始时间", all_pts_str)
        e_t = c3.selectbox("结束时间", all_pts_str, index=4)

        if st.form_submit_button("🚀 提交预约"):
            idx1, idx2 = all_pts_str.index(s_t), all_pts_str.index(e_t)
            pure_date = d_sel[:10]
            if idx2 <= idx1:
                st.error("结束时间需晚于开始时间")
            elif not u_name or not u_aim:
                st.warning("请完整填写姓名和目的")
            else:
                slots = all_pts_str[idx1 : idx2]
                if not df[(df['日期']==pure_date) & (df['时段'].isin(slots))].empty:
                    st.error("时段冲突！")
                else:
                    # 将“是/否”存入表格
                    s_n = "是" if show_name else "否"
                    s_a = "是" if show_aim else "否"
                    for s in slots:
                        sheet.append_row([pure_date, s, u_name, u_aim, s_n, s_a])
                    st.success("预约成功！")
                    st.rerun()

with t2:
    st.markdown("### 🛠️ 取消预约")
    u_n_cancel = st.text_input("输入预约时的姓名核验")
    if u_n_cancel:
        user_df = df[df['姓名'] == u_n_cancel].copy()
        if user_df.empty:
            st.info("无记录")
        else:
            # 简单展示逻辑
            user_df['display'] = user_df['日期'] + " " + user_df['时段']
            to_del = st.multiselect("选择时段", user_df['display'].unique())
            if st.button("确认撤回"):
                # 过滤掉选中的记录并重写表格
                new_df = df[~((df['姓名'] == u_n_cancel) & (df.apply(lambda x: f"{x['日期']} {x['时段']}" in str(to_del), axis=1)))]
                sheet.clear()
                sheet.append_row(['日期', '时段', '姓名', '目的', '显示姓名', '显示目的'])
                if not new_df.empty: sheet.append_rows(new_df.values.tolist())
                st.rerun()

with t3:
    if is_admin:
        st.dataframe(df.sort_values(['日期', '时段']), use_container_width=True)
    else:
        st.info("仅管理员可见详情清单。")




