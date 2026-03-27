from flask import Flask, render_template, request, redirect, send_from_directory
from flask_mysqldb import MySQL
import os

app = Flask(__name__)

# MySQL config
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = 'neve@2007'
app.config['MYSQL_DB'] = 'memory_bank'

mysql = MySQL(app)

# Upload folder
app.config['UPLOAD_FOLDER'] = 'uploads'


@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)


@app.route('/save_audio', methods=['POST'])
def save_audio():
    if 'audio' not in request.files:
        return "No audio file uploaded", 400

    audio_file = request.files['audio']
    title_input = request.form.get('title')

    cur = mysql.connection.cursor()

    # 👉 If user didn't enter title → auto generate
    if not title_input or title_input.strip() == "":
        cur.execute("SELECT COUNT(*) FROM memories WHERE description='Voice Memory'")
        count = cur.fetchone()[0]
        title = f"Memory {count + 1}"
    else:
        title = title_input

    # Save file
    filename = f"{title}.wav"
    save_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    audio_file.save(save_path)

    # Save to DB
    cur.execute(
        "INSERT INTO memories(title, description, file_path) VALUES(%s, %s, %s)",
        (title, "Voice Memory", save_path)
    )
    mysql.connection.commit()
    cur.close()

    return "Audio saved successfully!"


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']

        cur = mysql.connection.cursor()
        cur.execute(
            "INSERT INTO users(name,email,password) VALUES(%s,%s,%s)",
            (name, email, password)
        )
        mysql.connection.commit()
        cur.close()

        return redirect('/login')

    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        cur = mysql.connection.cursor()
        cur.execute(
            "SELECT * FROM users WHERE email=%s AND password=%s",
            (email, password)
        )
        user = cur.fetchone()
        cur.close()

        if user:
            return redirect('/dashboard')
        else:
            return "Invalid login"

    return render_template('login.html')


@app.route('/dashboard', methods=['GET', 'POST'])
def dashboard():
    cur = mysql.connection.cursor()

    # 🔍 Get search value
    search_query = request.form.get('search')

    # 📤 Upload feature
    if request.method == 'POST' and 'title' in request.form:
        title = request.form['title']
        description = request.form['description']
        file = request.files.get('file')

        filepath = None  # 👈 default (no file)

        if file and file.filename != "":
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
            file.save(filepath)

        cur.execute(
            "INSERT INTO memories(title,description,file_path) VALUES(%s,%s,%s)",
            (title, description, filepath)
        )
        mysql.connection.commit()
        cur.close()
        return redirect('/dashboard')

    # 🔍 Search + smart ordering
    if search_query and search_query.strip() != "":
        cur.execute("""
            SELECT * FROM memories
            ORDER BY
                CASE WHEN title LIKE %s THEN 0 ELSE 1 END,
                id DESC
        """, ('%' + search_query + '%',))
    else:
        cur.execute("SELECT * FROM memories ORDER BY id DESC")

    memories = cur.fetchall()
    cur.close()

    return render_template('dashboard.html', memories=memories)


@app.route('/delete/<int:id>')
def delete_memory(id):
    cur = mysql.connection.cursor()

    # Get file path first
    cur.execute("SELECT file_path FROM memories WHERE id=%s", (id,))
    memory = cur.fetchone()

    if memory:
        file_path = memory[0]

        # Delete file from folder
        if os.path.exists(file_path):
            os.remove(file_path)

        # Delete from DB
        cur.execute("DELETE FROM memories WHERE id=%s", (id,))
        mysql.connection.commit()

    cur.close()
    return redirect('/dashboard')


if __name__ == '__main__':
    app.run(debug=True)