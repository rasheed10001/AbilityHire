from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from . import mysql

auth = Blueprint('auth', __name__)

@auth.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        cur = mysql.connection.cursor()

        # Try login as Seeker
        cur.execute("SELECT seekerID, fname, password FROM jobseeker WHERE email = %s", (email,))
        seeker = cur.fetchone()

        if seeker:
            seeker_id, seeker_fname, seeker_password = seeker
            if seeker_password == password:
                session['user_id'] = seeker_id
                session['role'] = 'seeker'
                session['basic_info'] = {'first_name': seeker_fname} 
                flash("Login successful as Job Seeker!")
                cur.close()
                return redirect(url_for('views.seekerdashboard'))

        # Try login as Publisher
        cur.execute("SELECT publisherID, fname, password FROM jobpublisher WHERE email = %s", (email,))
        publisher = cur.fetchone()
        cur.close()

        if publisher:
            publisher_id, publisher_fname, publisher_password = publisher
            if publisher_password == password:
                session['user_id'] = publisher_id
                session['role'] = 'publisher'
                session['basic_info'] = {'first_name': publisher_fname}
                flash("Login successful as Publisher!")
                return redirect(url_for('views.publisher_dashboard'))

        flash("Invalid email or password.")
        return redirect(url_for('auth.login'))
    
    return render_template("login.html")


@auth.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('auth.login'))


@auth.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        # Add form validation
        required_fields = ['firstName', 'lastName', 'email', 'password', 'role']
        if not all(field in request.form for field in required_fields):
            flash('Please fill all required fields', 'danger')
            return redirect(url_for('auth.signup'))

        if request.form.get('password') != request.form.get('repeatPassword'):
            flash('Passwords do not match', 'danger')
            return redirect(url_for('auth.signup'))

        # Store in session
        session['basic_info'] = {
            'first_name': request.form.get('firstName'),
            'last_name': request.form.get('lastName'),
            'email': request.form.get('email'),
            'password': request.form.get('password'),
            'role': request.form.get('role')
        }

        # Verify role selection
        role = request.form.get('role')
        if role == 'seeker':
            return redirect(url_for('auth.seeker_info'))
        elif role == 'publisher':
            return redirect(url_for('auth.publisher_info'))
        
        flash('Invalid role selection', 'danger')
        return redirect(url_for('auth.signup'))

    return render_template('signup.html')


@auth.route('/seekerinfo', methods=['GET', 'POST'])
def seeker_info():
    if request.method == 'POST':
        try:
            if 'basic_info' not in session:
                flash("Session expired. Please start over.", 'danger')
                return redirect(url_for('auth.signup'))

            # Validate file upload
            if 'document' not in request.files:
                flash('Document is required', 'danger')
                return redirect(request.url)
            
            file = request.files['document']
            if file.filename == '':
                flash('No selected file', 'danger')
                return redirect(request.url)

            # Get form data
            phone = request.form.get('phone')
            address = request.form.get('address')
            city = request.form.get('city')
            country = request.form.get('country')
            gender = request.form.get('gender')
            document_data = file.read()

            # Get session data
            basic_info = session['basic_info']
            
            cursor = mysql.connection.cursor()
            cursor.execute("""
                INSERT INTO jobseeker 
                (fname, lname, email, password, phoneNumber, address, city, country, gender, disabilitydocument)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                basic_info['first_name'],
                basic_info['last_name'],
                basic_info['email'],
                basic_info['password'],  # Consider hashing this!
                phone,
                address,
                city,
                country,
                gender,
                document_data
            ))
            
            mysql.connection.commit()
            user_id = cursor.lastrowid
            cursor.close()

            session['user_id'] = user_id
            session['role'] = 'seeker'
            session.pop('basic_info', None)

            flash('Registration successful!', 'success')
            return redirect(url_for('views.seekerdashboard'))

        except Exception as e:
            mysql.connection.rollback()
            flash(f'Registration failed: {str(e)}', 'danger')
            return redirect(url_for('auth.signup'))

    return render_template('seekerinfo.html')


@auth.route('/publisherinfo', methods=['GET', 'POST'])
def publisher_info():
    if request.method == 'POST':
        if 'basic_info' not in session:
            flash("Please complete signup first.")
            return redirect(url_for('auth.signup'))

        # Extract form data
        phone = request.form.get('phone')
        address = request.form.get('address')
        city = request.form.get('city')
        country = request.form.get('country')
        gender = request.form.get('gender')

        fname = session['basic_info']['first_name']
        lname = session['basic_info']['last_name']
        email = session['basic_info']['email']
        password = session['basic_info']['password']

        cursor = mysql.connection.cursor()

        cursor.execute("""
            INSERT INTO jobpublisher (fname, lname, email, password, phoneNumber, address, city, country, gender)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (fname, lname, email, password, phone, address, city, country, gender))

        mysql.connection.commit()

        session['user_id'] = cursor.lastrowid
        session['role'] = 'publisher'
        session.pop('basic_info', None)

        cursor.close()

        flash("Publisher registration complete!")
        return redirect(url_for('views.publisher_dashboard'))

    return render_template('publisherinfo.html')