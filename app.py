import streamlit as st
import pandas as pd
import plotly.express as px
from supabase import create_client, Client
from PIL import Image
from paddleocr import PaddleOCR
import re
import io

# Initialize OCR only once
if "ocr" not in st.session_state:
    st.session_state.ocr = PaddleOCR(use_angle_cls=True, lang="en")

ocr = st.session_state.ocr

# Example usage:
# result = ocr.ocr("example.jpg", cls=True)
# st.write(result)


# -------------------- SUPABASE SETUP --------------------
SUPABASE_URL = "https://jaztokuyzxettemexcrc.supabase.co"
SUPABASE_KEY = "YOUR_SUPABASE_KEY"
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# -------------------- PAGE SETUP --------------------
st.set_page_config(page_title="SkillBot Career & Personality Profiler", layout="centered")

# -------------------- LOAD DATA --------------------
try:
    questions = pd.read_csv("questions.csv")
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
    "marksheet_df": None,
}
for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

def restart_all():
    for k, v in defaults.items():
        st.session_state[k] = v

# -------------------- AUTH --------------------
def signup_user(email, password):
    return supabase.auth.sign_up({"email": email, "password": password})

def login_user(email, password):
    return supabase.auth.sign_in_with_password({"email": email, "password": password})

def logout_user():
    st.session_state.user = None
    st.session_state.access_token = None
    st.session_state.sidebar_choice = "Home"
    st.success("Logged out successfully!")

# -------------------- SAVE RESULTS --------------------
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
            "tci_NoveltySeeking": tci_dict.get("NoveltySeeking"),
            "tci_RewardDependence": tci_dict.get("RewardDependence"),
            "tci_SelfDirectedness": tci_dict.get("SelfDirectedness"),
            "tci_SelfTranscendence": tci_dict.get("SelfTranscendence"),
        }).execute()
        st.success("✅ Test results saved!")
    except Exception as e:
        st.error(f"Could not save results: {e}")

def upload_marksheet(user_id, file):
    try:
        file_bytes = file.read()
        filename = f"{user_id}_{file.name}"
        supabase.storage.from_("marksheets").upload(filename, file_bytes)
        public_url = supabase.storage.from_("marksheets").get_public_url(filename)
        st.success("✅ Marksheet uploaded!")
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
            st.success("✅ Profile saved!")
        else:
            st.warning("Could not save profile. Check schema/permissions.")
    except Exception as e:
        st.error(f"Failed to save profile: {e}")

# -------------------- OCR --------------------
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
        except:
            return None
    return None

def parse_marks(text_list):
    subjects, maximum, obtained = [], [], []
    for i, t in enumerate(text_list):
        t = t.strip()
        if t and len(t)>1:
            subjects.append(t)
            maximum.append(100)
            obtained.append(80)  # demo value, replace with robust logic if needed
    return pd.DataFrame({"Subject": subjects, "Maximum": maximum, "Obtained": obtained})

# -------------------- RIASEC / TCI --------------------
def next_question(selected):
    st.session_state.answers.append(selected)
    st.session_state.index += 1
    if st.session_state.index >= len(questions):
        st.session_state.page = "riasec_results"
    st.rerun()

def next_tci(selected):
    st.session_state.tci_answers.append(selected)
    st.session_state.tci_index += 1
    if st.session_state.tci_index >= len(tci_questions):
        st.session_state.tci_page = "tci_results"
    st.rerun()

# -------------------- RECOMMENDATION --------------------
SUBFIELDS = {
    "Engineering":["Mechanical","Electrical","Civil","Software","Chemical"],
    "Medical":["MBBS","Pharmacy","Physio","Nursing","Biotech"],
    "Computer Science":["AI","Data Science","Cyber Security","Software","IT Management"],
    "Business":["BBA","Marketing","Finance","HR","Supply Chain"],
    "Arts":["Psychology","Fine Arts","Mass Comm","English","Sociology"],
    "Commerce":["B.Com","Accounting","Banking","Economics","Business Admin"]
}

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
    scores["Medical"] += (marks.get("biology",0)/150)*0.35 + (marks.get("chemistry",0)/150)*0.35
    scores["Engineering"] += (marks.get("math",0)/150)*0.35 + (marks.get("physics",0)/150)*0.35
    scores["Medical"] += personality.get("riasec_I",0)/10*0.3
    scores["Engineering"] += personality.get("riasec_C",0)/10*0.3
    total=sum(scores.values())
    probabilities={k:round(v/total,3) for k,v in scores.items()}
    return dict(sorted(probabilities.items(), key=lambda x:x[1], reverse=True))

def recommend_field(personality_csv, marksheet_csv):
    p= pd.read_csv(personality_csv)
    m= pd.read_csv(marksheet_csv)
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

# -------------------- SIDEBAR --------------------
st.sidebar.title("Navigation")
options = ["Home","RIASEC Test","TCI Test","Dashboard","Sign Up / Login","Profile Creation"]
choice = st.sidebar.radio("Go to:", options, index=options.index(st.session_state.sidebar_choice))
st.session_state.sidebar_choice = choice

# -------------------- PAGES --------------------
if choice=="Home":
    st.title("🎓 SkillBot Career Profiler")
    st.write("Discover your career & personality path.")
    if st.button("Start RIASEC Test"):
        st.session_state.page="quiz"
        st.session_state.sidebar_choice="RIASEC Test"
        st.rerun()

elif choice=="RIASEC Test":
    if st.session_state.page=="intro":
        st.title("🧭 RIASEC Test")
        if st.button("Start Test"):
            st.session_state.page="quiz"
            st.session_state.index=0
            st.session_state.answers=[]
            st.rerun()
    elif st.session_state.page=="quiz":
        q_idx = st.session_state.index
        if q_idx<len(questions):
            q=questions.iloc[q_idx]
            st.markdown(f"### {q['question']}")
            for i, opt in enumerate(["Strongly Disagree","Disagree","Neutral","Agree","Strongly Agree"]):
                if st.button(opt, key=f"riasec{q_idx}_{i}"):
                    next_question(opt)
    elif st.session_state.page=="riasec_results":
        df=questions.copy()
        df["answer"]=st.session_state.answers
        rating_map={"Strongly Disagree":1,"Disagree":2,"Neutral":3,"Agree":4,"Strongly Agree":5}
        df["score"]=df["answer"].map(rating_map)
        riasec_scores=df.groupby("category")["score"].mean().sort_values(ascending=False)
        st.session_state.riasec_scores=riasec_scores
        st.bar_chart(riasec_scores)
        if st.button("Next: TCI Test"):
            st.session_state.sidebar_choice="TCI Test"
            st.rerun()

elif choice=="TCI Test":
    if st.session_state.tci_page=="intro":
        st.title("🧠 TCI Test")
        if st.button("Start Test"):
            st.session_state.tci_page="quiz"
            st.session_state.tci_index=0
            st.session_state.tci_answers=[]
            st.rerun()
    elif st.session_state.tci_page=="quiz":
        q_idx=st.session_state.tci_index
        if q_idx<len(tci_questions):
            q=tci_questions.iloc[q_idx]
            st.markdown(f"### {q['question']}")
            col1,col2=st.columns(2)
            if col1.button("True",key=f"t{q_idx}"): next_tci("T")
            if col2.button("False",key=f"f{q_idx}"): next_tci("F")
    elif st.session_state.tci_page=="tci_results":
        df=tci_questions.copy()
        df["answer"]=st.session_state.tci_answers
        df["score"]=df["answer"].map({"T":1,"F":0})
        tci_scores=df.groupby("trait")["score"].sum()
        st.session_state.tci_scores=tci_scores
        fig=px.bar(tci_scores,x=tci_scores.index,y=tci_scores.values)
        st.plotly_chart(fig)
        if st.button("Go to Dashboard"):
            st.session_state.sidebar_choice="Dashboard"
            st.rerun()

elif choice=="Dashboard":
    st.title("📊 Dashboard")
    r,t=st.session_state.riasec_scores,st.session_state.tci_scores
    if r is None or t is None: st.warning("Complete tests first")
    else:
        c1,c2=st.columns(2)
        c1.subheader("RIASEC"); c1.bar_chart(r)
        c2.subheader("TCI"); c2.bar_chart(t)
        st.divider()
        st.info("Use profiles for career guidance")

elif choice=="Sign Up / Login":
    st.title("🔐 Account")
    tab1,tab2=st.tabs(["Login","Sign Up"])
    with tab1:
        email=st.text_input("Email",key="login_email")
        password=st.text_input("Password",type="password",key="login_pass")
        if st.button("Login"): 
            res=login_user(email,password)
            if res.user:
                st.session_state.user=res.user
                st.session_state.access_token=res.session.access_token
                st.success("Logged in!")
                st.session_state.sidebar_choice="Profile Creation"
                st.rerun()
    with tab2:
        email=st.text_input("Email",key="signup_email")
        password=st.text_input("Password",type="password",key="signup_pass")
        if st.button("Sign Up"): 
            res=signup_user(email,password)
            if res.user:
                st.session_state.user=res.user
                st.session_state.access_token=res.session.access_token
                st.success("Account created!")
                st.session_state.sidebar_choice="Profile Creation"
                st.rerun()

elif choice=="Profile Creation":
    st.title("👤 Profile")
    if st.session_state.user is None: st.warning("Login first")
    else:
        name=st.text_input("Full Name")
        gender=st.selectbox("Gender",["Male","Female","Other"])
        age=st.number_input("Age",min_value=10,max_value=100)
        qual=st.selectbox("Qualification",["Matric","Intermediate","Bachelors","Masters","PhD"])
        marksheet=st.file_uploader("Upload Marksheet",type=["jpg","jpeg","png","pdf"])
        if st.button("Submit"):
            if all([name,gender,age,qual,marksheet]):
                marksheet_url=upload_marksheet(st.session_state.user.id,marksheet)
                if marksheet_url:
                    save_profile(st.session_state.user.id,name,gender,age,qual,marksheet_url)
                    text_list=extract_text_from_image(marksheet)
                    df_marks=parse_marks(text_list)
                    df_marks.to_csv("user_marksheet.csv",index=False)
                    if st.session_state.riasec_scores is not None and st.session_state.tci_scores is not None:
                        save_results_to_supabase(st.session_state.user.id,
                                                 st.session_state.riasec_scores,
                                                 st.session_state.tci_scores)
                        recommend_field("response.csv","user_marksheet.csv")
