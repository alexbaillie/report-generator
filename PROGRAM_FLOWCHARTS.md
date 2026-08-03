# Program Flowcharts: User Inputs and Outputs

These charts describe the current report generator as implemented in the live codebase.

## 1. Whole App Data Flow

```mermaid
flowchart LR
    U["User"]
    UI["React / Electron UI"]
    API["FastAPI backend at 127.0.0.1:8000"]
    DB["SQLite database via SQLAlchemy"]
    FS["Uploaded files on disk"]
    AI["Local Ollama model"]
    OUT["Visible app output / downloaded files"]

    U -->|"Choose pages, type form data, upload files, click buttons"| UI
    UI -->|"Axios requests"| API
    API -->|"Create/read/update/delete templates, documents, reports"| DB
    API -->|"Save uploaded source documents"| FS
    API -->|"Send prompts for generated report sections"| AI
    AI -->|"Generated clinical text"| API
    API -->|"JSON responses"| UI
    UI -->|"Lists, previews, report detail screens, .txt export"| OUT
```

## 2. Template Inputs and Outputs

```mermaid
flowchart TD
    A["User opens Templates page"]
    B["User enters template name, description, type, content, default flag"]
    C{"Creating or editing?"}
    D["POST /api/templates/"]
    E["PUT /api/templates/{id}"]
    F["Template row saved in database"]
    G["GET /api/templates/"]
    H["Templates shown in Templates page"]
    I["Template also becomes selectable in New Report page"]

    A --> B
    B --> C
    C -->|"New Template"| D
    C -->|"Edit existing"| E
    D --> F
    E --> F
    F --> G
    G --> H
    G --> I
```

User inputs:
- Template name
- Description
- Template type
- Template content or JSON section schema
- Default-template checkbox

Program outputs:
- Saved template records
- Template cards in the Templates page
- Dynamic form sections on the New Report page

## 3. Document Upload Inputs and Outputs

```mermaid
flowchart TD
    A["User opens Documents page"]
    B["User uploads .txt, .pdf, .doc, or .docx"]
    C["POST /api/documents/upload multipart form-data"]
    D["Backend saves file to backend/data/uploads"]
    E{"File type"}
    F["Read text directly"]
    G["Extract PDF text with PyPDF2"]
    H["Extract DOCX paragraph text with python-docx"]
    I["Return unsupported/binary/error message"]
    J["Document row saved in database"]
    K["GET /api/documents/"]
    L["Documents list and extracted text preview shown in UI"]

    A --> B --> C --> D --> E
    E -->|Text| F
    E -->|PDF| G
    E -->|DOCX| H
    E -->|DOC or unknown binary| I
    F --> J
    G --> J
    H --> J
    I --> J
    J --> K --> L
```

User inputs:
- Source document file
- Delete confirmation when removing a document

Program outputs:
- Stored uploaded file
- Extracted text content in the database
- Document list and preview
- Deletion result message

## 4. New Report Generation Inputs and Outputs

```mermaid
flowchart TD
    A["User opens New Report page"]
    B["GET /api/templates/"]
    C["Default or selected template loaded"]
    D["Frontend parses template content into sections and fields"]
    E["User fills dynamic fields"]
    F["User uploads or pastes test score tables"]
    G["User clicks Generate Report"]
    H["Frontend gathers non-empty section inputs"]
    I{"For each section with input"}
    J["POST /api/reports/generate-section"]
    K["Backend builds section prompt from template + inputs + optional docs"]
    L["Ollama generates section text"]
    M["Frontend stores generated section content"]
    N["POST /api/reports/generate"]
    O["Backend combines section outputs into one report body"]
    P["Report row saved in database"]
    Q["UI navigates to /reports/{id}"]
    R["Generated report displayed"]

    A --> B --> C --> D
    D --> E
    D --> F
    E --> G
    F --> G
    G --> H --> I
    I -->|"Yes"| J --> K --> L --> M --> I
    I -->|"All done"| N --> O --> P --> Q --> R
```

User inputs:
- Selected template
- Dynamic section field values
- Dates, text fields, text areas, selects, checkboxes, multi-selects, tables, and file names
- Test table type, custom test name, pasted table HTML/text, table description, uploaded table files

Program outputs:
- AI-generated text for each completed section
- Combined report content
- Saved report record with title, patient name, report type, and content
- Report detail screen

Current implementation note:
- The report save step currently combines generated section text into plain text/Markdown-style content.
- `patient_name` is currently hardcoded as `Patient Name` in the frontend submit flow.
- `document_ids` are currently sent as an empty list from the New Report page, even though the backend can include document text when IDs are provided.

## 5. Report Viewing, Export, and Delete Flow

```mermaid
flowchart TD
    A["User opens Reports page"]
    B["GET /api/reports/"]
    C["Reports list displayed"]
    D{"User action"}
    E["Select report"]
    F["Report content preview displayed"]
    G["Click Export"]
    H["Browser creates text/plain Blob"]
    I["Download {report_title}.txt"]
    J["Click Delete"]
    K["Confirm deletion"]
    L["DELETE /api/reports/{id}"]
    M["Report removed from database and list"]

    A --> B --> C --> D
    D --> E --> F
    D --> G --> H --> I
    D --> J --> K --> L --> M
```

User inputs:
- Report selection
- Export click
- Delete click and confirmation

Program outputs:
- Report preview
- Downloaded `.txt` file
- Updated reports list after deletion

## 6. AI Section Prompt Flow

```mermaid
flowchart TD
    A["Section inputs from user"]
    B["Selected template row"]
    C["Optional source document rows"]
    D["build_section_prompt"]
    E["Prompt includes role, report type, section name, instructions"]
    F["Prompt adds document text if document IDs were supplied"]
    G["Prompt adds field labels and values"]
    H["Prompt adds AI_use guidance or default section guidance"]
    I["Ollama /api/generate"]
    J["Generated section text returned to frontend"]

    A --> D
    B --> D
    C --> D
    D --> E --> F --> G --> H --> I --> J
```

Main input to the model:
- Template type
- Section name
- User-entered section fields
- Optional extracted document text
- Optional `AI_use:` guidance from the template content

Main output from the model:
- A single generated section body, without the section heading.
