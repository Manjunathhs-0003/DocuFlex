# # run.py

# from app import create_app

# app = create_app()

# if __name__ == '__main__':
#     app.run(debug=True)

# run.py

from app import create_app

app = create_app()

if __name__ == '__main__':
    app.run()  # Replace with Gunicorn in production

