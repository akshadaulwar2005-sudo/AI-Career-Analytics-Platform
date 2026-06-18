from flask import Flask, render_template, request, redirect, session
import sqlite3
import pandas as pd
import plotly.express as px
import os
import PyPDF2
import joblib
import os

# =========================================
# FLASK APP
# =========================================

app = Flask(__name__)

app.secret_key = "salary_secret_key"

# =========================================
# UPLOAD FOLDERS
# =========================================

UPLOAD_FOLDER = "uploads"

PROFILE_FOLDER = "static/profile"

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

app.config["PROFILE_FOLDER"] = PROFILE_FOLDER

# CREATE uploads FOLDER

if not os.path.exists("static/profile"):
    os.makedirs("static/profile")

# CREATE profile image FOLDER

if not os.path.exists(PROFILE_FOLDER):

    os.makedirs(PROFILE_FOLDER)

# =========================================
# LOAD ML MODEL
# =========================================

try:

    model = joblib.load("salary_model.pkl")

    print("✅ Salary Model Loaded")

except Exception as e:

    model = None

    print("❌ Model Load Failed:", e)

# =========================================
# DATABASE
# =========================================

def init_db():

    conn = sqlite3.connect("users.db")

    cursor = conn.cursor()

    # =====================================
    # USERS TABLE
    # =====================================

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (

        id INTEGER PRIMARY KEY AUTOINCREMENT,

        username TEXT UNIQUE,

        password TEXT,

        email TEXT,

        full_name TEXT,

        bio TEXT,

        skills TEXT,

        github TEXT,

        linkedin TEXT,

        profile_image TEXT
    )
    """)

    # =====================================
    # PREDICTIONS TABLE
    # =====================================

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS predictions (

        id INTEGER PRIMARY KEY AUTOINCREMENT,

        username TEXT,

        role TEXT,

        city TEXT,

        experience INTEGER,

        work_type TEXT,

        skill TEXT,

        degree TEXT,

        company_type TEXT,

        internship TEXT,

        salary REAL
    )
    """)

    conn.commit()

    conn.close()

# =========================================
# HOME
# =========================================

@app.route("/")
def home():

    if "user" not in session:

        return redirect("/login")

    return render_template("index.html")

# =========================================
# SIGNUP
# =========================================

@app.route("/signup", methods=["GET", "POST"])
def signup():

    if request.method == "POST":

        username = request.form["username"]

        password = request.form["password"]

        email = request.form["email"]

        conn = sqlite3.connect("users.db")

        cursor = conn.cursor()

        cursor.execute(
            "SELECT * FROM users WHERE username=?",
            (username,)
        )

        existing_user = cursor.fetchone()

        if existing_user:

            conn.close()

            return render_template(
                "signup.html",
                error="Username already exists"
            )

        cursor.execute(
            """
            INSERT INTO users
            (username, password, email)

            VALUES (?, ?, ?)
            """,
            (username, password, email)
        )

        conn.commit()

        conn.close()

        return redirect("/login")

    return render_template("signup.html")

# =========================================
# LOGIN
# =========================================

@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        username = request.form["username"]

        password = request.form["password"]

        conn = sqlite3.connect("users.db")

        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT * FROM users
            WHERE username=? AND password=?
            """,
            (username, password)
        )

        user = cursor.fetchone()

        conn.close()

        if user:

            session["user"] = username

            return redirect("/")

        else:

            return render_template(
                "login.html",
                error="Invalid Username or Password"
            )

    return render_template("login.html")

# =========================================
# LOGOUT
# =========================================

@app.route("/logout")
def logout():
    session.pop("user", None)
    return redirect("/login")

# =========================================
# PROFILE
# =========================================

@app.route("/profile", methods=["GET", "POST"])
def profile():

    if "user" not in session:

        return redirect("/login")

    conn = sqlite3.connect("users.db")

    cursor = conn.cursor()

    # UPDATE PROFILE

    if request.method == "POST":

        full_name = request.form.get("full_name")

        bio = request.form.get("bio")

        skills = request.form.get("skills")

        github = request.form.get("github")

        linkedin = request.form.get("linkedin")

        profile_image = ""

        file = request.files.get("profile_image")

        if file and file.filename != "":

            profile_image = file.filename

            filepath = os.path.join(
                app.config["PROFILE_FOLDER"],
                file.filename
            )

            file.save(filepath)

            cursor.execute(
                """
                UPDATE users
                SET
                    full_name=?,
                    bio=?,
                    skills=?,
                    github=?,
                    linkedin=?,
                    profile_image=?
                WHERE username=?
                """,
                (
                    full_name,
                    bio,
                    skills,
                    github,
                    linkedin,
                    profile_image,
                    session["user"]
                )
            )

        else:

            cursor.execute(
                """
                UPDATE users
                SET
                    full_name=?,
                    bio=?,
                    skills=?,
                    github=?,
                    linkedin=?
                WHERE username=?
                """,
                (
                    full_name,
                    bio,
                    skills,
                    github,
                    linkedin,
                    session["user"]
                )
            )

        conn.commit()

    # GET USER DATA

    cursor.execute(
        """
        SELECT
            username,
            email,
            full_name,
            bio,
            skills,
            github,
            linkedin,
            profile_image
        FROM users
        WHERE username=?
        """,
        (session["user"],)
    )

    user = cursor.fetchone()

    conn.close()

    return render_template(
        "profile.html",
        user=user
    )
# =========================================
# SALARY PREDICTION
# =========================================

# =========================================
# SALARY PREDICTION
# =========================================

@app.route("/predict", methods=["POST"])
def predict():

    if "user" not in session:
        return redirect("/login")

    try:

        # GET FORM DATA

        role = request.form.get("role")

        city = request.form.get("location")

        experience = int(
            request.form.get("experience")
        )

        skill = request.form.get("skill")

        degree = request.form.get("degree")

        company_type = request.form.get(
            "company_type"
        )

        internship = request.form.get(
            "internship"
        )

        extra_skills = request.form.get(
            "extra_skills",
            ""
        )

        # COMBINE SKILLS

        all_skills = skill

        if extra_skills.strip() != "":
            all_skills += ", " + extra_skills

        # CREATE INPUT DATAFRAME

        input_df = pd.DataFrame({

            "role": [role],

            "city": [city],

            "experience_required": [experience],

            "skills": [all_skills],

            "degree": [degree],

            "company_type": [company_type],

            "internship_experience": [internship]

        })

        # CHECK MODEL

        if model is None:

            raise RuntimeError(
                "salary_model.pkl not found"
            )

        # PREDICT SALARY

        prediction = model.predict(
            input_df
        )[0]

        prediction = round(
            float(prediction),
            2
        )

        # SALARY BREAKDOWN

        base_salary = round(
            prediction * 0.80,
            2
        )

        bonus = round(
            prediction * 0.10,
            2
        )

        performance_pay = round(
            prediction * 0.07,
            2
        )

        other_benefits = round(
            prediction * 0.03,
            2
        )

        # CATEGORY

        if prediction < 8:

            category = "🟢 Fresher Level"

        elif prediction < 18:

            category = "🔵 Mid Level"

        elif prediction < 30:

            category = "🟣 Senior Level"

        else:

            category = "🔥 High Paying Tech Role"

        # SAVE TO DATABASE

        conn = sqlite3.connect(
            "users.db"
        )

        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT INTO predictions
            (
                username,
                role,
                city,
                experience,
                work_type,
                skill,
                degree,
                company_type,
                internship,
                salary
            )

            VALUES
            (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                session["user"],
                role,
                city,
                experience,
                "Full-time",
                all_skills,
                degree,
                company_type,
                internship,
                prediction
            )
        )

        conn.commit()

        conn.close()

        return render_template(

            "index.html",

            prediction_text=
            f"💰 Estimated Salary: ₹ {prediction} LPA",

            category=category,

            base_salary=base_salary,

            bonus=bonus,

            performance_pay=performance_pay,

            other_benefits=other_benefits
        )

    except Exception as e:

        print(
            "Prediction Error:",
            e
        )

        return render_template(

            "index.html",

            prediction_text=
            f"❌ Prediction Failed: {e}"
        )

# =========================================
# DASHBOARD
# =========================================

@app.route("/dashboard")
def dashboard():

    if "user" not in session:

        return redirect("/login")

    try:

        conn = sqlite3.connect("users.db")

        query = """
        SELECT role, salary
        FROM predictions
        WHERE username=?
        """

        df = pd.read_sql_query(
            query,
            conn,
            params=(session["user"],)
        )

        conn.close()

        if len(df) == 0:

            graph_html = """
            <h3 style='color:white;text-align:center;'>
            No Prediction Data Available
            </h3>
            """

        else:

            fig = px.bar(

                df,

                x="role",

                y="salary",

                color="role",

                text="salary",

                title="📊 Salary Prediction Analytics"

            )

            fig.update_layout(

                paper_bgcolor="rgba(0,0,0,0)",

                plot_bgcolor="rgba(0,0,0,0)",

                font_color="white"

            )

            graph_html = fig.to_html(
                full_html=False
            )

        return render_template(

            "dashboard.html",

            graph_html=graph_html
        )

    except Exception as e:

        return f"Dashboard Error: {e}"

# =========================================
# HISTORY
# =========================================

@app.route("/history")
def history():

    if "user" not in session:

        return redirect("/login")

    try:

        conn = sqlite3.connect("users.db")

        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT

                role,
                city,
                experience,
                skill,
                salary

            FROM predictions

            WHERE username=?

            ORDER BY id DESC
            """,
            (session["user"],)
        )

        history = cursor.fetchall()

        conn.close()

        return render_template(

            "history.html",

            history=history
        )

    except Exception as e:

        return f"History Error: {e}"

# RESUME ANALYZER - FIXED VERSION
# Replace only this route in your app.py
# =========================================

@app.route("/resume", methods=["GET", "POST"])
def resume():

    if "user" not in session:
        return redirect("/login")

    score = None
    skills_found = []
    suggestions = ""

    # Skills with normalized weights (out of 100 total possible)
    skills = {
        "Python": 8,
        "Java": 7,
        "C++": 6,
        "SQL": 7,
        "Machine Learning": 9,
        "Deep Learning": 9,
        "Artificial Intelligence": 9,
        "AI": 5,
        "TensorFlow": 8,
        "PyTorch": 8,
        "Flask": 6,
        "Django": 7,
        "React": 7,
        "Angular": 6,
        "JavaScript": 7,
        "HTML": 4,
        "CSS": 4,
        "Bootstrap": 5,
        "Node.js": 7,
        "MongoDB": 6,
        "Data Science": 8,
        "Power BI": 7,
        "Tableau": 7,
        "Excel": 5,
        "AWS": 8,
        "Azure": 8,
        "Cloud Computing": 7,
        "Cyber Security": 8,
        "Ethical Hacking": 8,
        "UI/UX": 6,
        "Figma": 5,
        "Android": 6,
        "Kotlin": 6,
        "Swift": 6,
        "Blockchain": 8,
        "DevOps": 8,
        "Docker": 7,
        "Kubernetes": 7,
        "Git": 5,
        "Linux": 6,
        "REST API": 6,
        "NLP": 8,
        "Computer Vision": 8,
        "Pandas": 6,
        "NumPy": 6,
        "Scikit-learn": 7,
        "FastAPI": 6,
        "TypeScript": 7,
        "Next.js": 7,
        "Vue": 6,
        "GraphQL": 6,
    }

    # Section bonus scores
    section_bonuses = {
        "project":       10,
        "internship":    10,
        "github":         5,
        "linkedin":       5,
        "certification":  8,
        "achievement":    5,
        "publication":    7,
        "education":      5,
        "objective":      3,
        "summary":        3,
    }

    if request.method == "POST":

        try:
            file = request.files["resume"]

            if file.filename == "":
                return render_template(
                    "resume.html",
                    suggestions="Please upload a Resume PDF file."
                )

            filepath = os.path.join(
                app.config["UPLOAD_FOLDER"],
                file.filename
            )
            file.save(filepath)

            # --- Extract text from PDF ---
            text = ""
            try:
                pdf = PyPDF2.PdfReader(filepath)
                for page in pdf.pages:
                    extracted = page.extract_text()
                    if extracted:
                        text += extracted + " "
            except Exception as pdf_err:
                return render_template(
                    "resume.html",
                    suggestions=f"PDF Read Error: {pdf_err}"
                )

            if not text.strip():
                return render_template(
                    "resume.html",
                    suggestions="Could not extract text from PDF. Make sure it is not a scanned image PDF."
                )

            text_lower = text.lower()

            # --- Skill Scoring (max 60 points from skills) ---
            raw_skill_score = 0
            for skill, weight in skills.items():
                if skill.lower() in text_lower:
                    skills_found.append(skill)
                    raw_skill_score += weight

            # Normalize skill score to max 60
            max_possible_skill = sum(skills.values())  # total if all skills present
            skill_score = round((raw_skill_score / max_possible_skill) * 60)

            # --- Section Scoring (max 40 points from sections) ---
            section_score = 0
            sections_found = []
            sections_missing = []

            for section, bonus in section_bonuses.items():
                if section in text_lower:
                    section_score += bonus
                    sections_found.append(section.capitalize())
                else:
                    sections_missing.append(section.capitalize())

            # Normalize section score to max 40
            max_possible_section = sum(section_bonuses.values())
            section_score = round((section_score / max_possible_section) * 40)

            # --- Final Score (out of 100) ---
            score = min(skill_score + section_score, 100)

            # --- Missing Skills (top skills not found) ---
            missing_skills = [
                skill for skill in skills
                if skill not in skills_found
            ]

            # --- Build Suggestions ---
            improvement_tips = []

            if "project" not in text_lower:
                improvement_tips.append("➕ Add a Projects section with descriptions")
            if "internship" not in text_lower:
                improvement_tips.append("➕ Add Internship / Work Experience")
            if "github" not in text_lower:
                improvement_tips.append("➕ Add your GitHub Profile link")
            if "linkedin" not in text_lower:
                improvement_tips.append("➕ Add your LinkedIn Profile link")
            if "certification" not in text_lower:
                improvement_tips.append("➕ Add Certifications / Courses")
            if "achievement" not in text_lower:
                improvement_tips.append("➕ Add Achievements / Awards")

            suggestions = (
                "🔍 <b>Missing Skills (Top 10):</b> "
                + ", ".join(missing_skills[:10])
                + "<br><br>📋 <b>Resume Improvements:</b><br>"
                + "<br>".join(improvement_tips if improvement_tips else ["✅ Great structure!"])
                + f"<br><br>📊 <b>Score Breakdown:</b> Skills = {skill_score}/60 | Sections = {section_score}/40"
            )

        except Exception as e:
            suggestions = f"Resume Error: {e}"

    return render_template(
        "resume.html",
        score=score,
        skills=", ".join(skills_found),
        suggestions=suggestions
    )
# =========================================
# AI LEARNING RECOMMENDATION
# =========================================

@app.route("/learning", methods=["GET", "POST"])
def learning():

    if "user" not in session:

        return redirect("/login")

    recommendations = []

    missing_skills = []

    target_role = ""

    if request.method == "POST":

        user_skills = request.form.get(
            "skills",
            ""
        ).lower()

        target_role = request.form.get(
            "role"
        )

        role_skills = {

            "Data Scientist": [
                "python",
                "machine learning",
                "sql",
                "deep learning",
                "statistics",
                "power bi"
            ],

            "AI Engineer": [
                "python",
                "machine learning",
                "deep learning",
                "tensorflow",
                "pytorch",
                "ai"
            ],

            "Frontend Developer": [
                "html",
                "css",
                "javascript",
                "react",
                "bootstrap"
            ],

            "Backend Developer": [
                "python",
                "django",
                "flask",
                "sql",
                "mongodb"
            ],

            "Cloud Engineer": [
                "aws",
                "azure",
                "docker",
                "kubernetes",
                "linux"
            ],

            "Cyber Security Analyst": [
                "cyber security",
                "ethical hacking",
                "linux",
                "networking"
            ]
        }

        required_skills = role_skills.get(
            target_role,
            []
        )

        for skill in required_skills:

            if skill not in user_skills:

                missing_skills.append(skill)

        youtube_links = {

            "python": {
                "channel": "CodeWithHarry",
                "link": "https://www.youtube.com/results?search_query=codewithharry+python"
            },

            "machine learning": {
                "channel": "Krish Naik",
                "link": "https://www.youtube.com/results?search_query=krish+naik+machine+learning"
            },

            "deep learning": {
                "channel": "Krish Naik",
                "link": "https://www.youtube.com/results?search_query=krish+naik+deep+learning"
            },

            "react": {
                "channel": "Hitesh Choudhary",
                "link": "https://www.youtube.com/results?search_query=hitesh+choudhary+react"
            },

            "aws": {
                "channel": "TechWorld with Nana",
                "link": "https://www.youtube.com/results?search_query=aws+techworld+with+nana"
            }

        }

        for skill in missing_skills:

            data = youtube_links.get(

                skill,

                {
                    "channel": "YouTube",
                    "link": f"https://www.youtube.com/results?search_query={skill}"
                }

            )

            recommendations.append({

                "skill": skill,

                "resource":
                f"Learn from {data['channel']}",

                "link": data["link"],

                "difficulty": "Medium"

            })

    return render_template(

        "learning.html",

        recommendations=recommendations,

        missing_skills=missing_skills,

        target_role=target_role
    )
# =========================================
# ADD ROADMAP ROUTE HERE
# =========================================

@app.route("/roadmap", methods=["GET", "POST"])
def roadmap():

    if "user" not in session:
        return redirect("/login")

    roadmap = []
    target_role = ""

    if request.method == "POST":

        target_role = request.form.get("role")

        role_roadmaps = {

            "AI Engineer": [
                "Learn Python",
                "Master DSA",
                "NumPy & Pandas",
                "Machine Learning",
                "Deep Learning",
                "TensorFlow / PyTorch",
                "Build AI Projects",
                "Learn MLOps",
                "Deploy Models",
                "Apply for Jobs"
            ],

            "Data Scientist": [
                "Learn Python",
                "Statistics",
                "SQL",
                "Data Analysis",
                "Machine Learning",
                "Power BI / Tableau",
                "Projects",
                "Kaggle",
                "Portfolio",
                "Apply for Jobs"
            ],

            "Frontend Developer": [
                "HTML",
                "CSS",
                "JavaScript",
                "React",
                "Responsive Design",
                "APIs",
                "Portfolio",
                "Deploy Projects",
                "Next.js",
                "Apply for Jobs"
            ],

            "Backend Developer": [
                "Python",
                "Flask",
                "Django",
                "SQL",
                "MongoDB",
                "REST API",
                "Authentication",
                "Deployment",
                "Projects",
                "Apply for Jobs"
            ],

            "Cloud Engineer": [
                "Linux",
                "Networking",
                "AWS",
                "Docker",
                "Kubernetes",
                "CI/CD",
                "Cloud Security",
                "Projects",
                "AWS Certification",
                "Apply for Jobs"
            ]
        }

        roadmap = role_roadmaps.get(target_role, [])

    return render_template(
        "roadmap.html",
        roadmap=roadmap,
        target_role=target_role
    )

# =========================================
# MAIN
# =========================================

if __name__ == "__main__":

    init_db()

    app.run(debug=True)