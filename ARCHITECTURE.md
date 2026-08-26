# Architecture Documentation

## System Overview

The Psychological Report Generator is a local-first desktop application built with a modern tech stack designed for security, performance, and maintainability.

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                     Electron Desktop App                     │
│  ┌───────────────────────────────────────────────────────┐  │
│  │                  React Frontend                        │  │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐            │  │
│  │  │  Pages   │  │Components│  │ Services │            │  │
│  │  └──────────┘  └──────────┘  └──────────┘            │  │
│  │       │              │              │                  │  │
│  │       └──────────────┴──────────────┘                  │  │
│  │                      │                                  │  │
│  │                 API Client (Axios)                     │  │
│  └──────────────────────┼───────────────────────────────┘  │
└─────────────────────────┼──────────────────────────────────┘
                          │ HTTP (localhost)
                          ▼
┌─────────────────────────────────────────────────────────────┐
│                    FastAPI Backend                           │
│  ┌───────────────────────────────────────────────────────┐  │
│  │                  API Routes                            │  │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐            │  │
│  │  │ Reports  │  │Documents │  │Templates │            │  │
│  │  └──────────┘  └──────────┘  └──────────┘            │  │
│  └──────┬────────────────┬────────────────┬──────────────┘  │
│         │                │                │                  │
│  ┌──────▼────────┐  ┌────▼─────┐  ┌──────▼──────┐          │
│  │   Services    │  │ Database │  │   Ollama    │          │
│  │  - Generator  │  │  Models  │  │   Client    │          │
│  │  - Processor  │  │  - ORM   │  │             │          │
│  └───────────────┘  └──────────┘  └──────┬──────┘          │
│                           │               │                  │
│                     ┌─────▼───────┐       │                  │
│                     │   SQLite    │       │                  │
│                     │ (Local DB)  │       │                  │
│                     └─────────────┘       │                  │
└───────────────────────────────────────────┼──────────────────┘
                                            │ HTTP
                                            ▼
                                    ┌───────────────┐
                                    │    Ollama     │
                                    │  (Llama 3.1)  │
                                    │  Local Model  │
                                    └───────────────┘
```

## Technology Stack

### Frontend Layer
- **React 18**: Modern UI library with hooks
- **TypeScript**: Type safety and better developer experience
- **TailwindCSS**: Utility-first CSS framework
- **React Router**: Client-side routing
- **Axios**: HTTP client for API communication
- **Lucide React**: Icon library

### Desktop Layer
- **Electron**: Cross-platform desktop framework
- **Electron Builder**: Package and distribute the app

### Backend Layer
- **FastAPI**: Modern Python web framework
- **Uvicorn**: ASGI server
- **SQLAlchemy**: ORM for database operations
- **Pydantic**: Data validation

### Data Layer
- **SQLite**: Lightweight embedded database
- **SQLCipher**: Encryption for SQLite (planned)

### AI Layer
- **Ollama**: Local LLM inference engine
- **Llama 3.1 8B**: Local language model used for report generation

### Testing
- **Jest**: JavaScript testing framework
- **React Testing Library**: React component testing
- **Pytest**: Python testing framework

## Project Structure

```
psychological-report-generator/
├── backend/
│   ├── api/                    # API route handlers
│   │   ├── reports.py         # Report endpoints
│   │   ├── documents.py       # Document endpoints
│   │   └── templates.py       # Template endpoints
│   ├── database/              # Database layer
│   │   ├── db.py             # Database configuration
│   │   └── models.py         # SQLAlchemy models
│   ├── services/             # Business logic
│   │   ├── ollama_client.py  # Ollama integration
│   │   ├── document_processor.py  # Document processing
│   │   └── report_generator.py    # Report generation
│   ├── tests/                # Backend tests
│   ├── data/                 # Local data storage
│   ├── main.py              # Application entry point
│   ├── seed_data.py         # Database seeding
│   └── requirements.txt     # Python dependencies
├── frontend/
│   ├── electron/            # Electron main process
│   │   ├── main.js         # Electron entry point
│   │   └── preload.js      # Preload script
│   ├── src/
│   │   ├── components/     # Reusable React components
│   │   │   └── Layout.tsx  # Main layout component
│   │   ├── pages/          # Page components
│   │   │   ├── HomePage.tsx
│   │   │   ├── NewReportPage.tsx
│   │   │   ├── ReportsPage.tsx
│   │   │   ├── TemplatesPage.tsx
│   │   │   └── DocumentsPage.tsx
│   │   ├── services/       # API services
│   │   │   └── api.ts      # API client
│   │   ├── App.tsx         # Main app component
│   │   ├── main.tsx        # React entry point
│   │   └── index.css       # Global styles
│   ├── tests/              # Frontend tests
│   ├── package.json        # Node dependencies
│   └── vite.config.ts      # Vite configuration
├── README.md               # Project overview
├── SETUP.md               # Setup instructions
└── ARCHITECTURE.md        # This file
```

## Data Flow

### Report Generation Flow

1. **User Input**
   - User fills out report form in React frontend
   - Selects template, documents, and adds additional info

2. **API Request**
   - Frontend sends POST request to `/api/reports/generate`
   - Request includes template_id, document_ids, and inputs

3. **Backend Processing**
   - FastAPI receives request
   - Retrieves template from database
   - Retrieves selected documents from database
   - Builds prompt from template + documents + inputs

4. **AI Generation**
   - Sends prompt to Ollama via HTTP
   - Ollama runs the Llama 3.1 8B model locally
   - Returns generated report text

5. **Storage**
   - Backend saves report to SQLite database
   - Returns report data to frontend

6. **Display**
   - Frontend displays generated report
   - User can view, edit, or export

### Document Upload Flow

1. User selects file in frontend
2. Frontend sends multipart/form-data to `/api/documents/upload`
3. Backend saves file to local filesystem
4. Backend extracts text content (if supported format)
5. Backend saves document metadata to database
6. Returns document info to frontend

## Security Considerations

### Local-First Design
- All data stored locally
- No external API calls (except to local Ollama)
- No telemetry or tracking

### Data Protection
- SQLite database stored in user data directory
- Planned: SQLCipher encryption for database
- File uploads stored in isolated directory
- No cloud storage or backups

### Network Security
- Backend only listens on localhost (127.0.0.1)
- CORS restricted to local origins
- No authentication needed (single-user local app)

Note:

- The app does not require internet for normal operation.
- Internet is only used if a user explicitly chooses to download an AI model (for example, the `llama3.1:8b` model via Ollama).

## Performance Considerations

### Frontend
- React lazy loading for routes
- Virtualized lists for large datasets
- Optimistic UI updates
- Debounced search/filter inputs

### Backend
- Async/await for I/O operations
- Database connection pooling
- Indexed database queries
- Streaming responses for large reports

### AI Inference
- Llama 3.1 8B chosen for output quality; runs locally with no network latency
- Configurable token limits
- Timeout handling for long generations
- Local inference (no network latency)

## Scalability

### Current Limitations
- Single-user application
- Local SQLite database
- Limited by local hardware for AI inference

### Future Enhancements
- Support for larger models (Llama 2, Mistral)
- PDF/DOCX document parsing
- Advanced text extraction
- Report templates with variables
- Export to multiple formats (PDF, DOCX)
- Batch report generation
- Database encryption
- Backup/restore functionality

## Testing Strategy

### Unit Tests
- Backend: Pytest for API endpoints and services
- Frontend: Jest for components and utilities

### Integration Tests
- API endpoint testing with TestClient
- Database operations testing
- Ollama integration testing (mocked)

### E2E Tests (Planned)
- Playwright for full workflow testing
- Report generation end-to-end
- Document upload and processing

## Deployment

### Development
- Backend: `python main.py` (hot reload)
- Frontend: `npm run dev` (Vite dev server)
- Electron: `npm run electron:dev`

### Production
- Build frontend: `npm run build`
- Package with Electron Builder: `npm run electron:build`
- Distributable includes:
  - Compiled React app
  - Electron runtime
  - Python backend (bundled)
  - SQLite database

### Distribution
- Windows: NSIS installer (.exe)
- macOS: DMG installer
- Linux: AppImage

## Maintenance

### Dependencies
- Regular updates for security patches
- Pin major versions for stability
- Test updates in development first

### Database Migrations
- SQLAlchemy Alembic for schema changes
- Backup before migrations
- Rollback capability

### Monitoring
- Local logging to files
- Error tracking in development
- No external monitoring (privacy)

## Future Architecture Considerations

### Multi-User Support
- Add authentication layer
- User-specific data isolation
- Role-based access control

### Cloud Sync (Optional)
- End-to-end encrypted sync
- User-controlled cloud storage
- Conflict resolution

### Plugin System
- Custom report templates
- Third-party integrations
- Extended document formats
