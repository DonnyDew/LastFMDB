import requests
import os
import mysql.connector
import keyring
from typing import Dict
from datetime import datetime

# Constants
API_KEY = os.environ["LASTFM_API_KEY"]
USER = "DonnyDew"

# Database config
config = {
    'user': 'root',
    'password': keyring.get_password("MySQL", "DonnyDew"),
    'host': 'localhost',
    'database': 'lastfm_data',  # add the database name here
}

def lastfm_get(payload: Dict) -> Dict:
    # define headers and URL
    headers = {'user-agent': USER}
    url = 'http://ws.audioscrobbler.com/2.0/'

    # Add API key and format to the payload
    payload['api_key'] = API_KEY
    payload['format'] = 'json'

    response = requests.get(url, headers=headers, params=payload)
    return response.json()

def fetch_all_tracks(user: str, from_timestamp: int = None, limit: int = 200, page: int = 1, tracks: Dict = {}, tracks_individual: list = []) -> Dict:
    """
    Function to recursively fetch all tracks played by a user.
    """
    payload = {
        'method': 'user.getRecentTracks',
        'user': user,
        'limit': limit,
        'page': page
    }

    # Only fetch tracks after a certain timestamp
    if from_timestamp:
        payload['from'] = from_timestamp

    # API request to fetch recent tracks
    response = lastfm_get(payload)

    # Check that 'recenttracks' is in the response
    if 'recenttracks' not in response:
        print(f"Error: 'recenttracks' not in response. Full response: {response}")
        return tracks, tracks_individual

    # Process each track
    for track in response['recenttracks']['track']:
        track_name = track['name']
        artist_name = track['artist']['#text']
        track_mbid = track.get('mbid', '')
        album_mbid = track.get('album', {}).get('mbid', '')
        track_id = (track_name, artist_name)

        # If track is already in the dict, increment its count
        if track_id in tracks:
            tracks[track_id] += 1
        else:
            tracks[track_id] = 1

        # Add track to the individual list
        playtime = track.get('date', {}).get('uts', '')
        if playtime:  # check if playtime is not an empty string
            play_date = datetime.fromtimestamp(int(playtime)).strftime("%Y-%m-%d")
            play_hour = datetime.fromtimestamp(int(playtime)).strftime("%H:%M:%S")
        else:  # if playtime is an empty string, set play_date and play_hour to empty strings as well
            play_date = None
            play_hour = None
        tracks_individual.append((track_name, artist_name, playtime, play_date, play_hour, track_mbid, album_mbid))


    # If there are more pages, fetch the next one
    if int(response['recenttracks']['@attr']['totalPages']) > page:
        tracks, tracks_individual = fetch_all_tracks(user, from_timestamp, limit, page + 1, tracks, tracks_individual)

    return tracks, tracks_individual

# Connect to the database
cnx = mysql.connector.connect(**config)
cursor = cnx.cursor()

# Create tables if they do not exist
cursor.execute(
    """
    CREATE TABLE IF NOT EXISTS track_plays (
    Track VARCHAR(255),
    Artist VARCHAR(255),
    PlayCount INT,
    PRIMARY KEY (Track, Artist)
    );
    """
)
cursor.execute(
    """
    CREATE TABLE IF NOT EXISTS individual_track_plays (
    Track VARCHAR(255),
    Artist VARCHAR(255),
    PlayTime BIGINT,
    PlayDate DATE,
    PlayHour TIME,
    TrackMBID VARCHAR(255),
    AlbumMBID VARCHAR(255),
    PRIMARY KEY (Track, Artist, PlayTime)
    );
    """
)

# Get the timestamp of the most recent play in the database
cursor.execute("SELECT MAX(PlayTime) FROM individual_track_plays;")
result = cursor.fetchone()
from_timestamp = result[0] if result else None

# If there is a most recent play, fetch tracks from 5 minutes before it
if from_timestamp:
    from_timestamp -= 5 * 60  # subtract 5 minutes in seconds

# Fetch all tracks
tracks, tracks_individual = fetch_all_tracks(USER, from_timestamp)

# Insert or update each track in the database
for (track, artist), playcount in tracks.items():
    data = (track, artist, playcount, playcount)
    cursor.execute("INSERT INTO track_plays (Track, Artist, PlayCount) VALUES (%s, %s, %s) ON DUPLICATE KEY UPDATE PlayCount = %s", data)

# Insert each individual play into the database
for (track, artist, playtime, play_date, play_hour, track_mbid, album_mbid) in tracks_individual:
    data = (track, artist, playtime, play_date, play_hour, track_mbid, album_mbid)
    cursor.execute("INSERT IGNORE INTO individual_track_plays (Track, Artist, PlayTime, PlayDate, PlayHour,TrackMBID, AlbumMBID) VALUES (%s, %s, %s, %s, %s, %s, %s)", data)

# Commit changes and close connection
cnx.commit()
cursor.close()
cnx.close()

print("Script Done")
