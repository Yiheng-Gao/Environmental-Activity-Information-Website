# Environmental Activity Information Website

This project is a web platform designed to display and manage environmental activity information.  
It provides user registration/login, activity browsing, activity signup, and an admin backend for activity management.  
The system is built using **Django 5**, **SQLite**, and supports media uploads such as activity images.

---

## Features

- User registration and login  
- Activity list display  
- Activity detail page  
- Activity signup  
- User activity history  
- Admin panel for managing activities  
- Media file support
- User Dashboard
- Comment Section

---

## Technology Stack

- **Python 3.11.9**
- **Django 5.2.8**
- **SQLite**
- **Pillow 12.0.0** (for image handling)

Dependencies (from `requirements.txt`):
asgiref==3.10.0
Django==5.2.8
pillow==12.0.0
sqlparse==0.5.3
tzdata==2025.2

##  Project Repository

GitHub link:  
https://github.com/Yiheng-Gao/Environmental-Activity-Information-Website/

---

##  Installation & Setup Guide

Follow these steps to run the project from scratch.

### 1 Clone the Repository

```sh
git clone https://github.com/Yiheng-Gao/Environmental-Activity-Information-Website.git
cd Environmental-Activity-Information-Website
```
### 2 Install Dependencies
```sh
pip install -r requirements.txt
```
## Database Setup
### 3 Apply Database Migrations
```sh
python manage.py migrate
```
### 4 Load Initial Data (Fixture)
fixtures/initial_data.json
```sh
python manage.py loaddata fixtures/initial_data.json
```

##Run the Development Server
```sh
python manage.py runserver
```
Then visit:
http://127.0.0.1:8000/

## Usage
After starting the server:
View the list of environmental activities
View activity details
Sign up for activities
Log in/out
Access admin panel at /admin/
If you loaded the initial data, sample activities and images will already be available.


