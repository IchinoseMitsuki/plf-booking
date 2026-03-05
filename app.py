import streamlit as st
import pandas as pd
import os
import hashlib
from datetime import datetime, timedelta

# 1. 基础配置
st.set_page_config(page_title="plf预约系统", layout="wide")

DATA_FILE = "bookings.csv"
ADMIN_PASSWORD = "123456" 

# 生成时间段格式 (例如 08:00-08:30)
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

# 2. 数据加载与基础清洗
if os.path.exists(DATA_FILE):
    try:
        df = pd.read_csv(DATA_FILE)
        df['日期'] = df['日期'].astype(str)
        df = df.dropna(subset=['时段'])
    except:
        df = pd.DataFrame(columns=['日期', '时段', '姓名', '目的'])
else:
    df = pd.DataFrame(columns=['日期', '时段', '姓名', '目的'])

# --- 莫兰蒂色系生成算法 ---
def get_morandi_color(name):
    if name == "空闲": 
        return "#f8f9fa", "#adb5bd"
    h_hex = hashlib.sha256((name + "plf_final_v6_stable").encode()).hexdigest()
    h_int = int(h_hex[:8], 16)
    hue = (h_int * 137.5) % 360
    saturation = 32 + (h_int % 13)
    lightness = 62 + (h_int % 8)
    return f"hsl({hue}, {saturation}%, {lightness}%)", "#4a5568"

# 3. 侧边栏
st.sidebar.title("🎸 plf后台")
role = st.sidebar.radio("身份选择", ["同学", "管理员"])
is_admin = False
if role == "管理员":
    pwd = st.sidebar.text_input("密码", type="password")
    if pwd == ADMIN_PASSWORD:
        is_admin = True
    elif pwd:
        st.sidebar.error("密码错误")

# --- 修改点：标题仅保留 plf ---
st.title("🎸 plf 使用预约周表")

# 4. 计算日期
today = datetime.now()
monday = today - timedelta(days=today.weekday())
week_dates = [(monday + timedelta(days=i)).strftime('%Y-%m-%d') for i in range(7)]

# 5. 构建后台数据矩阵
real_matrix = pd.DataFrame(index=TIME_RANGES, columns=DAYS)
for i, d_str in enumerate(week_dates):
    for r_str in TIME_RANGES:
        start_point = r_str.split("-")[0]
        match = df[(df['日期'] == d_str) & (df['时段'] == start_point)]
        real_matrix.loc[r_str, DAYS[i]] = match.iloc[0]['姓名'] if not match.empty else "空闲"

# 6. 构建显示矩阵
display_matrix = real_matrix.copy()
if not is_admin:
    display_matrix = display_matrix.replace(to_replace=r'^(?!空闲).*$', value='已占用', regex=True)

display_matrix.columns = [f"{DAYS[i]}\n({week_dates[i]})" for i in range(7)]

def style_fn(data):
    s = pd.DataFrame('', index=data.index, columns=data.columns)
    for col_idx, _ in enumerate(data.columns):
        for row_idx, _ in enumerate(data.index):
            real_val = real_matrix.iloc[row_idx, col_idx]
            bg, txt = get_morandi_color(real_val)
            s.iloc[row_idx, col_idx] = f'background-color:{bg};color:{txt};text-align:center;font-weight:500;border:1px solid #e2e8f0;border-radius:2px'
    return s

st.dataframe(display_matrix.style.apply(style_fn, axis=None), use_container_width=True, height=650)

# 7. 交互功能
t1, t2, t3 = st.tabs(["📝 提交预约", "❌ 取消预约", "🔍 详情清单"])

with t1:
    with st.form("booking_form", clear_on_submit=True):
        u_n = st.text_input("乐队名/姓名 (必填 - 取消预约时需再次填写)")
        u_p = st.text_input("使用目的")
        c1, c2, c3 = st.columns(3)
        d = c1.selectbox("预约日期", week_dates)
        
        # 供选择的时间点
        all_points = [datetime.strptime("08:00", "%H:%M") + timedelta(minutes=30*i) for i in range(29)]
        all_points_str = [t.strftime("%H:%M") for t in all_points]
        
        s_t = c2.selectbox("开始时间", all_points_str)
        e_t = c3.selectbox("结束时间", all_points_str, index=len(all_points_str)-1)
        
        if st.form_submit_button("确认提交"):
            idx1, idx2 = all_points_str.index(s_t), all_points_str.index(e_t)
            if idx2 <= idx1:
                st.error("结束时间不合法")
            elif not u_n:
                st.warning("请填写姓名")
            else:
                slots = all_points_str[idx1 : idx2] 
                if not df[(df['日期']==d) & (df['时段'].isin(slots))].empty:
                    st.error("时段冲突！")
                else:
                    new_rows = [[d, s, u_n, u_p] for s in slots]
                    new_df = pd.DataFrame(new_rows, columns=df.columns)
                    df = pd.concat([df, new_df], ignore_index=True)
                    df.to_csv(DATA_FILE, index=False)
                    st.success("预约成功！")
                    st.rerun()

with t2:
    st.subheader("我的预约管理")
    u_n_cancel = st.text_input("请输入预约时的乐队名/姓名", key="cancel_name_input")
    
    if u_n_cancel:
        user_df = df[df['姓名'] == u_n_cancel].copy()
        if user_df.empty:
            st.info("未找到该姓名下的预约记录。")
        else:
            # 安全解析与缝合
            user_df = user_df[user_df['时段'].str.len() == 5]
            user_df['time_dt'] = pd.to_datetime(user_df['时段'], format='%H:%M', errors='coerce')
            user_df = user_df.dropna(subset=['time_dt']).sort_values(by=['日期', 'time_dt'])
            
            merged_slots = []
            if not user_df.empty:
                current_group = []
                for i in range(len(user_df)):
                    curr_row = user_df.iloc[i]
                    if not current_group:
                        current_group.append(curr_row)
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
            
            st.write(f"✅ 您共有 {len(display_options)} 个预约批次：")
            selected_batches = st.multiselect("请选择要取消的完整时段", display_options)
            
            if st.button("确认取消选中批次"):
                if not selected_batches:
                    st.warning("请选择内容。")
                else:
                    for batch in selected_batches:
                        try:
                            b_date, b_range = batch.split(" ")
                            b_start, b_end = b_range.split("-")
                            fmt = '%H:%M'
                            curr = datetime.strptime(b_start, fmt)
                            limit = datetime.strptime(b_end, fmt)
                            to_del_slots = []
                            while curr < limit:
                                to_del_slots.append(curr.strftime(fmt))
                                curr += timedelta(minutes=30)
                            df = df[~((df['日期'] == b_date) & (df['时段'].isin(to_del_slots)) & (df['姓名'] == u_n_cancel))]
                        except: continue
                    df.to_csv(DATA_FILE, index=False)
                    st.success("选定的预约已撤回！")
                    st.rerun()
    else:
        st.caption("提示：输入姓名后即可管理您的预约记录。")

with t3:
    if is_admin:
        st.subheader("管理员详情看板")
        st.dataframe(df.sort_values(by=['日期', '时段']), use_container_width=True)
        if st.button("🔴 清空所有数据"):
            if os.path.exists(DATA_FILE): os.remove(DATA_FILE)
            st.rerun()
    else:
        st.info("🔒 详细名单仅管理员可见。")