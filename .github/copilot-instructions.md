# Mobywatel-Creator: AI Agent Instructions

## Project Overview
**Mobywatel-Creator** is a didactic Flask application designed to teach layered architecture patterns. It generates mock "mObywatel" documents with user authentication and admin management capabilities.

## Architecture: Strict Layered Pattern

The codebase follows a **5-layer architecture** with clear separation of concerns. Never mix layers:

1. **Edge Layer** (`nginx.conf`) - Reverse proxy, static file serving, SSL termination
2. **WSGI Layer** (`wsgi.py`, Gunicorn) - Process management and HTTP/WSGI translation
3. **Controller Layer** (`app.py`) - Request routing and orchestration ONLY (no business logic)
4. **Service Layer** (`user_auth.py`, `services.py`) - All business logic lives here
5. **Data Layer** (`models.py`) - SQLAlchemy ORM models and schema definitions

### Critical Pattern: Controller delegates to Services
```python
# ✅ CORRECT - app.py delegates to service layer
@app.route("/login", methods=["POST"])
def login():
    success, msg = auth_manager.authenticate_user(username, password)
    return jsonify({"success": success, "message": msg})

# ❌ WRONG - business logic in controller
@app.route("/login", methods=["POST"])
def login():
    user = User.query.filter_by(username=username).first()
    if bcrypt.checkpw(password, user.password):  # Don't do this!
```

## Database & Migrations

- **ORM**: SQLAlchemy with Flask-Migrate (Alembic)
- **Schema**: Defined in `models.py` - models include `User`, `AccessKey`, `Notification`, `Announcement`, `File`
- **Location**: `auth_data/database.db` (configured via `SQLALCHEMY_DATABASE_URI`)
- **Migration commands** (always run after model changes):
  ```bash
  flask db migrate -m "description"
  flask db upgrade
  ```

## Development Workflow

### Running the Application
```bash
# Development mode (Flask dev server)
flask run

# Production mode (Gunicorn)
gunicorn --workers 3 --bind 0.0.0.0:5000 wsgi:application

# Docker (uses docker-compose.yml)
docker-compose up --build
```

### Testing
```bash
# Run all tests with coverage
pytest

# Run specific test file
pytest tests/test_user_auth_extended.py

# Coverage is configured in pytest.ini - target sources: app.py, models.py, services.py, user_auth.py
```

### Load Testing Mode
The app supports a special `APP_ENV_MODE=load_test` environment variable that:
- Disables CSRF protection (`WTF_CSRF_ENABLED = False`)
- Disables rate limiting decorators
- Used by `locustfile.py` for performance testing

**Never use load test mode in production!**

## Security Patterns

### Password Handling
All password operations use bcrypt with 12 rounds (`UserAuthManager.BCRYPT_ROUNDS = 12`):
```python
# In user_auth.py
hashed = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt(rounds=12))
```

### Rate Limiting
Applied via `@limiter.limit()` decorators on public endpoints (login, register). Configuration in `production_config.py`:
```python
RATELIMIT_STORAGE_URL = "redis://redis:6379"  # Production uses Redis
```

### CSRF Protection
Enabled by default via `flask-wtf` (`CSRFProtect(app)`). All forms require CSRF tokens. Disabled only in test/load-test modes.

### Session Management
- Uses Redis-backed sessions (`SESSION_TYPE = "redis"`)
- Session cookie settings in `production_config.py`: `SESSION_COOKIE_SECURE`, `SESSION_COOKIE_HTTPONLY`, `SESSION_COOKIE_SAMESITE = "Lax"`

## Key Services (services.py)

### AccessKeyService
Manages registration access keys with expiration:
- `generate_access_key(description, expires_days)` - Creates new key
- `validate_access_key(key_val)` - Checks validity and expiration
- `use_access_key(key_val)` - Marks key as used and deactivates it

### NotificationService
User notification system with read/unread state management

### AnnouncementService
Site-wide announcements with expiration and active status

### StatisticsService
Aggregates user and system statistics

## HTML Manipulation Pattern

The app uses BeautifulSoup to modify HTML templates (`replace_html_data` function in `app.py`):
```python
# Searches by CSS class, modifies sibling text nodes
soup = BeautifulSoup(html_content, "html.parser")
element = soup.find(class_="dataSurnameKocpPersonName")
if element and element.find_next_sibling(string=True):
    element.find_next_sibling(string=True).replace_with(new_value)
```

## File Structure Conventions

- `user_data/<username>/` - User-specific generated files (dowodnowy.html, QR codes)
- `auth_data/` - SQLite database location
- `logs/` - Rotating logs (`app.log`, `user_activity.log`) with 5MB rotation
- `static/` - Frontend assets (CSS, JS, images)
- `templates/` - Jinja2 templates
- `tests/` - Pytest test suite with fixtures in `conftest.py`

## Admin Panel Routes

All admin routes require `admin_required` decorator and are prefixed with `/admin/`:
- `/admin/login` - Admin authentication (rate limited: 10 per minute)
- `/admin/api/users` - User management
- `/admin/api/access-keys` - Key generation/management
- `/admin/api/backup/full` - Full system backup (creates zip with DB + user files)
- `/admin/api/impersonate/start` - Admin impersonation feature

## Environment Variables

Critical production variables (see `production_config.py`):
```bash
FLASK_ENV=production  # Changes config class
SECRET_KEY=<random-secret>  # Required in production
ADMIN_USERNAME=<admin-user>
ADMIN_PASSWORD=<admin-pass>
APP_ENV_MODE=development|production|load_test
RATELIMIT_STORAGE_URL=redis://redis:6379
```

## Logging Strategy

Two separate rotating log files (5MB each, 5 backups):
1. **app.log** - General application logs (Flask, SQLAlchemy)
2. **user_activity.log** - User action audit trail with IP and username

Log directory size management runs every 5 minutes (`manage_log_directory_size()` function).

## PESEL Generator Module

`pesel_generator.py` generates valid Polish national ID numbers with:
- Century modifiers for month field (e.g., +20 for 2000-2099)
- Gender-specific serial numbers (odd=male, even=female)
- Control digit calculation with weighted sum algorithm
- Special validation for leap years and invalid dates

## Common Gotchas

1. **Never modify `models.py` without running migrations** - The schema will be out of sync
2. **Controller functions should be thin** - Business logic belongs in `services.py` or `user_auth.py`
3. **Use `@login_required` decorator** - Imported from `flask_login` for protected routes
4. **Test with CSRF enabled** - The default test config disables it (`WTF_CSRF_ENABLED = False`)
5. **Session data uses Redis** - Local development needs Redis running on port 6379
6. **File operations use SHA256 hashing** - In `POST /` endpoint, files are only written if hash changes (optimization)

## Testing Patterns

Test fixtures in `tests/conftest.py`:
- `app` - Flask app with in-memory SQLite
- `db_session` - Scoped database session with auto-rollback
- `user_auth_manager` - Initialized UserAuthManager instance
- `access_key_service` - AccessKeyService with valid test keys
- `registered_user` - Pre-created test user fixture

Tests use `@pytest.fixture` extensively and follow naming: `test_<functionality>_<scenario>`
