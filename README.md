---
title: Smart Clinic V2
emoji: 🏥
colorFrom: blue
colorTo: green
sdk: docker
pinned: false
app_port: 7860
---

# Smart Clinic Management System

A comprehensive, open-source clinic management solution built with modern technologies for scalability and performance.

## 🚀 Features

- **Multi-tenant Architecture**: Isolated data for each clinic
- **Role-based Access Control**: Super admin, admin, doctor, receptionist roles
- **AI-powered Assistant**: Natural language processing for common tasks
- **Real-time Dashboard**: Live analytics and clinic metrics
- **Patient Management**: Complete patient records and treatment history
- **Appointment Scheduling**: Smart booking and calendar integration
- **Financial Tracking**: Revenue, expenses, and payment tracking
- **Security First**: Enterprise-grade security and compliance

## 🛠 Tech Stack

### Backend
- **Framework**: FastAPI (Python)
- **Database**: PostgreSQL with SQLAlchemy ORM
- **Authentication**: JWT with refresh tokens
- **AI Integration**: Groq API for natural language processing
- **Caching**: Redis for performance optimization
- **Background Jobs**: Celery for async tasks

### Frontend
- **Framework**: React 18 with Vite
- **Styling**: Tailwind CSS with custom dark/light themes
- **State Management**: React Context API
- **Routing**: React Router v6
- **UI Components**: Custom-built reusable components

## 🏗 Architecture

```
backend/
├── ai/                 # AI agent and tools
├── core/              # Core utilities and configurations
├── crud/              # Database operations
├── middleware/        # Request processing middleware
├── models/            # Database models
├── routers/           # API endpoints
├── services/          # Business logic
├── tasks/             # Background job definitions
├── tests/             # Unit and integration tests
└── utils/             # Helper functions

frontend/
├── src/
│   ├── components/    # Reusable UI components
│   ├── pages/         # Route-specific components
│   ├── hooks/         # Custom React hooks
│   ├── utils/         # Utility functions
│   ├── api/           # API client and requests
│   └── contexts/      # React context providers
```

## 🚀 Quick Start

### Prerequisites
- Python 3.9+
- Node.js 18+
- PostgreSQL
- Redis (for caching)

### Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd smart-clinic
```

2. Backend setup:
```bash
cd backend
pip install -r requirements.txt

# Create environment file
cp .env.example .env
# Edit .env with your configuration

# Run database migrations
python -m alembic upgrade head

# Start the server
uvicorn main:app --reload
```

3. Frontend setup:
```bash
cd frontend
npm install

# Create environment file
cp .env.example .env
# Edit .env with your configuration

# Start development server
npm run dev
```

## 🛡️ Security

- JWT authentication with refresh token rotation
- Role-based access control
- Input validation and sanitization
- SQL injection prevention
- XSS protection
- Rate limiting
- Audit logging

## 🧪 Testing

### Backend Testing
The backend uses **pytest**.
```bash
cd backend
# Run all tests
pytest
# Run detailed tests with coverage
pytest --cov=backend
```

### Frontend Testing
The frontend uses **Vitest** and **React Testing Library**.
```bash
cd frontend
# Run tests
npm test
# Run tests with UI
npm run test:ui
```

### CI/CD Pipeline
- **Validation**: On every PR/Push to `main`.
- **Jobs**:
    - `backend-tests`: Postgres Service + Pytest.
    - `frontend-tests`: Node.js + Vitest.
    - `security-scan`: Local security audit.
- **Deployment**: Automatic deployment to production only if checks pass.

## 🛡️ Monitoring & Security
- **Error Tracking**: Integrated with **Sentry** (Backend & Frontend).
- **Health Checks**:
    - Basic: `/health` (Liveness)
    - Detailed: `/health/detailed` (DB, Redis, Disk, AI status)
- **Security**:
    - Rate Limiting (200 req/min global).
    - Strict CORS Policy.
    - Automated Vulnerability Scanning.

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🤝 Contributing

Contributions are welcome! Please read our contributing guidelines before submitting pull requests.

## 📞 Support

For support, please open an issue in the GitHub repository.