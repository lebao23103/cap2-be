import os
import sys
from waitress import serve
from book_web.wsgi import application

if __name__ == '__main__':
    print("Starting Waitress server on http://0.0.0.0:8000")
    serve(application, host='0.0.0.0', port=8000)
