import os
import json
import http.client
from datetime import datetime, timedelta
from pymongo import MongoClient
import time
from http.client import HTTPException
import argparse



# Retrieve API and MongoDB connection key from environment variables
API_KEY = os.getenv('RAPIDAPI_KEY')
db_con = os.getenv('DB_CONNECTION')


# Establish MongoDB connection
client = MongoClient(db_con)
db = client['instagram_analytics']
accounts_collection = db['accounts']
posts_collection = db['posts']


# Ensure API key is present
if not API_KEY:
    raise ValueError("API key is not set in environment variables")

def fetch_data(url, headers, max_retries=3):
    conn = http.client.HTTPSConnection("instagram-scraper-api2.p.rapidapi.com")
    attempts = 0
    while attempts < max_retries:
        try:
            conn.request("GET", url, headers=headers)
            response = conn.getresponse()
            if response.status == 200:
                return json.loads(response.read().decode("utf-8"))
            else:
                print(f"API error: {response.status} {response.reason}")
                time.sleep(2 ** attempts)  # Exponential backoff
                attempts += 1
        except HTTPException as e:
            print(f"HTTP error encountered: {e}")
            time.sleep(2 ** attempts)  # Exponential backoff
            attempts += 1
    raise Exception(f"Failed to fetch data after {max_retries} attempts")


# Function to save account data to MongoDB
def save_account_data_to_mongodb(account_data):
    run_time = datetime.utcnow().isoformat()
    composite_id = f"{account_data.get('username', 'N/A')}_{run_time.replace(':', '').replace('-', '').replace('.', '')}"

    account_document = {
        "_id": composite_id,
        "username": account_data.get('username', 'N/A'),
        "full_name": account_data.get('full_name', 'N/A'),
        "follower_count": account_data.get('follower_count', 'N/A'),
        "media_count": account_data.get('media_count', 'N/A'),
        "profile_link": f"https://www.instagram.com/{account_data.get('username', 'N/A')}/",
        "run_time": run_time
    }
    accounts_collection.insert_one(account_document)

# Function to save posts data to MongoDB
def save_posts_data_to_mongodb(posts_data, username):
    run_time = datetime.utcnow().isoformat()  # Common run time for all posts
    post_documents = []

    for post in posts_data:
        taken_at_unix = post.get('taken_at', None)
        taken_at_datetime = datetime.utcfromtimestamp(taken_at_unix).isoformat() + 'Z' if taken_at_unix else 'N/A'

        post_documents.append({
            "id": post.get('id', 'N/A'),
            "username": username,
            "code": post.get('code', 'N/A'),
            "taken_at": taken_at_datetime,
            "like_count": post.get('like_count', 'N/A'),
            "comment_count": post.get('comment_count', 'N/A'),
            "post_link": f"https://www.instagram.com/p/{post.get('code', 'N/A')}/",
            "run_time": run_time
        })

    if post_documents:
        posts_collection.insert_many(post_documents)  # Insert all posts at once

# Modified function to get all data and save it to MongoDB
def get_all_data(username, timeframe_days):
    print("Fetching data for", username)
    
    headers = {
        'x-rapidapi-key': API_KEY,
        'x-rapidapi-host': "instagram-scraper-api2.p.rapidapi.com"
    }
    
    # Get account information
    account_data_response = fetch_data(f"/v1/info?username_or_id_or_url={username}", headers)
    if 'data' in account_data_response:
        account_data = account_data_response['data']
        save_account_data_to_mongodb(account_data)
    else:
        print("Failed to retrieve account data for", username)
        return  # Exit if no account data is retrieved

    # Get posts with pagination and time filter
    all_posts = []
    pagination_token = None
    end_time = datetime.utcnow() - timedelta(days=timeframe_days)

    while True:
        url = f"/v1.2/posts?username_or_id_or_url={username}&pagination_token={pagination_token}" if pagination_token else f"/v1.2/posts?username_or_id_or_url={username}"
        posts_data_response = fetch_data(url, headers)
        if 'data' in posts_data_response and 'items' in posts_data_response['data']:
            posts = posts_data_response['data']['items']
        else:
            print("Failed to retrieve posts data or end of data for", username)
            break

        for post in posts:
            post_timestamp = datetime.utcfromtimestamp(post.get('taken_at', 0))
            if post_timestamp < end_time:
                break
            all_posts.append(post)
        
        pagination_token = posts_data_response.get('pagination_token')
        if pagination_token is None or post_timestamp < end_time:
            break

    if all_posts:
        save_posts_data_to_mongodb(all_posts, username)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Scrape Instagram data")
    parser.add_argument('username', type=str, help='Instagram username to scrape')
    parser.add_argument('timeframe_days', type=int, help='Timeframe in days to fetch posts')
    args = parser.parse_args()
    get_all_data(args.username, args.timeframe_days)