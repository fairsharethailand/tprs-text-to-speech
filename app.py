import streamlit as st
from gtts import gTTS
import base64
import os
import uuid
import random

# 1. ตั้งค่าหน้าเว็บ (Layout V.47 เป๊ะ)
st.set_page_config(page_title="TPRS Magic Wheel V58", layout="wide")

# 2. Session State สำหรับเก็บข้อความและควบคุมเสียง
if 'display_text' not in st.session_state:
    st.session_state.display_text = ""
if 'audio_key' not in st.session_state:
    st.session_state.audio_key = 0

# --- Grammar Logic (Past Simple & Perfect Tense) ---
PAST_TO_INF = {
    "went": "go", "ate": "eat", "saw": "see", "bought": "buy", 
    "had": "have", "did": "do", "drank": "drink", "slept": "sleep", 
    "wrote": "write", "came": "come", "ran": "run", "met": "meet",
    "spoke": "speak", "took": "take", "found": "find", "gave": "give",
    "thought": "think", "brought": "bring", "told": "tell", "made": "make"
}

def is_present_perfect(predicate):
    words = predicate.lower().split()
    return len(words) >= 2 and words[0] in ['have', 'has', 'had']

def get_auxiliary(subject, predicate):
    if is_present_perfect(predicate):
        return None 
    words = predicate.split()
    if not words: return "Does"
    v_first = words[0].lower().strip()
    if v_first in PAST_TO_INF or v_first.endswith("ed"):
        return "Did"
    s = subject.lower().strip()
    if 'and' in s or s in ['i', 'you', 'we', 'they'] or (s.endswith('s') and s not in ['james', 'charles', 'boss']):
        return "Do"
    return "Does"

def to_infinitive(predicate):
    words = predicate.split()
    if not words: return ""
    v = words[0].lower().strip()
    rest = " ".join(words[1:])
    if v in PAST_TO_INF: inf_v = PAST_TO_INF[v]
    elif v.endswith("ed"):
        if v.endswith("ied"): inf_v = v[:-3] + "y"
        else: inf_v = v[:-2]
    elif v in ["has"]: inf_v = "have"
    elif v.endswith("es"):
        for suffix in ['sses', 'ches', 'shes', 'xes']:
            if v.endswith(suffix): 
                inf_v = v[:-2]
                break
        else: inf_v = v[:-2]
    elif v.endswith("s") and not v.endswith("ss"): inf_v = v[:-1]
    else: inf_v = v
    return f"{inf_v} {rest}".strip()

def has_be_verb(predicate):
    v_low = predicate.lower().split()
    be_and_modals = ['is', 'am', 'are', 'was', 'were', 'can', 'will', 'must', 'should', 'could', 'would']
    return v_low and v_low[0] in be_and_modals

def build_logic(q_type, data):
    s1, p1, s2, p2 = data['s1'], data['p1'], data['s2'], data['p2']
    main_sent = data['main_sent']
    subj_real, pred_real = (s1 if s1 else "He"), (p1 if p1 else "is here")
    subj_trick = s2 if s2 != "-" else s1
    pred_trick = p2 if p2 != "-" else p1

    def swap_front(s, p):
        parts = p.split()
        return f"{parts[0].capitalize()} {s} {' '.join(parts[1:])}".strip().replace("  ", " ")

    if q_type == "Statement": return main_sent
    if q_type == "Negative":
        if has_be_verb(pred_trick) or is_present_perfect(pred_trick):
            parts = pred_trick.split()
            return f"No, {subj_trick} {parts[0]} not {' '.join(parts[1:])}."
        return f"No, {subj_trick} {get_auxiliary(subj_trick, pred_trick).lower()} not {to_infinitive(pred_trick)}."
    if q_type == "Yes-Q":
        if has_be_verb(pred_real) or is_present_perfect(pred_real): return swap_front(subj_real, pred_real) + "?"
        return f"{get_auxiliary(subj_real, pred_real)} {subj_real} {to_infinitive(pred_real)}?"
    if q_type == "No-Q":
        if has_be_verb(pred_trick) or is_present_perfect(pred_trick): return swap_front(subj_trick, pred_trick) + "?"
        return f"{get_auxiliary(subj_trick, pred_trick)} {subj_trick} {to_infinitive(pred_trick)}?"
    if q_type == "Either/Or":
        if s2 != "-" and s1.lower().strip() != s2.lower().strip():
            if has_be_verb(pred_real) or is_present_perfect(pred_real):
                v_f = pred_real.split()[0].capitalize()
                v_r = " ".join(pred_real.split()[1:])
                return f"{v_f} {subj_real} or {subj_trick} {v_r}?"
            return f"{get_auxiliary(subj_real, pred_real)} {subj_real} or {subj_trick} {to_infinitive(pred_real)}?"
        else:
            p_alt = p2 if p2 != "-" else "something else"
            if has_be_verb(pred_real) or is_present_perfect(pred_real):
                return f"{swap_front(subj_real, pred_real)} or {p_alt}?"
            aux = get_auxiliary(subj_real, pred_real)
            return f"{aux} {subj_real} {to_infinitive(pred_real)} or {to_infinitive(p_alt)}?"
    if q_type in ["Who", "What", "Where", "When", "How", "Why"]:
        if q_type == "Who": return f"Who {pred_real}?"
        if has_be_verb(pred_real) or is_present_perfect(pred_real):
            parts = pred_real.split()
            return f"{q_type} {parts[0]} {subj_real} {' '.join(parts[1:])}?"
        return f"{q_type} {get_auxiliary(subj_real, pred_real).lower()} {subj_real} {to_infinitive(pred_real)}?"
    return main_sent

def play_voice(text):
    if text:
        try:
            tts = gTTS(text=text, lang='en')
            filename = f"voice_{uuid.uuid4()}.mp3"
            tts.save(filename)
            with open(filename, "rb") as f:
                b64 = base64.b64encode(f.read()).decode()
            st.session_state.audio_key += 1
            audio_html = f'<audio autoplay key="{st.session_state.audio_key}"><source src="data:audio/mp3;base64,{b64}" type="audio/mp3"></audio>'
            st.markdown(audio_html, unsafe_allow_html=True)
            os.remove(filename)
        except: pass

# --- UI Layout ---
st.title("🎡 TPRS Magic Wheel V58 (Fixed Layout)")

main_input = st.text_input("📝 Main Sentence", "She has visited Tokyo.")
col1, col2 = st.columns(2)
with col1:
    s_r = st.text_input("Subject (R):", "She")
    p_r = st.text_input("Predicate (R):", "has visited Tokyo")
with col2:
    s_t = st.text_input("Subject (T):", "-")
    p_t = st.text_input("Predicate (T):", "has visited Osaka")

data_packet = {'s1':s_r, 'p1':p_r, 's2':s_t, 'p2':p_t, 'main_sent':main_input}
st.divider()

clicked_type = None
if st.button("🎰 RANDOM TRICK", use_container_width=True, type="primary"):
    clicked_type = random.choice(["Statement", "Yes-Q", "No-Q", "Negative", "Either/Or", "Who", "What", "Where", "When", "How", "Why"])

# --- ปรับลำดับปุ่มตรงนี้ ---
row1 = st.columns(5)
btns = [
    ("📢 Statement", "Statement"), 
    ("✅ Yes-Q", "Yes-Q"), 
    ("❌ No-Q", "No-Q"), 
    ("🚫 Negative", "Negative"), 
    ("⚖️ Either/Or", "Either/Or")
]
for i, (lbl, mode) in enumerate(btns):
    if row1[i].button(lbl, use_container_width=True): 
        clicked_type = mode

row2 = st.columns(6)
whs = ["Who", "What", "Where", "When", "How", "Why"]
for i, wh in enumerate(whs):
    if row2[i].button(f"❓ {wh}", use_container_width=True): 
        clicked_type = wh

if clicked_type:
    final_text = build_logic(clicked_type, data_packet)
    st.session_state.display_text = f"🎯 {clicked_type}: {final_text}"
    play_voice(final_text)

if st.session_state.display_text:
    st.info(st.session_state.display_text)
