import json
from .comments_collector import *
from modules.constants import PATH_TO_API_KEY

def build_service(api_key_file):
    """
    Reads the API key from the specified JSON file and initializes the YouTube service.
    """
    # Read the API key from the JSON file
    with open(api_key_file, 'r') as f:
        creds = json.load(f)
    
    # Get the API key and remove any extra whitespace or newlines
    api_key = creds.get("api_key", "").strip()

    if not api_key:
        raise ValueError("API key not found in creds.json")

    # Initialize and return the YouTube Data API service
    yt_service = build('youtube', 'v3', developerKey=api_key)
    return yt_service

def _get_comments(video_url, api_key_file, order='time', part='snippet', maxResults=100):
    """
    Fetches comments for a given YouTube video URL using the specified API key file.
    """
    # Build the YouTube service with the API key
    yt_service = build_service(api_key_file)
    
    # Extract the video ID from the URL
    video_ID = get_id(video_url)
    
    # Get comments and the video title using the helper function
    comments_dict, title = comments_helper(video_ID, api_key_file, yt_service)
    
    # Save the comments to a CSV file
    save_to_csv(comments_dict, title)
    
    return title

def get_comments_from_urls(urls):
    """
    Fetches comments for a list of YouTube video URLs.
    """
    # Get the path to the API key from the constants
    api_key_path = PATH_TO_API_KEY
    
    video_titles = []
    for url in urls:
        # Get comments for each URL and append the video title to the list
        title = _get_comments(url, api_key_path)
        video_titles.append(title)
    
    return video_titles
