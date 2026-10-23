from fastapi import FastAPI, HTTPException, status, Header
from pydantic import BaseModel
import sqlite3
import bcrypt

app = FastAPI(title="Movie Collection API", version="1.0")

def init_db():
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS movies (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            genre TEXT NOT NULL,
            rating REAL DEFAULT 5.0,
            user_id INTEGER,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')
    conn.commit()
    conn.close()

init_db()

class UserSchema(BaseModel):
    username: str
    password: str

class MovieCreate(BaseModel):
    title: str
    genre: str
    rating: float = 5.0
    user_id: int

class MovieUpdate(BaseModel):
    title: str
    genre: str
    rating: float

@app.post("/register", status_code=status.HTTP_201_CREATED)
def register(user: UserSchema):
    pwd_bytes = user.password.encode('utf-8')
    salt = bcrypt.gensalt()
    password_hash = bcrypt.hashpw(pwd_bytes, salt).decode('utf-8')

    try:
        conn = sqlite3.connect("database.db")
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO users (username, password_hash) VALUES (?, ?)",
            (user.username, password_hash)
        )
        conn.commit()
        conn.close()
    except sqlite3.IntegrityError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Пользователь с таким именем уже существует"
        )
    
    return {"message": "Регистрация прошла успешно!"}

@app.post("/login")
def login(user: UserSchema):
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()
    cursor.execute("SELECT id, password_hash FROM users WHERE username = ?", (user.username,))
    row = cursor.fetchone()
    conn.close()

    if not row or not bcrypt.checkpw(user.password.encode('utf-8'), row[1].encode('utf-8')):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверный логин или пароль"
        )

    return {"message": "Успешный вход!", "user_id": row[0], "status": 200}

@app.post("/movies", status_code=status.HTTP_201_CREATED)
def create_movie(movie: MovieCreate):
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()
    
    cursor.execute("SELECT id FROM users WHERE id = ?", (movie.user_id,))
    if not cursor.fetchone():
        conn.close()
        raise HTTPException(status_code=404, detail="Указанный пользователь не найден")

    cursor.execute(
        "INSERT INTO movies (title, genre, rating, user_id) VALUES (?, ?, ?, ?)",
        (movie.title, movie.genre, movie.rating, movie.user_id)
    )
    conn.commit()
    movie_id = cursor.lastrowid
    conn.close()
    
    return {"message": "Фильм успешно добавлен", "movie_id": movie_id, **movie.dict()}

@app.get("/movies")
def get_movies():
    conn = sqlite3.connect("database.db")
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM movies")
    rows = cursor.fetchall()
    conn.close()
    
    return [dict(row) for row in rows]

@app.put("/movies/{movie_id}")
def update_movie(movie_id: int, movie: MovieUpdate):
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE movies SET title = ?, genre = ?, rating = ? WHERE id = ?",
        (movie.title, movie.genre, movie.rating, movie_id)
    )
    conn.commit()
    updated_rows = cursor.rowcount
    conn.close()

    if updated_rows == 0:
        raise HTTPException(status_code=404, detail="Фильм не найден")

    return {"message": "Фильм успешно обновлен", "movie_id": movie_id, **movie.dict()}

@app.delete("/movies/{movie_id}")
def delete_movie(movie_id: int):
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()
    cursor.execute("DELETE FROM movies WHERE id = ?", (movie_id,))
    conn.commit()
    deleted_rows = cursor.rowcount
    conn.close()

    if deleted_rows == 0:
        raise HTTPException(status_code=404, detail="Фильм не найден")

    return {"message": "Фильм успешно удален", "movie_id": movie_id}