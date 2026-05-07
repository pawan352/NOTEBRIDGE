from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import sqlite3
import random
import string
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta
import hashlib
import os
import jwt
import secrets

app = Flask(__name__)
CORS(app)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'your-secret-key-change-in-production')

# Email Configuration
EMAIL_ADDRESS = os.getenv('EMAIL_ADDRESS', 'your-email@gmail.com')
EMAIL_PASSWORD = os.getenv('EMAIL_PASSWORD', 'your-app-password')
SMTP_SERVER = 'smtp.gmail.com'
SMTP_PORT = 587

# Database initialization
def init_db():
    conn = sqlite3.connect('notebridge.db')
    c = conn.cursor()
    
    # Users table
    c.execute('''CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY,
        first_name TEXT NOT NULL,
        last_name TEXT NOT NULL,
        email TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        university TEXT NOT NULL,
        email_verified BOOLEAN DEFAULT 0,
        verification_code TEXT,
        verification_code_expires TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    
    conn.commit()
    conn.close()

init_db()

def send_verification_email(email, verification_code, first_name):
    """Send verification email to user"""
    try:
        message = MIMEMultipart()
        message['From'] = EMAIL_ADDRESS
        message['To'] = email
        message['Subject'] = 'Email Verification - NOTEBRIDGE'
        
        body = f"""
        <html>
            <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                <div style="max-width: 600px; margin: 0 auto; padding: 20px; background-color: #f8f9fb; border-radius: 10px;">
                    <h2 style="color: #4f46e5; text-align: center;">NOTEBRIDGE</h2>
                    <h3>Welcome, {first_name}!</h3>
                    <p>Thank you for registering with NOTEBRIDGE. Please verify your email address to complete your registration.</p>
                    
                    <div style="background-color: white; padding: 20px; border-radius: 8px; text-align: center; margin: 20px 0;">
                        <p style="font-size: 16px; color: #666;">Your verification code is:</p>
                        <h1 style="font-size: 48px; letter-spacing: 5px; color: #4f46e5; margin: 20px 0;">{verification_code}</h1>
                        <p style="color: #999; font-size: 14px;">This code will expire in 24 hours</p>
                    </div>
                    
                    <p>Or click the button below:</p>
                    <div style="text-align: center; margin: 20px 0;">
                        <a href="http://localhost:5000/verify-email?code={verification_code}&email={email}" 
                           style="display: inline-block; padding: 12px 30px; background: linear-gradient(45deg, #4f46e5, #9333ea); color: white; text-decoration: none; border-radius: 8px; font-weight: bold;">
                            Verify Email
                        </a>
                    </div>
                    
                    <hr style="border: none; border-top: 1px solid #e0e0e0; margin: 20px 0;">
                    <p style="font-size: 12px; color: #999;">
                        If you didn't register for this account, you can safely ignore this email.
                    </p>
                </div>
            </body>
        </html>
        """
        
        message.attach(MIMEText(body, 'html'))
        
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
        server.send_message(message)
        server.quit()
        
        return True
    except Exception as e:
        print(f"Error sending email: {str(e)}")
        return False

def generate_verification_code():
    """Generate a 6-digit verification code"""
    return ''.join(random.choices(string.digits, k=6))

def hash_password(password):
    """Hash password using SHA-256"""
    return hashlib.sha256(password.encode()).hexdigest()

@app.route('/api/register', methods=['POST'])
def register():
    """Register a new user and send verification email"""
    try:
        data = request.json
        
        # Validation
        if not all([data.get('first_name'), data.get('last_name'), data.get('email'), 
                    data.get('password'), data.get('university')]):
            return jsonify({'error': 'All fields are required'}), 400
        
        if len(data['password']) < 6:
            return jsonify({'error': 'Password must be at least 6 characters'}), 400
        
        # Generate verification code
        verification_code = generate_verification_code()
        expires_at = (datetime.now() + timedelta(hours=24)).isoformat()
        
        # Hash password
        hashed_password = hash_password(data['password'])
        
        conn = sqlite3.connect('notebridge.db')
        c = conn.cursor()
        
        try:
            c.execute('''INSERT INTO users 
                        (first_name, last_name, email, password, university, verification_code, verification_code_expires)
                        VALUES (?, ?, ?, ?, ?, ?, ?)''',
                     (data['first_name'], data['last_name'], data['email'], hashed_password, 
                      data['university'], verification_code, expires_at))
            conn.commit()
        except sqlite3.IntegrityError:
            conn.close()
            return jsonify({'error': 'Email already registered'}), 400
        
        conn.close()
        
        # Send verification email
        if send_verification_email(data['email'], verification_code, data['first_name']):
            return jsonify({
                'success': True,
                'message': 'Registration successful! Please check your email for verification code.',
                'email': data['email']
            }), 201
        else:
            return jsonify({'error': 'Failed to send verification email'}), 500
            
    except Exception as e:
        print(f"Error: {str(e)}")
        return jsonify({'error': 'Registration failed'}), 500

@app.route('/api/verify-email', methods=['POST'])
def verify_email():
    """Verify email with verification code"""
    try:
        data = request.json
        email = data.get('email')
        code = data.get('code')
        
        if not email or not code:
            return jsonify({'error': 'Email and code required'}), 400
        
        conn = sqlite3.connect('notebridge.db')
        c = conn.cursor()
        
        # Check if user exists and code is valid
        c.execute('''SELECT verification_code, verification_code_expires, email_verified 
                     FROM users WHERE email = ?''', (email,))
        result = c.fetchone()
        
        if not result:
            conn.close()
            return jsonify({'error': 'User not found'}), 404
        
        stored_code, expires_at, email_verified = result
        
        if email_verified:
            conn.close()
            return jsonify({'error': 'Email already verified'}), 400
        
        # Check if code is expired
        if datetime.fromisoformat(expires_at) < datetime.now():
            conn.close()
            return jsonify({'error': 'Verification code expired'}), 400
        
        # Check if code matches
        if stored_code != code:
            conn.close()
            return jsonify({'error': 'Invalid verification code'}), 400
        
        # Mark email as verified
        c.execute('''UPDATE users SET email_verified = 1, verification_code = NULL 
                     WHERE email = ?''', (email,))
        conn.commit()
        conn.close()
        
        return jsonify({
            'success': True,
            'message': 'Email verified successfully! You can now login.'
        }), 200
        
    except Exception as e:
        print(f"Error: {str(e)}")
        return jsonify({'error': 'Verification failed'}), 500

@app.route('/api/resend-code', methods=['POST'])
def resend_code():
    """Resend verification code to email"""
    try:
        data = request.json
        email = data.get('email')
        
        if not email:
            return jsonify({'error': 'Email required'}), 400
        
        conn = sqlite3.connect('notebridge.db')
        c = conn.cursor()
        
        c.execute('''SELECT first_name, email_verified FROM users WHERE email = ?''', (email,))
        result = c.fetchone()
        
        if not result:
            conn.close()
            return jsonify({'error': 'User not found'}), 404
        
        first_name, email_verified = result
        
        if email_verified:
            conn.close()
            return jsonify({'error': 'Email already verified'}), 400
        
        # Generate new verification code
        new_code = generate_verification_code()
        expires_at = (datetime.now() + timedelta(hours=24)).isoformat()
        
        c.execute('''UPDATE users SET verification_code = ?, verification_code_expires = ? 
                     WHERE email = ?''', (new_code, expires_at, email))
        conn.commit()
        conn.close()
        
        # Send email
        if send_verification_email(email, new_code, first_name):
            return jsonify({
                'success': True,
                'message': 'Verification code sent to your email'
            }), 200
        else:
            return jsonify({'error': 'Failed to send email'}), 500
            
    except Exception as e:
        print(f"Error: {str(e)}")
        return jsonify({'error': 'Failed to resend code'}), 500

@app.route('/api/login', methods=['POST'])
def login():
    """Login user"""
    try:
        data = request.json
        email = data.get('email')
        password = data.get('password')
        
        if not email or not password:
            return jsonify({'error': 'Email and password required'}), 400
        
        hashed_password = hash_password(password)
        
        conn = sqlite3.connect('notebridge.db')
        c = conn.cursor()
        
        c.execute('''SELECT id, first_name, email_verified FROM users 
                     WHERE email = ? AND password = ?''', (email, hashed_password))
        result = c.fetchone()
        conn.close()
        
        if not result:
            return jsonify({'error': 'Invalid email or password'}), 401
        
        user_id, first_name, email_verified = result
        
        if not email_verified:
            return jsonify({
                'error': 'Email not verified',
                'email': email,
                'message': 'Please verify your email first'
            }), 403
        
        return jsonify({
            'success': True,
            'message': f'Welcome back, {first_name}!',
            'user_id': user_id,
            'email': email,
            'token': jwt.encode({'user_id': user_id, 'email': email}, app.config['SECRET_KEY'], algorithm='HS256')
        }), 200
        
    except Exception as e:
        print(f"Error: {str(e)}")
        return jsonify({'error': 'Login failed'}), 500

def verify_token(token):
    """Verify JWT token and return user_id"""
    try:
        data = jwt.decode(token, app.config['SECRET_KEY'], algorithms=['HS256'])
        return data.get('user_id')
    except:
        return None

@app.route('/api/check-auth', methods=['POST'])
def check_auth():
    """Check if user is authenticated"""
    try:
        token = request.json.get('token')
        
        if not token:
            return jsonify({'authenticated': False}), 200
        
        user_id = verify_token(token)
        
        if not user_id:
            return jsonify({'authenticated': False}), 200
        
        return jsonify({'authenticated': True, 'user_id': user_id}), 200
        
    except Exception as e:
        return jsonify({'authenticated': False}), 200

@app.route('/api/download/<path:filename>', methods=['GET'])
def download_note(filename):
    """Download a note file - requires authentication"""
    try:
        token = request.headers.get('Authorization', '').replace('Bearer ', '')
        
        if not token:
            return jsonify({'error': 'Authentication required', 'redirect': 'login'}), 401
        
        user_id = verify_token(token)
        
        if not user_id:
            return jsonify({'error': 'Invalid or expired token', 'redirect': 'login'}), 401
        
        # Sanitize filename to prevent directory traversal
        filename = os.path.basename(filename)
        file_path = os.path.join('notes', filename)
        
        if not os.path.exists(file_path):
            return jsonify({'error': 'File not found'}), 404
        
        return send_file(file_path, as_attachment=True)
        
    except Exception as e:
        print(f"Error: {str(e)}")
        return jsonify({'error': 'Download failed'}), 500

@app.route('/verify-email', methods=['GET'])
def verify_email_link():
    """Handle email verification link from email"""
    try:
        code = request.args.get('code')
        email = request.args.get('email')
        
        if not code or not email:
            return "Invalid verification link", 400
        
        conn = sqlite3.connect('notebridge.db')
        c = conn.cursor()
        
        c.execute('''SELECT verification_code, verification_code_expires FROM users WHERE email = ?''', (email,))
        result = c.fetchone()
        
        if not result or result[0] != code:
            conn.close()
            return "Invalid or expired verification link", 400
        
        # Mark as verified
        c.execute('''UPDATE users SET email_verified = 1, verification_code = NULL WHERE email = ?''', (email,))
        conn.commit()
        conn.close()
        
        return f"""
        <html>
            <body style="font-family: Arial; text-align: center; padding: 50px;">
                <h1 style="color: #4f46e5;">Email Verified!</h1>
                <p>Your email has been successfully verified.</p>
                <p>You can now <a href="login.html">login to your account</a></p>
            </body>
        </html>
        """, 200
        
    except Exception as e:
        return f"Error: {str(e)}", 500

if __name__ == '__main__':
    app.run(debug=True, host='localhost', port=5000)
