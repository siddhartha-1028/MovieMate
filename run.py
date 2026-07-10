from app import create_app, db

app = create_app()

# Ensure SQLite database and tables are created
with app.app_context():
    db.create_all()

if __name__ == "__main__":
    app.run(debug=True)

