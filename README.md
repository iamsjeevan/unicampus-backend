# UniCampus Backend: A DevOps-Driven Microservices Platform

<p align="center">
  <img src="https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python">
  <img src="https://img.shields.io/badge/Node.js-339933?style=for-the-badge&logo=nodedotjs&logoColor=white" alt="Node.js">
  <img src="https://img.shields.io/badge/Flask-000000?style=for-the-badge&logo=flask&logoColor=white" alt="Flask">
  <img src="https://img.shields.io/badge/Docker-2496ED?style=for-the-badge&logo=docker&logoColor=white" alt="Docker">
  <img src="https://img.shields.io/badge/Ansible-EE0000?style=for-the-badge&logo=ansible&logoColor=white" alt="Ansible">
  <img src="https://img.shields.io/badge/GitHub%20Actions-2088FF?style=for-the-badge&logo=github-actions&logoColor=white" alt="GitHub Actions">
</p>

This repository contains the backend services and complete DevOps infrastructure for **UniCampus**, a MERN-stack application. The architecture features a polyglot microservices system and is designed around a fully automated CI/CD pipeline for robust, repeatable deployments.

**Disclaimer:** This application is designed to be used exclusively by the students of **M. S. Ramaiah Institute of Technology**.

---

## 🏛️ Architecture Overview

This project is architected as a set of containerized microservices managed by Docker Compose for local development and deployed to AWS using an automated CI/CD pipeline.

*   **Node.js Service (`node_service`):** The primary API for the MERN application, handling user authentication, data management, and core business logic.
*   **Flask Service (`flask_service`):** A dedicated Python service responsible for scraping essential data from the college website, processing it, and making it available to the main application.
*   **DevOps Automation:** The entire workflow from code commit to deployment is automated using a suite of modern DevOps tools.

*A visual diagram of the architecture would be placed here.*
`![Architecture Diagram](./docs/architecture.png)`

---

## ✨ Key Features

*   **Microservices Architecture:** Decoupled Node.js and Flask services for maintainability and scalability.
*   **Containerized Environment:** Uses **Docker** and **Docker Compose** to ensure a consistent development and production environment.
*   **Automated CI/CD Pipeline:** Leverages **GitHub Actions** to automatically build, test, and analyze code on every push.
*   **Infrastructure as Code (IaC):** Utilizes **Ansible** playbooks to automate the configuration and deployment of the backend services to AWS EC2.
*   **Automated Code Quality:** Integrated with **SonarCloud** to perform static code analysis, ensuring high-quality, secure, and clean code.
*   **Automated Data Ingestion:** A dedicated Flask scraper service runs periodically to keep application data up-to-date.

---

## 🛠️ Tech Stack

*   **Backend Services:** Node.js, Express.js, Python, Flask
*   **Database:** MongoDB
*   **Containerization:** Docker, Docker Compose
*   **CI/CD:** GitHub Actions
*   **Deployment & Configuration:** Ansible
*   **Code Quality:** SonarCloud
*   **Testing:** Pytest

---

## 🏁 Getting Started

To get a local copy up and running, follow these simple steps.

### Prerequisites

You must have Git and Docker Desktop installed on your machine.
*   [Docker Desktop](https://www.docker.com/products/docker-desktop/)

### Installation & Running Locally

1.  **Clone the repository:**
    ```sh
    git clone https://github.com/iamsjeevan/unicampus-backend.git
    cd unicampus-backend
    ```

2.  **Set up environment variables:**
    Create a `.env` file in the root of the project by copying the example file.
    ```sh
    cp .env.example .env
    ```
    Now, open the `.env` file and add your configuration values (e.g., your MongoDB connection string, JWT secret).

3.  **Run with Docker Compose:**
    This single command will build the Docker images for both the Node.js and Flask services and start the containers in the background.
    ```sh
    docker-compose up -d --build
    ```
    *   The Node.js API will be accessible at `http://localhost:5000` (or the port you define).
    *   The Flask service will be running inside the Docker network.

4.  **To stop the services:**
    ```sh
    docker-compose down
    ```

---

## 📧 Contact

Jeevan S. - [iamsjeevan@gmail.com](mailto:iamsjeevan@gmail.com)

Project Link: [https://github.com/iamsjeevan/unicampus-backend](https://github.com/iamsjeevan/unicampus-backend)
