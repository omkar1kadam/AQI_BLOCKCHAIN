from flask import Flask

app = Flask(__name__)

@app.route('/test')
def test():
    return "✅ Flask is working!"

if __name__ == "__main__":
    print("🔥 Flask is running...")
    app.run(debug=True)
