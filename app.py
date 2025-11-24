import streamlit as st
import pandas as pd
import plotly.express as px
from supabase import create_client, Client
from PIL import Image
from paddleocr import PaddleOCR
import re
import io

# -------------------- SUPABASE SETUP --------------------
SUPABASE_URL = "https://jaztokuyzxettemexcrc.supabase.co"
SUPABASE_KEY = "YOUR_SUPABASE_KEY"
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# -------------------- PAGE SETUP --------------------
st.set_page_config(page_title="SkillBot Career & Personality Profiler", layout="centered")

# -------------------- LOAD DATA --------------------
try:
    questions = pd.read_csv("questions.csv")
    careers = pd.read_csv("careers.csv")
    tci_questions = pd.read_csv("tci_questions.csv")
except FileNotFoundError as e:
    st.error(f"Error loading data file: {e}")
    st.stop()

# -------------------- SESSION STATE --------------------
defaults = {
    "page": "intro",
    "index": 0,
    "answers": [],
    "tci_page": "intro",
    "tci_index": 0,
    "tci_answers": [],
    "riasec_scores": None,
    "tci_scores": None,
    "sidebar_choice": "Home",
    "user": None,
    "access_token": None,
}
for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

def restart_all():
    for k, v in defaults.items():
        st.session_state[k] = v

# -------------------- AUTH HELPERS --------------------
def signup_user(email, password):
    return supabase.auth.sign_up({"email": email, "password": password})

def login_user(email, password):
    return supabase.auth.sign_in_with_password({"email": email, "password": password})

def logout_user():
    st.session_state.user = None
    st.session_state.access_token = None
    st.session_state.sidebar_choice = "Home"
    st.success("Logged out successfully!")

# -------------------- DB SAVE HELPERS --------------------
def save_results_to_supabase(user_id, riasec, tci):
    try:
        riasec_dict = riasec.to_dict()
        tci_dict = tci.to_dict()

        supabase.table("test_results").insert({
            "user_id": user_id,
            "riasec_R": riasec_dict.get("R"),
            "riasec_I": riasec_dict.get("I"),
            "riasec_A": riasec_dict.get("A"),
            "riasec_S": riasec_dict.get("S"),
            "riasec_E": riasec_dict.get("E"),
            "riasec_C": riasec_dict.get("C"),
            "tci_Persistence": tci_dict.get("Persistence"),
            "tci_HarmAvoidance": tci_dict.get("Harm Avoidance"),
            "tci_Cooperativeness": tci_dict.get("Cooperativeness"),
            "tci_NoveltySeeking": tci_dict.get("Novelty Seeking"),
            "tci_RewardDependence": tci_dict.get("Reward Dependence"),
            "tci_SelfDirectedness": tci_dict.get("Self-Directedness"),
            "tci_SelfTranscendence": tci_dict.get("Self-Transcendence"),
        }).execute()
        st.success("✅ Test results saved into separate columns!")
    except Exception as e:
        st.error(f"⚠️ Could not save results: {e}")

def upload_marksheet(user_id, file):
    try:
        file_bytes = file.read()
        filename = f"{user_id}_{file.name}"
        supabase.storage.from_("marksheets").upload(filename, file_bytes)
        public_url = supabase.storage.from_("marksheets").get_public_url(filename)
        st.success("✅ Marksheet uploaded successfully!")
        return public_url
    except Exception as e:
        st.error(f"Error uploading file: {e}")
        return None

def save_profile(user_id, name, gender, age, qualification, marksheet_url):
    try:
        response = supabase.table("profiles").upsert({
            "user_id": user_id,
            "full_name": name,
            "gender": gender,
            "age": age,
            "qualification": qualification,
            "marksheet_url": marksheet_url
        }).execute()
        if response.data is not None:
            st.success("✅ Profile created successfully!")
        else:
            st.warning("⚠️ Could not save profile. Check your table schema or permissions.")
    except Exception as e:
        st.error(f"Failed to save profile: {e}")

# -------------------- OCR HELPER (PaddleOCR + Pillow) --------------------
ocr = PaddleOCR(use_angle_cls=True, lang='en')

def extract_text_from_image(uploaded_file):
    image = Image.open(uploaded_file).convert("RGB")
    img_byte_arr = io.BytesIO()
    image.save(img_byte_arr, format='PNG')
    result = ocr.ocr(img_byte_arr.getvalue())
    text_list = []
    if result and result[0]:
        for line in result[0]:
            text_list.append(line[1][0])
    return text_list

def extract_number_robust(s):
    s = str(s).strip()
    match = re.search(r'\d+\.?\d*', s)
    if match:
        try:
            return float(match.group(0)) if '.' in match.group(0) else int(match.group(0))
        except ValueError:
            return None
    return None

def parse_marks(text_list):
    subjects, maximum, obtained = [], [], []
    start_index = 0
    for idx, text in enumerate(text_list):
        if "SUBJECT" in text.upper():
            start_index = idx + 1
            break
    i = start_index
    while i < len(text_list):
        t = text_list[i].strip()
        if not t or len(t) < 2:
            i += 1
            continue
        # Simplified parsing logic
        subjects.append(t)
        max_val, obt_val = 100, 80  # Placeholder for demo; replace with real extraction
        maximum.append(max_val)
        obtained.append(obt_val)
        i += 1
    return pd.DataFrame({"Subject": subjects, "Maximum": maximum, "Obtained": obtained})

# -------------------- MERGED CODE (PERSONALITY + MARKSHEET + RECOMMENDATIONS) --------------------
SUBFIELDS = {
    "Engineering":["Mechanical","Electrical","Civil","Software","Chemical"],
    "Medical":["MBBS","Pharmacy","Physio","Nursing","Biotech"],
    "Computer Science":["AI","Data Science","Cyber Security","Software","IT Management"],
    "Business":["BBA","Marketing","Finance","HR","Supply Chain"],
    "Arts":["Psychology","Fine Arts","Mass Communication","English","Sociology"],
    "Commerce":["B.Com","Accounting","Banking","Economics","Business Admin"]
}

def load_personality(csv_path):
    df = pd.read_csv(csv_path)
    df = df.rename(columns={"user_id":"student_id"})
    return df

def load_marksheet(csv_path):
    df = pd.read_csv(csv_path)
    df = df.rename(columns={"Obtained":"marks","Subject":"subject"})
    df = df[["subject","marks"]]
    df = df[~df["subject"].str.contains("TOTAL", case=False)]
    df["subject"] = df["subject"].str.upper().str.strip()
    df = df.groupby("subject")["marks"].max().reset_index()
    return df

def extract_subject_scores(df):
    subjects = {"math":["MATH","MATHEMATICS"],"physics":["PHYSICS"],"chemistry":["CHEMISTRY"],
                "biology":["BIOLOGY"],"computer":["COMPUTER"],"english":["ENGLISH"],
                "urdu":["URDU"],"islamiat":["ISLAM","ISLAMIYAT"],"pakstudies":["PAKISTAN"]}
    extracted = {}
    for key, kws in subjects.items():
        extracted[key]=0
        for kw in kws:
            row = df[df["subject"].str.contains(kw)]
            if len(row)>0:
                extracted[key]=int(row.iloc[0]["marks"])
                break
    return extracted

def calculate_best_fit(marks, personality):
    scores = {"Medical":0,"Engineering":0,"Computer Science":0,"Arts":0,"Business":0,"Commerce":0}
    # Marks weighting simplified
    scores["Medical"] += (marks.get("biology",0)/150)*0.35 + (marks.get("chemistry",0)/150)*0.35
    scores["Engineering"] += (marks.get("math",0)/150)*0.35 + (marks.get("physics",0)/150)*0.35
    # Personality weights simplified
    scores["Medical"] += personality.get("riasec_I",0)/10*0.3
    scores["Engineering"] += personality.get("riasec_C",0)/10*0.3
    total=sum(scores.values())
    probabilities={k:round(v/total,3) for k,v in scores.items()}
    return dict(sorted(probabilities.items(), key=lambda x:x[1], reverse=True))

def recommend_field(personality_csv, marksheet_csv):
    p=load_personality(personality_csv)
    m=load_marksheet(marksheet_csv)
    personality=p.iloc[0].to_dict()
    marks=extract_subject_scores(m)
    field_scores=calculate_best_fit(marks, personality)
    best_field=max(field_scores,key=field_scores.get)
    best_subfields=SUBFIELDS[best_field]
    st.subheader("Recommended Field: "+best_field)
    st.write("Subfields:")
    for s in best_subfields:
        st.write("-",s)
    return best_field, best_subfields
