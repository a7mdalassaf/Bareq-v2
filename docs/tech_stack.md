# RettLock Info - Technical Stack Documentation

## Core Technologies

### Backend
- **Framework**: Flask (Python)
- **Database**: SQLite with SQLAlchemy ORM
- **Authentication**: Custom auth service
- **Background Jobs**: APScheduler

### Frontend
- **Framework**: Bootstrap 5
- **JavaScript**: Vanilla JS with Fetch API
- **Template Engine**: Jinja2
- **UI Components**: 
  - Bootstrap Tooltips
  - Font Awesome Icons
  - Custom Toast Notifications

### External APIs
- **TTLock API**: Smart lock management
  - Lock status
  - Passcode management
  - Access control
- **Tuya API**: Smart device control
  - Device status
  - Light control
  - State management

## Project Structure

### Core Components
- `web_app.py`: Main Flask application
- `models.py`: Database models and schemas
- `jobs.py`: Background job definitions

### Services Layer
- `services/`
  - `auth_service.py`: Authentication and authorization
  - `audit_service.py`: Activity logging
  - `credential_service.py`: API credential management

### Routes
- `routes/`
  - `admin.py`: Admin panel routes
  - `locks.py`: Lock management endpoints

### Adapters
- `ttlock_adapter.py`: TTLock API integration
- `tuya_adapter.py`: Tuya API integration

### Templates
- `templates/`
  - `index.html`: Main dashboard
  - Various component templates

## Architecture

### Data Flow
1. User requests -> Flask Routes
2. Routes -> Services
3. Services -> External APIs/Database
4. Response -> Jinja2 Templates
5. Templates -> User Interface

### State Management
- Server-side state: SQLite Database
- Client-side state: DOM data attributes
- Real-time updates: Periodic AJAX polling

### Security
- API credential encryption
- Session-based authentication
- CSRF protection
- Secure password handling

## Development Tools
- Version Control: Git
- IDE Support: VS Code
- API Testing: Postman
- Database Management: SQLite Browser
