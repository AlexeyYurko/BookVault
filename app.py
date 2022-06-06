from flask import Flask

from database import datab
from handlers import books, home

app = Flask(__name__)
app.register_blueprint(books)
app.register_blueprint(datab)
app.register_blueprint(home)


if __name__ == '__main__':
    app.run()
