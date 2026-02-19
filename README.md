# ClinicOps - Clinic Operations Management System

ClinicOps is a robust, multi-tenant backend server designed to manage clinic operations efficiently. It provides a comprehensive set of features for patient management, visit tracking, billing, and detailed reporting.

## 🏗 Architecture

The project follows a modular, clean architecture using Django and Django REST Framework, specifically designed to scale and serve a multi-tenant frontend (Next.js).

### Tech Stack
- **Framework:** Django 5.0 + Django REST Framework 3.14
- **Database:** PostgreSQL 16
- **Caching & Broker:** Redis 7
- **Task Queue:** Celery 5.3 (for background jobs & scheduled tasks)
- **API Documentation:** drf-spectacular (OpenAPI/Swagger)
- **Containerization:** Docker & Docker Compose

### Key Architectural Patterns
- **Multi-Tenant Isolation:** Every request is scoped to a clinic via JWT claims. The `ClinicScopedMixin` ensures data isolation across all API endpoints.
- **Phone-Based Authentication:** Uses phone numbers instead of emails for user identification, with JWT stored in secure, HTTP-only cookies.
- **Custom ID Generation:** Human-readable IDs with prefixes (e.g., `PAT-`, `VIS-`, `INV-`) generated server-side.
- **Soft Deletion:** Critical data (patients, services) use soft deletes to prevent accidental data loss.
- **Immutable Audit Trail:** All sensitive operations are automatically logged in an immutable audit log.

### Application Modules (`apps/`)
- **`accounts`**: Custom user model, phone-based auth, and role-based permissions.
- **`clinics`**: Clinic settings and service catalog management.
- **`patients`**: Central registry for patient records.
- **`visits`**: Lifecycle management of patient visits and service assignments.
- **`billing`**: Invoicing, payment processing, and daily reconciliations.
- **`reports`**: Dashboard metrics and PDF/CSV export generation.
- **`audit`**: Automated auditing of system changes.
- **`core`**: Shared utilities, base models, and global exception handling.

---

## 🚀 Getting Started

### Prerequisites
- Docker and Docker Compose installed.
- Python 3.12+ (optional, for local linting/tooling).

### 1. Environment Configuration
The application uses environment-specific `.env` files. Start by creating your development environment file:

```bash
cp .env.example .env.dev
```

Edit `.env.dev` and update the `SECRET_KEY` and any database credentials if necessary.

### 2. Running the Application
We use a `Makefile` to simplify common operations.

**Development Mode:**
```bash
# Build the images
make build ENV=dev

# Start all services (Backend, DB, Redis, Celery, Beat)
make up ENV=dev
```
The API will be available at `http://localhost:8000`.

**Production Mode:**
```bash
make build ENV=prod
make up-d ENV=prod
```

### 3. Initial Setup
After starting the containers, you need to set up the database and create an admin user:

```bash
# Apply migrations
make migrate ENV=dev

# Create a superuser
make superuser ENV=dev
```

---

## 🛠 Development Workflow

### Common Makefile Commands
| Command | Description |
|---------|-------------|
| `make up` | Start containers |
| `make down` | Stop containers |
| `make logs` | Follow logs |
| `make shell` | Open Django shell |
| `make test` | Run test suite |
| `make makemigrations` | Generate new migration files |
| `make migrate` | Apply migrations |

### API Documentation
Once the server is running, you can access the interactive API documentation:
- **Swagger UI:** `http://localhost:8000/api/docs/`
- **ReDoc:** `http://localhost:8000/api/docs/redoc/`
- **Schema (YAML):** `http://localhost:8000/api/schema/`

### Running Tests
To ensure system integrity, run the tests frequently:
```bash
make test ENV=dev
```

---

## 📂 Project Structure
```text
clinicops-server/
├── apps/           # Modular Django applications
├── config/         # Project-wide settings and URL routing
├── docker/         # Dockerfiles for dev and prod
├── docs/           # Detailed architectural and API documentation
├── requirements/   # Python dependency files
├── templates/      # Email and document templates
├── Makefile        # Command shortcuts
└── compose.dev.yml # Docker Compose for development
```
