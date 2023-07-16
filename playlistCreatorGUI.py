import tkinter as tk
from tkinter import Listbox, MULTIPLE, Entry, StringVar
import spotipy
from spotipy.oauth2 import SpotifyOAuth
import os
from playlistData import get_playlist_tracks,get_lastfm_plays

# Create the main window
root = tk.Tk()

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

# Function to get all playlists
def get_all_playlists():
    username = sp.me()['id']
    offset = 0
    limit = 50
    playlist_names = []

    while True:
        # Retrieve the next set of playlists
        playlists = sp.user_playlists(user=username, limit=limit, offset=offset)

        # Add each playlist name to the list
        for playlist in playlists['items']:
            playlist_names.append(playlist['name'])

        # Check if there are more playlists to retrieve
        if playlists['next']:
            offset += limit
        else:
            break

    return playlist_names

# Get the playlists
playlists = get_all_playlists()

# Create a frame for the playlist selection widgets
playlist_frame = tk.Frame(root, padx=10, pady=10)
playlist_frame.pack()

# Add a label for the playlist list box
playlist_label = tk.Label(playlist_frame, text="Playlists:")
playlist_label.pack()

# Create a Listbox widget for the playlists
playlist_listbox = Listbox(playlist_frame, selectmode=MULTIPLE, width=50, height=10) # Set selectmode to MULTIPLE to allow multiple items to be selected

# Add each playlist to the Listbox
for playlist in playlists:
    playlist_listbox.insert(tk.END, playlist)

playlist_listbox.pack() # Add the Listbox to the window

# Create a StringVar for the minimum track count
min_track_count = StringVar()

# Create an Entry widget for the minimum track count
min_track_count_entry = Entry(playlist_frame, textvariable=min_track_count)
min_track_count_entry.pack() # Add the Entry to the window

# Create a frame for the track plays selection widgets
track_plays_frame = tk.Frame(root, padx=10, pady=10)
track_plays_frame.pack()

# Add a label for the track plays list box
track_plays_label = tk.Label(track_plays_frame, text="Track plays:")
track_plays_label.pack()

# Create a Listbox widget for the track plays
track_plays_listbox = Listbox(track_plays_frame, selectmode=MULTIPLE, width=50, height=10)
track_plays_listbox.pack()

tracks = []
track_plays = []

# Function to handle button click
def on_button_click():
    global tracks
    global track_plays

    # Get the indices of the selected playlists
    selected_indices = playlist_listbox.curselection()

    # Get the selected playlists
    selected_playlists = [playlists[i] for i in selected_indices]

    # Get the minimum track count
    min_track_count_value = int(min_track_count.get())  # Convert the value to int

    # Get the tracks from the selected playlists
    tracks = get_playlist_tracks(selected_playlists)

    # Get the Last.fm plays for the tracks
    track_plays = get_lastfm_plays(tracks, min_plays=min_track_count_value)

    # Clear the track plays Listbox
    track_plays_listbox.delete(0, tk.END)

    # Sort the track plays by playcount (assumed to be the third element of each item)
    track_plays.sort(key=lambda x: x[2], reverse=True)

    # Add each track play to the Listbox
    for track_play in track_plays:
        track_name, artist_name, plays = track_play[0], track_play[1], track_play[2]
        track_plays_listbox.insert(tk.END, f"{track_name} by {artist_name} - {plays} plays")

# Create a Button widget that will print the selected playlists and minimum track count when clicked
button = tk.Button(track_plays_frame, text="Get track plays", command=on_button_click)
button.pack()  # Add the Button to the window

# Create a StringVar for the playlist name
playlist_name = StringVar()

# Create an Entry widget for the playlist name
playlist_name_entry = Entry(root, textvariable=playlist_name)
playlist_name_entry.pack()  # Add the Entry to the window

# Function to handle button click
def on_create_playlist_button_click():
    # Get the indices of the selected track plays
    selected_indices = track_plays_listbox.curselection()

    # Get the selected track plays
    selected_track_plays = [track_plays[i] for i in selected_indices]

    # Get the track IDs
    track_ids = [track_play[3] for track_play in selected_track_plays]

    # Get the playlist name
    playlist_name_value = playlist_name.get()

    # Create a new playlist
    username = sp.me()['id']
    playlist = sp.user_playlist_create(user=username, name=playlist_name_value)

    # Add the tracks to the playlist
    sp.playlist_add_items(playlist_id=playlist['id'], items=track_ids)

    print(f'Playlist "{playlist_name_value}" created with the selected tracks.')

# Create a Button widget that will create a new playlist with the selected track plays when clicked
create_playlist_button = tk.Button(root, text="Create playlist", command=on_create_playlist_button_click)
create_playlist_button.pack()  # Add the Button to the window

root.mainloop() # Start the Tkinter event loop
