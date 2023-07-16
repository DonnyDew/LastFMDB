import spotipy
from spotipy.oauth2 import SpotifyOAuth
import os
from fuzzywuzzy import fuzz
import mysql.connector
import keyring

# Set up Spotify API client
SPOTIPY_CLIENT_ID = str(os.environ.get('SPOTIPY_CLIENT_ID'))
SPOTIPY_CLIENT_SECRET = str(os.environ.get('SPOTIPY_CLIENT_SECRET'))
SPOTIPY_REDIRECT_URI = str(os.environ.get('SPOTIPY_REDIRECT_URI'))

# Create an instance of the Spotify client credentials manager
client_credentials_manager = SpotifyOAuth(client_id=SPOTIPY_CLIENT_ID,
                                          client_secret=SPOTIPY_CLIENT_SECRET,
                                          redirect_uri=SPOTIPY_REDIRECT_URI,
                                          scope='playlist-read-private user-read-private')

# Create a Spotipy client using the client credentials manager
sp = spotipy.Spotify(auth_manager=client_credentials_manager)

def get_playlist_tracks(playlist_names):
    username = sp.me()['id']
    offset = 0
    limit = 50
    playlist_ids = []

    while True:
        # Retrieve the next set of playlists
        playlists = sp.user_playlists(user=username, limit=limit, offset=offset)

        # Find playlists with the specified names
        for playlist in playlists['items']:
            if playlist['name'] in playlist_names:
                playlist_ids.append(playlist['id'])

        # Check if there are more playlists to retrieve
        if playlists['next']:
            offset += limit
        else:
            break

    # Get the tracks from these playlists
    tracks = []
    for playlist_id in playlist_ids:
        playlist_tracks = sp.playlist_tracks(playlist_id)
        
        for item in playlist_tracks['items']:
            track = item['track']
            if track:
                track_name = track.get('name', 'Unknown Track')
                artist_name = track['artists'][0]['name'] if track['artists'] else 'Unknown Artist'
                track_id = track.get('id')
            else:
                track_name = 'Unknown Track'
                artist_name = 'Unknown Artist'
                track_id = None
            tracks.append((track_name, artist_name, track_id))

    return tracks


def get_lastfm_plays(tracks, min_similarity=90, min_plays=10):
    # Connect to the database
    cnx = mysql.connector.connect(user='root', password=keyring.get_password("MySQL", "DonnyDew"), host='localhost', database='lastfm_data')
    cursor = cnx.cursor()

    # Prepare the SQL query
    query = "SELECT Track, Artist, PlayCount FROM track_plays;"

    # Execute the SQL query
    cursor.execute(query)

    # Fetch all tracks from the database
    lastfm_tracks = cursor.fetchall()

    # Close the database connection
    cursor.close()
    cnx.close()

    # Match each Spotify track with a Last.fm track
    track_plays = []
    for track_name, artist_name,track_id in tracks:
        for lastfm_track_name, lastfm_artist_name, play_count in lastfm_tracks:
            # Calculate the similarity between the Spotify track and the Last.fm track
            track_similarity = fuzz.ratio(track_name.lower(), lastfm_track_name.lower())
            artist_similarity = fuzz.ratio(artist_name.lower(), lastfm_artist_name.lower())
            similarity = (track_similarity + artist_similarity) / 2  # Average similarity

            # If the similarity is above the threshold and play count is above the minimum, add the track to the list
            if similarity >= min_similarity and play_count >= min_plays:
                track_plays.append((track_name, artist_name, play_count,track_id))
                break  # Stop searching after finding a match

    return track_plays


tracks = get_playlist_tracks(["June 2020"])
track_plays = get_lastfm_plays(tracks)


