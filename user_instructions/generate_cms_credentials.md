# How to Generate New CMS Credentials

This document explains how to create a new user for the Content Management System (CMS), which effectively generates new credentials for accessing it.

## Overview

The system uses a JWT-based authentication system with a dedicated registration endpoint. To generate new credentials, you need to send a request to this endpoint with the new user's information.

## Using `curl` to Register a New User

You can register a new user by sending a `POST` request to the `/api/v1/auth/register` endpoint.

### Command

```bash
curl -X POST "http://127.0.0.1:8000/api/v1/auth/register" \
-H "Content-Type: application/json" \
-d '{
  "email": "new_user_email@example.com",
  "password": "a_strong_password",
  "full_name": "New User Name",
  "role": "writer",
  "is_active": true
}'
```

### Command Breakdown

1.  **`curl -X POST "http://127.0.0.1:8000/api/v1/auth/register"`**: This part of the command specifies that you are sending a `POST` request to the registration endpoint of your local backend server.

2.  **`-H "Content-Type: application/json"`**: This header tells the server that the data you are sending is in JSON format.

3.  **`-d '{...}'`**: This flag contains the data payload for the new user.

### Payload Fields

*   **`email`** (string, required): The email address for the new user. This will be used as the username for logging in. **It must be unique.**
*   **`password`** (string, required): The password for the new user. Choose a strong, secure password.
*   **`full_name`** (string, optional): The user's full name.
*   **`role`** (string, required): The role assigned to the user, which determines their permissions. Common roles are `writer` or `editor`.
*   **`is_active`** (boolean, required): Set this to `true` to ensure the account is enabled immediately upon creation.

## After Registration

Once the command is executed successfully, a new user will be created in the database. You can then use the `email` and `password` you provided to log into the CMS via the login page or to request a JWT access token from the `/api/v1/auth/token` endpoint.
