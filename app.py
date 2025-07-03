from flask import Flask, render_template, request
import requests

app= Flask(__name__)
API_KEY= 'ab3fc89f40fa5a5313c8c7599f07ca1b'

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/search')
def search():
    query= request.args.get('query')
    url = f"https://api.themoviedb.org/3/search/movie?api_key={API_KEY}&query={query}"
    response= requests.get(url)
    data= response.json()
    movies= data['results']
    return render_template('results.html',movies=movies)

if __name__ =='__main__':
    app.run(debug=True)

