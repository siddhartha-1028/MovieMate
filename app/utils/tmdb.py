import requests
import os
from flask import flash, current_app
from dotenv import load_dotenv

def fetch_tmdb_results(query, endpoint="search/movie"):
    """Search TMDB for movies matching a query string."""
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

def fetch_movie_videos(movie_id):
    """
    Fetches YouTube trailer key for a given TMDB movie ID.
    Returns the YouTube video key (string) of the first official trailer,
    or None if no trailer is found.
    
    Example: key="dQw4w9WgXcQ" → embed URL is https://www.youtube.com/embed/dQw4w9WgXcQ
    """
    api_key = current_app.config['API_KEY']
    try:
        url = f"https://api.themoviedb.org/3/movie/{movie_id}/videos?api_key={api_key}"
        response = requests.get(url, timeout=5)
        response.raise_for_status()
        videos = response.json().get("results", [])

        # Find the first YouTube "Trailer" type; fall back to any YouTube video
        for video in videos:
            if video.get("site") == "YouTube" and video.get("type") == "Trailer":
                return video.get("key")
        for video in videos:
            if video.get("site") == "YouTube":
                return video.get("key")
        return None
    except Exception:
        return None