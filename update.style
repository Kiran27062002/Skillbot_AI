import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import auth
import os

# -------------------- PAGE SETUP --------------------
st.set_page_config(page_title="SkillBot Interest Profiler", layout="centered")

# -------------------- CUSTOM CSS --------------------
st.markdown("""
    <style>
    body {
        font-family: 'Poppins', sans-serif;
        background: linear-gradient(to right, #e0f7fa, #f1f8e9);
    }
    .stApp {
        max-width: 700px;
        margin: auto;
        background-color: #ffffff;
        padding: 30px 40px;
        border-radius: 15px;
        box-shadow: 0px 4px 10px rgba(0,0,0,0.1);
    }
    h1, h2, h3 {
        color: #005b96;
        text-align: center;
    }
    .stButton > button {
        background-color: #0288d1;
        color: white;
        border: none;
        padding: 12px 25px;
        border-radius: 8px;
        font-size: 16px;
        font-weight: 500;
        transition: all 0.3s ease;
        width: 100%;
        margin-top: 10px;
    }
    .stButton > button:hover {
        background-color: #0277bd;
        transform: scale(1.03);
    }
    .question-box {
        background-color: #f0f4f8;
        padding: 25px;
        border-radius: 12px;
        text-align: center;
        margin-top: 20px;
        box-shadow: 0px 3px 8px rgba(0,0,0,0.05);
    }
    .emoji-btn {
        display: inline-block;
        background-color: #e3f2fd;
        color: #1565c0;
        font-size: 18px;
        font-weight: 600;
        border-radius: 10px;
        padding: 12px 18px;
        margin: 8px;
        transition: 0.3s ease;
        cursor: pointer;
        text-align: center;
        width: 140px;
    }
    .emoji-btn:hover {
        background-color: #bbdefb;
        transform: translateY(-3px);
    }
    @media screen and (max-width: 600px) {
        .emoji-btn {
            width: 100%;
            margin: 5px 0;
        }
    }
    </style>
""", unsafe_allow_html=True)

# -------------------- RESPONSES FILE SETUP --------------------
RESPONSES_FILE = "responses/responses.xlsx"
os.makedirs("responses", exist_ok=True)

# -------------------- SESSION --------------------
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "page" not in st.session_state:
    st.session_state.page = "home"
if "index" not in st.session_state:
    st.session_state.index = 0
if "answers" not in st.session_state:
    st.session_state.answers = []

# -------------------- NAVBAR --------------------
col1, col2 = st.columns([0.8,0.2])
with col1:
    st.title("🔹 SkillBot Interest Profiler")
with col2:
    if not st.session_state.logged_in:
        if st.button("Register"):
            st.session_state.show_register = True
            st.session_state.show_login = False
        if st.button("Sign In"):
            st.session_state.show_login = True
            st.session_state.show_register = False
    else:
        if st.button("Logout"):
            st.session_state.logged_in = False
            st.session_state.answers = []
            st.session_state.index = 0
            st.session_state.page = "home"
            st.stop()

# -------------------- REGISTER / LOGIN --------------------
if st.session_state.get("show_register", False):
    st.subheader("Register Now")
    email = st.text_input("Email")
    password = st.text_input("Password", type="password")
    confirm = st.text_input("Confirm Password", type="password")
    if st.button("Register Account"):
        if password != confirm:
            st.error("Passwords do not match")
        elif auth.signup(email, password):
            st.success("Registration successful! Please Sign In now")
            st.session_state.show_register = False
            st.session_state.show_login = True
            st.stop()
        else:
            st.error("Email already exists!")

elif st.session_state.get("show_login", False):
    st.subheader("Sign In")

    if "login_email" not in st.session_state:
        st.session_state.login_email = ""
    if "login_password" not in st.session_state:
        st.session_state.login_password = ""

    st.session_state.login_email = st.text_input("Email", value=st.session_state.login_email)
    st.session_state.login_password = st.text_input("Password", type="password", value=st.session_state.login_password)

    if st.button("Login"):
        if auth.login(st.session_state.login_email, st.session_state.login_password):
            st.session_state.logged_in = True
            st.session_state.show_login = False
            st.session_state.page = "intro"
            st.session_state.username = st.session_state.login_email
            st.stop()
        else:
            st.error("Invalid credentials")

# -------------------- LOAD DATA --------------------
questions = pd.read_csv("questions.csv")
careers = pd.read_csv("careers.csv")

# -------------------- FUNCTIONS --------------------
def restart():
    st.session_state.page = "intro"
    st.session_state.index = 0
    st.session_state.answers = []

def next_question(selected):
    st.session_state.answers.append(selected)
    st.session_state.index += 1
    if st.session_state.index >= len(questions):
        st.session_state.page = "results"
    st.experimental_rerun()

def save_responses():
    df = questions.copy()
    df["answer"] = st.session_state.answers
    df["username"] = st.session_state.get("username")
    df["email"] = st.session_state.get("email")

    if os.path.exists(RESPONSES_FILE):
        existing = pd.read_excel(RESPONSES_FILE)
        df_to_save = pd.concat([existing, df], ignore_index=True)
    else:
        df_to_save = df

    df_to_save.to_excel(RESPONSES_FILE, index=False)
    st.success("Your responses have been saved successfully!")

# -------------------- INTRO PAGE --------------------
if st.session_state.page == "intro":
    st.title("Welcome to SkillBot Interest Profiler 🌟")
    st.write("""
    Discover your work interests and explore matching careers.
    Answer **30 fun questions** — it takes just 5 minutes!
    """)
    if st.button("🚀 Start the Profiler"):
        st.session_state.page = "quiz"
        st.experimental_rerun()

# -------------------- QUIZ PAGE --------------------
elif st.session_state.page == "quiz":
    q_idx = st.session_state.index
    q = questions.iloc[q_idx]

    st.markdown(f"<div class='question-box'><h3>Question {q_idx + 1} of {len(questions)}</h3><p>{q['question']}</p></div>", unsafe_allow_html=True)

    options = {
        "Strongly Dislike": "😠",
        "Dislike": "🙁",
        "Unsure": "😐",
        "Like": "🙂",
        "Strongly Like": "🤩"
    }

    # Display as styled emoji buttons
    for label, icon in options.items():
        if st.button(f"{icon} {label}", key=f"{q_idx}-{label}"):
            next_question(label)

# -------------------- RESULTS PAGE --------------------
elif st.session_state.page == "results":
    st.title("🎯 Your Interest Profile")
    df = questions.copy()
    df["answer"] = st.session_state.answers
    rating_map = {"Strongly Dislike": 1, "Dislike": 2, "Unsure": 3, "Like": 4, "Strongly Like": 5}
    df["score"] = df["answer"].map(rating_map)
    riasec_scores = df.groupby("category")["score"].mean().sort_values(ascending=False)
    top = riasec_scores.head(3).index.tolist()
    save_responses()

    st.write("### Your RIASEC Scores")
    fig, ax = plt.subplots()
    ax.bar(riasec_scores.index, riasec_scores.values, color="#4fc3f7")
    ax.set_ylabel("Average Score")
    ax.set_title("RIASEC Interest Profile")
    st.pyplot(fig)

    st.markdown(f"**Your top interests:** 🎨 {', '.join(top)}")
    if st.button("💼 Explore Careers"):
        st.session_state.page = "careers"
        st.session_state.top_interests = top
        st.experimental_rerun()
    if st.button("🔁 Restart"):
        restart()
        st.experimental_rerun()

# -------------------- CAREER PAGE --------------------
elif st.session_state.page == "careers":
    st.title("💼 Career Suggestions")
    top_interests = st.session_state.get("top_interests", [])
    if not top_interests:
        st.warning("Please complete the test first.")
    else:
        for cat in top_interests:
            row = careers[careers["category"] == cat]
            if not row.empty:
                st.markdown(f"### {cat} — {row.iloc[0]['careers']}")
    if st.button("🏠 Back to Start"):
        restart()
        st.experimental_rerun()
