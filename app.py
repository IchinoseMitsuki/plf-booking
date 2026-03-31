import streamlit as st
import pandas as pd
import hashlib
import gspread
import pytz
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

# Google Sheets 配置 (适配云端 Secrets 版)
@st.cache_resource
def init_spreadsheet():
    # 定义访问权限范围
    scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
    try:
        # 【核心修改】：从 Streamlit Secrets 中读取你刚才填写的配置
        creds_info = st.secrets["gcp_service_account"]
        
        # 使用 from_json_keyfile_dict 这种方式来解析 Secrets 里的内容
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_info, scope)
        client = gspread.authorize(creds)
        
        # 打开你的 Google 表格
        sheet = client.open("PLF_Booking").sheet1 
        return sheet
    except Exception as e:
        # 如果连接失败，会在网页上显示具体的错误原因
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
    4. 周六开放至下周五的预约。
    5. 周一开放本周末的预约。
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
shanghai_tz = pytz.timezone('Asia/Shanghai')
now_sh = datetime.now(shanghai_tz)
st.markdown(f"## 🎸 PLF预约周表 `v2.0.1`")
st.caption(f"数据实时同步自 Google Sheets | 当前时间: {now_sh.strftime('%Y-%m-%d %H:%M')}")

# --- 修正后的动态日期逻辑 ---
today = now_sh
weekday = today.weekday()  # 获取今天是周几 (0是周一, 5是周六, 6是周日)

# 判断：周一(0)到周五(4)显示本周；周六(5)及以后显示从今天开始的7天
if weekday < 5:
    start_date = today - timedelta(days=weekday)
else:
    start_date = today

# 生成动态日期列表
week_dates = []
for i in range(7):
    d = start_date + timedelta(days=i)
    date_str = d.strftime('%Y-%m-%d')
    day_name = DAYS[d.weekday()]  # 自动匹配对应的星期文字
    week_dates.append(f"{date_str} ({day_name})")
# 5. 构建后台数据矩阵
real_matrix = pd.DataFrame(index=TIME_RANGES, columns=DAYS)

for i, d_str in enumerate(week_dates):
    pure_date = d_str[:10] 
    for r_str in TIME_RANGES:
        start_point = r_str.split("-")[0]
        match = df[(df['日期'] == pure_date) & (df['时段'] == start_point)]
        
        if not match.empty:
            row = match.iloc[0]
            # 读取隐私设置（处理可能为空的情况，默认为True）
            # 注意：Google Sheets 读取回来的可能是字符串 'True'/'False'
            s_name = str(row.get('显示姓名', 'True')).upper() == 'TRUE'
            s_aim = str(row.get('显示目的', 'True')).upper() == 'TRUE'
            
            name_val = row['姓名']
            aim_val = row['目的']
            
            # --- 核心逻辑：根据勾选情况拼接显示文字 ---
            display_text = "已预约"
            if s_name and s_aim:
                display_text = f"已预约-{name_val}-{aim_val}"
            elif s_name:
                display_text = f"已预约-{name_val}"
            elif s_aim:
                display_text = f"已预约-{aim_val}"
            # ---------------------------------------
            
            real_matrix.loc[r_str, DAYS[i]] = display_text
        else:
            real_matrix.loc[r_str, DAYS[i]] = "空闲"

# 这里的 display_matrix 逻辑需要微调
display_matrix = real_matrix.copy()
# 如果不是管理员，由于 real_matrix 已经处理过隐私文字了，直接显示即可
# 不再需要原来的 replace(r'^(?!空闲).*$', value='已占用') 这一行

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

# 在 t1 (提交预约) 的 form 内部修改
with t1:
    with st.form("booking_form", clear_on_submit=True):
        col_name, col_aim = st.columns([1, 1])
        u_n = col_name.text_input("乐队名/姓名 (必填)", placeholder="例如: Chakura")
        u_p = col_aim.text_input("使用目的", placeholder="例如: 乐队合练")
        
        # --- 新增：隐私选项 ---
        c_show_1, c_show_2 = st.columns(2)
        show_name = c_show_1.checkbox("公开显示姓名", value=True)
        show_aim = c_show_2.checkbox("公开显示目的", value=True)
        # --------------------

        # ... (中间的日期和时间选择代码保持不变) ...

        if st.form_submit_button("🚀 提交预约并同步"):
            # ... (校验逻辑保持不变) ...
            else:
                slots = all_points_str[idx1 : idx2] 
                if not df[(df['日期']==pure_date) & (df['时段'].isin(slots))].empty:
                    st.error("⚠️ 时段冲突！")
                else:
                    for s in slots:
                        # 【修改点】：写入 Google Sheets 时增加两列布尔值
                        sheet.append_row([pure_date, s, u_n, u_p, str(show_name), str(show_aim)])
                    st.success(f"✅ 预约成功！")
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







