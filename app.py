import streamlit as st
import pandas as pd
import plotly.express as px
import sqlite3
import json
import os
from supabase import create_client, Client

SUPABASE_URL = st.secrets["https://supabase.com/dashboard/project/qbhnfvrqzsmvxggtlxoq/settings/api-keys"]
SUPABASE_KEY = st.secrets["eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InFiaG5mdnJxenNtdnhnZ3RseG9xIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjMxMTY4NDUsImV4cCI6MjA3ODY5Mjg0NX0.EQVJqrn5gQy_ofKPY3z8zIR-N8Zv35R9YuJ0xAkXWsA"]

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
def upload_marksheet(file):
    file_bytes = file.read()
    file_path = file.name

    supabase.storage.from_("marksheets").upload(file_path, file_bytes)

    public_url = supabase.storage.from_("marksheets").get_public_url(file_path)
    return public_url

# =====================================================
# DATABASE CONNECTION
# =====================================================
conn = sqlite3.connect("skillbot.db", check_same_thread=False)
cursor = conn.cursor()

# =====================================================
# PAGE SETUP
# =====================================================
st.set_page_config(page_title="SkillBot Career & Personality Profiler", layout="centered")

# =====================================================
# DATABASE SETUP
# =====================================================
def init_db():
    conn = sqlite3.connect("skillbot.db")
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            age INTEGER,
            gender TEXT,
            education TEXT,
            marksheet_filename TEXT,
            riasec_scores TEXT,
            tci_scores TEXT
        )
    """)
    conn.commit()
    conn.close()


def save_profile_to_db(profile_data):
    import sqlite3, json

    conn = sqlite3.connect("skillbot.db")
    c = conn.cursor()

    # Convert pandas objects (like Series or DataFrame) into dicts before saving
    riasec_scores = profile_data.get("riasec_scores", {})
    if hasattr(riasec_scores, "to_dict"):
        riasec_scores = riasec_scores.to_dict()

    tci_scores = profile_data.get("tci_scores", {})
    if hasattr(tci_scores, "to_dict"):
        tci_scores = tci_scores.to_dict()

    riasec_json = json.dumps(riasec_scores)
    tci_json = json.dumps(tci_scores)

    c.execute("""
        INSERT INTO users (name, age, gender, education, marksheet_filename, riasec_scores, tci_scores)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        profile_data["name"],
        profile_data["age"],
        profile_data["gender"],
        profile_data["education"],
        profile_data["marksheet_filename"],
        riasec_json,
        tci_json
    ))

    conn.commit()
    conn.close()


def fetch_all_profiles():
    conn = sqlite3.connect("skillbot.db")
    df = pd.read_sql_query("SELECT * FROM users", conn)
    conn.close()
    return df


# Initialize DB at startup
init_db()

# =====================================================
# LOAD DATA
# =====================================================
try:
    questions = pd.read_csv("questions.csv")
    careers = pd.read_csv("careers.csv")
    tci_questions = pd.read_csv("tci_questions.csv")
except FileNotFoundError as e:
    st.error(f"Error loading data file: {e}. Make sure 'questions.csv', 'careers.csv', and 'tci_questions.csv' are in the correct directory.")
    st.stop()

# =====================================================
# SESSION STATE
# =====================================================
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
}

for key, val in defaults.items():
    if key not in st.session_state:
        st.session_state[key] = val


def restart_all():
    for key, val in defaults.items():
        st.session_state[key] = val


# =====================================================
# FLOW HELPERS
# =====================================================
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
# MAIN NAVIGATION
# =====================================================
st.sidebar.title("🧭 Navigation")
sidebar_options = ["Home", "RIASEC Test", "TCI Test", "Dashboard", "Profile Creation (Hidden)"]

visible_options = [opt for opt in sidebar_options if "Hidden" not in opt]

if st.session_state.sidebar_choice == "Profile Creation (Hidden)":
    choice = "Profile Creation (Hidden)"
else:
    selected_index = visible_options.index(st.session_state.sidebar_choice) if st.session_state.sidebar_choice in visible_options else 0
    st.session_state.sidebar_choice = st.sidebar.radio("Choose a section:", visible_options, index=selected_index)
    choice = st.session_state.sidebar_choice


# =====================================================
# HOME PAGE
# =====================================================
if choice == "Home":
    st.title("🎓 SkillBot Career & Personality Profiler")
    st.write("""
        Discover your ideal **career path** and **personality traits** using two scientifically
        proven models:
        - **RIASEC (Holland Codes)** → measures your work interests  
        - **TCI (Temperament & Character Inventory)** → measures your personality
    """)
    st.image("https://upload.wikimedia.org/wikipedia/commons/3/3c/Holland_RIASEC_model.png", use_container_width=True)

    if st.button("Start Now ➡️"):
        st.session_state.page = "quiz"
        st.session_state.index = 0
        st.session_state.answers = []
        st.session_state.sidebar_choice = "RIASEC Test"
        st.rerun()


# =====================================================
# RIASEC TEST
# =====================================================
elif choice == "RIASEC Test":
    if st.session_state.page == "intro":
        st.title("🧭 RIASEC Interest Profiler")
        st.write("Rate how much you’d enjoy different work activities.")
        if st.button("Start RIASEC Test"):
            st.session_state.page = "quiz"
            st.session_state.index = 0
            st.session_state.answers = []
            st.rerun()

    elif st.session_state.page == "quiz":
        if st.session_state.index < len(questions):
            q_idx = st.session_state.index
            q = questions.iloc[q_idx]
            st.markdown(f"### Question {q_idx + 1} of {len(questions)}")
            st.markdown(f"**{q['question']}**")

            options = {
                "Strongly Disagree": "😠",
                "Disagree": "🙁",
                "Neutral": "😐",
                "Agree": "🙂",
                "Strongly Agree": "🤩"
            }

            cols = st.columns(len(options))
            for i, (label, icon) in enumerate(options.items()):
                if cols[i].button(f"{icon} {label}", key=f"riasec_q{q_idx}_option{i}"):
                    next_question(label)
        else:
            st.session_state.page = "riasec_results"
            st.rerun()

    elif st.session_state.page == "riasec_results":
        st.title("Your RIASEC Profile")
        if not st.session_state.answers:
            st.warning("Please complete the RIASEC test first.")
        else:
            df = questions.copy()
            df["answer"] = st.session_state.answers
            rating_map = {"Strongly Disagree": 1, "Disagree": 2, "Neutral": 3, "Agree": 4, "Strongly Agree": 5}
            df["score"] = df["answer"].map(rating_map)
            riasec_scores = df.groupby("category")["score"].mean().sort_values(ascending=False)
            st.session_state.riasec_scores = riasec_scores

            st.bar_chart(riasec_scores)
            top = riasec_scores.head(3).index.tolist()
            st.success(f"Your top RIASEC types are: **{', '.join(top)}**")

            if st.button("Next ➡️ Go to TCI Test"):
                st.session_state.tci_page = "intro"
                st.session_state.sidebar_choice = "TCI Test"
                st.rerun()


# =====================================================
# TCI TEST
# =====================================================
elif choice == "TCI Test":
    if st.session_state.tci_page == "intro":
        st.title("🧠 Temperament & Character Inventory (TCI)")
        st.write("Measures seven personality traits that define your behavior and values.")
        if st.button("Start TCI Test"):
            st.session_state.tci_page = "quiz"
            st.session_state.tci_index = 0
            st.session_state.tci_answers = []
            st.rerun()

    elif st.session_state.tci_page == "quiz":
        if st.session_state.tci_index < len(tci_questions):
            q_idx = st.session_state.tci_index
            q = tci_questions.iloc[q_idx]
            st.markdown(f"### Question {q_idx + 1} of {len(tci_questions)}")
            st.markdown(f"**{q['question']}**")

            cols = st.columns(2)
            if cols[0].button("✅ True", key=f"tci_q{q_idx}_true"):
                next_tci("T")
            if cols[1].button("❌ False", key=f"tci_q{q_idx}_false"):
                next_tci("F")
        else:
            st.session_state.tci_page = "tci_results"
            st.rerun()

    elif st.session_state.tci_page == "tci_results":
        st.title("Your TCI Personality Profile")
        df = tci_questions.copy()
        df["answer"] = st.session_state.tci_answers
        df["score"] = df["answer"].map({"T": 1, "F": 0})
        tci_scores = df.groupby("trait")["score"].sum()
        st.session_state.tci_scores = tci_scores

        fig = px.bar(tci_scores, x=tci_scores.index, y=tci_scores.values,
                     labels={"x": "Trait", "y": "Score"},
                     title="Temperament and Character Dimensions")
        st.plotly_chart(fig, use_container_width=True)
        st.info("High scores = stronger presence of that trait.")

        if st.button("View Combined Dashboard ➡️"):
            st.session_state.sidebar_choice = "Dashboard"
            st.rerun()


# =====================================================
# DASHBOARD
# =====================================================
elif choice == "Dashboard":
    st.title("📊 Combined Career & Personality Dashboard")

    riasec_scores = st.session_state.get("riasec_scores", None)
    tci_scores = st.session_state.get("tci_scores", None)

    if riasec_scores is None or tci_scores is None:
        st.warning("⚠️ Please complete both tests first (RIASEC and TCI).")
    else:
        col1, col2 = st.columns(2)
        with col1:
            st.subheader("RIASEC Interests")
            st.bar_chart(riasec_scores)
        with col2:
            st.subheader("TCI Personality Traits")
            st.bar_chart(tci_scores)

        st.divider()
        st.subheader("🧩 Insight Summary")
        top_interest = riasec_scores.idxmax()
        top_trait = tci_scores.idxmax()
        st.write(f"Your strongest **career interest** is **{top_interest}**, and your dominant **personality trait** is **{top_trait}**.")

        st.divider()
        if st.button("✨ Want more personalized results?"):
            st.session_state.sidebar_choice = "Profile Creation (Hidden)"
            st.rerun()

        if st.button("🏠 Back to Home"):
            restart_all()
            st.session_state.sidebar_choice = "Home"
            st.rerun()

        st.divider()
        st.subheader("🗂️ Saved Profiles in Database")
        profiles = fetch_all_profiles()
        if not profiles.empty:
            st.dataframe(profiles)
        else:
            st.info("No profiles saved yet.")
            
def save_profile_to_supabase(data):
    response = supabase.table("profiles").insert({
        "name": data["name"],
        "age": data["age"],
        "gender": data["gender"],
        "education": data["education"],
        "marksheet_url": data["marksheet_url"],
        "riasec_scores": data["riasec_scores"],
        "tci_scores": data["tci_scores"]
    }).execute()
    return response


# =====================================================
# PROFILE CREATION (Hidden Tab)
# =====================================================
elif choice == "Profile Creation (Hidden)":
    st.title("👤 SkillBot AI - Profile Creation")
    st.write("Please fill your details and upload your marksheet:")

    # Basic Info
    name = st.text_input("Full Name")
    age = st.number_input("Age", min_value=10, max_value=100)
    gender = st.selectbox("Gender", ["Male", "Female", "Other"])
    education = st.text_input("Current Class/Grade")
    marksheet = st.file_uploader("Upload Your Marksheet (PDF or Image)", type=["pdf", "png", "jpg", "jpeg"])

  if st.button("Submit Profile"):
    if not name or not age or not gender or not education or not marksheet:
        st.error("Please fill all fields and upload marksheet")
    else:
        # Upload marksheet to Supabase Storage
        marksheet_url = upload_marksheet(marksheet)

        # Prepare data for database
        data = {
            "name": name,
            "age": age,
            "gender": gender,
            "education": education,
            "marksheet_url": marksheet_url,
            "riasec_scores": st.session_state.get("riasec_scores", {}),
            "tci_scores": st.session_state.get("tci_scores", {})
        }

        # Save to Supabase table
        save_profile_to_supabase(data)

        st.success("Profile saved successfully to Supabase!")
        st.json(data)

         

    if st.button("⬅️ Back to Dashboard"):
        st.session_state.sidebar_choice = "Dashboard"
        st.rerun()
