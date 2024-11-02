import os
import qrcode
import io
import base64
from flask import Flask, redirect, url_for, render_template, request, send_file, session
from flask_dance.contrib.google import make_google_blueprint, google
from flask_dance.consumer import oauth_authorized
from flask_dance.consumer.storage.session import SessionStorage
from oauthlib.oauth2.rfc6749.errors import TokenExpiredError
from dotenv import load_dotenv
from appwrite.client import Client
from appwrite.services.databases import Databases
from appwrite.services.users import Users
from appwrite.services.storage import Storage

from database import (
    create_user, get_user, update_user, 
    create_qr_code, get_user_qr_codes, 
    upload_qr_image, get_qr_image, delete_qr_code, delete_qr_image,
    get_qr_code  
)
from models import User, QRCode

load_dotenv()

os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'

DATABASE_ID = os.getenv('APPWRITE_DATABASE_ID')
USERS_COLLECTION_ID = os.getenv('APPWRITE_USERS_COLLECTION_ID')
QR_CODES_COLLECTION_ID = os.getenv('APPWRITE_QR_CODES_COLLECTION_ID')
STORAGE_BUCKET_ID = os.getenv('APPWRITE_STORAGE_BUCKET_ID')

# print(f"Database ID: {DATABASE_ID}")
# print(f"Users Collection ID: {USERS_COLLECTION_ID}")
# print(f"Storage Bucket ID: {STORAGE_BUCKET_ID}")

app = Flask(__name__, static_folder='static')
app.secret_key = os.getenv("FLASK_SECRET_KEY", "supersekrit")
app.config["GOOGLE_OAUTH_CLIENT_ID"] = os.getenv("GOOGLE_OAUTH_CLIENT_ID")
app.config["GOOGLE_OAUTH_CLIENT_SECRET"] = os.getenv("GOOGLE_OAUTH_CLIENT_SECRET")

client = Client()
client.set_endpoint(os.getenv('APPWRITE_ENDPOINT'))
client.set_project(os.getenv('APPWRITE_PROJECT_ID'))
client.set_key(os.getenv('APPWRITE_API_KEY'))

databases = Databases(client)
users = Users(client)
storage = Storage(client)

# print("Setting up storage bucket...")

try:
    
    storage.create_bucket(
        bucket_id=STORAGE_BUCKET_ID,  
        name='QR Codes',
        permissions=['read("any")', 'write("any")'],
        file_security=False,  
        enabled=True,
        maximum_file_size=10485760,  # 10MB
        allowed_file_extensions=['png']  
    )
    print("Storage bucket created successfully")
except Exception as e:
    print(f"Bucket setup error (might already exist): {str(e)}")

try:
    bucket = storage.get_bucket(bucket_id=STORAGE_BUCKET_ID)
    print(f"Verified bucket exists: {bucket['$id']}")
except Exception as e:
    print(f"Error verifying bucket: {str(e)}")

google_bp = make_google_blueprint(
    client_id=app.config["GOOGLE_OAUTH_CLIENT_ID"],
    client_secret=app.config["GOOGLE_OAUTH_CLIENT_SECRET"],
    scope=[
        "https://www.googleapis.com/auth/userinfo.email",
        "https://www.googleapis.com/auth/userinfo.profile",
        "openid"
    ],
)
app.register_blueprint(google_bp, url_prefix="/login")

@app.route("/")
def index():
    if not google.authorized:
        return redirect(url_for("login"))
    return redirect(url_for("dashboard"))

@app.route("/login")
def login():
    return render_template("login.html")

@app.route("/dashboard", methods=["GET", "POST"])
def dashboard():
    try:
        if not google.authorized:
            return redirect(url_for("login"))
        
        try:
            resp = google.get("/oauth2/v2/userinfo")
        except TokenExpiredError:
            del google.token
            session.clear()
            return redirect(url_for("login"))
            
        assert resp.ok, resp.text
        user_info = resp.json()
        
        try:
            user = get_user(user_info['email'])
            if not user:
                print(f"Creating new user with email: {user_info['email']}")
                user = create_user(
                    user_info['id'],
                    user_info['email'],
                    user_info['name'],
                    user_info.get('picture') 
                )
            else:
                print(f"Updating existing user with email: {user_info['email']}")
                user = update_user(
                    user_info['id'],
                    user_info['email'],
                    user_info['name'],
                    user_info.get('picture')  
                )
            
            if not user:
                print("User creation/update failed - user object is None")
                return "Error creating/updating user account. Please try again.", 400

            qr_codes = get_user_qr_codes(user.doc_id)  
            
            if request.method == "POST":
                link = request.form.get("link")
                fill_color = request.form.get("fill_color", "#000000")
                transparent_bg = request.form.get("transparent_bg")
                box_size = int(request.form.get("box_size", 10))
                
                if link:
                    qr = qrcode.QRCode(version=1, box_size=box_size, border=4)
                    qr.add_data(link)
                    qr.make(fit=True)
                    
                    bg_color = "transparent" if transparent_bg else request.form.get("bg_color", "#ffffff")
                    img = qr.make_image(fill_color=fill_color, back_color=bg_color)
                    
                    buffered = io.BytesIO()
                    img.save(buffered, format="PNG")
                    img_str = base64.b64encode(buffered.getvalue()).decode()
                    
                    return render_template(
                        "dashboard.html",
                        user=user,
                        qr_image=img_str
                    )

            return render_template("dashboard.html", user=user)

        except Exception as e:
            print(f"Detailed error in dashboard route: {str(e)}")
            print(f"Error type: {type(e)}")
            if isinstance(e, TokenExpiredError):
                del google.token
                session.clear()
                return redirect(url_for("login"))
            return f"An error occurred: {str(e)}", 400

    except Exception as e:
        print(f"Detailed error in dashboard route: {str(e)}")
        print(f"Error type: {type(e)}")
        if isinstance(e, TokenExpiredError):
            del google.token
            session.clear()
            return redirect(url_for("login"))
        return f"An error occurred: {str(e)}", 400

@app.route("/download-qr/<file_id>")
def download_qr(file_id):
    if not google.authorized:
        return redirect(url_for("login"))
    
    file = get_qr_image(file_id)
    if file:
        return send_file(
            io.BytesIO(file),
            mimetype='image/png',
            as_attachment=True,
            download_name='qr_code.png'
        )
    return "No QR code available", 400

@app.route("/delete-qr/<qr_id>")
def delete_qr(qr_id):
    if not google.authorized:
        return redirect(url_for("login"))
    
    qr_code = get_qr_code(qr_id)
    if qr_code:
        delete_qr_image(qr_code.file_id)
        delete_qr_code(qr_id)
    
    return redirect(url_for("dashboard"))

@app.route("/logout")
def logout():
    try:
        if google.authorized:
            token = google.token["access_token"]
            resp = google.post(
                "https://accounts.google.com/o/oauth2/revoke",
                params={"token": token},
                headers={"Content-Type": "application/x-www-form-urlencoded"}
            )
            
            del google.token
    except:
        pass  
    
    session.clear()
    return redirect(url_for("login"))

if __name__ == "__main__":
    app.run(debug=True)
