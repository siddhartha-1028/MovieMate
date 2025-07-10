import requests
import os
from flask import flash, current_app
from dotenv import load_dotenv

def fetch_tmdb_results(query, endpoint="search/movie"):
    api_key = current_app.config['API_KEY']
    try:
        url = f"https://api.themoviedb.org/3/{endpoint}?api_key={api_key}&query={query}"
        response = requests.get(url, timeout=5)
        response.raise_for_status()
        return response.json().get("results", [])
    except requests.exceptions.Timeout:
        flash("TMDb API timed out. Please try again later.", "danger")
        return []
    except requests.exceptions.RequestException:
        flash("TMDb API failed. Please try again later.", "danger")
        return []