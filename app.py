import streamlit as st
import pandas as pd
import plotly.express as px
import json

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
    "page": "intro",  # RIASEC internal page flow
    "index": 0,       # RIASEC question index
    "answers": [],    # RIASEC answers
    "tci_page": "intro",  # TCI internal page flow
    "tci_index": 0,       # TCI question index
    "tci_answers": [],    # TCI answers
    "riasec_scores": None,
    "tci_scores": None,
    "sidebar_choice": "Home",  # current section
}
for key, val in defaults.items():
    if key not in st.session_state:
        st.session_state[key] = val


def restart_all():
    for key, val in defaults.items():
        st.session_state[key] = val


# -------------------- FLOW HELPERS --------------------
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
# MAIN NAVIGATION (Profile Creation hidden)
# =====================================================
st.sidebar.title("🧭 Navigation")
sidebar_options = ["Home", "RIASEC Test", "TCI Test", "Dashboard", "Profile Creation (Hidden)"]

# Hide Profile Creation from visible sidebar
visible_options = [opt for opt in sidebar_options if "Hidden" not in opt]

# If user is already in hidden page, don't reset choice
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
    st.write(
        """
        Discover your ideal **career path** and **personality traits** using two scientifically
        proven models:
        - **RIASEC (Holland Codes)** → measures your work interests  
        - **TCI (Temperament & Character Inventory)** → measures your personality

        Take both tests to unlock your personalized dashboard!
        """
    )
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

        if top_interest == "Social" and top_trait in ["Cooperativeness", "Reward Dependence"]:
            st.success("✅ You might excel in people-centered fields such as teaching, healthcare, or counseling.")
        elif top_interest == "Investigative" and top_trait in ["Persistence", "Self-Directedness"]:
            st.success("✅ You may thrive in analytical or research careers, like data science or engineering.")
        elif top_interest == "Artistic" and top_trait in ["Novelty Seeking", "Self-Transcendence"]:
            st.success("✅ Creative roles such as design, writing, or media could fit your personality.")
        else:
            st.info("Use both profiles to guide your exploration — your mix of traits is unique!")

        st.divider()
        if st.button("✨ Want more personalized results?"):
            st.session_state.sidebar_choice = "Profile Creation (Hidden)"
            st.rerun()

        if st.button("🏠 Back to Home"):
            restart_all()
            st.session_state.sidebar_choice = "Home"
            st.rerun()

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

    # Education Info
    education = st.text_input("Current Class/Grade")

    # Upload marksheet
    marksheet = st.file_uploader("Upload Your Marksheet (PDF or Image)", type=["pdf", "png", "jpg", "jpeg"])

    if st.button("Submit Profile"):
        if not name or not age or not gender or not education or not marksheet:
            st.error("Please fill all fields and upload marksheet")
        else:
            profile_data = {
                "name": name,
                "age": age,
                "gender": gender,
                "education": education,
                "marksheet_filename": marksheet.name
            }
            with open(f"{name}_profile.json", "w") as f:
                json.dump(profile_data, f)

            st.success("Profile created successfully!")
            st.json(profile_data)
            if st.button("⬅️ Back to Dashboard"):
                st.session_state.sidebar_choice = "Dashboard"
                st.rerun()
