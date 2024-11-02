from appwrite.client import Client
from appwrite.services.databases import Databases
from appwrite.services.users import Users
from appwrite.services.storage import Storage
from appwrite.query import Query
import os
from dotenv import load_dotenv
from models import User  # Add this import at the top

# Load environment variables
load_dotenv()

# Initialize Appwrite client
client = Client()
client.set_endpoint(os.getenv('APPWRITE_ENDPOINT'))
client.set_project(os.getenv('APPWRITE_PROJECT_ID'))
client.set_key(os.getenv('APPWRITE_API_KEY'))

databases = Databases(client)
users = Users(client)
storage = Storage(client)

DATABASE_ID = os.getenv('APPWRITE_DATABASE_ID')
USERS_COLLECTION_ID = os.getenv('APPWRITE_USERS_COLLECTION_ID')
QR_CODES_COLLECTION_ID = os.getenv('APPWRITE_QR_CODES_COLLECTION_ID')
STORAGE_BUCKET_ID = os.getenv('APPWRITE_STORAGE_BUCKET_ID')

def create_user(user_id, email, name, picture=None):  # Add picture parameter
    try:
        print(f"Attempting to create user with email: {email}, name: {name}")
        
        user_data = {
            'email': email,
            'name': name,
            'picture': picture  # Add picture to user data
        }
        
        response = databases.create_document(
            database_id=DATABASE_ID,
            collection_id=USERS_COLLECTION_ID,
            document_id='unique()',
            data=user_data
        )
        
        print(f"Created user document: {response}")
        
        return User(
            doc_id=response['$id'],
            email=email,
            name=name,
            picture=picture
        )
    except Exception as e:
        print(f"Error in create_user: {str(e)}")
        return None

def get_user(email):
    try:
        print(f"Attempting to get user with email: {email}")
        response = databases.list_documents(
            database_id=DATABASE_ID,
            collection_id=USERS_COLLECTION_ID,
            queries=[
                Query.equal('email', email)
            ]
        )
        
        if response['documents']:
            doc = response['documents'][0]
            print(f"Found user document: {doc}")
            return User(
                doc_id=doc['$id'],
                email=doc['email'],
                name=doc['name'],
                picture=doc.get('picture')  # Get picture if it exists
            )
        return None
    except Exception as e:
        print(f"Error getting user: {str(e)}")
        return None

def update_user(user_id, email, name, picture=None):  # Add picture parameter
    try:
        response = databases.list_documents(
            database_id=DATABASE_ID,
            collection_id=USERS_COLLECTION_ID,
            queries=[
                Query.equal('email', email)
            ]
        )
        
        if response['documents']:
            doc = response['documents'][0]
            updated = databases.update_document(
                database_id=DATABASE_ID,
                collection_id=USERS_COLLECTION_ID,
                document_id=doc['$id'],
                data={
                    'name': name,
                    'email': email,
                    'picture': picture  # Add picture to update data
                }
            )
            
            return User(
                doc_id=updated['$id'],
                email=email,
                name=name,
                picture=picture
            )
        return None
    except Exception as e:
        print(f"Error in update_user: {str(e)}")
        return None

def create_qr_code(user_id, link, file_id):
    try:
        document = databases.create_document(
            database_id=DATABASE_ID,
            collection_id=QR_CODES_COLLECTION_ID,
            document_id='unique()',
            data={
                'user_id': user_id,
                'link': link,
                'file_id': file_id
            }
        )
        return document
    except Exception as e:
        print(f"Error creating QR code record: {str(e)}")
        return None

def get_user_qr_codes(user_id):
    try:
        documents = databases.list_documents(
            database_id=DATABASE_ID,
            collection_id=QR_CODES_COLLECTION_ID,
            queries=[Query.equal('user_id', user_id)]
        )
        return documents['documents']
    except Exception as e:
        print(f"Error getting user QR codes: {str(e)}")
        return []

def delete_qr_code(document_id):
    try:
        databases.delete_document(
            database_id=DATABASE_ID,
            collection_id=QR_CODES_COLLECTION_ID,
            document_id=document_id
        )
        return True
    except Exception as e:
        print(f"Error deleting QR code: {str(e)}")
        return False

def get_qr_code(document_id):
    try:
        document = databases.get_document(
            database_id=DATABASE_ID,
            collection_id=QR_CODES_COLLECTION_ID,
            document_id=document_id
        )
        return document
    except Exception as e:
        print(f"Error getting QR code: {str(e)}")
        return None

def upload_qr_image(image_bytes, filename):
    try:
        print(f"Attempting to upload QR image with filename: {filename}")
        
        from appwrite.input_file import InputFile
        input_file = InputFile.from_bytes(image_bytes, filename)
        
        result = storage.create_file(
            bucket_id=STORAGE_BUCKET_ID,
            file_id='unique()',
            file=input_file
        )
        
        print(f"Successfully uploaded file: {result}")
        return result
        
    except Exception as e:
        print(f"Error uploading QR image: {str(e)}")
        return None

def get_qr_image(file_id):
    try:
        file = storage.get_file_view(
            bucket_id=STORAGE_BUCKET_ID,
            file_id=file_id
        )
        return file
    except Exception as e:
        print(f"Error getting QR image: {str(e)}")
        return None

def delete_qr_image(file_id):
    try:
        storage.delete_file(
            bucket_id=STORAGE_BUCKET_ID,
            file_id=file_id
        )
        return True
    except Exception as e:
        print(f"Error deleting QR image: {str(e)}")
        return False
