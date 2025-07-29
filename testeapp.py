from flask import Flask

app = Flask(__name__)

@app.before_first_request
def init_db():
    print("Inicializando banco!")

@app.route('/')
def home():
    return "Flask funcionando!"

if __name__ == '__main__':
    app.run(debug=True)