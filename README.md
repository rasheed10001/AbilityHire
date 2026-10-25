# AbilityHire

Graduation project: a job platform connecting people with disabilities to employers. Built with Flask and MySQL.

## Features
- Separate sign-up and login for job seekers and job publishers
- Seeker and publisher dashboards and editable profiles
- Publishers can post, edit and manage jobs
- Seekers can search and browse jobs

## Tech stack
Python, Flask, MySQL (flask-mysqldb), HTML/Jinja templates

## Run locally
1. `pip install -r requirements.txt`
2. Create the database and tables: `mysql -u root -p < schema.sql`
3. Set environment variables: `SECRET_KEY`, `MYSQL_HOST`, `MYSQL_USER`, `MYSQL_PASSWORD`, `MYSQL_DB`
4. `python main.py`

## Author
Rasheed Alomari - [LinkedIn](https://www.linkedin.com/in/rasheed-alomari/)
