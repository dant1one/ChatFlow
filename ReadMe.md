# ChatFlow - Real-Time Chat Application

## Description

ChatFlow is a full-stack real-time chat web application built with FastAPI and a modern frontend interface.
The project allows users to register, search users, send and receive messages, Talk in groups and manage conversations in real time.

The application includes authentication, responsive UI, chat history, message search.

---

# Features

## User Management

* User registration
* User search
* User list display
* Online/offline status

## Messaging

* Send messages
* Receive real-time messages
* Chat history
* Search messages
* Conversations between users

## Frontend

* Responsive design
* Dark mode
* User sidebar
* Search functionality

## Backend

* FastAPI REST API
* WebSocket support for real-time communication
* Database integration
* Authentication system

## Additional Features

* Docker support
* Notifications system

---

# Tech Stack

## Backend

* Python
* FastAPI
* WebSockets
* SQLAlchemy
* PostgreSQL / SQLite
* Pydantic

## Frontend

* HTML
* CSS
* JavaScript
* React (optional)

## Deployment

* Docker
* GitHub
* PythonAnywhere

---

# How to Run Locally

## 1. Clone Repository

```bash
git clone https://github.com/dant1one/ChatFlow.git
cd chatflow
```

---

## 2. Create Virtual Environment

### Linux/macOS

```bash
python3 -m venv venv
source venv/bin/activate
```

### Windows

```bash
python -m venv venv
venv\Scripts\activate
```

---

## 3. Install Dependencies

```bash
pip install -r requirements.txt
```

---

## 4. Run Backend

```bash
uvicorn app.main:app --reload
```

Backend runs at:

```bash
http://127.0.0.1:8000
```

Swagger API docs:

```bash
http://127.0.0.1:8000/docs
```

---

## 5. Run Frontend

Open:

```bash
frontend/index.html
```

Or run with Live Server.

---

# Docker Run (Best Way)

## Build and Start

```bash
cd ~yourpath/Chat; docker-compose up -d
```

---

## Live Website

```text
ec2-54-165-72-221.compute-1.amazonaws.com
```

## Deployment Platform

* AWS

---

# GitHub Repository

```text
https://github.com/dant1one/ChatFlow
```

---

## YouTube Link

```text
https://youtu.be/StI503MXXXk
```

---

# Screenshots

## Login/Registration

![alt text](<Screenshot from 2026-05-12 16-26-47.png>)

## Home Page

![alt text](<Screenshot from 2026-05-12 16-27-14.png>)

## Chat Window

![alt text](<Screenshot from 2026-05-12 16-27-23.png>)

---

# Author

Developed by Daniyal Va-Akhunov.