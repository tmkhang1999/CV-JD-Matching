# CV-JD Matcher - Modern UI

A beautiful, minimalist single-page application for CV-JD matching with a modern, clean design.

## Features

### 1. Upload Tab
- **Upload CVs**: Drag-and-drop or click to upload CV files (PDF, DOCX, DOC)
- **Upload JDs**: Drag-and-drop or click to upload Job Description files
- **File Management**: View uploaded files with metadata
- **Delete Files**: Remove CVs and JDs from the system with one click
- **Real-time Updates**: UI refreshes immediately after upload/delete

### 2. CVs Tab
- **View All CVs**: Searchable table with all uploaded CVs
- **Schema Display**: View complete structured CV data (extracted information)
- **Filter & Search**: Full-text search across all fields
- **Sorting**: Click column headers to sort by ID, Name, or Title
- **View Details**: Click "View" button to see complete JSON schema with all extracted data

### 3. JDs Tab
- **View All JDs**: Searchable table with all uploaded Job Descriptions
- **Schema Display**: View complete structured JD data
- **Filter & Search**: Full-text search across all fields
- **Sorting**: Click column headers to sort by ID, Company, or Job Title
- **View Details**: Click "View" button to see complete JSON schema

### 4. CV Matching Tab
- **Select CV**: Choose a CV from dropdown
- **Find JDs**: Click button to find top 5 matching Job Descriptions
- **View Matches**: Results shown in sortable table with scores
- **Rerank with LLM**: Use AI to intelligently rerank the top 5 results
- **Score Color Coding**: 
  - Green (85+): Strong match
  - Orange (70-84): Good match
  - Red (<70): Potential match
- **View Match Details**: Click "View" to see detailed match analysis

### 5. JD Matching Tab
- **Select JD**: Choose a Job Description from dropdown
- **Find CVs**: Click button to find top 5 matching CVs
- **View Matches**: Results shown in sortable table with scores
- **Rerank with LLM**: Use AI to intelligently rerank the top 5 results
- **Score Color Coding**: Same as CV Matching
- **View Match Details**: Click "View" to see detailed match analysis

## Design Philosophy

- **Minimalist**: Clean, uncluttered interface with focus on content
- **Neutral Colors**: Grayscale palette (neutrals with blue accent)
- **Whitespace**: Generous spacing for readability
- **Flat Design**: Subtle rounded corners, no decorative elements or shadows
- **Modern Typography**: System fonts (-apple-system, Segoe UI, etc.)
- **Developer Tool Aesthetic**: Professional, efficient appearance
- **Responsive**: Works on desktop and tablet

## Color Palette

- **Neutral 50**: Background (#fafafa)
- **Neutral 100**: Light surfaces (#f5f5f5)
- **Neutral 200**: Borders and dividers (#e5e5e5)
- **Neutral 700**: Text (#404040)
- **Neutral 900**: Dark text (#171717)
- **Accent Blue**: Action buttons (#3b82f6)
- **Score High**: #15803d (green)
- **Score Medium**: #d97706 (orange)
- **Score Low**: #b91c1c (red)

## API Endpoints

All endpoints connect to the backend API (default: http://localhost:50921):

### CV Endpoints
- `GET /api/v1/cv/` - List all CVs
- `GET /api/v1/cv/{cv_id}` - Get full CV details
- `POST /api/v1/cv/upload` - Upload a new CV
- `DELETE /api/v1/cv/{cv_id}` - Delete a CV

### JD Endpoints
- `GET /api/v1/jd/` - List all JDs
- `GET /api/v1/jd/{jd_id}` - Get full JD details
- `POST /api/v1/jd/upload` - Upload a new JD
- `DELETE /api/v1/jd/{jd_id}` - Delete a JD

### Matching Endpoints
- `POST /api/v1/match/cv/{cv_id}/jds` - Find matching JDs for a CV
- `POST /api/v1/match/jd/{jd_id}/cvs` - Find matching CVs for a JD
- `POST /api/v1/match/cv/{cv_id}/rerank` - Rerank JDs with LLM
- `POST /api/v1/match/jd/{jd_id}/rerank` - Rerank CVs with LLM

## Usage

1. Open `index.html` in a web browser
2. Start by uploading CVs and JDs using the Upload tab
3. View uploaded documents in CVs/JDs tabs with filtering and sorting
4. Use CV Matching or JD Matching tabs to find matches
5. Click "Rerank with LLM" to get AI-powered ranking

## Configuration

Set the API base URL by modifying the `API_BASE` variable:

```javascript
const API_BASE = window.API_BASE || 'http://localhost:50921';
```

You can also set it globally before loading the page:

```javascript
window.API_BASE = 'https://api.example.com';
```

## Browser Compatibility

- Chrome/Edge 90+
- Firefox 88+
- Safari 14+
- Modern mobile browsers

## Technologies

- Vanilla JavaScript (no frameworks)
- CSS3 (Grid, Flexbox)
- Fetch API
- HTML5

## Performance

- Single-file application (no build required)
- Efficient re-rendering only on state changes
- Minimal CSS and JavaScript
- No external dependencies

