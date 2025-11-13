import streamlit as st
import sqlite3
import pandas as pd
from PIL import Image
import pytesseract
import re

# =====================================================
# DATABASE SETUP
# =====================================================
def init_db():
    conn = sqlite3.connect("skillbot_profiles.db")
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS profiles (
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
    conn = sqlite3.connect("skillbot_profiles.db")
    c = conn.cursor()
    c.execute("""
        INSERT INTO profiles (name, age, gender, education, marksheet_filename, riasec_scores, tci_scores)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        profile_data["name"],
        profile_data["age"],
        profile_data["gender"],
        profile_data["education"],
        profile_data["marksheet_filename"],
        str(profile_data["riasec_scores"]),
        str(profile_data["tci_scores"])
    ))
    conn.commit()
    conn.close()

# =====================================================
# OCR AND FIELD SUGGESTION FUNCTIONS
# =====================================================
def extract_marks_from_image(file):
    """Extract subject marks from an uploaded marksheet image."""
    marks = {}

    try:
        img = Image.open(file)
        text = pytesseract.image_to_string(img)

        # Extract subject marks (e.g., English: 85)
        pattern = r"([A-Za-z ]+)\s*[:\-]\s*(\d{1,3})"
        for subject, score in re.findall(pattern, text):
            marks[subject.strip().title()] = int(score)

        if not marks:
            marks["Note"] = "No clear marks found — please upload a clearer marksheet."
    except Exception as e:
        marks["error"] = str(e)

    return marks


def suggest_fields(riasec_scores, tci_scores, marks):
    """Suggest career fields based on RIASEC, TCI, and marks."""
    suggestions = []

    def get(subject):
        for k, v in marks.items():
            if subject.lower() in k.lower():
                return v
        return 0

    # Example heuristic rules:
    if get("Math") > 80 and riasec_scores.get("Investigative", 0) >= 3.5:
        suggestions.append("Engineering / Computer Science / Research")

    if get("Biology") > 75 and riasec_scores.get("Realistic", 0) >= 3.5:
        suggestions.append("Medical / Healthcare / Biotechnology")

    if get("English") > 75 and riasec_scores.get("Artistic", 0) >= 3.5:
        suggestions.append("Writing / Design / Communication")

    if get("Social") > 70 and riasec_scores.get("Social", 0) >= 3.5:
        suggestions.append("Teaching / Counseling / HR")

    if not suggestions:
        suggestions.append("General Career Options: Business, Administration, or Entrepreneurship")

    return suggestions

# =====================================================
# STREAMLIT UI
# =====================================================
st.set_page_config(page_title="SkillBot AI", layout="centered")
st.title("🎓 SkillBot AI — Smart Career & Personality Profiler")

menu = ["Home", "RIASEC Test", "TCI Test", "Profile Creation", "Dashboard"]
choice = st.sidebar.selectbox("Navigation", menu)

init_db()

# ----------------------------------
# HOME
# ----------------------------------
if choice == "Home":
    st.markdown("""
    Welcome to **SkillBot AI**, your smart career guidance companion!  
    Take the tests, upload your marksheet, and get career suggestions based on your:
    - ✅ Personality (RIASEC + TCI)
    - ✅ Academic strengths (from your marksheet)
    - ✅ AI-powered recommendations
    """)

# ----------------------------------
# RIASEC TEST
# ----------------------------------
elif choice == "RIASEC Test":
    st.header("🧩 RIASEC Personality Test")
    st.info("Rate each statement from 1 (Strongly Disagree) to 5 (Strongly Agree)")
    riasec = ["Realistic", "Investigative", "Artistic", "Social", "Enterprising", "Conventional"]
    scores = {}
    for t in riasec:
        scores[t] = st.slider(f"I enjoy {t.lower()} activities", 1, 5, 3)
    if st.button("Save RIASEC Scores"):
        st.session_state["riasec_scores"] = scores
        st.success("RIASEC scores saved!")

# ----------------------------------
# TCI TEST
# ----------------------------------
elif choice == "TCI Test":
    st.header("🧠 TCI Personality Test")
    tci_traits = ["Novelty-Seeking", "Harm-Avoidance", "Reward-Dependence", "Persistence",
                  "Self-Directedness", "Cooperativeness", "Self-Transcendence"]
    scores = {}
    for t in tci_traits:
        scores[t] = st.slider(f"My {t.lower().replace('-', ' ')} level", 1, 7, 4)
    if st.button("Save TCI Scores"):
        st.session_state["tci_scores"] = scores
        st.success("TCI scores saved!")

# ----------------------------------
# PROFILE CREATION
# ----------------------------------
elif choice == "Profile Creation":
    st.header("📋 Create Student Profile")

    name = st.text_input("Name")
    age = st.number_input("Age", 10, 100, 18)
    gender = st.selectbox("Gender", ["Male", "Female", "Other"])
    education = st.text_input("Education (e.g., Intermediate, Bachelor's)")
    marksheet = st.file_uploader("Upload Marksheet Image (JPG, PNG only)", type=["jpg", "jpeg", "png"])

    if st.button("Submit Profile"):
        if not name or not age or not gender or not education or not marksheet:
            st.error("Please fill all fields and upload marksheet.")
        else:
            st.info("🔍 Extracting marks from marksheet...")
            marks = extract_marks_from_image(marksheet)
            riasec = st.session_state.get("riasec_scores", {})
            tci = st.session_state.get("tci_scores", {})
            suggestions = suggest_fields(riasec, tci, marks)

            profile_data = {
                "name": name,
                "age": age,
                "gender": gender,
                "education": education,
                "marksheet_filename": marksheet.name,
                "riasec_scores": riasec,
                "tci_scores": tci
            }
            save_profile_to_db(profile_data)

            st.success("✅ Profile saved successfully!")
            st.subheader("📄 Extracted Marks:")
            st.json(marks)
            st.subheader("🎯 Suggested Career Fields:")
            for s in suggestions:
                st.markdown(f"- {s}")

# ----------------------------------
# DASHBOARD
# ----------------------------------
elif choice == "Dashboard":
    st.header("📊 Saved Profiles Dashboard")
    conn = sqlite3.connect("skillbot_profiles.db")
    df = pd.read_sql_query("SELECT * FROM profiles", conn)
    conn.close()
    if df.empty:
        st.warning("No profiles found.")
    else:
        st.dataframe(df)
