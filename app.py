import streamlit as st
import pandas as pd
import plotly.express as px
import cv2
import re
from supabase import create_client, Client
from paddleocr import PaddleOCR

# -------------------- SUPABASE SETUP --------------------
SUPABASE_URL = "https://jaztokuyzxettemexcrc.supabase.co"
SUPABASE_KEY = "YOUR_SUPABASE_KEY_HERE"
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# -------------------- PAGE SETUP --------------------
st.set_page_config(page_title="SkillBot Career & Personality Profiler", layout="centered")

# -------------------- LOAD QUESTIONS --------------------
try:
    questions = pd.read_csv("questions.csv")
    tci_questions = pd.read_csv("tci_questions.csv")
except FileNotFoundError as e:
    st.error(f"Error loading data file: {e}")
    st.stop()

# -------------------- SESSION STATE --------------------
def init_session():
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
        "marksheet_df": None,
        "recommended_field": None,
        "recommended_subfields": None
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

init_session()

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

# -------------------- OCR FUNCTIONS --------------------
ocr = PaddleOCR(use_angle_cls=True, lang='en')

def preprocess_image(path):
    img = cv2.imread(path)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    gray = cv2.bilateralFilter(gray, 9, 75, 75)
    thresh = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 31, 10)
    return img, thresh

def extract_text(img):
    result = ocr.ocr(img)
    text_data = []
    if result and result[0]:
        if isinstance(result[0], dict) and 'rec_texts' in result[0]:
            text_data = result[0]['rec_texts']
        elif isinstance(result[0], list):
            for item in result[0]:
                if isinstance(item, (list, tuple)) and len(item) == 3:
                    _, text_str, _ = item
                    text_data.append(text_str)
                elif isinstance(item, (list, tuple)) and len(item) == 2:
                    _, text_info = item
                    if isinstance(text_info, (list, tuple)) and len(text_info) == 2:
                        text_data.append(text_info[0])
                    else:
                        text_data.append(str(text_info))
    return text_data

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
    start_index = -1
    for idx, text in enumerate(text_list):
        if 'SUBJECT - WISE STATEMENT OF MARKS' in text.upper():
            start_index = idx
            break
    i = start_index+1 if start_index!=-1 else 0

    forbidden = {'SR.NO.', 'SUBJECTS', 'MARKS', 'MAXIMUM', 'OBTAINED'}
    noise_words = set([chr(x) for x in range(65, 91)])  # A-Z

    while i < len(text_list):
        t = text_list[i].strip()
        if not t or t.upper() in forbidden or t.upper() in noise_words:
            i += 1
            continue
        subject_name = t
        found_nums = []
        scan_idx = i+1
        num_search_count = 0
        while scan_idx < len(text_list) and len(found_nums)<2 and num_search_count<4:
            num = extract_number_robust(text_list[scan_idx])
            if num is not None:
                found_nums.append(num)
            scan_idx += 1
            num_search_count +=1
        if len(found_nums)>=2:
            subjects.append(subject_name)
            maximum.append(int(found_nums[0]))
            obtained.append(int(found_nums[1]))
        i = scan_idx

    df = pd.DataFrame({"Subject": subjects, "Maximum": maximum, "Obtained": obtained})
    return df

def extract_marks_from_file(file):
    img, _ = preprocess_image(file)
    text_list = extract_text(img)
    df = parse_marks(text_list)
    return df

# -------------------- FIELD & UNIVERSITY RECOMMENDATION --------------------
SUBFIELDS = {
    "Engineering":["Mechanical Engineering","Electrical Engineering","Civil Engineering","Software Engineering","Chemical Engineering"],
    "Medical":["MBBS","Pharmacy","Physiotherapy","Nursing","Biotechnology"],
    "Computer Science":["Artificial Intelligence","Data Science","Cyber Security","Software Development","IT Management"],
    "Business":["BBA","Marketing","Finance","HR Management","Supply Chain"],
    "Arts":["Psychology","Fine Arts","Mass Communication","English Literature","Sociology"],
    "Commerce":["B.Com","Accounting","Banking","Economics","Business Administration"]
}

def extract_subject_scores(df):
    subjects = {"math":["MATH","MATHEMATICS"], "physics":["PHYSICS"], "chemistry":["CHEMISTRY"], "biology":["BIOLOGY"], "computer":["COMPUTER"], "english":["ENGLISH"], "urdu":["URDU"], "islamiat":["ISLAM","ISLAMIYAT"], "pakstudies":["PAKISTAN"]}
    extracted = {}
    for key, keywords in subjects.items():
        extracted[key]=0
        for kw in keywords:
            row = df[df["Subject"].str.contains(kw, case=False)]
            if len(row)>0:
                extracted[key] = int(row.iloc[0]["Obtained"])
                break
    return extracted

# Simple rule-based scoring
def calculate_best_fit(marks, personality):
    scores = {field:0 for field in SUBFIELDS.keys()}
    # Marks weighting (same as before)
    scores["Medical"] += (marks["biology"]/150)*0.35 + (marks["chemistry"]/150)*0.35 + (marks["physics"]/150)*0.1 + (marks["math"]/150)*0.1 + (marks["english"]/150)*0.05 + (marks["urdu"]/150)*0.05
    scores["Engineering"] += (marks["math"]/150)*0.35 + (marks["physics"]/150)*0.35 + (marks["chemistry"]/150)*0.1 + (marks["biology"]/150)*0.05 + (marks["english"]/150)*0.05 + (marks["urdu"]/150)*0.1
    scores["Computer Science"] += (marks["math"]/150)*0.3 + (marks["physics"]/150)*0.2 + (marks["computer"]/150)*0.25 + (marks["english"]/150)*0.1 + (marks["biology"]/150)*0.05 + (marks["urdu"]/150)*0.1
    scores["Arts"] += (marks["english"]/150)*0.4 + (marks["urdu"]/150)*0.3 + (marks["biology"]/150)*0.05 + (marks["chemistry"]/150)*0.05 + (marks["math"]/150)*0.1 + (marks["physics"]/150)*0.1
    scores["Business"] += (marks["math"]/150)*0.2 + (marks["english"]/150)*0.3 + (marks["urdu"]/150)*0.2 + (marks["biology"]/150)*0.05 + (marks["chemistry"]/150)*0.05 + (marks["physics"]/150)*0.2
    scores["Commerce"] += (marks["math"]/150)*0.3 + (marks["english"]/150)*0.25 + (marks["urdu"]/150)*0.2 + (marks["biology"]/150)*0.05 + (marks["chemistry"]/150)*0.05 + (marks["physics"]/150)*0.15
    # Personality weights
    scores["Medical"] += ((personality.get("riasec_I",0)+personality.get("riasec_A",0))/10)*0.3
    scores["Engineering"] += ((personality.get("riasec_I",0)+personality.get("riasec_C",0))/10)*0.3
    scores["Computer Science"] += ((personality.get("riasec_C",0)+personality.get("tci_NoveltySeeking",0))/10)*0.3
    scores["Arts"] += ((personality.get("riasec_A",0)+personality.get("riasec_E",0))/10)*0.3
    scores["Business"] += ((personality.get("riasec_E",0)+personality.get("tci_RewardDependence",0))/10)*0.3
    scores["Commerce"] += ((personality.get("riasec_E",0)+personality.get("riasec_C",0))/10)*0.3
    # Normalize
    total = sum(scores.values())
    probs = {k: round(v/total,3) for k,v in scores.items()}
    probs = dict(sorted(probs.items(), key=lambda x: x[1], reverse=True))
    return probs

# -------------------- STREAMLIT SIDEBAR --------------------
st.sidebar.title("Navigation")
options = ["Home","RIASEC Test","TCI Test","Profile Creation","Dashboard","Recommendations"]
choice = st.sidebar.radio("Choose a section:", options, index=options.index(st.session_state.sidebar_choice))
st.session_state.sidebar_choice = choice

# -------------------- STREAMLIT PAGES --------------------
if choice=="Home":
    st.title("SkillBot Career & Personality Profiler")
    st.write("Discover your ideal career and personality traits")
    if st.button("Start RIASEC Test"):
        st.session_state.sidebar_choice = "RIASEC Test"
        st.session_state.page="quiz"
        st.session_state.index=0
        st.session_state.answers=[]
        st.rerun()

elif choice=="RIASEC Test":
    # (RIASEC test code same as before, using session_state.answers)
    pass

elif choice=="TCI Test":
    # (TCI test code same as before, using session_state.tci_answers)
    pass

elif choice=="Profile Creation":
    st.title("Create Profile")
    if st.session_state.user is None:
        st.warning("Login first")
    else:
        name = st.text_input("Full Name")
        gender = st.selectbox("Gender",["Male","Female","Other"])
        age = st.number_input("Age",10,100)
        qualification = st.selectbox("Qualification",["Matric","Intermediate","Bachelors","Masters","PhD"])
        marksheet = st.file_uploader("Upload Marksheet", type=["jpg","png","jpeg"])
        if st.button("Submit"):
            if marksheet:
                df_marks = extract_marks_from_file(marksheet)
                st.session_state.marksheet_df = df_marks
                st.success("Marksheet processed")

elif choice=="Recommendations":
    st.title("Career Recommendations")
    if st.session_state.marksheet_df is None or st.session_state.riasec_scores is None or st.session_state.tci_scores is None:
        st.warning("Complete tests and upload marksheet first")
    else:
        marks = extract_subject_scores(st.session_state.marksheet_df)
        personality = {**st.session_state.riasec_scores.to_dict(), **st.session_state.tci_scores.to_dict()}
        probs = calculate_best_fit(marks, personality)
        best_field = max(probs, key=probs.get)
        st.session_state.recommended_field = best_field
        st.session_state.recommended_subfields = SUBFIELDS[best_field]
        st.write(f"Recommended Field: {best_field}")
        st.write("Recommended Subfields:")
        for s in SUBFIELDS[best_field]:
            st.write(f"- {s}")

elif choice=="Dashboard":
    st.title("Dashboard")
    if st.session_state.riasec_scores is not None:
        st.subheader("RIASEC")
        st.bar_chart(st.session_state.riasec_scores)
    if st.session_state.tci_scores is not None:
        st.subheader("TCI")
        st.bar_chart(st.session_state.tci_scores)
    if st.session_state.recommended_field:
        st.subheader("Recommended Field")
        st.write(st.session_state.recommended_field)
        st.write(st.session_state.recommended_subfields)
