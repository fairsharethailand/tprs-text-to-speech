import streamlit as st
from gtts import gTTS
import base64
import os
import uuid
import random
import json

# 1. ตั้งค่าหน้าเว็บ
st.set_page_config(page_title="Speak V1.0", layout="wide")

# --- UI Helper Functions (Callback) ---
def clear_text(key_name):
    st.session_state[key_name] = ""

# 2. Session State Initialization
defaults = {
    "m_input": "The children make a cake.",
    "sr_input": "The children",
    "pr_input": "make a cake",
    "st_input": "-",
    "pt_input": "make a bread",
    "display_text": "",
    "audio_key": 0
}

for key, default_val in defaults.items():
    if key not in st.session_state:
        st.session_state[key] = default_val

# --- Grammar Logic ---
def load_irregular_verbs():
    try:
        if os.path.exists('verbs.json'):
            with open('verbs.json', 'r', encoding='utf-8') as f:
                return json.load(f)
        else:
            return {
                "went": "go", "ate": "eat", "saw": "see", "bought": "buy", 
                "had": "have", "has": "have", "did": "do", "drank": "drink", 
                "slept": "sleep", "wrote": "write", "came": "come", "ran": "run", 
                "met": "meet", "spoke": "speak", "took": "take", "found": "find", 
                "gave": "give", "thought": "think", "brought": "bring", 
                "told": "tell", "made": "make", "was": "be", "were": "be"
            }
    except Exception:
        return {"went": "go", "ate": "eat"}

PAST_TO_INF = load_irregular_verbs()
IRR_PL = ["children", "people", "men", "women", "mice", "teeth", "feet", "geese", "oxen", "data", "media"]

def is_present_perfect(predicate):
    words = predicate.lower().split()
    if len(words) >= 2 and words[0] in ['have', 'has', 'had']:
        v2 = words[1]
        if v2.endswith('ed') or v2 in PAST_TO_INF or v2 in ['been', 'done', 'gone', 'seen', 'eaten']:
            return True
    return False

def check_tense_type(predicate):
    words = predicate.split()
    if not words: return "unknown"
    v = words[0].lower().strip()
    # เช็กว่าเป็น Past หรือไม่จาก list และการลงท้าย ed
    if v.endswith("ed") or v in PAST_TO_INF:
        return "past"
    return "present"

def conjugate_singular(predicate):
    words = predicate.split()
    if not words: return ""
    v = words[0].lower(); rest = " ".join(words[1:])
    if v in ['have', 'has']: return f"has {rest}".strip()
    if v.endswith(('ch', 'sh', 'x', 's', 'z', 'o')): v += "es"
    elif v.endswith('y') and len(v) > 1 and v[-2] not in 'aeiou': v = v[:-1] + "ies"
    else: v += "s"
    return f"{v} {rest}".strip()

def get_auxiliary(subject, pred_target, pred_other):
    # 1. ข้ามถ้าเป็น Present Perfect
    if is_present_perfect(pred_target): return None 
    
    # 2. เช็กว่าเป็น Past หรือไม่ ถ้าใช่ใช้ Did
    if check_tense_type(pred_target) == "past" or check_tense_type(pred_other) == "past":
        return "Did"
    
    # 3. Logic สำหรับ Present Simple (Do/Does)
    s_clean = subject.lower().strip()
    s_words = s_clean.split()
    found_irregular = any(word in IRR_PL for word in s_words)
    
    # เงื่อนไขการใช้ Do (พหูพจน์ / I, You, We, They)
    if (found_irregular or 'and' in s_clean or s_clean in ['i', 'you', 'we', 'they'] or 
        (s_clean.endswith('s') and s_clean not in ['james', 'charles', 'boss'])):
        return "Do"
    
    # เงื่อนไขการใช้ Does (เอกพจน์)
    return "Does"

def to_infinitive(predicate, other_predicate):
    words = predicate.split()
    if not words: return ""
    v = words[0].lower().strip(); rest = " ".join(words[1:])
    
    # แปลงกริยากลับเป็นช่อง 1 เสมอเมื่อมี auxiliary
    if v in ['had', 'has', 'have']:
        inf_v = "have"
    elif v in PAST_TO_INF:
        inf_v = PAST_TO_INF[v]
    elif v.endswith("ies"):
        inf_v = v[:-3] + "y"
    elif v.endswith("es"):
        if any(v.endswith(suffix) for suffix in ['oes', 'shes', 'ches', 'xes']):
            inf_v = v[:-2]
        else:
            inf_v = v[:-1]
    elif v.endswith("s") and not v.endswith("ss"):
        inf_v = v[:-1]
    else:
        inf_v = v
        
    return f"{inf_v} {rest}".strip()

def has_be_verb(predicate):
    v_low = predicate.lower().split()
    be_modals = ['is', 'am', 'are', 'was', 'were', 'can', 'will', 'must', 'should', 'could', 'would']
    return v_low and v_low[0] in be_modals

def build_logic(q_type, data):
    s1, p1, s2, p2 = data['s1'], data['p1'], data['s2'], data['p2']
    subj_r, pred_r = (s1 if s1 else "He"), (p1 if p1 else "is here")
    subj_t = s2 if (s2 and s2 != "-") else s1
    pred_t = p2 if (p2 and p2 != "-") else p1

    def swap(s, p):
        pts = p.split()
        return f"{pts[0].capitalize()} {s} {' '.join(pts[1:])}".strip()

    if q_type == "Statement": return data['main_sent']
    if q_type == "Negative":
        if has_be_verb(pred_t) or is_present_perfect(pred_t):
            return f"No, {subj_t} {pred
