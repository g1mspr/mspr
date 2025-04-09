#! /usr/bin/env python
from nesterapp import app
from nesterapp.init_db import init_db

if __name__ == "__main__":
    app.run(debug=True)
    init_db()

