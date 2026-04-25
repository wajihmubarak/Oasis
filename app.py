from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
import datetime
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = 'oasis_pro_secure_key_2026'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///oasis_database.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# جدول المستخدمين
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    balance = db.Column(db.Float, default=0.0)
    wallet = db.Column(db.String(200), default='')
    ref_by = db.Column(db.String(50), default='')

# جدول العمليات (إيداع وسحب)
class Transaction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_email = db.Column(db.String(100))
    amount = db.Column(db.Float)
    type = db.Column(db.String(20)) # Deposit / Withdraw
    status = db.Column(db.String(20), default='Pending') 
    txid = db.Column(db.String(200), default='')
    date = db.Column(db.String(50), default=datetime.datetime.now().strftime("%Y-%m-%d %H:%M"))

with app.app_context():
    db.create_all()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/admin')
def admin_page():
    return render_template('admin.html')

# --- APIs للمستخدم ---
@app.route('/api/register', methods=['POST'])
def register():
    data = request.json
    if User.query.filter_by(email=data['email']).first():
        return jsonify({"success": False, "message": "الإيميل مسجل مسبقاً"})
    hashed_pw = generate_password_hash(data['password'], method='pbkdf2:sha256')
    new_user = User(username=data['username'], email=data['email'], password=hashed_pw, ref_by=data.get('ref', ''))
    db.session.add(new_user)
    db.session.commit()
    return jsonify({"success": True})

@app.route('/api/login', methods=['POST'])
def login():
    data = request.json
    user = User.query.filter_by(email=data['email']).first()
    if user and check_password_hash(user.password, data['password']):
        session['user_id'] = user.id
        return jsonify({"success": True, "balance": user.balance, "wallet": user.wallet})
    return jsonify({"success": False, "message": "بيانات خاطئة"})

@app.route('/api/deposit', methods=['POST'])
def deposit():
    if 'user_id' not in session: return jsonify({"success": False})
    user = User.query.get(session['user_id'])
    data = request.json
    new_tx = Transaction(user_email=user.email, amount=0.0, type='Deposit', txid=data['txid'])
    db.session.add(new_tx)
    db.session.commit()
    return jsonify({"success": True})

@app.route('/api/update_wallet', methods=['POST'])
def update_wallet():
    if 'user_id' not in session: return jsonify({"success": False})
    user = User.query.get(session['user_id'])
    user.wallet = request.json['wallet']
    db.session.commit()
    return jsonify({"success": True})

# --- APIs للأدمن ---
@app.route('/api/admin/pending')
def get_pending():
    deposits = Transaction.query.filter_by(type='Deposit', status='Pending').all()
    return jsonify({"pending": [{"id": d.id, "email": d.user_email, "txid": d.txid} for d in deposits]})

@app.route('/api/admin/confirm', methods=['POST'])
def confirm():
    data = request.json
    tx = Transaction.query.get(data['id'])
    user = User.query.filter_by(email=tx.user_email).first()
    if tx and user:
        user.balance += float(data['amount'])
        tx.status = 'Success'
        db.session.commit()
        return jsonify({"success": True})
    return jsonify({"success": False})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
