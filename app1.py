import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import auth
import os


# -------------------- PAGE SETUP --------------------
st.set_page_config(page_title="SkillBot Interest Profiler", layout="centered")
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
            # Switch to login form automatically
            st.session_state.show_register = False
            st.session_state.show_login = True
            st.stop()  # re-render to show login form
        else:
            st.error("Email already exists!")



elif st.session_state.get("show_login", False):
    st.subheader("Sign In")

    # Keep input values after rerun
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
            st.session_state.page = "intro"      # go to Intro page after login
            st.session_state.username = st.session_state.login_email
            st.stop()             # reload the page immediately
        else:
            st.error("Invalid credentials")


# -------------------- LOAD DATA --------------------
questions = pd.read_csv("questions.csv")
careers = pd.read_csv("careers.csv")

# -------------------- SESSION STATE --------------------
if "page" not in st.session_state:
    st.session_state.page = "intro"
if "index" not in st.session_state:
    st.session_state.index = 0
if "answers" not in st.session_state:
    st.session_state.answers = []

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
def save_responses():
    df = questions.copy()
    df["answer"] = st.session_state.answers
    df["username"] = st.session_state.get("username")
    df["email"] = st.session_state.get("email")

    # Save to Excel
    if os.path.exists(RESPONSES_FILE):
        existing = pd.read_excel(RESPONSES_FILE)
        df_to_save = pd.concat([existing, df], ignore_index=True)
    else:
        df_to_save = df

    df_to_save.to_excel(RESPONSES_FILE, index=False)
    st.success("Your responses have been saved successfully!")


# -------------------- INTRO PAGE --------------------
if st.session_state.page == "intro":
    st.title("Welcome to the SkillBot Interest Profiler!")
    st.write("""
    Discover your work-related interests and explore career options that are a good fit for you.

    The process is super easy, but take your time — the results can help guide your future!
    """)
    st.markdown("""
    **Here’s how it works:**
    1. Think about how much you’d like to do various activities if they were part of your job.  
    2. See what your answers reveal about your work interests.  
    3. Explore careers matching your interest profile.  
    4. Have fun learning and exploring!
    """)
    st.divider()
    st.subheader("What would you enjoy doing at your dream job?")
    st.write("""
    You’ll read 30 short work activity descriptions.  
    Picture yourself doing each one and select how much you’d like it.

    There are **no right or wrong answers**, and **no need to think about pay or education**—just interest!
    """)
    if st.button(" Start the Profiler"):
        st.session_state.page = "quiz"

# -------------------- QUIZ PAGE --------------------
elif st.session_state.page == "quiz":
    q_idx = st.session_state.index
    q = questions.iloc[q_idx]

    st.markdown(f"### Question {q_idx + 1} of {len(questions)}")
    st.markdown(f"**{q['question']}**")

    st.write("How much would you enjoy this activity?")
    options = {
        "Strongly Dislike": "😠",
        "Dislike": "🙁",
        "Unsure": "😐",
        "Like": "🙂",
        "Strongly Like": "🤩"
    }

    cols = st.columns(len(options))
    for i, (label, icon) in enumerate(options.items()):
        if cols[i].button(f"{icon} {label}"):
            next_question(label)

# -------------------- RESULTS PAGE --------------------
elif st.session_state.page == "results":
    st.title("Your Interest Profile")

    # Calculate RIASEC scores
    df = questions.copy()
    df["answer"] = st.session_state.answers
    rating_map = {
        "Strongly Dislike": 1,
        "Dislike": 2,
        "Unsure": 3,
        "Like": 4,
        "Strongly Like": 5,
    }
    df["score"] = df["answer"].map(rating_map)

    riasec_scores = df.groupby("category")["score"].mean().sort_values(ascending=False)
    top = riasec_scores.head(3).index.tolist()
    save_responses()

    st.subheader(" What is RIASEC?")
    st.write("RIASEC stands for **Realistic, Investigative, Artistic, Social, Enterprising, Conventional** — six types of work interests defined by psychologist John Holland.")

    st.write("### Your Profile Scores:")
    # Create a bar chart
    fig, ax = plt.subplots()
    ax.bar(riasec_scores.index, riasec_scores.values)
    ax.set_xlabel("RIASEC Categories")
    ax.set_ylabel("Average Score")
    ax.set_title("Your RIASEC Interest Profile")
    st.pyplot(fig)
    st.markdown(f"**Your top interests are:** {', '.join(top)}")

    st.divider()
    st.write("Next, plan your career training and preparation—or skip ahead to see all your options!")

    if st.button("Explore Careers"):
        st.session_state.page = "careers"
        st.session_state.top_interests = top
    if st.button("🔁 Restart"):
        restart()

# -------------------- CAREER PAGE --------------------
elif st.session_state.page == "careers":
    st.title("💼 Career Suggestions")

    top_interests = st.session_state.get("top_interests", [])
    if not top_interests:
        st.warning("Please complete the test first.")
    else:
        st.write("Based on your top RIASEC interests, here are some careers you might explore:")
        for cat in top_interests:
            row = careers[careers["category"] == cat]
            if not row.empty:
                st.markdown(f"### {cat} — {row.iloc[0]['careers']}")
        st.divider()
        st.info("These careers are just starting points — explore more based on your interests and skills!")

    if st.button("🏠 Back to Start"):
        restart()

