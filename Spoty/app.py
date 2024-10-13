from flask import Flask, jsonify, send_from_directory, request, render_template, url_for, redirect, session, flash
from db_connect import get_db_connection
from werkzeug.security import generate_password_hash, check_password_hash
from bson.objectid import ObjectId
from functools import wraps
import os

app = Flask(__name__)
app.secret_key = "abc"

db = get_db_connection()
users = db['users']
artists = db['artists']


# Home Page
@app.route("/")
def index():
    return render_template("index.html")


# User Registration Route
@app.route("/register-user", methods=["GET", "POST"])
def register_user():
    if request.method == "POST":
        users_collection = db.users
        name = request.form.get("name")
        email = request.form.get("email")
        phone = request.form.get("phone")
        password = request.form.get("password")

        # Check if email already exists
        if users_collection.find_one({"email": email}):
            return jsonify({"message": "Email already registered!"}), 400

        # Hash password and store user data
        hashed_password = generate_password_hash(password)
        user_data = {
            "name": name,
            "email": email,
            "phone": phone,
            "password": hashed_password,
        }
        users_collection.insert_one(user_data)

        return redirect(url_for("login"))

    return render_template("./user/register_user.html")


# Artist Registration Route
@app.route("/register-artist", methods=["GET", "POST"])
def register_artist():
    if request.method == "POST":
        artists_collection = db.artists
        name = request.form.get("name")
        email = request.form.get("email")
        phone = request.form.get("phone")
        password = request.form.get("password")

        # Check if email already exists
        if artists_collection.find_one({"email": email}):
            return jsonify({"message": "Email already registered!"}), 400

        # Hash password and store artist data
        hashed_password = generate_password_hash(password)
        artist_data = {
            "name": name,
            "email": email,
            "phone": phone,
            "password": hashed_password,
            "songs": []  
        }
        artists_collection.insert_one(artist_data)

        return redirect(url_for("login"))

    return render_template("./artist/register_artist.html")

#Dual login
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        # Identify which form is submitted
        if 'email1' in request.form:
            # User login form submitted
            users_collection = db.users
            email = request.form.get("email1")
            password = request.form.get("password1")

            # Fetch user by email
            user = users_collection.find_one({"email": email})

            if not user or not check_password_hash(user["password"], password):
                return jsonify({"message": "Invalid user email or password!"}), 400

            # Set session and redirect to user dashboard
            session["user_name"] = user["name"]
            return redirect(url_for("user_dashboard"))

        elif 'email2' in request.form:
            # Artist login form submitted
            artists_collection = db.artists
            banned_users_collection = db.banned_users  # Collection for banned artists
            email = request.form.get("email2")
            password = request.form.get("password2")

            # Fetch artist by email
            artist = artists_collection.find_one({"email": email})

            # Check if the artist is banned
            if banned_users_collection.find_one({"email": email}):
                # Redirect banned artists to banned page
                return redirect(url_for("artist_banned"))  # Redirect to the banned page

            # If artist not found or password incorrect
            if not artist:
                return jsonify({"message": "Invalid artist email!"}), 400
            if not check_password_hash(artist["password"], password):
                return jsonify({"message": "Invalid artist password!"}), 400

            # Set session and redirect to artist dashboard
            session["artist_email"] = artist["email"]  # Set session for artist
            session["artist_name"] = artist["name"]
            return redirect(url_for("artist_dashboard"))

    return render_template("login/login.html")  # Combined login form
@app.route("/artist_banned")
def artist_banned():
    return render_template("artist/artist_banned.html")  # Render the banned artist page


# User Dashboard
@app.route("/user-dashboard")
def user_dashboard():
    # Check if the user is logged in, if not, redirect to the login page
    if "user_name" not in session:
        return redirect(url_for("login"))

    # Fetch all songs from the artists collection
    artists_collection = db.artists
    all_songs = []
    
    # Fetch the user's playlists from the playlists collection
    playlists_collection = db.playlists
    user_playlists = playlists_collection.find({"user_name": session["user_name"]})

    # Fetch all artists and their songs
    artists = artists_collection.find({})
    artist_list = []
    for artist in artists:
        artist_list.append({
            "_id": artist["_id"],
            "name": artist["name"],
            "songs": artist.get("songs", [])
        })

    # Iterate through each artist and extract their songs
    for artist in artist_list:
        all_songs.extend(artist["songs"])

    # Render the user dashboard with the user's name, songs, playlists, and artist list
    return render_template("./user/user_dashboard.html", 
                           user_name=session["user_name"], 
                           songs=all_songs, 
                           playlists=user_playlists,
                           artists=artist_list)  # Pass the list of artists to the template

@app.route("/artist/<artist_id>")
def artist_page(artist_id):
    # Fetch the artist's data from the artists collection
    artists_collection = db.artists
    artist = artists_collection.find_one({"_id": ObjectId(artist_id)})

    if not artist:
        return "Artist not found", 404

    # Get the songs for the artist
    songs = artist.get("songs", [])

    # Render the artist page with the artist's name and songs
    return render_template("user/artist.html", 
                           artist_name=artist["name"], 
                           songs=songs)



@app.route("/create_playlist", methods=["GET", "POST"])
def create_playlist():
    # Check if the user is logged in
    if "user_name" not in session:
        return redirect(url_for("login"))

    # Fetch all songs from the artists collection
    artists_collection = db.artists
    all_songs = []
    
    # Fetch the user's playlists from the playlists collection
    playlists_collection = db.playlists

    # Iterate through each artist and extract their songs
    artists = artists_collection.find({})
    for artist in artists:
        all_songs.extend(artist.get("songs", []))

    if request.method == "POST":
        playlist_name = request.form.get("playlist_name")
        selected_songs = request.form.getlist("selected_songs")  # Retrieve selected songs
        
        # Prepare songs in the format {'title': title, 'src': src}
        formatted_songs = []
        for song in selected_songs:
            title, src = song.split("|")  # Split the value to get title and src
            formatted_songs.append({"title": title, "src": src})

        # Create a new playlist document
        new_playlist = {
            "user_name": session["user_name"],
            "name": playlist_name,
            "songs": formatted_songs  # Store the formatted songs
        }

        # Insert the new playlist into the collection
        playlists_collection.insert_one(new_playlist)

        return redirect(url_for("user_dashboard"))

    return render_template("user/create_playlist.html", songs=all_songs)

@app.route("/playlist/<playlist_id>")
def view_playlist(playlist_id):
    # Check if the user is logged in
    if "user_name" not in session:
        return redirect(url_for("login"))

    # Fetch the playlist from the database using the playlist_id
    playlists_collection = db.playlists
    playlist = playlists_collection.find_one({"_id": ObjectId(playlist_id)})

    if not playlist:
        return "Playlist not found", 404

    return render_template("user/view_playlist.html", playlist=playlist)

# Artist Dashboard
@app.route("/artist-dashboard")
def artist_dashboard():
    if "artist_email" not in session:
        return redirect(url_for("login"))

    artists_collection = db.artists  # Assuming you have a collection named "artists"

    # Fetch the logged-in artist
    artist = artists_collection.find_one({"email": session["artist_email"]})

    if not artist:
        return redirect(url_for("login"))

    # Check if the artist is banned
    if artist.get("banned", False):
        # Notify the artist and allow them to send a query to the admin
        return render_template("artist/artist_banned.html", artist_name=artist["name"])

    # Fetch all songs from the artist
    all_songs = artist.get("songs", [])

    return render_template("artist/artist_dashboard.html", 
                           artist_name=artist["name"], 
                           songs=all_songs)


# Route for submitting a query to the admin if the artist is banned
@app.route("/send-query", methods=["POST"])
def send_query():
    # Check if the artist is logged in
    if "artist_email" not in session:
        return redirect(url_for("login"))

    query = request.form.get("query")
    artist_email = session["artist_email"]

    # Insert the query into the "queries" collection
    queries_collection = db.queries
    queries_collection.insert_one({
        "artist_email": artist_email,
        "query": query,
        "status": "pending"
    })

    # Flash a success message
    flash("Your query has been sent successfully. The admin will resolve it shortly.", "success")

    # Redirect to the Banned Artist page
    return redirect(url_for("artist_banned"))


@app.route("/artist-songs")
def artist_songs():
    if "artist_email" not in session:
        return redirect(url_for("login"))

    artists_collection = db.artists  # Assuming you have a collection named "artists"
    artist = artists_collection.find_one({"email": session["artist_email"]})

    if not artist:
        return redirect(url_for("login"))

    artist_songs = artist.get("songs", [])  # Assuming the songs are stored under the "songs" field

    return render_template("artist/artist_songs.html", artist_name=artist["name"], songs=artist_songs)

@app.route("/add-song", methods=["POST"])
def add_song():
    if "artist_email" not in session:
        return redirect(url_for("login"))

    song_title = request.form['title']
    song_file = request.files['song_file']

    # Save the file to the static/songs folder
    songs_folder = "static/songs/"
    if not os.path.exists(songs_folder):
        os.makedirs(songs_folder)

    song_file_path = os.path.join(songs_folder, song_file.filename)
    song_file.save(song_file_path)

    # Create the song object with a unique _id
    new_song = {
        "_id": ObjectId(),  # Generate a unique ID for the song
        "title": song_title,
        "src": song_file_path
    }

    # Update the artist's document in the database
    artists_collection = db.artists
    artists_collection.update_one(
        {"email": session["artist_email"]},
        {"$push": {"songs": new_song}}
    )

    return redirect(url_for("artist_dashboard"))

@app.route("/edit-song/<song_id>", methods=["POST"])
def edit_song(song_id):
    if "artist_email" not in session:
        return jsonify({"error": "Unauthorized access"}), 403

    new_title = request.json.get("new_title")

    if not new_title:
        return jsonify({"error": "Invalid song title"}), 400

    # Find the artist by email and update the song title by song_id
    artists_collection = db.artists
    result = artists_collection.update_one(
        {"email": session["artist_email"], "songs._id": ObjectId(song_id)},
        {"$set": {"songs.$.title": new_title}}
    )

    if result.modified_count == 1:
        return jsonify({"message": "Song title updated successfully!"}), 200
    else:
        return jsonify({"error": "Song not found or update failed!"}), 404


@app.route("/delete-song/<song_id>", methods=["DELETE"])
def delete_song(song_id):
    if "artist_email" not in session:
        return jsonify({"error": "Unauthorized access"}), 403

    # Find the artist by email and remove the song by song_id
    artists_collection = db.artists
    result = artists_collection.update_one(
        {"email": session["artist_email"]},
        {"$pull": {"songs": {"_id": ObjectId(song_id)}}}
    )

    if result.modified_count == 1:
        return jsonify({"message": "Song deleted successfully!"}), 200
    else:
        return jsonify({"error": "Song not found or deletion failed!"}), 404
    

#Logout Route
@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.route("/logedout", methods=["GET"])
def logedout():
    return jsonify({"message": "Logged out successfully!"}), 200


@app.route("/admin-login", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        # Get the form data
        email = request.form.get('email')
        password = request.form.get('password')

        # Check against predefined static credentials
        if email == "admin@gmail.com" and password == "admin":
            # Set session variable to indicate admin is logged in
            session['admin_logged_in'] = True
            return redirect(url_for("admin_artist"))  # Redirect to admin artist page
        else:
            return render_template("admin/admin_login.html", error="Incorrect email or password.")  # Show error message

    return render_template("admin/admin_login.html") 

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'admin_logged_in' not in session:
            return redirect(url_for('admin_login'))
        return f(*args, **kwargs)
    return decorated_function

@app.route("/admin-artist")
@login_required
def admin_artist():
    artists_collection = db.artists
    banned_artists_collection = db.banned_users

    # Fetch active artists
    artists = list(artists_collection.find({}))
    for artist in artists:
        artist['_id'] = str(artist['_id'])

    # Fetch banned artists
    banned_artists = list(banned_artists_collection.find({}))
    for banned_artist in banned_artists:
        banned_artist['_id'] = str(banned_artist['_id'])  # Convert ObjectId to string if needed

    # Render template with both active and banned artists
    return render_template("admin/admin_artist.html", artists=artists, banned_artists=banned_artists)

@app.route("/admin-artist-songs/<string:artist_id>", methods=["POST"])
@login_required
def admin_artist_songs(artist_id):
    artists_collection = db.artists
    
    try:
        artist = artists_collection.find_one({"_id": ObjectId(artist_id)})
    except Exception as e:
        print(f"Error: {e}")
        artist = None

    songs = artist.get("songs", []) if artist else []

    for song in songs:
        song['_id'] = str(song.get('_id', ''))

    print(songs)

    return render_template("admin/admin_artist_songs.html", songs=songs)

@app.route('/banArtist', methods=['POST'])
def ban_artist():
    data = request.get_json()
    artist_email = data.get('artistEmail')

    if artist_email:
        # Remove artist from the artists collection
        artists_collection = db.artists
        banned_artists_collection = db.banned_users
        
        # Find the artist to ban
        artist = artists_collection.find_one({"email": artist_email})

        if artist:
            # Remove artist from the artists collection
            artists_collection.delete_one({"email": artist_email})

            # Insert artist into banned_users collection
            banned_artists_collection.insert_one(artist)

            # Optionally, you could flash a message or return a response
            return jsonify({"message": "Artist banned successfully"}), 200
        else:
            return jsonify({"error": "Artist not found"}), 404

    return jsonify({"error": "No artist email provided"}), 400



# Admin view to see banned users and their queries
@app.route('/admin/banned-artists')
def admin_banned_artists():
    # Fetch all banned artists and their queries
    banned_artists = list(db.banned_users.find({}))
    
    return render_template('admin/banned_artists.html', banned_artists=banned_artists)


# Admin can unban artist
@app.route('/unbanArtist', methods=['POST'])
def unban_artist():
    data = request.get_json()
    artist_email = data.get('artistEmail')

    if artist_email:
        banned_artists_collection = db.banned_users
        artists_collection = db.artists
        
        # Find the banned artist
        banned_artist = banned_artists_collection.find_one({"email": artist_email})

        if banned_artist:
            # Remove the artist from the banned_users collection
            banned_artists_collection.delete_one({"email": artist_email})
            artists_collection.insert_one(banned_artist)

            return jsonify({"message": "Artist unbanned successfully"}), 200
        else:
            return jsonify({"error": "Artist not found in banned list"}), 404

    return jsonify({"error": "No artist email provided"}), 400

@app.route("/admin/queries")
def admin_queries():
    # Fetch all queries from the "queries" collection
    queries_collection = db.queries
    queries = list(queries_collection.find())  # Convert cursor to a list

    return render_template("admin/queries.html", queries=queries)


@app.route("/admin-users")
@login_required
def admin_users():
    users_collection = db.users
    users = list(users_collection.find({}))
    
    for user in users:
        user['_id'] = str(user['_id'])
    
    return render_template("admin/admin_users.html", users=users)



if __name__ == "__main__":
    app.run(debug=True)