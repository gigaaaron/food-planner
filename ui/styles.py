import streamlit as st
import os


def load_css():
    css_path = os.path.join(os.path.dirname(__file__), "..", "styles.css")
    with open(css_path) as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)


def metric_card(label, value):
    st.markdown(
        f"""
        <div class="metric-card">
            <div class="label">{label}</div>
            <div class="value">{value}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def allergen_chips(allergies):
    if not allergies:
        return
    chips = "".join(f'<span class="recipe-chip">⚠ {a}</span>' for a in allergies)
    st.markdown(
        f'<div style="margin-top:0.75rem;margin-bottom:1.5rem">'
        f'<div class="section-label">Allergies excluded</div>{chips}</div>',
        unsafe_allow_html=True,
    )


def section_label(text):
    st.markdown(f'<div class="section-label">{text}</div>', unsafe_allow_html=True)


def status_badge(success=True):
    if success:
        st.markdown('<div class="status-ok"> Plan generated</div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="status-ok status-warn"> Ollama connection issue</div>', unsafe_allow_html=True)