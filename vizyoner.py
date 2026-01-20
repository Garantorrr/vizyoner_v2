import os
import sqlite3
import requests
from flask import Flask, render_template, request, redirect, url_for, flash, session
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user

app = Flask(__name__)
app.config['SECRET_KEY'] = 'vizyoner-gizli-anahtar-123'

# Veritabanı yolu
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE = os.path.join(BASE_DIR, "vizyoner.db")

TMDB_API_KEY = "42df14bcedce9a5420ef8fcb19f2ff7b"
TMDB_URL = "https://api.themoviedb.org/3"

def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_db() as conn:
        conn.execute("CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT UNIQUE, password TEXT)")
        conn.execute("CREATE TABLE IF NOT EXISTS favoriler (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, tur TEXT, isim TEXT)")
        conn.commit()

with app.app_context():
    init_db()

login_manager = LoginManager(app)
login_manager.login_view = 'login'

class User(UserMixin):
    def __init__(self, id, username):
        self.id = id
        self.username = username

@login_manager.user_loader
def load_user(user_id):
    db = get_db()
    user = db.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    return User(user['id'], user['username']) if user else None

def fetch_tmdb(endpoint, params={}):
    params.update({'api_key': TMDB_API_KEY, 'language': 'tr-TR'})
    try:
        r = requests.get(f"{TMDB_URL}/{endpoint}", params=params, timeout=5)
        return r.json().get('results', [])
    except: return []

@app.route('/')
def index():
    vizyon = fetch_tmdb("movie/now_playing")[:6]
    trendler = fetch_tmdb("trending/all/week")[:10]
    return render_template('index.html', vizyon=vizyon, trendler=trendler)

@app.route('/film/<int:film_id>')
def film_detay(film_id):
    params = {'api_key': TMDB_API_KEY, 'language': 'tr-TR'}
    # Film Bilgisi
    r = requests.get(f"{TMDB_URL}/movie/{film_id}", params=params)
    film = r.json()
    # Oyuncular ve Yönetmen
    c = requests.get(f"{TMDB_URL}/movie/{film_id}/credits", params=params)
    credits = c.json()
    oyuncular = credits.get('cast', [])[:10]
    yonetmen = next((m['name'] for m in credits.get('crew', []) if m['job'] == 'Director'), "Bilinmiyor")
    return render_template('detail.html', film=film, oyuncular=oyuncular, yonetmen=yonetmen)

@app.route('/search')
def search():
    query = request.args.get('q')
    if not query:
        return redirect(url_for('index'))
    params = {'api_key': TMDB_API_KEY, 'language': 'tr-TR', 'query': query}
    r = requests.get(f"{TMDB_URL}/search/movie", params=params)
    sonuclar = r.json().get('results', [])
    return render_template('search_results.html', sonuclar=sonuclar, query=query)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user = get_db().execute("SELECT * FROM users WHERE username = ?", (request.form['username'],)).fetchone()
        if user and check_password_hash(user['password'], request.form['password']):
            login_user(User(user['id'], user['username']))
            return redirect(url_for('index'))
        flash("Hatalı bilgiler!", "danger")
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        u, p = request.form['username'], request.form['password']
        if not u or not p:
            flash("Tüm alanları doldurun!", "danger")
            return redirect(url_for('register'))
        phash = generate_password_hash(p)
        try:
            with get_db() as conn:
                conn.execute("INSERT INTO users (username, password) VALUES (?, ?)", (u, phash))
                conn.commit()
            flash("Kayıt başarılı!", "success")
            return redirect(url_for('login'))
        except: flash("Bu kullanıcı adı alınmış!", "danger")
    return render_template('register.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

if __name__ == "__main__":
    app.run(debug=True)