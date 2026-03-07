import streamlit as st
import pandas as pd
import hashlib
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime, timedelta

# --- 1. 基础配置与 Google Sheets 连接 ---
st.set_page_config(page_title="PLF 预约系统", layout="wide", initial_sidebar_state="expanded")

# --- 深度优化后的自定义 CSS ---
st.markdown("""
    <style>
    /* 1. 字体与背景优化 */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&display=swap');
    html, body, [class*="css"] {
        font-family: 'Inter', -apple-system, sans-serif;
    }

    /* 2. 隐藏默认页眉页脚，美化 Header */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header { background-color: rgba(0,0,0,0); }

    /* 3. 表格响应式与美化 */
    .stDataFrame div[data-testid="stTable"] {
        min-width: 850px;
        border-radius: 12px;
        overflow: hidden;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
    }
    
    /* 4. 按钮样式升级：增加悬停动画 */
    div.stButton > button {
        width: 100%;
        height: 3.2em;
        border-radius: 10px !important;
        background-color: #ffffff;
        color: #1e293b;
        border: 1px solid #e2e8f0 !important;
        font-weight: 600 !important;
        transition: all 0.2s ease;
    }
    div.stButton > button:hover {
        border-color: #6366f1 !important;
        color: #6366f1 !important;
        box-shadow: 0 4px 12px rgba(99, 102, 241, 0.1);
    }
    
    /* 5. 侧边栏卡片化 */
    section[data-testid="stSidebar"] {
        background-color: #f8fafc;
        border-right: 1px solid #f1f5f9;
    }
    
    /* 6. 输入框与标签优化 */
    .stTextInput input, .stSelectbox select {
        border-radius: 8px !important;
    }
    label {
        font-weight: 500 !important;
        color: #475569 !important;
    }

    /* 7. Tab 标签美化 */
    button[data-baseweb="tab"] {
        font-size: 16px;
        font-weight: 500;
        padding: 10px 20px;
        border-radius: 8px 8px 0 0;
    }
    button[data-baseweb="tab"][aria-selected="true"] {
        background-color: rgba(99, 102, 241, 0.05) !important;
        color: #6366f1 !important;
        border-bottom: 2px solid #6366f1 !important;
    }
    </style>
    """, unsafe_allow_html=True)

# Google Sheets 配置 (保持原样)
@st.cache_resource
def init_spreadsheet():
    scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
    try:
        creds = ServiceAccountCredentials.from_json_keyfile_name('credentials.json', scope)
        client = gspread.authorize(creds)
        sheet = client.open("PLF_Booking").sheet1 
        return sheet
    except Exception as e:
        st.error(f"无法连接到 Google Sheets: {e}")
        return None

sheet = init_spreadsheet()
ADMIN_PASSWORD = "123456" 

# 生成时间段格式 (保持原样)
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
TIME_POINTS = [r.split("-")[0] for r in TIME_RANGES] 
DAYS = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]

# --- 2. 数据加载函数 (保持原样) ---
def load_data():
    if sheet:
        data = sheet.get_all_records()
        if data:
            temp_df = pd.DataFrame(data)
            temp_df['日期'] = temp_df['日期'].astype(str)
            return temp_df
    return pd.DataFrame(columns=['日期', '时段', '姓名', '目的'])

df = load_data()

# --- 颜色生成算法 (保持原样) ---
def get_morandi_color(name):
    if name == "空闲": 
        return "#f8f9fa", "#adb5bd"
    h_hex = hashlib.sha256((name + "plf_final_v6_stable_ultra").encode()).hexdigest()
    h_int = int(h_hex[:8], 16)
    hue = (h_int * 157.3) % 360
    saturation = 30 + (h_int % 15) 
    lightness = 60 + (h_int % 10)
    return f"hsl({hue}, {saturation}%, {lightness}%)", "#4a5568"

# 3. 侧边栏优化
with st.sidebar:
    st.markdown("# 🎸 PLF 后台")
    st.info("""
    **💡 预约快速指南**
    1. 查阅右侧表格确认**空闲**。
    2. 使用下方 **“📝 提交预约”**。
    3. 取消请确保姓名一致。
    """)
    st.divider()
    role = st.radio("🔑 身份切换", ["同学", "管理员"], horizontal=True)
    is_admin = False
    if role == "管理员":
        pwd = st.text_input("管理密码", type="password")
        if pwd == ADMIN_PASSWORD:
            is_admin = True
            st.success("管理权限已开启")
        elif pwd:
            st.error("密码错误")

# 4. 标题与状态
st.markdown(f"## 🎸 PLF 排练室预约周表 `v2.0`")
st.caption(f"数据实时同步自 Google Sheets | 当前时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}")

# 计算日期
today = datetime.now()
monday = today - timedelta(days=today.weekday())
week_dates = [f"{(monday + timedelta(days=i)).strftime('%Y-%m-%d')} ({DAYS[i]})" for i in range(7)]

# 5. 构建后台数据矩阵 (逻辑保持一致)
real_matrix = pd.DataFrame(index=TIME_RANGES, columns=DAYS)
for i, d_str in enumerate(week_dates):
    pure_date = d_str[:10] 
    for r_str in TIME_RANGES:
        start_point = r_str.split("-")[0]
        match = df[(df['日期'] == pure_date) & (df['时段'] == start_point)]
        real_matrix.loc[r_str, DAYS[i]] = match.iloc[0]['姓名'] if not match.empty else "空闲"

display_matrix = real_matrix.copy()
if not is_admin:
    display_matrix = display_matrix.replace(to_replace=r'^(?!空闲).*$', value='已占用', regex=True)

display_matrix.columns = [d.replace(" (", "\n(") for d in week_dates]

# 样式函数 (增加边框美化)
def style_fn(data):
    s = pd.DataFrame('', index=data.index, columns=data.columns)
    for col_idx, _ in enumerate(data.columns):
        for row_idx, _ in enumerate(data.index):
            real_val = real_matrix.iloc[row_idx, col_idx]
            bg, txt = get_morandi_color(real_val)
            s.iloc[row_idx, col_idx] = f'background-color:{bg};color:{txt};text-align:center;font-weight:500;border:0.5px solid #f1f5f9;'
    return s

st.dataframe(display_matrix.style.apply(style_fn, axis=None), use_container_width=True, height=600)

st.markdown("---")

# 7. 交互功能布局优化
t1, t2, t3 = st.tabs(["📝 提交预约", "❌ 取消预约", "🔍 管理看板" if is_admin else "🔍 详情清单"])

with t1:
    with st.form("booking_form", clear_on_submit=True):
        col_name, col_aim = st.columns([1, 1])
        u_n = col_name.text_input("乐队名/姓名 (必填)", placeholder="例如: Chakura")
        u_p = col_aim.text_input("使用目的", placeholder="例如: 乐队合练")
        
        c1, c2, c3 = st.columns(3)
        d = c1.selectbox("预约日期", week_dates)
        
        all_points = [datetime.strptime("08:00", "%H:%M") + timedelta(minutes=30*i) for i in range(29)]
        all_points_str = [t.strftime("%H:%M") for t in all_points]
        
        s_t = c2.selectbox("开始时间", all_points_str)
        e_t = c3.selectbox("结束时间", all_points_str, index=min(4, len(all_points_str)-1)) # 默认给个2小时跨度
        
        st.markdown("<br>", unsafe_allow_html=True)
        if st.form_submit_button("🚀 提交预约并同步"):
            idx1, idx2 = all_points_str.index(s_t), all_points_str.index(e_t)
            pure_date = d[:10]
            if idx2 <= idx1:
                st.error("错误：结束时间不能早于或等于开始时间")
            elif not u_n:
                st.warning("请填写姓名")
            else:
                slots = all_points_str[idx1 : idx2] 
                if not df[(df['日期']==pure_date) & (df['时段'].isin(slots))].empty:
                    st.error("⚠️ 时段冲突！该时段已被他人抢先预约")
                else:
                    for s in slots:
                        sheet.append_row([pure_date, s, u_n, u_p])
                    st.success(f"✅ 预约成功！{u_n} 已登记至 {pure_date}")
                    st.rerun()

with t2:
    st.markdown("### 🛠️ 我的预约管理")
    u_n_cancel = st.text_input("输入预约时的姓名进行核验", key="cancel_name_input")
    
    if u_n_cancel:
        user_df = df[df['姓名'] == u_n_cancel].copy()
        if user_df.empty:
            st.info("未找到预约记录，请检查姓名是否输入正确。")
        else:
            # 逻辑保持原样，仅美化显示
            user_df['time_dt'] = pd.to_datetime(user_df['时段'], format='%H:%M', errors='coerce')
            user_df = user_df.dropna(subset=['time_dt']).sort_values(by=['日期', 'time_dt'])
            
            # (合并逻辑保持原样)
            merged_slots = []
            current_group = []
            for i in range(len(user_df)):
                curr_row = user_df.iloc[i]
                if not current_group: current_group.append(curr_row)
                else:
                    last_row = current_group[-1]
                    time_diff = (curr_row['time_dt'] - last_row['time_dt']).total_seconds() / 60
                    if curr_row['日期'] == last_row['日期'] and time_diff == 30:
                        current_group.append(curr_row)
                    else:
                        merged_slots.append(current_group)
                        current_group = [curr_row]
            merged_slots.append(current_group)

            display_options = []
            for group in merged_slots:
                date = group[0]['日期']
                start_t = group[0]['时段']
                end_dt = group[-1]['time_dt'] + timedelta(minutes=30)
                end_t = end_dt.strftime('%H:%M')
                display_options.append(f"{date} {start_t}-{end_t}")
            
            selected_batches = st.multiselect("选择要取消的时段 (可多选)", display_options)
            
            if st.button("🗑️ 确认撤回选中预约"):
                if selected_batches:
                    # 重新读取以确保同步，逻辑保持原样
                    new_df = df[~((df['姓名'] == u_n_cancel) & (df.apply(lambda x: f"{x['日期']} {x['时段']}" in str(selected_batches), axis=1)))]
                    sheet.clear()
                    sheet.append_row(['日期', '时段', '姓名', '目的'])
                    if not new_df.empty:
                        sheet.append_rows(new_df.values.tolist())
                    st.success("已成功撤回。")
                    st.rerun()

with t3:
    if is_admin:
        st.markdown("### 🔐 全量预约清单")
        st.dataframe(df.sort_values(by=['日期', '时段']), use_container_width=True)
        st.divider()
        if st.button("⚠ 清空云端所有数据"):
            if st.checkbox("我确认要永久删除所有记录"):
                sheet.clear()
                sheet.append_row(['日期', '时段', '姓名', '目的'])
                st.success("已清空")
                st.rerun()
    else:
        st.info("🔒 详细清单目前仅对管理员开放。")