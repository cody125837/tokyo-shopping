import streamlit as st
import pandas as pd
import requests
import json
import os

# --- 設定頁面 (手機版面優化) ---
st.set_page_config(page_title="東京戰利品 🇯🇵", page_icon="🛍️")

# --- 檔案路徑 ---
DATA_FILE = "shopping_list.json"

# --- 函式：讀取資料 (支援舊格式自動升級) ---
def load_data():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                # 如果是最舊的陣列格式，升級成字典
                if isinstance(data, list):
                    return {"personal": data, "agent": [], "todo": []}
                # 如果是上一版字典格式，補上 todo 欄位
                if "todo" not in data:
                    data["todo"] = []
                return data
        except:
            return {"personal": [], "agent": [], "todo": []}
    return {"personal": [], "agent": [], "todo": []}

# --- 函式：儲存資料 ---
def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

# --- 函式：抓取匯率 ---
@st.cache_data(ttl=3600)
def get_rate():
    try:
        url = "https://api.exchangerate-api.com/v4/latest/JPY"
        resp = requests.get(url)
        data = resp.json()
        return data["rates"]["TWD"]
    except:
        return 0.215 # 預設匯率

# --- 初始化 Session State ---
if "data" not in st.session_state:
    st.session_state.data = load_data()

rate = get_rate()

# ================= 介面開始 =================

# 標題區
col1, col2 = st.columns([3, 1])
with col1:
    st.title("🛍️ 東京購物 & 代辦")
with col2:
    st.link_button("📅 行程", "https://www.funliday.com/cody125837/trips/691c24b34b66e0a4513ef0aa")

st.info(f"💴 目前匯率：1 JPY ≈ **{rate}** TWD")
st.markdown("---")

# ================= 區塊 1: 代辦事項 =================
st.header("✅ 旅途代辦事項")
st.caption("出發前或旅途中的重要任務")

with st.expander("➕ 新增代辦", expanded=False):
    with st.form("add_todo", clear_on_submit=True):
        task_name = st.text_input("事項名稱", placeholder="ex: 拿護照、買 Suica 卡、預約餐廳")
        submitted_todo = st.form_submit_button("加入代辦")
        
        if submitted_todo and task_name:
            new_task = {"task": task_name, "done": False}
            st.session_state.data["todo"].append(new_task)
            save_data(st.session_state.data)
            st.rerun()

if st.session_state.data["todo"]:
    df_todo = pd.DataFrame(st.session_state.data["todo"])
    
    column_config_todo = {
        "done": st.column_config.CheckboxColumn("完成?", width="small"),
        "task": st.column_config.TextColumn("代辦內容", width="large")
    }

    edited_df_todo = st.data_editor(
        df_todo, 
        column_config=column_config_todo, 
        use_container_width=True, 
        hide_index=True, 
        num_rows="dynamic", 
        key="editor_todo"
    )

    current_todo_data = edited_df_todo[["task", "done"]].to_dict("records")
    if current_todo_data != st.session_state.data["todo"]:
        st.session_state.data["todo"] = current_todo_data
        save_data(st.session_state.data)
        st.rerun()
else:
    st.info("目前沒有代辦事項，可以放心去玩！")

st.markdown("---")

# ================= 區塊 2: 自己的清單 =================
st.header("🛍️ 自己要買")
st.caption("這是你要買給自己的東西")

with st.expander("➕ 新增商品 (自用)", expanded=False):
    with st.form("add_personal", clear_on_submit=True):
        c1, c2 = st.columns([2, 1])
        name = c1.text_input("商品名稱")
        price = c2.number_input("日幣", min_value=0, step=100)
        submitted = st.form_submit_button("加入清單")
        
        if submitted and name:
            new_item = {"name": name, "price_jpy": price, "bought": False}
            st.session_state.data["personal"].append(new_item)
            save_data(st.session_state.data)
            st.rerun()

if st.session_state.data["personal"]:
    df = pd.DataFrame(st.session_state.data["personal"])
    df["price_twd"] = (df["price_jpy"] * rate).astype(int)
    
    column_config = {
        "bought": st.column_config.CheckboxColumn("已買?", width="small"),
        "name": st.column_config.TextColumn("商品名稱", width="medium"),
        "price_jpy": st.column_config.NumberColumn("日幣", format="¥%d"),
        "price_twd": st.column_config.NumberColumn("台幣", format="NT$%d", disabled=True)
    }

    edited_df = st.data_editor(df, column_config=column_config, use_container_width=True, hide_index=True, num_rows="dynamic", key="editor_personal")

    current_data = edited_df[["name", "price_jpy", "bought"]].to_dict("records")
    if current_data != st.session_state.data["personal"]:
        st.session_state.data["personal"] = current_data
        save_data(st.session_state.data)
        st.rerun()
        
    total_jpy = df[~df["bought"]]["price_jpy"].sum()
    total_twd = int(total_jpy * rate)
    st.metric("💰 自用小計", f"NT$ {total_twd:,}", f"¥ {total_jpy:,}")
else:
    st.info("目前沒有自用清單")

st.markdown("---")

# ================= 區塊 3: 代購清單 =================
st.header("📦 幫別人買 (代購)")
st.caption("親友委託的清單，記得收錢！")

with st.expander("➕ 新增代購商品", expanded=False):
    with st.form("add_agent", clear_on_submit=True):
        c1, c2 = st.columns([2, 1])
        name = c1.text_input("商品名稱", placeholder="ex: 合利他命")
        price = c2.number_input("日幣", min_value=0, step=100)
        client = st.text_input("委託人 (誰要買?)", placeholder="ex: 阿姨、同事小王")
        submitted_agent = st.form_submit_button("加入代購")
        
        if submitted_agent and name:
            new_agent_item = {"client": client if client else "未標記", "name": name, "price_jpy": price, "bought": False}
            st.session_state.data["agent"].append(new_agent_item)
            save_data(st.session_state.data)
            st.rerun()

if st.session_state.data["agent"]:
    df_agent = pd.DataFrame(st.session_state.data["agent"])
    df_agent["price_twd"] = (df_agent["price_jpy"] * rate).astype(int)
    
    column_config_agent = {
        "bought": st.column_config.CheckboxColumn("已買?", width="small"),
        "client": st.column_config.TextColumn("委託人", width="small"),
        "name": st.column_config.TextColumn("商品名稱", width="medium"),
        "price_jpy": st.column_config.NumberColumn("日幣", format="¥%d"),
        "price_twd": st.column_config.NumberColumn("台幣", format="NT$%d", disabled=True)
    }

    edited_df_agent = st.data_editor(df_agent, column_config=column_config_agent, use_container_width=True, hide_index=True, num_rows="dynamic", key="editor_agent")

    current_agent_data = edited_df_agent[["client", "name", "price_jpy", "bought"]].to_dict("records")
    if current_agent_data != st.session_state.data["agent"]:
        st.session_state.data["agent"] = current_agent_data
        save_data(st.session_state.data)
        st.rerun()

    total_agent_jpy = df_agent[~df_agent["bought"]]["price_jpy"].sum()
    total_agent_twd = int(total_agent_jpy * rate)
    st.metric("💸 代購墊付小計", f"NT$ {total_agent_twd:,}", f"¥ {total_agent_jpy:,}")
else:
    st.info("目前沒有代購清單")

# ================= 總計 =================
st.markdown("---")
all_jpy = 0
if st.session_state.data["personal"]:
    all_jpy += pd.DataFrame(st.session_state.data["personal"]).query("bought == False")["price_jpy"].sum()
if st.session_state.data["agent"]:
    all_jpy += pd.DataFrame(st.session_state.data["agent"]).query("bought == False")["price_jpy"].sum()

st.subheader("👜 總結帳預估")
st.caption(f"全部未購買的總花費 (含代購): **¥ {all_jpy:,}** (約 NT$ {int(all_jpy*rate):,})")