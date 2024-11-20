'''
The helper file to get the comments from a particular video URL
'''

import requests
import pandas as pd
import json
import time
from apiclient.discovery import build
from csv import writer
from urllib.parse import urlparse, parse_qs
import re

def get_keys(filename):
    '''
    To get YouTube API key from the specified JSON file
    '''
    with open(filename) as f:
        key = f.readline().strip()
    return {'key': key, 'name': 'youtube', 'version': 'v3'}


def build_service(filename):
    '''
    To build the YouTube API service
    '''
    with open(filename) as f:
        key = f.readline().strip()

    YOUTUBE_API_SERVICE_NAME = "youtube"
    YOUTUBE_API_VERSION = "v3"
    return build(YOUTUBE_API_SERVICE_NAME,
                 YOUTUBE_API_VERSION,
                 developerKey=key)


def get_id(url):
    '''
    To get the video ID from the video URL
    '''
    u_pars = urlparse(url)
    quer_v = parse_qs(u_pars.query).get('v')
    if quer_v:
        return quer_v[0]
    pth = u_pars.path.split('/')
    if pth:
        return pth[-1]


def save_to_csv(output_dict, filename):
    '''
    To save the comments + other columns to the CSV file specified with name
    '''
    if not output_dict['Comment']:
        print(f"No comments found for {filename}. Skipping CSV save.")
        return

    # Remove special characters from the filename
    safe_filename = re.sub(r'[<>:"/\\|?*]', '_', filename)

    try:
        output_df = pd.DataFrame(output_dict)
        if output_df.empty:
            print(f"DataFrame is empty for {safe_filename}. Skipping save.")
            return

        output_df.to_csv(f'./data/{safe_filename}.csv', index=False)
        print(f"Successfully saved comments to ./data/{safe_filename}.csv")
    except Exception as e:
        print(f"Error saving CSV for {safe_filename}: {e}")


def comments_helper(video_ID, api_key, service):
    '''
    To get all comments in the form of a dictionary containing:
    1. Comment ID
    2. Comment text
    3. Comment author
    4. Comment likes
    '''

    # Lists to store extracted data
    comments, commentsId, likesCount, authors = [], [], [], []

    # Fetch video title
    try:
        response_title = service.videos().list(
            part='snippet',
            id=video_ID
        ).execute()
        video_title = response_title['items'][0]['snippet']['title']
        print(f"Fetching comments for video: {video_title}")
    except Exception as e:
        print(f"Error fetching video title for video ID {video_ID}: {e}")
        return {}, ""

    # Initial API request to get comments
    try:
        response = service.commentThreads().list(
            part="snippet",
            videoId=video_ID,
            textFormat="plainText",
            maxResults=100
        ).execute()
    except Exception as e:
        print(f"Error fetching comments for video ID {video_ID}: {e}")
        return {}, video_title

    # Page number of comments
    page = 0

    # Fetch comments until there are no more pages
    while response:
        print(f"Processing page {page + 1}")
        page += 1

        # Extract comments from the response
        for item in response['items']:
            try:
                comment = item["snippet"]["topLevelComment"]
                author = comment["snippet"]["authorDisplayName"]
                text = comment["snippet"]["textDisplay"]
                comment_id = item['snippet']['topLevelComment']['id']
                like_count = item['snippet']['topLevelComment']['snippet']['likeCount']

                # Append the comment data to the lists
                comments.append(text)
                commentsId.append(comment_id)
                likesCount.append(like_count)
                authors.append(author)
            except Exception as e:
                print(f"Error parsing comment: {e}")

        # Check if there's a next page of comments
        if 'nextPageToken' in response:
            time.sleep(0.1)  # Add a small delay to avoid rate limiting
            try:
                response = service.commentThreads().list(
                    part="snippet",
                    videoId=video_ID,
                    textFormat="plainText",
                    pageToken=response['nextPageToken'],
                    maxResults=100
                ).execute()
            except Exception as e:
                print(f"Error fetching next page of comments for video ID {video_ID}: {e}")
                break
        else:
            # No more pages
            break

    print(f"Fetched {len(comments)} comments.")

    # Return the data as a dictionary and the video title
    return {
        'Comment': comments,
        'Author': authors,
        'Comment ID': commentsId,
        'Like Count': likesCount
    }, video_title
