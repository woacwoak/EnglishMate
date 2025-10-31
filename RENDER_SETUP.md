# Hosting Your Telegram Bot on Render

This guide will walk you through deploying your Python Telegram bot to Render, a Platform as a Service (PaaS) that simplifies hosting.

## Prerequisites

1.  **GitHub Account:** Your bot's code must be in a GitHub repository.
2.  **Render Account:** Sign up at [https://render.com/](https://render.com/).

## Steps

### 1. Push Your Code to GitHub

Ensure your project (including `telegram_bot.py` and `requirements.txt`) is pushed to a new or existing GitHub repository. Make sure your `.env` file is NOT committed (it should be in `.gitignore`).

### 2. Create a New Web Service on Render

1.  Log in to your Render account.
2.  Click on **"New"** -> **"Web Service"**.
3.  Connect your GitHub account if you haven't already, and select the repository containing your bot's code.

### 3. Configure Your Web Service

Fill in the service details as follows:

*   **Name:** Choose a unique name for your bot (e.g., `my-telegram-quiz-bot`).
*   **Region:** Select a region close to you or your users.
*   **Branch:** `main` (or your primary branch).
*   **Root Directory:** Leave blank if your `telegram_bot.py` is in the root of your repository.
*   **Runtime:** `Python 3`
*   **Build Command:** `pip install -r requirements.txt`
*   **Start Command:** `python telegram_bot.py`
*   **Instance Type:** Choose a suitable instance type. The "Free" instance type is usually sufficient for a small bot.

### 4. Add Environment Variables

This is crucial for securely storing your `TELEGRAM_TOKEN` and `HF_TOKEN`.

1.  In the service configuration page, navigate to the **"Environment"** section.
2.  Add the following environment variables:
    *   **Key:** `TELEGRAM_TOKEN`, **Value:** Your actual Telegram Bot Token.
    *   **Key:** `HF_TOKEN`, **Value:** Your actual Hugging Face API Token.

### 5. Deploy

1.  Click **"Create Web Service"**.
2.  Render will now automatically pull your code, install dependencies, and run your bot. You can monitor the deployment logs on the Render dashboard.

Once deployed, your bot will run continuously without you needing to keep your local machine on. Any changes pushed to your GitHub repository's main branch will trigger an automatic redeployment on Render.