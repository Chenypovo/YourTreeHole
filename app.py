# app.py — Treehole Streamlit 界面
from __future__ import annotations

import streamlit as st

from cli.main import create_agent, generate_greeting
from core.config import AppConfig


def init_session_state():
    """初始化 session state，只跑一次。"""
    if "agent" not in st.session_state:
        config = AppConfig.from_file()
        agent, emotion = create_agent(config)
        st.session_state.agent = agent
        st.session_state.emotion = emotion
        st.session_state.messages = []

        # 生成问候语
        greeting = generate_greeting(agent.llm, agent.profile, agent.memory)
        if greeting:
            st.session_state.messages.append({"role": "assistant", "content": greeting})

        # 检查久别重逢
        if emotion.bond.check_return_after_absence():
            st.session_state.messages.append({"role": "assistant", "content": "好久不见！"})

        # 同步侧边栏刷新标记
        st.session_state.sidebar_rerun = False


def render_sidebar():
    """侧边栏：记忆、画像、情绪。"""
    agent = st.session_state.agent
    emotion = st.session_state.emotion

    with st.sidebar:
        st.header("记忆管理")

        # 手动添加记忆
        with st.form("add_memory", clear_on_submit=True):
            new_memory = st.text_input("添加记忆", placeholder="输入你想让我记住的事...")
            if st.form_submit_button("记住"):
                if new_memory.strip():
                    agent.memory.save_memory(new_memory.strip(), category="手动", resolved=True)
                    st.success(f"已记住: {new_memory.strip()}")
                    st.rerun()

        st.divider()

        # 记忆列表
        entries = agent.memory.list_memories()
        if entries:
            st.subheader(f"记忆 ({len(entries)})")
            for i, entry in enumerate(entries, start=1):
                check = "✅" if entry["resolved"] else "⬜"
                label = f'{check} [{entry["category"]}] {entry["content"]}'
                if st.button(f"🗑 {label}", key=f"del_{i}", help=f"删除记忆 #{i}"):
                    agent.memory.delete_memory(i)
                    st.rerun()
        else:
            st.info("还没有记忆，和我聊聊吧～")

        st.divider()

        # 情绪状态
        if emotion:
            state = emotion.get_state()
            st.subheader("情感状态")
            st.metric("心情", f"{state.mood_label} {state.mood_hearts}", f"{state.mood_value}/100")
            st.metric("羁绊", f"Lv.{state.bond_level} {state.bond_name}")
            st.metric("精力", f"{state.energy}/100")

        st.divider()

        # 用户画像
        st.subheader("用户画像")
        profile_text = agent.profile.load()
        if profile_text:
            st.markdown(profile_text)
        else:
            st.info("画像会在聊天过程中自动更新")

        st.divider()

        # 重置对话
        if st.button("🔄 重置对话", type="secondary"):
            agent.memory.clear()
            st.session_state.messages = []
            st.rerun()


def render_chat():
    """主聊天区域。"""
    agent = st.session_state.agent

    # 显示历史消息
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    # 用户输入
    if prompt := st.chat_input("说点什么..."):
        # 显示用户消息
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        # 流式生成助手回复
        with st.chat_message("assistant"):
            response = st.write_stream(agent.run_stream(prompt))

        st.session_state.messages.append({"role": "assistant", "content": response})


def main():
    st.set_page_config(
        page_title="Treehole",
        page_icon="🌳",
        layout="wide",
    )

    st.title("🌳 Treehole")
    st.caption("一个永远不会忘记你的 AI")

    init_session_state()
    render_sidebar()
    render_chat()


if __name__ == "__main__":
    main()
