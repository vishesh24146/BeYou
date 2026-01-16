# 🛡️ BeYou – Secure Social Media Platform

> A privacy-focused social platform developed for the IIIT-Delhi internal network. Built with Django, MySQL, and Docker for robust collaboration, secure messaging, and modular deployment.

---

## 💡 Overview

BeYou is a secure social networking platform that supports:

* OTP-based user authentication
* Encrypted private & group messaging
* Media sharing with CSRF, SQLi, and XSS protection
* Role-based admin features and a lightweight P2P marketplace

Built for **security**, **scalability**, and **modularity**.

---

## ⚙️ Tech Stack

* **Backend:** Django (Python), MySQL
* **Frontend:** HTML, CSS, JS
* **Containerization:** Docker + Docker Compose
* **Web Server (Deployment):** Nginx
* **Auth:** PKI-based flows, OTP with virtual keyboard
* **Security:** HTTPS, CSRF protection, custom middleware logging

---

## 🚀 Local Setup

> 🐳 This project uses Docker to streamline team collaboration and setup. You should have **Docker** and **Docker Compose** installed.

1. **Clone the Repo**

   ```bash
   git clone https://github.com/YOUR-TEAM/BeYou.git
   cd BeYou
   ```

2. **Configure Environment**
   Copy and customize the `.env` file:

   ```bash
   cp backend/.env.example backend/.env
   nano backend/.env  # or use any editor
   ```

3. **Start Services**
   From the root directory:

   ```bash
   docker-compose up -d --build
   ```

4. **Check Containers**

   ```bash
   docker ps
   ```

5. **Access Locally**
   Open your browser:

   ```
   http://192.168.2.239/
   ```
---


## 🔐 Security Considerations (Already Enabled)

Production settings (`settings.py`) include:

* Enforced HTTPS and secure cookies
* CSRF origin whitelisting
* Custom login attempt middleware
* Secret/environment variable injection via `.env`
* SQL mode strict enforcement

---

## 🧠 Notes

* You **don’t** need to manually install Python, MySQL, etc. — Docker handles it.
* Use `docker-compose logs -f backend` for debugging.
* Default DB host inside Docker is `db` (defined in `docker-compose.yml`).
* For internal access, whitelist `192.168.2.239` in `ALLOWED_HOSTS`.

---

## 🧑‍💻 Credits
Developed by a team of 4 at IIIT-Delhi under the guidance of **Dr. Arun Balaji Buduru**
