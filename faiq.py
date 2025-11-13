import streamlit as st
import pandas as pd
import plotly.express as px
import json
import os
from datetime import datetime

# -------------------- PAGE SETUP --------------------
st.set_page_config(page_title="SkillBot Career & Personality Profiler", layout="centered")

# -------------------- LOAD DATA --------------------
try:
    questions = pd.read_csv("questions.csv")
    careers = pd.read_csv("careers.csv")
    tci_questions = pd.read_csv("tci_questions.csv")
except FileNotFoundError as e:
    st.error(f"Error loading data file: {e}. Make sure 'questions.csv', 'careers.csv', and 'tci_questions.csv' are in the correct directory.")
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
    "user_authenticated": False,
    "user_data": None,
}
for key, val in defaults.items():
    if key not in st.session_state:
        st.session_state[key] = val


def restart_all():
    for key, val in defaults.items():
        st.session_state[key] = val


# -------------------- HELPERS --------------------
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
sidebar_options = ["Home", "RIASEC Test", "TCI Test", "Dashboard", "Sign Up", "Profile Creation (Hidden)"]
visible_options = [opt for opt in sidebar_options if "Hidden" not in opt]
if st.session_state.sidebar_choice == "Profile Creation (Hidden)":
    choice = "Profile Creation (Hidden)"
else:
    selected_index = visible_options.index(st.session_state.sidebar_choice) if st.session_state.sidebar_choice in visible_options else 0
    st.session_state.sidebar_choice = st.sidebar.radio(
        "Choose a section:",
        visible_options,
        index=selected_index
    )
    choice = st.session_state.sidebar_choice


# =====================================================
# HOME PAGE
# =====================================================
if choice == "Home":
    st.title("🎓 SkillBot Career & Personality Profiler")
    st.write("""
        Discover your ideal **career path** and **personality traits** using:
        - **RIASEC (Holland Codes)** → measures your work interests  
        - **TCI (Temperament & Character Inventory)** → measures your personality
    """)
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
    elif st.session_state.page == "riasec_results":
        st.title("Your RIASEC Profile")
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
        st.warning("⚠️ Please complete both tests first.")
    else:
        col1, col2 = st.columns(2)
        with col1:
            st.subheader("RIASEC Interests")
            st.bar_chart(riasec_scores)
        with col2:
            st.subheader("TCI Traits")
            st.bar_chart(tci_scores)

        st.divider()
        st.subheader("Insight Summary")
        top_interest = riasec_scores.idxmax()
        top_trait = tci_scores.idxmax()
        st.write(f"Top Interest: **{top_interest}**, Top Trait: **{top_trait}**")

        st.info("Use both profiles to guide your career choices!")

        st.divider()
        if st.button("✨ Want more personalized results?"):
            st.session_state.sidebar_choice = "Sign Up"
            st.rerun()


# =====================================================
# SIGN UP
# =====================================================
elif choice == "Sign Up":
    st.title("🔐 Create an Account")
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")
    confirm = st.text_input("Confirm Password", type="password")

    if st.button("Sign Up"):
        if not username or not password or not confirm:
            st.error("Please fill all fields.")
        elif password != confirm:
            st.error("Passwords do not match.")
        else:
            os.makedirs("users", exist_ok=True)
            data = {"username": username, "password": password}
            with open(f"users/{username}.json", "w") as f:
                json.dump(data, f)
            st.success("Account created successfully!")
            st.session_state.user_authenticated = True
            st.session_state.sidebar_choice = "Profile Creation (Hidden)"
            st.rerun()


# =====================================================
# PROFILE CREATION
# =====================================================
elif choice == "Profile Creation (Hidden)":
    st.title("👤 Create Your Profile")
    name = st.text_input("Full Name")
    gender = st.selectbox("Gender", ["Male", "Female", "Other"])
    age = st.number_input("Age", min_value=10, max_value=100)
    qualification = st.selectbox("Qualification Level", ["Matric", "Intermediate", "Bachelors", "Masters", "PhD"])
    marksheet = st.file_uploader("Upload your marksheet (image or PDF)", type=["jpg", "jpeg", "png", "pdf"])

    if st.button("Submit Profile"):
        if not name or not gender or not age or not qualification or not marksheet:
            st.error("Please fill all fields and upload your marksheet.")
        else:
            os.makedirs("profiles", exist_ok=True)
            # Save marksheet temporarily
            file_path = f"profiles/{datetime.now().strftime('%Y%m%d_%H%M%S')}_{marksheet.name}"
            with open(file_path, "wb") as f:
                f.write(marksheet.getbuffer())

            profile = {
                "name": name,
                "gender": gender,
                "age": age,
                "qualification": qualification,
                "marksheet_file": file_path
            }
            with open(f"profiles/{name}_profile.json", "w") as f:
                json.dump(profile, f)
            st.success("Profile created successfully!")
            st.json(profile)
