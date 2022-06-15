from flask import Flask

from db.database import database_bp
from handlers import books_bp, home_bp

app = Flask(__name__)
app.register_blueprint(books_bp)
app.register_blueprint(database_bp)
app.register_blueprint(home_bp)


if __name__ == '__main__':
    app.run()
