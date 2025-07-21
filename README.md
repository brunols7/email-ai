# AI Email Sorter

[![Build Status](https://img.shields.io/badge/build-passing-brightgreen)](https://github.com/brunols7/email-ai)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

An intelligent email management application that uses AI to automatically categorize, summarize, and archive your Gmail inbox, helping you focus on what matters most.

## Overview

AI Email Sorter is a web application designed to bring order to chaotic inboxes. By connecting your Gmail account(s), you can define custom categories with descriptions. The application's AI engine, powered by Google's Generative AI, reads new emails, generates a concise summary, assigns the appropriate category, and archives the email from your Gmail inbox.

Once processed, you can view your categorized emails within the app, read their AI-generated summaries, and perform bulk actions like deleting emails or using an AI-powered agent to automatically handle the unsubscribe process.

## Key Features

* **Google OAuth 2.0:** Securely sign in and connect one or more Gmail accounts.
* **AI-Powered Categorization:** Uses Google's Generative AI to analyze email content and sort it into user-defined categories based on natural language descriptions.
* **AI-Generated Summaries:** Every processed email includes a one-sentence summary, allowing you to grasp its content at a glance.
* **Automatic Archiving:** After an email is successfully imported and categorized, it is automatically archived in your Gmail inbox to keep it clean.
* **Bulk Actions:** Select multiple emails within a category to delete them permanently or initiate the unsubscribe process.
* **AI Unsubscribe Agent:** A sophisticated agent that finds the unsubscribe link in an email, navigates to the page using a headless browser (Playwright), and uses AI to identify and click the final confirmation button.
* **Periodic Syncing:** A GitHub Actions workflow runs on a schedule to automatically process new emails from all connected accounts.

## Tech Stack

* **Backend:** FastAPI
* **Database:** PostgreSQL
* **ORM:** SQLModel
* **AI / LLM:** Google Generative AI (Gemini 1.5 Flash)
* **Authentication:** Google OAuth 2.0 (Authlib)
* **Web Automation:** Playwright
* **Containerization:** Docker & Docker Compose
* **Testing:** Pytest & Pytest-Mock

## Getting Started

Follow these instructions to set up and run the project in a local development environment.

### Prerequisites

* Docker
* Docker Compose

### Configuration

1.  **Clone the repository:**
    ```sh
    git clone [https://github.com/brunols7/email-ai.git](https://github.com/brunols7/email-ai.git)
    cd email-ai
    ```

2.  **Create an environment file:**
    Create a file named `.env` in the root of the project and add the following environment variables. You will need to get credentials from the Google Cloud Console for OAuth and the Generative AI API.

    ```dotenv
    # .env file

    # For Google OAuth 2.0
    GOOGLE_CLIENT_ID="YOUR_GOOGLE_CLIENT_ID"
    GOOGLE_CLIENT_SECRET="YOUR_GOOGLE_CLIENT_SECRET"

    # For Google Generative AI API
    GOOGLE_API_KEY="YOUR_GOOGLE_API_KEY"
    
    # A strong, random string for session signing
    SECRET_KEY="YOUR_SECRET_KEY"
    
    # Database connection string for Docker Compose
    DATABASE_URL="postgresql://postgres:mysecretpassword@db:5432/email_ai_db"
    
    # A secret to protect the cron job webhook
    CRON_SECRET="A_STRONG_RANDOM_SECRET_FOR_CRON"
    ```

### Running the Application

1.  **Build and run the services using Docker Compose:**
    ```sh
    docker-compose up --build
    ```

2.  **Access the application:**
    The application will be running at `http://localhost:8000`.

## Usage

1.  **Sign In:** Navigate to the application and click "Login with Google to Get Started".
2.  **Create Categories:** Go to the "My Categories" page and create categories with descriptive names and descriptions to guide the AI.
3.  **Sync Emails:** Click the "Sync New Emails" button to start the initial processing of your inbox. The app will fetch the latest emails, summarize and categorize them, and then archive them in Gmail.
4.  **Manage Emails:** Click on a category to view the summarized emails. Use the checkboxes and bulk action buttons to delete emails or let the AI agent unsubscribe you from mailing lists.

## Running Tests

To run the automated tests, execute the following command in the root directory:

```sh
python -m pytest
```

## Deployment

The application is containerized with Docker and ready for deployment on services like Render, Fly.io, or any platform that supports Docker containers.

The cron job for periodic email syncing is managed via a GitHub Actions workflow defined in `.github/workflows/sync_emails.yml`. You will need to configure a `SYNC_URL` secret in your GitHub repository settings, pointing to the `/cron/sync-all/{CRON_SECRET}` endpoint of your deployed application.

## License

This project is licensed under the MIT License.