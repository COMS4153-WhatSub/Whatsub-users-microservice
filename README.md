# Whatsub Users Microservice (FastAPI)

A user microservice for a subscription management tool, implemented in Python with FastAPI.

## Structure

```
app/
  main.py
  middleware/
  models/
  resources/
  services/
  utils/
```

- middleware: Request logging and error handling
- models: Pydantic schemas for request/response
- resources: FastAPI routers/controllers
- services: Business logic and persistence adapters
- utils: Logger and settings utilities

## Getting Started (conda)

1. Create and activate a conda environment

```bash
conda create -n whatsub-users python=3.12 -y
conda activate whatsub-users
```

2. Install dependencies

```bash
python -m pip install -r requirements.txt
```

3. Configure environment variables

Create a `.env` file with the following variables:

```bash
# Application Settings
APP_NAME=whatsub-users
APP_ENV=development
LOG_LEVEL=INFO
PORT=8080

# Database Settings
DB_HOST=localhost
DB_PORT=3306
DB_USER=whatsub
DB_PASS=your_password_here
DB_NAME=whatsub

# Google OAuth Settings (Required for Google login)
# Get these from Google Cloud Console: https://console.cloud.google.com/apis/credentials
GOOGLE_CLIENT_ID=your-google-client-id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your-google-client-secret

# JWT Settings
# IMPORTANT: Change this to a secure random string in production!
# Generate one with: python -c "import secrets; print(secrets.token_urlsafe(32))"
JWT_SECRET_KEY=your-secret-key-change-in-production
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=30
```

4. Run the server

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Alternative: module mode or direct file
```bash
python -m app.main
# or
python app/main.py
```

5. Open API docs

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Health Check

- GET /health → { "status": "ok" }

## API Endpoints

### Health Check
- GET /health → { "status": "ok" }

### Users API
- POST /users - Create user
- GET /users - List users
- GET /users/{user_id} - Get user by ID
- PATCH /users/{user_id} - Update user
- DELETE /users/{user_id} - Delete user

### Authentication API
- POST /auth/google - Login with Google OAuth

  Request body:
  ```json
  {
    "id_token": "google-id-token-from-oauth-flow"
  }
  ```

  Response:
  ```json
  {
    "user": {
      "id": "user-uuid",
      "email": "user@example.com",
      "full_name": "User Name",
      "primary_phone": null
    },
    "token": {
      "access_token": "jwt-token",
      "token_type": "bearer",
      "expires_in": 1800
    },
    "is_new_user": false
  }
  ```

## Google OAuth Setup

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select an existing one
3. Enable Google+ API (or Google Identity API)
4. Go to **APIs & Services** > **Credentials**
5. Click **Create Credentials** > **OAuth client ID**
6. Choose **Web application**
7. Add authorized redirect URIs (e.g., `http://localhost:8080/auth/callback` for development)
8. Copy the **Client ID** and **Client Secret** to your `.env` file

## Database Migration

### New Database
If you're creating a new database, the service will automatically create the `users` table with the `google_id` column on first startup. No manual migration needed.

### Existing Database
If your `users` table already exists, you need to add the `google_id` column manually.

Connect to MySQL and run:
```sql
ALTER TABLE users 
ADD COLUMN google_id VARCHAR(255) NULL 
AFTER phone;

CREATE UNIQUE INDEX idx_google_id ON users(google_id);
```

#### Verify Migration
Check if the column was added:
```sql
DESCRIBE users;
-- or
SHOW COLUMNS FROM users LIKE 'google_id';
```
