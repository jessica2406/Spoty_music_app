from pymongo import MongoClient

def get_db_connection():
    try:
        client = MongoClient('mongodb://localhost:27017/')
        db = client['spoty']  # Replace with your MongoDB database name
        print("Connected to MongoDB successfully!")
        return db
    except Exception as e:
        print(f"An error occurred while connecting to MongoDB: {e}")
        return None

def get_users_collection():
    """
    Returns the 'users' collection from the connected MongoDB database.
    """
    db = get_db_connection()
    if db:
        return db['users']
    else:
        return None

    
def get_playlist_collection():
    db = get_db_connection()
    return db['playlists']

