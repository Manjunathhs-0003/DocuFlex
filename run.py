from app import create_app
from scheduler import scheduler

app = create_app()

if __name__ == "__main__":
    app.run(debug=True)
    scheduler.start()