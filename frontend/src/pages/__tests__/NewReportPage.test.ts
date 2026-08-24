import {
  escapeHtml,
  extractFirstTableFromHtml,
  parseDelimitedTextToHtmlTable,
  isFrontPageMetadataSection,
  metadataLinesFromInputs,
} from '../NewReportPage';

describe('escapeHtml', () => {
  it('escapes HTML-significant characters', () => {
    expect(escapeHtml('<b>"quote" & \'apos\'</b>')).toBe(
      '&lt;b&gt;&quot;quote&quot; &amp; &#39;apos&#39;&lt;/b&gt;'
    );
  });

  it('leaves plain text unchanged', () => {
    expect(escapeHtml('plain text 123')).toBe('plain text 123');
  });
});

describe('extractFirstTableFromHtml', () => {
  it('extracts a table embedded in other markup', () => {
    const html = '<div>before</div><table><tr><td>1</td></tr></table><p>after</p>';
    expect(extractFirstTableFromHtml(html)).toBe('<table><tr><td>1</td></tr></table>');
  });

  it('returns an empty string when there is no table', () => {
    expect(extractFirstTableFromHtml('<div>no table here</div>')).toBe('');
  });
});

describe('parseDelimitedTextToHtmlTable', () => {
  it('returns an empty string for empty input', () => {
    expect(parseDelimitedTextToHtmlTable('')).toBe('');
    expect(parseDelimitedTextToHtmlTable('   \n  ')).toBe('');
  });

  it('parses comma-delimited text into an HTML table', () => {
    const result = parseDelimitedTextToHtmlTable('a,b\nc,d');
    expect(result).toBe(
      '<table><tbody><tr><td>a</td><td>b</td></tr><tr><td>c</td><td>d</td></tr></tbody></table>'
    );
  });

  it('detects tab-delimited text (e.g. pasted from Excel) over commas', () => {
    const result = parseDelimitedTextToHtmlTable('a\tb\nc\td');
    expect(result).toBe(
      '<table><tbody><tr><td>a</td><td>b</td></tr><tr><td>c</td><td>d</td></tr></tbody></table>'
    );
  });

  it('pads short rows to the longest row length', () => {
    const result = parseDelimitedTextToHtmlTable('a,b,c\nd');
    expect(result).toBe(
      '<table><tbody><tr><td>a</td><td>b</td><td>c</td></tr><tr><td>d</td><td></td><td></td></tr></tbody></table>'
    );
  });

  it('HTML-escapes cell content', () => {
    const result = parseDelimitedTextToHtmlTable('<script>,b');
    expect(result).toContain('&lt;script&gt;');
    expect(result).not.toContain('<script>');
  });
});

// Regression coverage for the front-page metadata fix: the "Report Metadata
// (Front Page)" section must be detected and sent as structured "Label: value"
// lines, never through the AI — otherwise the DOCX exporter's title-page table
// (DOB, dates, examiner, etc.) silently comes back blank.
describe('isFrontPageMetadataSection', () => {
  it('matches the standard front-page section title', () => {
    expect(isFrontPageMetadataSection('Report Metadata (Front Page)')).toBe(true);
  });

  it('matches case-insensitively and ignores surrounding whitespace', () => {
    expect(isFrontPageMetadataSection('  report METADATA  ')).toBe(true);
    expect(isFrontPageMetadataSection('front page')).toBe(true);
  });

  it('does not match unrelated section titles', () => {
    expect(isFrontPageMetadataSection('Reason for Referral')).toBe(false);
    expect(isFrontPageMetadataSection('Presenting Concerns')).toBe(false);
  });
});

describe('metadataLinesFromInputs', () => {
  it('formats each field as "Label: value"', () => {
    expect(metadataLinesFromInputs({ 'Client full name': 'Ava Thompson' })).toBe(
      'Client full name: Ava Thompson'
    );
  });

  it('omits empty, null, and undefined values', () => {
    const result = metadataLinesFromInputs({
      A: 'x',
      B: '',
      C: undefined,
      D: null,
    });
    expect(result).toBe('A: x');
  });

  it('joins array values with commas', () => {
    expect(metadataLinesFromInputs({ 'Copies to': ['Parents', 'School'] })).toBe(
      'Copies to: Parents, School'
    );
  });

  it('returns an empty string when there are no fields to include', () => {
    expect(metadataLinesFromInputs({})).toBe('');
  });
});
