from flask import (
    Flask,
    render_template,
    request,
    redirect,
    session,
    flash,
    send_from_directory
)

import sqlite3
import os

from datetime import datetime

from werkzeug.security import (
    generate_password_hash,
    check_password_hash
)

from werkzeug.utils import secure_filename


# =========================================================
# APP
# =========================================================

app = Flask(__name__)
app.secret_key = "campus-mate-secret-key"


# =========================================================
# FILE UPLOAD SETTINGS
# =========================================================

UPLOAD_FOLDER = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "uploads"
)

ALLOWED_EXTENSIONS = {
    "pdf",
    "ppt",
    "pptx"
}

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

os.makedirs(UPLOAD_FOLDER, exist_ok=True)


def allowed_file(filename):
    return (
        "." in filename
        and filename.rsplit(".", 1)[1].lower()
        in ALLOWED_EXTENSIONS
    )


# =========================================================
# COURSE DATA
# =========================================================

COURSES = {
    "python": "Python",
    "foundation-of-engineering": "Foundation of Engineering",
    "calculus": "Calculus",
    "computational-chemistry": "Computational Chemistry",
    "tpse": "TPSE"
}


# =========================================================
# RESOURCE CATEGORIES
# =========================================================

CATEGORIES = {
    "classes": "Classes",
    "assignments": "Assignments",
    "practice-sheets": "Practice Sheets"
}


# =========================================================
# BATCHES
# =========================================================

BATCHES = {
    "batch-1-4": "Batch 1 – 4",
    "batch-5-8": "Batch 5 – 8",
    "batch-9-12": "Batch 9 – 12",
    "batch-13-16": "Batch 13 – 16"
}


# =========================================================
# DATABASE
# =========================================================

def get_db():

    db_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "database.db"
    )

    conn = sqlite3.connect(db_path)

    return conn


# =========================================================
# DATABASE COLUMN HELPER
# =========================================================

def add_column_if_missing(
    conn,
    table_name,
    column_name,
    column_definition
):

    cursor = conn.execute(
        f"PRAGMA table_info({table_name})"
    )

    columns = [
        column[1]
        for column in cursor.fetchall()
    ]

    if column_name not in columns:

        conn.execute(
            f"""
            ALTER TABLE {table_name}
            ADD COLUMN {column_name}
            {column_definition}
            """
        )


# =========================================================
# DATABASE INITIALIZATION
# =========================================================

def init_db():

    conn = get_db()

    # =====================================================
    # STUDENTS
    # =====================================================

    conn.execute("""
        CREATE TABLE IF NOT EXISTS students (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            branch TEXT,
            year TEXT,
            role TEXT DEFAULT 'student',
            batch TEXT,
            created_at TEXT,
            updated_at TEXT
        )
    """)

    add_column_if_missing(
        conn,
        "students",
        "role",
        "TEXT DEFAULT 'student'"
    )

    add_column_if_missing(
        conn,
        "students",
        "batch",
        "TEXT DEFAULT 'batch-1-4'"
    )

    add_column_if_missing(
        conn,
        "students",
        "created_at",
        "TEXT"
    )

    add_column_if_missing(
        conn,
        "students",
        "updated_at",
        "TEXT"
    )

    current_time = datetime.now().strftime(
        "%Y-%m-%d %H:%M:%S"
    )

    conn.execute("""
        UPDATE students
        SET created_at = ?
        WHERE created_at IS NULL
        OR created_at = ''
    """, (current_time,))

    conn.execute("""
        UPDATE students
        SET updated_at = ?
        WHERE updated_at IS NULL
        OR updated_at = ''
    """, (current_time,))

    conn.execute("""
        UPDATE students
        SET batch = 'batch-1-4'
        WHERE role = 'student'
        AND (
            batch IS NULL
            OR batch = ''
        )
    """)

    # =====================================================
    # TEAMMATES
    # =====================================================

    conn.execute("""
        CREATE TABLE IF NOT EXISTS teammates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            branch TEXT NOT NULL,
            year TEXT NOT NULL,
            skill TEXT NOT NULL,
            description TEXT
        )
    """)

    # =====================================================
    # ANNOUNCEMENTS
    # =====================================================

    conn.execute("""
        CREATE TABLE IF NOT EXISTS announcements (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            description TEXT NOT NULL,
            date TEXT NOT NULL
        )
    """)

    # =====================================================
    # EVENTS
    # =====================================================

    conn.execute("""
        CREATE TABLE IF NOT EXISTS events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            description TEXT NOT NULL,
            date TEXT NOT NULL
        )
    """)

    # =====================================================
    # CONNECTIONS
    # =====================================================

    conn.execute("""
        CREATE TABLE IF NOT EXISTS connections (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sender_id INTEGER NOT NULL,
            receiver_id INTEGER NOT NULL,
            status TEXT NOT NULL DEFAULT 'pending',
            created_at TEXT NOT NULL
        )
    """)

    # =====================================================
    # STUDY RESOURCES
    # =====================================================

    conn.execute("""
        CREATE TABLE IF NOT EXISTS study_resources (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            filename TEXT NOT NULL,
            course TEXT DEFAULT 'General',
            category TEXT DEFAULT 'Classes',
            batch TEXT DEFAULT 'General',
            file_type TEXT NOT NULL,
            uploaded_by INTEGER NOT NULL,
            uploaded_at TEXT NOT NULL
        )
    """)

    add_column_if_missing(
        conn,
        "study_resources",
        "course",
        "TEXT DEFAULT 'General'"
    )

    add_column_if_missing(
        conn,
        "study_resources",
        "category",
        "TEXT DEFAULT 'Classes'"
    )

    add_column_if_missing(
        conn,
        "study_resources",
        "batch",
        "TEXT DEFAULT 'General'"
    )

    # =====================================================
    # MAILS
    # =====================================================

    conn.execute("""
        CREATE TABLE IF NOT EXISTS mails (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sender_id INTEGER NOT NULL,
            receiver_id INTEGER NOT NULL,
            subject TEXT NOT NULL,
            message TEXT NOT NULL,
            created_at TEXT NOT NULL,
            is_read INTEGER DEFAULT 0
        )
    """)

    # =====================================================
    # BATCH CHAT
    # =====================================================

    conn.execute("""
        CREATE TABLE IF NOT EXISTS batch_chat_messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            batch TEXT NOT NULL,
            sender_id INTEGER NOT NULL,
            message TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
    """)

    # =====================================================
    # SAMPLE ANNOUNCEMENTS
    # =====================================================

    cursor = conn.execute(
        "SELECT COUNT(*) FROM announcements"
    )

    if cursor.fetchone()[0] == 0:

        conn.execute("""
            INSERT INTO announcements
            (title, description, date)
            VALUES
            (?, ?, ?),
            (?, ?, ?),
            (?, ?, ?)
        """, (

            "Hackathon Registration",
            "Registration is open for the upcoming college hackathon.",
            "October 3, 2026",

            "Internal Exams",
            "Internal examinations will begin soon. Check your department schedule.",
            "October 10, 2026",

            "Tech Club Event",
            "Join the upcoming Tech Club event and learn from fellow students.",
            "October 15, 2026"

        ))

    # =====================================================
    # SAMPLE EVENTS
    # =====================================================

    cursor = conn.execute(
        "SELECT COUNT(*) FROM events"
    )

    if cursor.fetchone()[0] == 0:

        conn.execute("""
            INSERT INTO events
            (title, description, date)
            VALUES
            (?, ?, ?),
            (?, ?, ?),
            (?, ?, ?)
        """, (

            "Coding Hackathon",
            "Build an innovative project with your team.",
            "October 7-8, 2026",

            "Tech Talk",
            "Learn about the latest technologies from industry speakers.",
            "October 15, 2026",

            "Sports Day",
            "Participate in exciting college sports activities.",
            "October 20, 2026"

        ))

    # =====================================================
    # DEFAULT LECTURER
    # =====================================================

    cursor = conn.execute(
        "SELECT id FROM students WHERE email = ?",
        ("lecturer@campusmate.com",)
    )

    if not cursor.fetchone():

        password = generate_password_hash(
            "lecturer123"
        )

        now = datetime.now().strftime(
            "%Y-%m-%d %H:%M:%S"
        )

        conn.execute("""
            INSERT INTO students
            (
                name,
                email,
                password,
                branch,
                year,
                role,
                batch,
                created_at,
                updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            "Campus Lecturer",
            "lecturer@campusmate.com",
            password,
            "Faculty",
            "Faculty",
            "lecturer",
            None,
            now,
            now
        ))

    # =====================================================
    # DEFAULT MANAGEMENT
    # =====================================================

    cursor = conn.execute(
        "SELECT id FROM students WHERE email = ?",
        ("management@campusmate.com",)
    )

    if not cursor.fetchone():

        password = generate_password_hash(
            "management123"
        )

        now = datetime.now().strftime(
            "%Y-%m-%d %H:%M:%S"
        )

        conn.execute("""
            INSERT INTO students
            (
                name,
                email,
                password,
                branch,
                year,
                role,
                batch,
                created_at,
                updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            "Campus Management",
            "management@campusmate.com",
            password,
            "Administration",
            "Management",
            "management",
            None,
            now,
            now
        ))

    conn.commit()
    conn.close()


# =========================================================
# HOME
# =========================================================

@app.route("/")
def home():

    return render_template("home.html")


# =========================================================
# STUDENT LOGIN
# =========================================================

@app.route("/login", methods=["GET", "POST"])
def login():

    print("========== STUDENT LOGIN ROUTE HIT ==========")
    print("METHOD:", request.method)

    if request.method == "POST":

        print("POST DATA:", request.form)

        email = request.form.get(
            "email",
            ""
        ).strip().lower()

        password = request.form.get(
            "password",
            ""
        )

        print("EMAIL:", email)
        print("PASSWORD RECEIVED:", bool(password))

        if not email or not password:

            print("ERROR: EMAIL OR PASSWORD MISSING")

            return render_template(
                "login.html",
                error="Please enter your email and password."
            )

        conn = get_db()

        cursor = conn.cursor()

        cursor.execute("""
            SELECT
                id,
                name,
                email,
                password,
                branch,
                year,
                role,
                batch
            FROM students
            WHERE LOWER(email) = ?
        """, (email,))

        user = cursor.fetchone()

        print("DATABASE USER:", user)

        conn.close()

        if not user:

            print("ERROR: STUDENT ACCOUNT NOT FOUND")

            return render_template(
                "login.html",
                error="Invalid student email or password."
            )

        print("ACCOUNT ROLE:", user[6])

        if user[6] != "student":

            print("ERROR: THIS ACCOUNT IS NOT A STUDENT ACCOUNT")

            return render_template(
                "login.html",
                error="This account is not a student account."
            )

        if not check_password_hash(
            user[3],
            password
        ):

            print("ERROR: WRONG PASSWORD")

            return render_template(
                "login.html",
                error="Invalid student email or password."
            )

        print("LOGIN SUCCESSFUL!")

        session.clear()

        session["student_id"] = user[0]
        session["name"] = user[1]
        session["email"] = user[2]
        session["role"] = "student"
        session["batch"] = user[7]

        print("SESSION CREATED")
        print("STUDENT ID:", session["student_id"])
        print("STUDENT ROLE:", session["role"])
        print("STUDENT BATCH:", session["batch"])
        print("REDIRECTING TO /dashboard")

        return redirect("/dashboard")

    return render_template(
        "login.html",
        error=None
    )


# =========================================================
# LECTURER LOGIN
# =========================================================

@app.route("/lecturer/login", methods=["GET", "POST"])
def lecturer_login():

    if request.method == "POST":

        email = request.form.get(
            "email",
            ""
        ).strip().lower()

        password = request.form.get(
            "password",
            ""
        )

        if not email or not password:

            return render_template(
                "lecturer_login.html",
                error="Please enter your email and password."
            )

        conn = get_db()

        cursor = conn.cursor()

        cursor.execute("""
            SELECT
                id,
                name,
                email,
                password,
                branch,
                year,
                role,
                batch
            FROM students
            WHERE LOWER(email) = ?
        """, (email,))

        user = cursor.fetchone()

        conn.close()

        if not user:

            return render_template(
                "lecturer_login.html",
                error="Invalid lecturer email or password."
            )

        if user[6] != "lecturer":

            return render_template(
                "lecturer_login.html",
                error="This account is not a lecturer account."
            )

        if not check_password_hash(
            user[3],
            password
        ):

            return render_template(
                "lecturer_login.html",
                error="Invalid lecturer email or password."
            )

        session.clear()

        session["student_id"] = user[0]
        session["name"] = user[1]
        session["email"] = user[2]
        session["role"] = "lecturer"

        return redirect(
            "/lecturer/select-course"
        )

    return render_template(
        "lecturer_login.html",
        error=None
    )


# =========================================================
# REGISTER
# =========================================================

@app.route("/register", methods=["GET", "POST"])
def register():

    return """
        <h2>Account creation is managed by Campus Management.</h2>
        <p>Students and lecturers cannot create accounts themselves.</p>
        <a href="/login">Go to Student Login</a>
    """


# =========================================================
# MANAGEMENT LOGIN
# =========================================================

@app.route("/management/login", methods=["GET", "POST"])
def management_login():

    if request.method == "POST":

        email = request.form.get(
            "email",
            ""
        ).strip().lower()

        password = request.form.get(
            "password",
            ""
        )

        conn = get_db()

        cursor = conn.cursor()

        cursor.execute("""
            SELECT *
            FROM students
            WHERE LOWER(email) = ?
            AND role = 'management'
        """, (email,))

        management = cursor.fetchone()

        conn.close()

        if management and check_password_hash(
            management[3],
            password
        ):

            session.clear()

            session["student_id"] = management[0]
            session["name"] = management[1]
            session["email"] = management[2]
            session["role"] = "management"

            return redirect(
                "/management/dashboard"
            )

        return render_template(
            "management_login.html",
            error="Invalid management email or password."
        )

    return render_template(
        "management_login.html",
        error=None
    )


# =========================================================
# MANAGEMENT DASHBOARD
# =========================================================

@app.route("/management/dashboard")
def management_dashboard():

    if "student_id" not in session:
        return redirect("/management/login")

    if session.get("role") != "management":
        return "Access denied.", 403

    conn = get_db()

    cursor = conn.cursor()

    cursor.execute("""
        SELECT COUNT(*)
        FROM students
        WHERE role = 'student'
    """)

    student_count = cursor.fetchone()[0]

    cursor.execute("""
        SELECT COUNT(*)
        FROM students
        WHERE role = 'lecturer'
    """)

    lecturer_count = cursor.fetchone()[0]

    total_accounts = (
        student_count +
        lecturer_count
    )

    cursor.execute("""
        SELECT
            id,
            name,
            email,
            branch,
            year,
            role,
            batch,
            created_at,
            updated_at
        FROM students
        WHERE role IN ('student', 'lecturer')
        ORDER BY id DESC
    """)

    accounts = cursor.fetchall()

    conn.close()

    return render_template(
        "management_dashboard.html",
        student_count=student_count,
        lecturer_count=lecturer_count,
        total_accounts=total_accounts,
        accounts=accounts
    )


# =========================================================
# MANAGEMENT CREATE ACCOUNT
# =========================================================

@app.route(
    "/management/create-account",
    methods=["GET", "POST"]
)
def management_create_account():

    if "student_id" not in session:
        return redirect("/management/login")

    if session.get("role") != "management":
        return "Access denied.", 403

    if request.method == "POST":

        name = request.form.get(
            "name",
            ""
        ).strip()

        email = request.form.get(
            "email",
            ""
        ).strip().lower()

        password = request.form.get(
            "password",
            ""
        )

        branch = request.form.get(
            "branch",
            ""
        ).strip()

        year = request.form.get(
            "year",
            ""
        ).strip()

        role = request.form.get(
            "role",
            ""
        ).strip().lower()

        if role not in (
            "student",
            "lecturer"
        ):

            return "Invalid account role.", 400

        batch = request.form.get(
            "batch",
            ""
        ).strip()

        if role == "student":

            if batch not in BATCHES:

                return (
                    "Please select a valid student batch.",
                    400
                )

        else:

            batch = None

        if not name or not email or not password:

            return (
                "Please fill all required fields.",
                400
            )

        hashed_password = generate_password_hash(
            password
        )

        now = datetime.now().strftime(
            "%Y-%m-%d %H:%M:%S"
        )

        conn = get_db()

        try:

            conn.execute("""
                INSERT INTO students
                (
                    name,
                    email,
                    password,
                    branch,
                    year,
                    role,
                    batch,
                    created_at,
                    updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                name,
                email,
                hashed_password,
                branch,
                year,
                role,
                batch,
                now,
                now
            ))

            conn.commit()

        except sqlite3.IntegrityError:

            conn.close()

            return (
                "This email is already registered.",
                400
            )

        conn.close()

        flash(
            "✅ Account created successfully!"
        )

        return redirect(
            "/management/dashboard"
        )

    return render_template(
        "management_create_account.html",
        batches=BATCHES
    )


# =========================================================
# MANAGEMENT DELETE ACCOUNT
# =========================================================

@app.route(
    "/management/delete-account/<int:account_id>",
    methods=["POST"]
)
def management_delete_account(account_id):

    if "student_id" not in session:
        return redirect("/management/login")

    if session.get("role") != "management":
        return "Access denied.", 403

    conn = get_db()

    cursor = conn.cursor()

    cursor.execute("""
        SELECT id, name, email, role
        FROM students
        WHERE id = ?
    """, (account_id,))

    account = cursor.fetchone()

    if not account:

        conn.close()

        return "Account not found.", 404

    if account[3] == "management":

        conn.close()

        return (
            "Management account cannot be deleted.",
            403
        )

    conn.execute("""
        DELETE FROM students
        WHERE id = ?
        AND role IN ('student', 'lecturer')
    """, (account_id,))

    conn.commit()

    conn.close()

    flash(
        f"🗑️ Account '{account[1]}' deleted successfully."
    )

    return redirect(
        "/management/dashboard"
    )


# =========================================================
# MANAGEMENT NOTIFICATIONS
# =========================================================

@app.route(
    "/management/notifications",
    methods=["GET", "POST"]
)
def management_notifications():

    if "student_id" not in session:
        return redirect("/management/login")

    if session.get("role") != "management":
        return "Access denied.", 403

    if request.method == "POST":

        title = request.form.get(
            "title",
            ""
        ).strip()

        description = request.form.get(
            "description",
            ""
        ).strip()

        date = request.form.get(
            "date",
            ""
        ).strip()

        if not title or not description or not date:

            flash(
                "Please fill all notification details."
            )

            return redirect(
                "/management/notifications"
            )

        conn = get_db()

        conn.execute("""
            INSERT INTO announcements
            (
                title,
                description,
                date
            )
            VALUES (?, ?, ?)
        """, (
            title,
            description,
            date
        ))

        conn.commit()

        conn.close()

        flash(
            "📢 Notification pushed successfully!"
        )

        return redirect(
            "/management/notifications"
        )

    conn = get_db()

    cursor = conn.cursor()

    cursor.execute("""
        SELECT *
        FROM announcements
        ORDER BY id DESC
    """)

    notifications = cursor.fetchall()

    conn.close()

    return render_template(
        "management_notifications.html",
        notifications=notifications
    )


# =========================================================
# DELETE NOTIFICATION
# =========================================================

@app.route(
    "/management/delete-notification/<int:notification_id>",
    methods=["POST"]
)
def delete_management_notification(notification_id):

    if "student_id" not in session:
        return redirect("/management/login")

    if session.get("role") != "management":
        return "Access denied.", 403

    conn = get_db()

    conn.execute("""
        DELETE FROM announcements
        WHERE id = ?
    """, (notification_id,))

    conn.commit()

    conn.close()

    flash(
        "🗑️ Notification deleted successfully!"
    )

    return redirect(
        "/management/notifications"
    )


# =========================================================
# MANAGEMENT EVENTS
# =========================================================

@app.route(
    "/management/events",
    methods=["GET", "POST"]
)
def management_events():

    if "student_id" not in session:
        return redirect("/management/login")

    if session.get("role") != "management":
        return "Access denied.", 403

    if request.method == "POST":

        title = request.form.get(
            "title",
            ""
        ).strip()

        description = request.form.get(
            "description",
            ""
        ).strip()

        date = request.form.get(
            "date",
            ""
        ).strip()

        if not title or not description or not date:

            flash(
                "Please fill all event details."
            )

            return redirect(
                "/management/events"
            )

        conn = get_db()

        conn.execute("""
            INSERT INTO events
            (
                title,
                description,
                date
            )
            VALUES (?, ?, ?)
        """, (
            title,
            description,
            date
        ))

        conn.commit()

        conn.close()

        flash(
            "📅 Event published successfully!"
        )

        return redirect(
            "/management/events"
        )

    conn = get_db()

    cursor = conn.cursor()

    cursor.execute("""
        SELECT *
        FROM events
        ORDER BY id DESC
    """)

    event_history = cursor.fetchall()

    conn.close()

    return render_template(
        "management_events.html",
        events=event_history
    )


# =========================================================
# DELETE EVENT
# =========================================================

@app.route(
    "/management/delete-event/<int:event_id>",
    methods=["POST"]
)
def delete_management_event(event_id):

    if "student_id" not in session:
        return redirect("/management/login")

    if session.get("role") != "management":
        return "Access denied.", 403

    conn = get_db()

    conn.execute("""
        DELETE FROM events
        WHERE id = ?
    """, (event_id,))

    conn.commit()

    conn.close()

    flash(
        "🗑️ Event deleted successfully!"
    )

    return redirect(
        "/management/events"
    )


# =========================================================
# MANAGEMENT ANNOUNCEMENTS
# =========================================================

@app.route(
    "/management/announcements",
    methods=["GET", "POST"]
)
def management_announcements():

    if "student_id" not in session:
        return redirect("/management/login")

    if session.get("role") != "management":
        return "Access denied.", 403

    if request.method == "POST":

        title = request.form.get(
            "title",
            ""
        ).strip()

        description = request.form.get(
            "description",
            ""
        ).strip()

        date = request.form.get(
            "date",
            ""
        ).strip()

        if not title or not description or not date:

            flash(
                "Please fill in all announcement details."
            )

            return redirect(
                "/management/announcements"
            )

        conn = get_db()

        conn.execute("""
            INSERT INTO announcements
            (
                title,
                description,
                date
            )
            VALUES (?, ?, ?)
        """, (
            title,
            description,
            date
        ))

        conn.commit()

        conn.close()

        flash(
            "📢 Announcement posted successfully!"
        )

        return redirect(
            "/management/announcements"
        )

    return render_template(
        "management_announcements.html"
    )


# =========================================================
# MANAGEMENT MAIL
# =========================================================

@app.route(
    "/management/mail",
    methods=["GET", "POST"]
)
def management_mail():

    if "student_id" not in session:
        return redirect("/management/login")

    if session.get("role") != "management":
        return "Access denied.", 403

    if request.method == "POST":

        recipient = request.form.get(
            "recipient",
            ""
        )

        subject = request.form.get(
            "subject",
            ""
        ).strip()

        message = request.form.get(
            "message",
            ""
        ).strip()

        if not recipient or not subject or not message:

            flash(
                "Please fill all mail details."
            )

            return redirect(
                "/management/mail"
            )

        conn = get_db()

        cursor = conn.cursor()

        if recipient == "all_students":

            cursor.execute("""
                SELECT id
                FROM students
                WHERE role = 'student'
            """)

        elif recipient == "all_lecturers":

            cursor.execute("""
                SELECT id
                FROM students
                WHERE role = 'lecturer'
            """)

        elif recipient == "all":

            cursor.execute("""
                SELECT id
                FROM students
                WHERE role IN ('student', 'lecturer')
            """)

        else:

            conn.close()

            flash(
                "Invalid recipient."
            )

            return redirect(
                "/management/mail"
            )

        receivers = cursor.fetchall()

        now = datetime.now().strftime(
            "%Y-%m-%d %H:%M:%S"
        )

        for receiver in receivers:

            conn.execute("""
                INSERT INTO mails
                (
                    sender_id,
                    receiver_id,
                    subject,
                    message,
                    created_at,
                    is_read
                )
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                session["student_id"],
                receiver[0],
                subject,
                message,
                now,
                0
            ))

        conn.commit()

        conn.close()

        flash(
            "📨 Mail sent successfully!"
        )

        return redirect(
            "/management/mail"
        )

    return render_template(
        "management_mail.html"
    )


# =========================================================
# STUDENT / LECTURER MAILS
# =========================================================

@app.route("/mails")
def mails():

    if "student_id" not in session:
        return redirect("/login")

    if session.get("role") == "management":
        return redirect("/management/dashboard")

    conn = get_db()

    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            mails.id,
            mails.subject,
            mails.message,
            mails.created_at,
            mails.is_read,
            students.name
        FROM mails
        JOIN students
        ON mails.sender_id = students.id
        WHERE mails.receiver_id = ?
        ORDER BY mails.id DESC
    """, (
        session["student_id"],
    ))

    mail_list = cursor.fetchall()

    conn.close()

    return render_template(
        "mails.html",
        mails=mail_list
    )


@app.route("/mail/<int:mail_id>")
def open_mail(mail_id):

    if "student_id" not in session:
        return redirect("/login")

    if session.get("role") == "management":
        return redirect("/management/dashboard")

    conn = get_db()

    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            mails.id AS id,
            mails.subject AS subject,
            mails.message AS message,
            mails.created_at AS created_at,
            mails.is_read AS is_read,
            students.name AS name
        FROM mails
        JOIN students
        ON mails.sender_id = students.id
        WHERE mails.id = ?
    """, (mail_id,))

    mail = cursor.fetchone()

    if not mail:

        conn.close()

        return "Mail not found.", 404

    cursor.execute("""
        SELECT id
        FROM mails
        WHERE id = ?
        AND receiver_id = ?
    """, (
        mail_id,
        session["student_id"]
    ))

    receiver_check = cursor.fetchone()

    if not receiver_check:

        conn.close()

        return (
            "You do not have access to this mail.",
            403
        )

    cursor.execute("""
        UPDATE mails
        SET is_read = 1
        WHERE id = ?
        AND receiver_id = ?
    """, (
        mail_id,
        session["student_id"]
    ))

    conn.commit()

    conn.close()

    return render_template(
        "mail_detail.html",
        mail=mail
    )


# =========================================================
# LECTURER COURSE SELECTION
# =========================================================

@app.route("/lecturer/select-course")
def lecturer_select_course():

    if "student_id" not in session:
        return redirect("/lecturer/login")

    if session.get("role") != "lecturer":
        return "Access denied.", 403

    return render_template(
        "lecturer_course_select.html",
        courses=COURSES
    )


@app.route("/lecturer/select-course/<course>")
def lecturer_choose_course(course):

    if "student_id" not in session:
        return redirect("/lecturer/login")

    if session.get("role") != "lecturer":
        return "Access denied.", 403

    if course not in COURSES:
        return "Course not found.", 404

    session["lecturer_course"] = course

    return redirect("/dashboard")


# =========================================================
# DASHBOARD
# =========================================================

@app.route("/dashboard")
def dashboard():

    if "student_id" not in session:
        return redirect("/login")

    if session.get("role") == "management":
        return redirect("/management/dashboard")

    conn = get_db()

    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            name,
            email,
            branch,
            year,
            role
        FROM students
        WHERE id = ?
    """, (
        session["student_id"],
    ))

    user = cursor.fetchone()

    conn.close()

    if not user:

        session.clear()

        return redirect("/login")

    # =====================================================
    # LECTURER
    # =====================================================

    if user[4] == "lecturer":

        if not session.get("lecturer_course"):

            return redirect(
                "/lecturer/select-course"
            )

        return render_template(
            "lecturer_dashboard.html",
            student=user,
            course_name=COURSES[
                session["lecturer_course"]
            ]
        )

    # =====================================================
    # STUDENT
    # =====================================================

    return render_template(
        "dashboard.html",
        student=user
    )


# =========================================================
# PROFILE
# =========================================================

@app.route("/profile")
def profile():

    if "student_id" not in session:
        return redirect("/login")

    conn = get_db()

    cursor = conn.cursor()

    cursor.execute(
        "SELECT * FROM students WHERE id = ?",
        (session["student_id"],)
    )

    user = cursor.fetchone()

    print("LOGIN USER:", user)

    conn.close()

    if not user:

        session.clear()

        return redirect("/login")

    return render_template(
        "profile.html",
        student=user
    )


# =========================================================
# LOGOUT
# =========================================================

@app.route("/logout")
def logout():

    session.clear()

    return redirect("/")


# =========================================================
# ANNOUNCEMENTS
# =========================================================

@app.route("/announcements")
def announcements():

    if "student_id" not in session:
        return redirect("/login")

    conn = get_db()

    cursor = conn.cursor()

    cursor.execute("""
        SELECT *
        FROM announcements
        ORDER BY id DESC
    """)

    announcement_list = cursor.fetchall()

    conn.close()

    return render_template(
        "announcements.html",
        announcements=announcement_list
    )


# =========================================================
# EVENTS
# =========================================================

@app.route("/events")
def events():

    if "student_id" not in session:
        return redirect("/login")

    conn = get_db()

    cursor = conn.cursor()

    cursor.execute("""
        SELECT *
        FROM events
        ORDER BY id DESC
    """)

    event_list = cursor.fetchall()

    conn.close()

    return render_template(
        "events.html",
        events=event_list
    )


# =========================================================
# STUDENT RESOURCES
# =========================================================

@app.route("/resources")
def resources():

    if "student_id" not in session:
        return redirect("/login")

    if session.get("role") == "lecturer":

        return redirect(
            "/lecturer-resources"
        )

    return render_template(
        "resources.html",
        courses=COURSES,
        role="student"
    )


# =========================================================
# LECTURER RESOURCES MAIN PAGE
# =========================================================

@app.route("/lecturer-resources")
def lecturer_resources():

    if "student_id" not in session:
        return redirect("/lecturer/login")

    if session.get("role") != "lecturer":
        return "Access denied.", 403

    if not session.get("lecturer_course"):

        return redirect(
            "/lecturer/select-course"
        )

    return render_template(
        "lecturer_resources.html"
    )


# =========================================================
# LECTURER RESOURCE CATEGORY
# =========================================================

@app.route("/lecturer-resources/<category>")
def lecturer_resource_category_select(category):

    if "student_id" not in session:
        return redirect("/lecturer/login")

    if session.get("role") != "lecturer":
        return "Access denied.", 403

    if not session.get("lecturer_course"):

        return redirect(
            "/lecturer/select-course"
        )

    if category not in CATEGORIES:
        return "Resource category not found.", 404

    return render_template(
        "lecturer_resources_batch.html",
        category=category,
        category_name=CATEGORIES[category],
        batches=BATCHES
    )


# =========================================================
# LECTURER RESOURCE UPLOAD
# =========================================================

@app.route(
    "/lecturer-resources/<category>/<batch>",
    methods=["GET", "POST"]
)
def lecturer_resource_upload(category, batch):

    if "student_id" not in session:
        return redirect("/lecturer/login")

    if session.get("role") != "lecturer":
        return "Access denied.", 403

    if not session.get("lecturer_course"):

        return redirect(
            "/lecturer/select-course"
        )

    if category not in CATEGORIES:
        return "Resource category not found.", 404

    if batch not in BATCHES:
        return "Batch not found.", 404

    category_name = CATEGORIES[category]
    batch_name = BATCHES[batch]

    course_key = session["lecturer_course"]
    course_name = COURSES[course_key]

    # =====================================================
    # UPLOAD
    # =====================================================

    if request.method == "POST":

        title = request.form.get(
            "title",
            ""
        ).strip()

        file = request.files.get("file")

        if not title:

            flash(
                "Please enter a material title."
            )

            return redirect(
                f"/lecturer-resources/{category}/{batch}"
            )

        if not file or file.filename == "":

            flash(
                "Please select a file."
            )

            return redirect(
                f"/lecturer-resources/{category}/{batch}"
            )

        if not allowed_file(file.filename):

            flash(
                "Only PDF, PPT and PPTX files are allowed."
            )

            return redirect(
                f"/lecturer-resources/{category}/{batch}"
            )

        original_filename = secure_filename(
            file.filename
        )

        unique_filename = (
            datetime.now().strftime(
                "%Y%m%d%H%M%S%f"
            )
            + "_"
            + original_filename
        )

        file_path = os.path.join(
            app.config["UPLOAD_FOLDER"],
            unique_filename
        )

        file.save(file_path)

        file_type = (
            original_filename
            .rsplit(".", 1)[1]
            .upper()
        )

        conn = get_db()

        conn.execute("""
            INSERT INTO study_resources
            (
                title,
                filename,
                course,
                category,
                batch,
                file_type,
                uploaded_by,
                uploaded_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            title,
            unique_filename,
            course_name,
            category_name,
            batch_name,
            file_type,
            session["student_id"],
            datetime.now().strftime(
                "%Y-%m-%d %H:%M:%S"
            )
        ))

        conn.commit()

        conn.close()

        flash(
            f"✅ {course_name} → "
            f"{category_name} material uploaded successfully!"
        )

        return redirect(
            f"/lecturer-resources/{category}/{batch}"
        )

    # =====================================================
    # LOAD MATERIALS
    # =====================================================

    conn = get_db()

    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            study_resources.id,
            study_resources.title,
            study_resources.filename,
            study_resources.category,
            study_resources.file_type,
            study_resources.uploaded_at
        FROM study_resources
        WHERE study_resources.course = ?
        AND study_resources.category = ?
        AND study_resources.batch = ?
        ORDER BY study_resources.id DESC
    """, (
        course_name,
        category_name,
        batch_name
    ))

    resources_list = cursor.fetchall()

    conn.close()

    return render_template(
        "lecturer_resources_category.html",
        resources=resources_list,
        category=category,
        category_name=category_name,
        batch=batch,
        batch_name=batch_name,
        course_name=course_name
    )


# =========================================================
# STUDENT COURSE PAGE
# =========================================================

@app.route("/resources/<course>")
def resource_course(course):

    if "student_id" not in session:
        return redirect("/login")

    if session.get("role") == "lecturer":

        return redirect(
            "/lecturer-resources"
        )

    if course not in COURSES:
        return "Course not found.", 404

    return render_template(
        "resource_course.html",
        course=course,
        course_name=COURSES[course],
        categories=CATEGORIES,
        role="student"
    )


# =========================================================
# STUDENT RESOURCE CATEGORY
# =========================================================

@app.route("/resources/<course>/<category>")
def resource_category(course, category):

    if "student_id" not in session:
        return redirect("/login")

    if session.get("role") == "lecturer":

        return redirect(
            "/lecturer-resources"
        )

    if course not in COURSES:
        return "Course not found.", 404

    if category not in CATEGORIES:
        return "Resource category not found.", 404

    course_name = COURSES[course]
    category_name = CATEGORIES[category]

    conn = get_db()

    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            study_resources.id,
            study_resources.title,
            study_resources.filename,
            study_resources.course,
            study_resources.category,
            study_resources.file_type,
            study_resources.uploaded_at,
            students.name
        FROM study_resources
        JOIN students
        ON study_resources.uploaded_by = students.id
        WHERE study_resources.course = ?
        AND study_resources.category = ?
        ORDER BY study_resources.id DESC
    """, (
        course_name,
        category_name
    ))

    resources_list = cursor.fetchall()

    conn.close()

    return render_template(
        "resource_category.html",
        resources=resources_list,
        course=course,
        course_name=course_name,
        category=category,
        category_name=category_name,
        role="student"
    )


# =========================================================
# OPEN RESOURCE
# =========================================================

@app.route("/uploads/<filename>")
def open_resource(filename):

    if "student_id" not in session:
        return redirect("/login")

    return send_from_directory(
        app.config["UPLOAD_FOLDER"],
        filename
    )


# =========================================================
# TEAMMATES
# =========================================================

@app.route("/teammates")
def teammates():

    if "student_id" not in session:
        return redirect("/login")

    skill = request.args.get(
        "skill",
        ""
    )

    conn = get_db()

    cursor = conn.cursor()

    if skill:

        cursor.execute("""
            SELECT *
            FROM teammates
            WHERE skill LIKE ?
        """, (
            "%" + skill + "%"
        ))

    else:

        cursor.execute(
            "SELECT * FROM teammates"
        )

    teammate_list = cursor.fetchall()

    conn.close()

    return render_template(
        "teammates.html",
        teammates=teammate_list
    )


# =========================================================
# ADD TEAMMATE
# =========================================================

@app.route(
    "/add-teammate",
    methods=["GET", "POST"]
)
def add_teammate():

    if "student_id" not in session:
        return redirect("/login")

    if session.get("role") != "student":
        return "Access denied.", 403

    if request.method == "POST":

        name = request.form["name"]
        branch = request.form["branch"]
        year = request.form["year"]
        skill = request.form["skill"]
        description = request.form["description"]

        conn = get_db()

        conn.execute("""
            INSERT INTO teammates
            (
                name,
                branch,
                year,
                skill,
                description
            )
            VALUES (?, ?, ?, ?, ?)
        """, (
            name,
            branch,
            year,
            skill,
            description
        ))

        conn.commit()

        conn.close()

        return redirect("/teammates")

    return render_template(
        "add_teammate.html"
    )


# =========================================================
# CONNECT
# =========================================================

@app.route(
    "/connect/<int:teammate_id>",
    methods=["POST"]
)
def connect(teammate_id):

    if "student_id" not in session:
        return redirect("/login")

    if session.get("role") != "student":
        return "Access denied.", 403

    conn = get_db()

    conn.execute("""
        INSERT INTO connections
        (
            sender_id,
            receiver_id,
            status,
            created_at
        )
        VALUES (?, ?, ?, ?)
    """, (
        session["student_id"],
        teammate_id,
        "pending",
        datetime.now().strftime(
            "%Y-%m-%d %H:%M:%S"
        )
    ))

    conn.commit()

    conn.close()

    flash(
        "🤝 Connection request sent successfully!"
    )

    return redirect("/teammates")


# =========================================================
# MY CONNECTIONS
# =========================================================

@app.route("/connections")
def connections():

    if "student_id" not in session:
        return redirect("/login")

    if session.get("role") != "student":
        return "Access denied.", 403

    conn = get_db()

    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            connections.id,
            connections.status,
            connections.created_at,
            teammates.name,
            teammates.branch,
            teammates.year,
            teammates.skill
        FROM connections
        JOIN teammates
        ON connections.receiver_id = teammates.id
        WHERE connections.sender_id = ?
        ORDER BY connections.id DESC
    """, (
        session["student_id"],
    ))

    connection_list = cursor.fetchall()

    conn.close()

    return render_template(
        "connections.html",
        connections=connection_list
    )


# =========================================================
# CAMPUS ASSISTANT
# =========================================================

@app.route("/assistant")
def assistant():

    if "student_id" not in session:
        return redirect("/login")

    return render_template(
        "assistant.html"
    )


@app.route(
    "/ask",
    methods=["POST"]
)
def ask():

    if "student_id" not in session:
        return redirect("/login")

    question = request.form[
        "question"
    ].lower()

    if "library" in question:

        answer = (
            "📚 The library is available for students "
            "during 8am to 8pm."
        )

    elif (
        "timing" in question
        or "time" in question
    ):

        answer = (
            "🕐 College working hours are generally "
            "from 8:30am to 4:30pm for juniors."
        )

    elif "club" in question:

        answer = (
            "🎯 You can join college clubs by contacting "
            "the respective club coordinators."
        )

    elif "help" in question:

        answer = (
            "🤝 You can contact your department or "
            "college administration for further help."
        )

    else:

        answer = (
            "🤖 Sorry, I don't have an answer for that yet."
        )

    return render_template(
        "assistant.html",
        answer=answer
    )


# =========================================================
# CAMPUS INFO
# =========================================================

@app.route("/campus-info")
def campus_info():

    if "student_id" not in session:
        return redirect("/login")

    return render_template(
        "campus_info.html"
    )


# =========================================================
# BATCH CHAT
# =========================================================

@app.route("/batch-chat")
def batch_chat():

    if "student_id" not in session:
        return redirect("/login")

    role = session.get("role")

    # =====================================================
    # STUDENT
    # ONLY THEIR ASSIGNED BATCH
    # =====================================================

    if role == "student":

        conn = get_db()

        cursor = conn.cursor()

        cursor.execute("""
            SELECT batch
            FROM students
            WHERE id = ?
            AND role = 'student'
        """, (
            session["student_id"],
        ))

        student = cursor.fetchone()

        conn.close()

        if not student:

            session.clear()

            return redirect("/login")

        student_batch = student[0]

        if student_batch not in BATCHES:

            return (
                "Your batch has not been assigned yet.",
                400
            )

        return render_template(
            "batch_chat.html",
            batches={
                student_batch: BATCHES[student_batch]
            }
        )

    # =====================================================
    # LECTURER
    # ALL BATCHES
    # =====================================================

    if role == "lecturer":

        return render_template(
            "batch_chat.html",
            batches=BATCHES
        )

    return "Access denied.", 403


# =========================================================
# BATCH CHAT ROOM
# =========================================================

@app.route(
    "/batch-chat/<batch>",
    methods=["GET", "POST"]
)
def batch_chat_room(batch):

    if "student_id" not in session:
        return redirect("/login")

    role = session.get("role")

    # =====================================================
    # ONLY STUDENT AND LECTURER
    # =====================================================

    if role not in (
        "student",
        "lecturer"
    ):

        return "Access denied.", 403

    # =====================================================
    # CHECK VALID BATCH
    # =====================================================

    if batch not in BATCHES:

        return "Batch not found.", 404

    # =====================================================
    # STUDENT BATCH SECURITY
    # =====================================================

    if role == "student":

        conn = get_db()

        cursor = conn.cursor()

        cursor.execute("""
            SELECT batch
            FROM students
            WHERE id = ?
            AND role = 'student'
        """, (
            session["student_id"],
        ))

        student = cursor.fetchone()

        conn.close()

        if not student:

            session.clear()

            return redirect("/login")

        assigned_batch = student[0]

        if assigned_batch != batch:

            return (
                "You can only access your assigned batch chat.",
                403
            )

    # =====================================================
    # SEND MESSAGE
    # =====================================================

    if request.method == "POST":

        message = request.form.get(
            "message",
            ""
        ).strip()

        if message:

            conn = get_db()

            conn.execute("""
                INSERT INTO batch_chat_messages
                (
                    batch,
                    sender_id,
                    message,
                    created_at
                )
                VALUES (?, ?, ?, ?)
            """, (
                batch,
                session["student_id"],
                message,
                datetime.now().strftime(
                    "%Y-%m-%d %H:%M:%S"
                )
            ))

            conn.commit()

            conn.close()

        return redirect(
            f"/batch-chat/{batch}"
        )

    # =====================================================
    # LOAD MESSAGES
    # =====================================================

    conn = get_db()

    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            batch_chat_messages.id AS id,
            batch_chat_messages.message AS message,
            batch_chat_messages.created_at AS created_at,
            students.name AS name,
            students.role AS role
        FROM batch_chat_messages
        JOIN students
        ON batch_chat_messages.sender_id = students.id
        WHERE batch_chat_messages.batch = ?
        ORDER BY batch_chat_messages.id ASC
    """, (
        batch,
    ))

    messages = cursor.fetchall()

    conn.close()

    return render_template(
        "batch_chat_room.html",
        batch=batch,
        batch_name=BATCHES[batch],
        messages=messages
    )


# =========================================================
# INITIALIZE DATABASE
# =========================================================

# This must run when Flask starts,
# including when deployed with Gunicorn on Render.
init_db()


# =========================================================
# START APP
# =========================================================

if __name__ == "__main__":

    app.run(
        host="0.0.0.0",
        port=5000,
        debug=True
    )