from flask import Blueprint, render_template, redirect, url_for, session, flash, request
import MySQLdb
from . import mysql  
import base64

views = Blueprint('views', __name__)


@views.route('/')
def home():
    return render_template("base.html")


@views.route('/seekerdashboard')
def seekerdashboard():
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))

    try:
        # Fetch seeker's first name and city from database
        cur = mysql.connection.cursor()
        cur.execute("SELECT fname, city FROM jobseeker WHERE seekerID = %s", (session['user_id'],))
        seeker = cur.fetchone()
        
        if seeker:
            user_name = seeker[0]
            user_city = seeker[1]
            
            session['basic_info'] = {'first_name': user_name}
            
            # Fetch recommended jobs based on city
            job_query = """
                SELECT jobID, jobtitle, jobdescription, city, salary, postingdate, status 
                FROM job 
                WHERE status = 'Open' AND city = %s
                ORDER BY postingdate DESC
                LIMIT 3
            """
            cur.execute(job_query, (user_city,))
            recommended_jobs = cur.fetchall()
            
            # Format job data
            jobs = []
            for job in recommended_jobs:
                jobs.append({
                    'jobID': job[0],
                    'jobtitle': job[1],
                    'city': job[3],
                    'salary': f"{job[4]:,.0f}",
                    'postingdate': job[5].strftime('%b %d, %Y')
                })
            
            # Get application count
            cur.execute("SELECT COUNT(*) FROM applyto WHERE seekerID = %s", (session['user_id'],))
            application_count = cur.fetchone()[0]
        else:
            user_name = 'Guest'
            jobs = []
            application_count = 0

        cur.close()
        return render_template('seekerdashboard.html', 
                             user=user_name, 
                             recommended_jobs=jobs,
                             application_count=application_count)
    
    except Exception as e:
        flash(f'Error loading dashboard: {str(e)}', 'danger')
        return redirect(url_for('auth.login'))
    

@views.route('/publisherdashboard')
def publisher_dashboard():
    if 'user_id' not in session or session.get('role') != 'publisher':
        flash("Please login as publisher first", 'warning')
        return redirect(url_for('auth.login'))

    try:
        conn = mysql.connection
        cursor = conn.cursor()
        
        # Fetch publisher data
        cursor.execute("""
            SELECT fname, lname, email, phoneNumber, address, city, country, gender 
            FROM jobpublisher 
            WHERE publisherID = %s
        """, (session['user_id'],))
        publisher = cursor.fetchone()

        if not publisher:
            flash("Publisher not found", 'danger')
            return redirect(url_for('auth.login'))

        # Get counts
        cursor.execute("SELECT COUNT(*) FROM job WHERE publisherid = %s", (session['user_id'],))
        job_count = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM job WHERE publisherid = %s AND status = 'Open'", (session['user_id'],))
        open_jobs_count = cursor.fetchone()[0]

        cursor.execute("""
            SELECT COUNT(*) FROM applyto a
            JOIN job j ON a.jobID = j.jobID
            WHERE j.publisherid = %s
        """, (session['user_id'],))
        application_count = cursor.fetchone()[0]

        # Get recent applicants
        recent_applicants = []
        try:
            cursor.execute("""
                SELECT j.jobtitle, s.fname, s.lname, a.applytodate 
                FROM applyto a
                JOIN job j ON a.jobID = j.jobID
                JOIN jobseeker s ON a.seekerID = s.seekerID
                WHERE j.publisherid = %s
                ORDER BY a.applytodate DESC
                LIMIT 5
            """, (session['user_id'],))
            recent_applicants = cursor.fetchall()
        except Exception as e:
            print(f"Error fetching applicants: {str(e)}")
            flash("Could not load recent applicants", 'warning')

        cursor.close()

        publisher_data = {
            'fname': publisher[0],
            'lname': publisher[1],
            'email': publisher[2],
            'phone': publisher[3],
            'address': publisher[4],
            'city': publisher[5],
            'country': publisher[6],
            'gender': publisher[7],
            'job_count': job_count,
            'open_jobs_count': open_jobs_count,
            'application_count': application_count,
            'recent_applicants': recent_applicants
        }

        return render_template('publisherdashboard.html', publisher=publisher_data)

    except Exception as e:
        print(f"Dashboard error: {str(e)}")
        flash(f"Error loading dashboard: {str(e)}", 'danger')
        return redirect(url_for('auth.login'))


@views.route('/about')
def about():
    return render_template('about.html')


@views.route('/setting', methods=['GET', 'POST'])
def setting():
    if 'user_id' not in session or 'role' not in session:
        return redirect(url_for('auth.login'))

    user_id = session['user_id']
    role = session['role']
    conn = mysql.connection
    cursor = None  # Initialize cursor

    try:
        if request.method == 'POST':
            cursor = conn.cursor()
            font_size = request.form.get('fontSize', '16px')
            notifications = 1 if request.form.get('notifications') == 'on' else 0

            # Determine which column to use based on role
            if role == 'seeker':
                cursor.execute("""
                    INSERT INTO user_settings (seeker_id, font_size, notifications)
                    VALUES (%s, %s, %s)
                    ON DUPLICATE KEY UPDATE
                    font_size = VALUES(font_size),
                    notifications = VALUES(notifications)
                """, (user_id, font_size, notifications))
            elif role == 'publisher':
                cursor.execute("""
                    INSERT INTO user_settings (publisher_id, font_size, notifications)
                    VALUES (%s, %s, %s)
                    ON DUPLICATE KEY UPDATE
                    font_size = VALUES(font_size),
                    notifications = VALUES(notifications)
                """, (user_id, font_size, notifications))
            
            conn.commit()
            flash('Settings saved successfully!', 'success')

        # GET Request Handling
        cursor = conn.cursor()
        if role == 'seeker':
            cursor.execute("""
                SELECT font_size, notifications 
                FROM user_settings 
                WHERE seeker_id = %s
            """, (user_id,))
        elif role == 'publisher':
            cursor.execute("""
                SELECT font_size, notifications 
                FROM user_settings 
                WHERE publisher_id = %s
            """, (user_id,))
        
        settings = cursor.fetchone()
        default_settings = {'font_size': '16px', 'notifications': True}

        return render_template('setting.html',
            font_size=settings[0] if settings else default_settings['font_size'],
            notifications='on' if (settings[1] if settings else default_settings['notifications']) else 'off')

    except Exception as e:
        conn.rollback()
        flash(f'Error processing settings: {str(e)}', 'danger')
        return redirect(url_for('views.setting'))
    
    finally:
        if cursor:
            cursor.close()


@views.route('/searchjob')
def searchjob():
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))

    try:
        conn = mysql.connection
        cursor = conn.cursor(MySQLdb.cursors.DictCursor)
        
        # Get search filters from query parameters
        keywords = request.args.get('keywords', '')
        location = request.args.get('location', '')
        min_salary = request.args.get('minSalary', '')
        
        # Base query
        query = """
            SELECT jobID, jobtitle, jobdescription, city, salary, postingdate, status 
            FROM job 
            WHERE status = 'Open'
        """
        params = []

        # Add filters
        if keywords:
            query += " AND (jobtitle LIKE %s OR jobdescription LIKE %s)"
            params.extend([f'%{keywords}%', f'%{keywords}%'])
        
        if location:
            query += " AND city LIKE %s"
            params.append(f'%{location}%')
        
        if min_salary:
            try:
                min_salary_int = int(min_salary)
                query += " AND salary >= %s"
                params.append(min_salary_int)
            except ValueError:
                flash('Please enter a valid salary number', 'warning')


        cursor.execute(query, params)
        jobs = cursor.fetchall()
        
        # Format date and salary
        for job in jobs:
            job['postingdate'] = job['postingdate'].strftime('%b %d, %Y')
            job['salary'] = f"{job['salary']:,.0f}"

        cursor.close()
        return render_template('searchjob.html', jobs=jobs)

    except Exception as e:
        flash(f'Error loading jobs: {str(e)}', 'danger')
        return render_template('searchjob.html', jobs=[])


@views.route('/profile')
def profile():
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))

    user_id = session['user_id']
    conn = mysql.connection
    cursor = conn.cursor()
    cursor.execute(
        "SELECT fname, lname, email, phonenumber, gender, city, disabilitydocument FROM jobseeker WHERE seekerid = %s",
        (user_id,)
    )
    user_profile = cursor.fetchone()

    if user_profile:
        fname, lname, email, phone, gender, city, disabilitydoc = user_profile
        # Convert blob to base64 if there's data
        if disabilitydoc:
            disabilitydoc = base64.b64encode(disabilitydoc).decode('utf-8')
    else:
        fname = lname = email = phone = gender = city = disabilitydoc = ''

    return render_template('seekerprofileaccount.html',
                           fname=fname,
                           lname=lname,
                           email=email,
                           phone=phone,
                           gender=gender,
                           city=city,
                           disabilitydoc=disabilitydoc)


# Flask Route Updates
@views.route('/editprofile', methods=['GET', 'POST'])
def editprofile():
    if 'user_id' not in session or 'role' not in session:
        return redirect(url_for('auth.login'))

    user_id = session['user_id']
    role = session['role']
    conn = mysql.connection
    cursor = conn.cursor()

    if request.method == 'POST':
        try:
            # Get form data
            fname = request.form.get('firstName')
            lname = request.form.get('lastName')
            email = request.form.get('email')
            phone = request.form.get('phone')
            gender = request.form.get('gender')
            city = request.form.get('city')
            
            # Handle file upload
            disability_doc = None
            if 'disabilityDoc' in request.files:
                file = request.files['disabilityDoc']
                if file.filename != '':
                    disability_doc = file.read()

            if role == 'seeker':
                # Update jobseeker table
                update_query = """
                    UPDATE jobseeker 
                    SET fname = %s, lname = %s, email = %s, 
                        phoneNumber = %s, gender = %s, city = %s
                """
                params = (fname, lname, email, phone, gender, city)
                
                if disability_doc:
                    update_query = update_query[:-1] + ", disabilitydocument = %s"
                    params += (disability_doc,)
                
                update_query += " WHERE seekerID = %s"
                params += (user_id,)
                
                cursor.execute(update_query, params)
                
            conn.commit()
            flash('Profile updated successfully!', 'success')
        except Exception as e:
            conn.rollback()
            flash(f'Error updating profile: {str(e)}', 'danger')
        finally:
            cursor.close()

        return redirect(url_for('views.profile'))

    # GET Request - Populate form with existing data
    try:
        cursor.execute(
            "SELECT fname, lname, email, phoneNumber, gender, city "
            "FROM jobseeker WHERE seekerID = %s",
            (user_id,)
        )
        user_data = cursor.fetchone()
        cursor.close()

        if user_data:
            return render_template('editprofile.html',
                                fname=user_data[0],
                                lname=user_data[1],
                                email=user_data[2],
                                phone=user_data[3],
                                gender=user_data[4],
                                city=user_data[5])
        
        flash('User not found', 'danger')
        return redirect(url_for('views.profile'))

    except Exception as e:
        flash(f'Error retrieving profile: {str(e)}', 'danger')
        return redirect(url_for('views.profile'))
    

@views.context_processor
def inject_settings():
    settings = {'global_font_size': '16px'} 
    if 'user_id' in session and 'role' in session:
        try:
            conn = mysql.connection
            cursor = conn.cursor()
            
            # Determine which column to query based on user role
            role = session['role']
            user_id = session['user_id']
            
            if role == 'seeker':
                cursor.execute("""
                    SELECT font_size FROM user_settings 
                    WHERE seeker_id = %s
                """, (user_id,))
            elif role == 'publisher':
                cursor.execute("""
                    SELECT font_size FROM user_settings 
                    WHERE publisher_id = %s
                """, (user_id,))
            
            result = cursor.fetchone()
            if result and result[0]:
                settings['global_font_size'] = result[0]
            cursor.close()
        except Exception as e:
            print(f"Error loading settings: {str(e)}")
            if 'cursor' in locals():
                cursor.close()
    return settings


@views.route('/postjobs', methods=['GET', 'POST'])
def postjobs():
    if 'user_id' not in session or session.get('role') != 'publisher':
        flash("Please login as publisher first", 'warning')
        return redirect(url_for('auth.login'))

    if request.method == 'POST':
        try:
            # Get form data
            job_data = {
                'jobtitle': request.form.get('jobTitle'),
                'jobdescription': request.form.get('jobDescription'),
                'city': request.form.get('city'),
                'salary': request.form.get('salary'),
                'status': request.form.get('status'),
                'publisherid': session['user_id']
            }

            # Validate required fields
            required_fields = ['jobtitle', 'jobdescription', 'city', 'salary', 'status']
            for field in required_fields:
                if not job_data[field]:
                    flash(f"{field.capitalize()} is required", 'danger')
                    return redirect(url_for('views.postjobs'))

            # Convert salary to integer
            try:
                job_data['salary'] = int(job_data['salary'])
            except ValueError:
                flash('Please enter a valid salary number', 'danger')
                return redirect(url_for('views.postjobs'))

            conn = mysql.connection
            cursor = conn.cursor()
            
            # Insert new job
            cursor.execute("""
                INSERT INTO job (postingdate, salary, city, status, jobtitle, jobdescription, publisherid)
                VALUES (CURDATE(), %s, %s, %s, %s, %s, %s)
            """, (
                job_data['salary'],
                job_data['city'],
                job_data['status'],
                job_data['jobtitle'],
                job_data['jobdescription'],
                job_data['publisherid']
            ))
            
            conn.commit()
            cursor.close()
            flash('Job posted successfully!', 'success')
            return redirect(url_for('views.postjobs'))

        except Exception as e:
            conn.rollback()
            flash(f'Error posting job: {str(e)}', 'danger')
            return redirect(url_for('views.postjobs'))

    # GET request - show form and existing jobs
    try:
        # Get publisher's posted jobs
        conn = mysql.connection
        cursor = conn.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute("""
            SELECT jobID, jobtitle, city, salary, postingdate, status 
            FROM job 
            WHERE publisherid = %s
            ORDER BY postingdate DESC
        """, (session['user_id'],))
        
        jobs = cursor.fetchall()
        
        # Format date and salary
        for job in jobs:
            job['postingdate'] = job['postingdate'].strftime('%b %d, %Y')
            job['salary'] = f"{job['salary']:,.0f} SAR"

        cursor.close()
        return render_template('PostJobs.html', jobs=jobs)

    except Exception as e:
        flash(f'Error loading jobs: {str(e)}', 'danger')
        return render_template('PostJobs.html', jobs=[])
    

@views.route('/delete_job', methods=['POST'])
def delete_job():
    if 'user_id' not in session or session.get('role') != 'publisher':
        flash("Unauthorized action", 'danger')
        return redirect(url_for('auth.login'))

    job_id = request.form.get('job_id')
    try:
        conn = mysql.connection
        cursor = conn.cursor()
        cursor.execute("DELETE FROM job WHERE jobID = %s AND publisherid = %s", 
                      (job_id, session['user_id']))
        conn.commit()
        cursor.close()
        flash('Job deleted successfully', 'success')
    except Exception as e:
        conn.rollback()
        flash(f'Error deleting job: {str(e)}', 'danger')
    
    return redirect(url_for('views.postjobs'))



@views.route('/apply_job', methods=['POST'])
def apply_job():
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))

    try:
        job_id = request.form.get('job_id')
        seeker_id = session['user_id']
        
        # Check if already applied
        cur = mysql.connection.cursor()
        cur.execute("SELECT * FROM applyto WHERE seekerID = %s AND jobID = %s", (seeker_id, job_id))
        existing_application = cur.fetchone()
        
        if existing_application:
            flash('You have already applied to this job', 'warning')
            return redirect(request.referrer or url_for('views.seekerdashboard'))

        # Insert new application
        cur.execute("""
            INSERT INTO applyto (seekerID, jobID, applytodate) 
            VALUES (%s, %s, CURDATE())
        """, (seeker_id, job_id))
        
        mysql.connection.commit()
        cur.close()
        flash('Application submitted successfully!', 'success')
    except Exception as e:
        mysql.connection.rollback()
        flash(f'Error applying to job: {str(e)}', 'danger')
    
    return redirect(request.referrer or url_for('views.seekerdashboard'))



@views.route('/edit_job/<int:job_id>', methods=['GET', 'POST'])
def edit_job(job_id):
    if 'user_id' not in session or session.get('role') != 'publisher':
        flash("Please login as publisher first", 'warning')
        return redirect(url_for('auth.login'))

    conn = mysql.connection
    cursor = conn.cursor(MySQLdb.cursors.DictCursor)

    try:
        # Check if job belongs to current publisher
        cursor.execute("""
            SELECT * FROM job 
            WHERE jobID = %s AND publisherid = %s
        """, (job_id, session['user_id']))
        job = cursor.fetchone()

        if not job:
            flash("Job not found or you don't have permission", 'danger')
            return redirect(url_for('views.postjobs'))

        if request.method == 'POST':
            # Get updated data from form - use lowercase field names to match the form
            updated_data = {
                'jobtitle': request.form.get('jobTitle'),
                'jobdescription': request.form.get('jobDescription'),
                'city': request.form.get('city'),  # Changed from 'City' to 'city'
                'salary': request.form.get('salary'),  # Changed from 'Salary' to 'salary'
                'status': request.form.get('status'),  # Changed from 'Status' to 'status'
                'job_id': job_id
            }
            
            # Validate salary
            try:
                updated_data['salary'] = int(updated_data['salary'])
            except (ValueError, TypeError):
                flash('Please enter a valid salary number', 'danger')
                return redirect(url_for('views.edit_job', job_id=job_id))

            # Update job in database
            cursor.execute("""
                UPDATE job SET
                    jobtitle = %s,
                    jobdescription = %s,
                    city = %s,
                    salary = %s,
                    status = %s
                WHERE jobID = %s
            """, (
                updated_data['jobtitle'],
                updated_data['jobdescription'],
                updated_data['city'],
                updated_data['salary'],
                updated_data['status'],
                job_id
            ))
            
            conn.commit()
            flash('Job updated successfully!', 'success')
            return redirect(url_for('views.postjobs'))

        # For GET request - format the date properly
        if job['PostingDate']:
            job['PostingDate'] = job['PostingDate'].strftime('%Y-%m-%d')
        else:
            job['PostingDate'] = ''  # or use today's date if you prefer

        return render_template('editjob.html', job=job)

    except Exception as e:
        conn.rollback()
        flash(f'Error updating job: {str(e)}', 'danger')
        return redirect(url_for('views.postjobs'))
    finally:
        cursor.close()
        
        
        
        
@views.route('/publisherprofile')
def publisher_profile():
    if 'user_id' not in session or session.get('role') != 'publisher':
        flash("Please login as publisher first", 'warning')
        return redirect(url_for('auth.login'))

    try:
        conn = mysql.connection
        cursor = conn.cursor()
        cursor.execute("""
            SELECT fname, lname, email, phoneNumber, address, city, country, gender 
            FROM jobpublisher 
            WHERE publisherID = %s
        """, (session['user_id'],))
        publisher = cursor.fetchone()

        if not publisher:
            flash("Publisher not found", 'danger')
            return redirect(url_for('auth.login'))

        publisher_data = {
            'fname': publisher[0],
            'lname': publisher[1],
            'email': publisher[2],
            'phone': publisher[3],
            'address': publisher[4],
            'city': publisher[5],
            'country': publisher[6],
            'gender': publisher[7]
        }

        cursor.close()
        return render_template('publisherprofileaccount.html', **publisher_data)

    except Exception as e:
        flash(f'Error loading profile: {str(e)}', 'danger')
        return redirect(url_for('auth.login'))
    
    

@views.route('/editpublisherprofile', methods=['GET', 'POST'])
def edit_publisher_profile():
    if 'user_id' not in session or session.get('role') != 'publisher':
        flash("Please login as publisher first", 'warning')
        return redirect(url_for('auth.login'))

    user_id = session['user_id']
    conn = mysql.connection
    cursor = conn.cursor()

    if request.method == 'POST':
        try:
            # Get form data
            fname = request.form.get('firstName')
            lname = request.form.get('lastName')
            email = request.form.get('email')
            phone = request.form.get('phone')
            address = request.form.get('address')
            city = request.form.get('city')
            country = request.form.get('country')
            gender = request.form.get('gender')

            # Update publisher table
            cursor.execute("""
                UPDATE jobpublisher 
                SET fname = %s, lname = %s, email = %s, 
                    phoneNumber = %s, address = %s, city = %s,
                    country = %s, gender = %s
                WHERE publisherID = %s
            """, (fname, lname, email, phone, address, city, country, gender, user_id))
            
            conn.commit()
            flash('Profile updated successfully!', 'success')
            return redirect(url_for('views.publisher_profile'))

        except Exception as e:
            conn.rollback()
            flash(f'Error updating profile: {str(e)}', 'danger')
            return redirect(url_for('views.edit_publisher_profile'))
        finally:
            cursor.close()

    # GET Request - Populate form with existing data
    try:
        cursor.execute("""
            SELECT fname, lname, email, phoneNumber, address, city, country, gender 
            FROM jobpublisher 
            WHERE publisherID = %s
        """, (user_id,))
        publisher_data = cursor.fetchone()
        cursor.close()

        if publisher_data:
            return render_template('editpublisherprofile.html',
                                fname=publisher_data[0],
                                lname=publisher_data[1],
                                email=publisher_data[2],
                                phone=publisher_data[3],
                                address=publisher_data[4],
                                city=publisher_data[5],
                                country=publisher_data[6],
                                gender=publisher_data[7])
        
        flash('Publisher not found', 'danger')
        return redirect(url_for('views.publisher_profile'))

    except Exception as e:
        flash(f'Error retrieving profile: {str(e)}', 'danger')
        return redirect(url_for('views.publisher_profile'))        

