from flask import Flask

from handlers import homepage, search_books
from db.database import create_db
from db.seed import seed_db

app = Flask(__name__)

app.add_url_rule("/create_db", "create_db", create_db, methods=["GET"])
app.add_url_rule("/seed_db", "seed_db", seed_db, methods=["GET"])
app.add_url_rule("/search", "search_books", search_books, methods=["POST"])
app.add_url_rule("/", "homepage", homepage, methods=["GET"])


if __name__ == '__main__':
    app.run()
