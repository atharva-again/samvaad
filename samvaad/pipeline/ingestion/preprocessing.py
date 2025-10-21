from samvaad.utils.filehash_db import init_db, file_exists, add_file
from samvaad.utils.hashing import generate_file_id


# This function can be extended for more preprocessing steps

def preprocess_file(contents: bytes, filename: str) -> bool:
    """
    Returns True if file is a duplicate (file_id exists), False otherwise.
    Initializes DB if needed. Also records file metadata if not duplicate.
    """
    init_db()
    file_id = generate_file_id(contents)
    if file_exists(file_id):
        return True
    return False

def update_file_metadata_db(contents: bytes, filename: str):
    file_id = generate_file_id(contents)
    add_file(file_id, filename)
