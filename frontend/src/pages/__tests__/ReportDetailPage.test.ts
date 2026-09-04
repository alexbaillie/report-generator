import { filenameFromDisposition } from '../ReportDetailPage';

// Regression coverage for the export-filename fix: the backend's
// Content-Disposition header is only readable by the browser once CORS
// expose_headers includes it, and this parser is what turns that header into
// the actual downloaded filename.
describe('filenameFromDisposition', () => {
  it('falls back when no header is present', () => {
    expect(filenameFromDisposition(undefined, 'report.docx')).toBe('report.docx');
  });

  it('extracts a quoted filename', () => {
    expect(
      filenameFromDisposition('attachment; filename="ASD_Report.docx"', 'fallback.docx')
    ).toBe('ASD_Report.docx');
  });

  it('extracts an unquoted filename', () => {
    expect(filenameFromDisposition('attachment; filename=Report.docx', 'fallback.docx')).toBe(
      'Report.docx'
    );
  });

  it('extracts and URL-decodes an RFC 5987 filename*= value', () => {
    expect(
      filenameFromDisposition(
        "attachment; filename*=UTF-8''Report%20Name.docx",
        'fallback.docx'
      )
    ).toBe('Report Name.docx');
  });

  it('falls back when the header has no filename', () => {
    expect(filenameFromDisposition('attachment', 'fallback.docx')).toBe('fallback.docx');
  });
});
