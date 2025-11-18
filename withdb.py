import streamlit as st
import pandas as pd
import plotly.express as px
from supabase import create_client, Client

# -------------------- SUPABASE SETUP --------------------
SUPABASE_URL = "https://oyevrxbodltehetyqisn.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im95ZXZyeGJvZGx0ZWhldHlxaXNuIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjM0NjQwMTQsImV4cCI6MjA3OTA0MDAxNH0.KPtbyyQjpwyPX-DU3R4t7iZ1o_uXVsd6dImYBD9yO6U"  # Replace with your key
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
    "user": None,  # Supabase user object
    "access_token": None
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
        # Convert Pandas Series to normal dict
        riasec_dict = riasec.to_dict()
        tci_dict = tci.to_dict()

        response = supabase.table("test_results").insert({
            "user_id": user_id,

            # ----- RIASEC -----
            "riasec_R": riasec_dict.get("R"),
            "riasec_I": riasec_dict.get("I"),
            "riasec_A": riasec_dict.get("A"),
            "riasec_S": riasec_dict.get("S"),
            "riasec_E": riasec_dict.get("E"),
            "riasec_C": riasec_dict.get("C"),

            # ----- TCI -----
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

        # Upload file
        supabase.storage.from_("marksheets").upload(filename, file_bytes)

        # Get public URL (returns a string)
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

# -------------------- HELPER FUNCTIONS --------------------
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

# =====================================================
# SIDEBAR NAVIGATION
# =====================================================
st.sidebar.title("🧭 Navigation")
options = ["Home", "RIASEC Test", "TCI Test", "Dashboard", "Sign Up / Login", "Profile Creation (Hidden)"]
choice = st.sidebar.radio("Choose a section:", options, index=options.index(st.session_state.sidebar_choice))
st.session_state.sidebar_choice = choice

# =====================================================
# HOME PAGE
# =====================================================
if choice == "Home":
    st.title("🎓 SkillBot Career & Personality Profiler")
    st.write("""
        Discover your ideal **career path** and **personality traits** using:
        - **RIASEC (Holland Codes)**  
        - **TCI (Temperament & Character Inventory)**
    """)
    if st.button("Start Now ➡️"):
        st.session_state.page = "quiz"
        st.session_state.sidebar_choice = "RIASEC Test"
        st.rerun()

# =====================================================
# RIASEC TEST
# =====================================================
elif choice == "RIASEC Test":
    if st.session_state.page == "intro":
        st.title("🧭 RIASEC Interest Profiler")
        if st.button("Start RIASEC Test"):
            st.session_state.page = "quiz"
            st.session_state.index = 0
            st.session_state.answers = []
            st.rerun()
    elif st.session_state.page == "quiz":
        q_idx = st.session_state.index
        if q_idx < len(questions):
            q = questions.iloc[q_idx]
            st.markdown(f"### Question {q_idx + 1} of {len(questions)}")
            st.markdown(f"**{q['question']}**")
            options_map = {"Strongly Disagree":"😠","Disagree":"🙁","Neutral":"😐","Agree":"🙂","Strongly Agree":"🤩"}
            cols = st.columns(len(options_map))
            for i, (label, icon) in enumerate(options_map.items()):
                if cols[i].button(f"{icon} {label}", key=f"riasec_q{q_idx}_{i}"):
                    next_question(label)
    elif st.session_state.page == "riasec_results":
        st.title("Your RIASEC Profile")
        df = questions.copy()
        df["answer"] = st.session_state.answers
        rating_map = {"Strongly Disagree":1,"Disagree":2,"Neutral":3,"Agree":4,"Strongly Agree":5}
        df["score"] = df["answer"].map(rating_map)
        riasec_scores = df.groupby("category")["score"].mean().sort_values(ascending=False)
        st.session_state.riasec_scores = riasec_scores
        st.bar_chart(riasec_scores)
        top = riasec_scores.head(3).index.tolist()
        st.success(f"Your top RIASEC types are: **{', '.join(top)}**")
        if st.button("Next ➡️ Go to TCI Test"):
            st.session_state.sidebar_choice = "TCI Test"
            st.rerun()

# =====================================================
# TCI TEST
# =====================================================
elif choice == "TCI Test":
    if st.session_state.tci_page == "intro":
        st.title("🧠 Temperament & Character Inventory (TCI)")
        if st.button("Start TCI Test"):
            st.session_state.tci_page = "quiz"
            st.session_state.tci_index = 0
            st.session_state.tci_answers = []
            st.rerun()
    elif st.session_state.tci_page == "quiz":
        q_idx = st.session_state.tci_index
        if q_idx < len(tci_questions):
            q = tci_questions.iloc[q_idx]
            st.markdown(f"### Question {q_idx + 1} of {len(tci_questions)}")
            st.markdown(f"**{q['question']}**")
            col1, col2 = st.columns(2)
            if col1.button("✅ True", key=f"tci_t{q_idx}"):
                next_tci("T")
            if col2.button("❌ False", key=f"tci_f{q_idx}"):
                next_tci("F")
    elif st.session_state.tci_page == "tci_results":
        st.title("Your TCI Personality Profile")
        df = tci_questions.copy()
        df["answer"] = st.session_state.tci_answers
        df["score"] = df["answer"].map({"T": 1, "F": 0})
        tci_scores = df.groupby("trait")["score"].sum()
        st.session_state.tci_scores = tci_scores
        fig = px.bar(tci_scores, x=tci_scores.index, y=tci_scores.values, labels={"x": "Trait","y": "Score"})
        st.plotly_chart(fig, use_container_width=True)
        if st.button("View Combined Dashboard ➡️"):
            st.session_state.sidebar_choice = "Dashboard"
            st.rerun()

# =====================================================
# DASHBOARD
# =====================================================
elif choice == "Dashboard":
    st.title("📊 Combined Career & Personality Dashboard")
    r, t = st.session_state.riasec_scores, st.session_state.tci_scores
    if r is None or t is None:
        st.warning("Please complete both tests first.")
    else:
        c1, c2 = st.columns(2)
        with c1: st.subheader("RIASEC"); st.bar_chart(r)
        with c2: st.subheader("TCI"); st.bar_chart(t)
        st.divider()
        st.info("Use both profiles to guide your career choices!")
        if st.button("✨ Want more personalized results?"):
            st.session_state.sidebar_choice = "Sign Up / Login"
            st.rerun()

# =====================================================
# SIGN UP / LOGIN
# =====================================================
elif choice == "Sign Up / Login":
    st.title("🔐 Account")
    tab1, tab2 = st.tabs(["Login", "Sign Up"])

    with tab1:
        email = st.text_input("Email", key="login_email")
        password = st.text_input("Password", type="password", key="login_pass")
        if st.button("Login"):
            res = login_user(email, password)
            if res.user:
                st.session_state.user = res.user
                st.session_state.access_token = res.session.access_token
                st.success("✅ Logged in successfully!")
                st.session_state.sidebar_choice = "Profile Creation (Hidden)"
                st.rerun()

    with tab2:
        email = st.text_input("Email", key="signup_email")
        password = st.text_input("Password", type="password", key="signup_pass")
        if st.button("Sign Up"):
            res = signup_user(email, password)
            if res.user:
                st.session_state.user = res.user
                st.session_state.access_token = res.session.access_token
                st.success("✅ Account created successfully!")
                st.session_state.sidebar_choice = "Profile Creation (Hidden)"
                st.rerun()

# =====================================================
# PROFILE CREATION
# =====================================================
elif choice == "Profile Creation (Hidden)":
    st.title("👤 Create Your Profile")
    if st.session_state.user is None:
        st.warning("Please login first.")
    else:
        name = st.text_input("Full Name")
        gender = st.selectbox("Gender", ["Male", "Female", "Other"])
        age = st.number_input("Age", min_value=10, max_value=100)
        qualification = st.selectbox("Qualification", ["Matric","Intermediate","Bachelors","Masters","PhD"])
        marksheet = st.file_uploader("Upload Marksheet", type=["jpg","jpeg","png","pdf"])

        if st.button("Submit Profile"):
            if not all([name, gender, age, qualification, marksheet]):
                st.error("Please fill all fields.")
            else:
                marksheet_url = upload_marksheet(st.session_state.user.id, marksheet)
                if marksheet_url:
                    save_profile(
                        st.session_state.user.id, name, gender, age, qualification, marksheet_url
                    )
                    if st.session_state.riasec_scores is not None and st.session_state.tci_scores is not None:
                        save_results_to_supabase(
                            st.session_state.user.id, st.session_state.riasec_scores, st.session_state.tci_scores
                        )
