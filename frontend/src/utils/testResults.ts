// Score tables/graphs a psychologist attaches to a test (e.g. WISC-V). Extracted
// from an uploaded Word/PDF score report by the backend, or pasted as HTML.

/** 'fill': put the scores into the Word template's own tables (its look is untouched).
 *  'insert': replace those tables with the score report's tables as they appear there. */
export type PlacementMode = 'fill' | 'insert';

export interface ScoreItem {
  id: string;
  kind: 'table' | 'image';
  caption: string;
  rows?: string[][];
  /** [row, col, rowspan, colspan] for merged cells; the merged-over cells are empty strings in `rows`. */
  merges?: number[][];
  /** Relative column widths from the score report. */
  widths?: number[];
  /** false when the extractor thinks it is not a graph (a cover picture or logo). */
  suggested?: boolean;
  content_type?: string;
  data_b64?: string;
  width?: number;
  height?: number;
  selected: boolean;
}

export interface TestEntryLike {
  type: string;
  customName: string;
  tableHtml: string;
  items: ScoreItem[];
  mode?: PlacementMode;
}

export interface TestResultPayload {
  test_name: string;
  mode: PlacementMode;
  pasted_html: string;
  items: Array<Omit<ScoreItem, 'id' | 'selected'>>;
}

export function resolveTestName(entry: Pick<TestEntryLike, 'type' | 'customName'>): string {
  return entry.type === 'Other' ? (entry.customName.trim() || 'Other') : entry.type;
}

export function selectedItems(entry: Pick<TestEntryLike, 'items'>): ScoreItem[] {
  return entry.items.filter((item) => item.selected);
}

export function hasPastedTable(html: string): boolean {
  return /<table[\s>]/i.test(html || '');
}

export function hasAttachedResults(entry: TestEntryLike): boolean {
  return selectedItems(entry).length > 0 || hasPastedTable(entry.tableHtml);
}

export function countItems(items: Array<Pick<ScoreItem, 'kind'>>): { tables: number; images: number } {
  return {
    tables: items.filter((i) => i.kind === 'table').length,
    images: items.filter((i) => i.kind === 'image').length,
  };
}

function plural(count: number, singular: string, pluralForm: string): string {
  return `${count} ${count === 1 ? singular : pluralForm}`;
}

export function describeCounts(tables: number, images: number): string {
  const parts: string[] = [];
  if (tables) parts.push(plural(tables, 'table', 'tables'));
  if (images) parts.push(plural(images, 'graph', 'graphs'));
  return parts.join(' and ');
}

/** One request group per test that has something attached; skips unnamed or empty entries. */
export function buildTestResults(entries: TestEntryLike[]): TestResultPayload[] {
  const payload: TestResultPayload[] = [];
  for (const entry of entries) {
    const testName = resolveTestName(entry);
    if (!testName || !hasAttachedResults(entry)) continue;
    payload.push({
      test_name: testName,
      mode: entry.mode ?? 'fill',
      pasted_html: hasPastedTable(entry.tableHtml) ? entry.tableHtml : '',
      items: selectedItems(entry).map(({ id: _id, selected: _selected, ...rest }) => rest),
    });
  }
  return payload;
}

/** Entries that have results attached but no test chosen would be silently dropped. */
export function entriesMissingATest(entries: TestEntryLike[]): number {
  return entries.filter((entry) => !resolveTestName(entry) && hasAttachedResults(entry)).length;
}

export function isScoreReportFile(file: { name: string }): boolean {
  return /\.(docx|pdf)$/i.test(file.name || '');
}

/** Items start ticked unless the extractor thinks they are cover art or a logo. */
export function isSuggested(item: { suggested?: boolean }): boolean {
  return item.suggested !== false;
}

export interface PreviewCell {
  text: string;
  col: number;
  rowSpan: number;
  colSpan: number;
}

/** A table's rows as HTML-style cells: merged-over cells are dropped and the cell
 *  that starts a merge carries its row/column span (clamped to the rows shown). */
export function tableCells(rows: string[][], merges: number[][] = [], maxRows = rows.length): PreviewCell[][] {
  const shownRows = Math.min(rows.length, maxRows);
  const covered = new Set<string>();
  const spans = new Map<string, { rowSpan: number; colSpan: number }>();
  for (const [r, c, rowSpan, colSpan] of merges) {
    if (r >= shownRows) continue;
    spans.set(`${r},${c}`, { rowSpan: Math.min(rowSpan, shownRows - r), colSpan });
    for (let dr = 0; dr < rowSpan; dr++) {
      for (let dc = 0; dc < colSpan; dc++) {
        if (dr || dc) covered.add(`${r + dr},${c + dc}`);
      }
    }
  }
  return rows.slice(0, shownRows).map((row, r) =>
    row.flatMap((text, c) => {
      if (covered.has(`${r},${c}`)) return [];
      const span = spans.get(`${r},${c}`);
      return [{ text, col: c, rowSpan: span?.rowSpan ?? 1, colSpan: span?.colSpan ?? 1 }];
    })
  );
}

/** Title rows (a one-cell banner such as "Index Scores") sit above the real column
 *  headings; only the heading row is styled as the header. Mirrors the backend. */
export function headerRows(rows: string[][], merges: number[][] = []): { titles: Set<number>; header: number } {
  const columns = Math.max(0, ...rows.map((r) => r.length));
  const titles = new Set<number>();
  for (let r = 0; r < Math.min(rows.length, 3); r++) {
    const filled = rows[r].filter((c) => c.trim()).length;
    const fullSpan = merges.some(([mr, mc, , cs]) => mr === r && mc === 0 && cs >= columns);
    if (filled >= 2 && !fullSpan) return { titles, header: r };
    titles.add(r);
  }
  return { titles: new Set(), header: 0 };
}

// What the Word export did with a test's scores (the X-Score-Fill response header).
export interface FillSummary {
  test_name: string;
  result: 'filled' | 'replaced' | 'added';
  filled?: number;
  tables_filled?: number;
  not_administered?: string[];
  not_in_report?: string[];
  ambiguous?: string[];
  unfilled_columns?: string[];
  not_in_template?: string[];
}

export function parseFillHeader(value: unknown): FillSummary[] {
  if (typeof value !== 'string' || !value) return [];
  try {
    const parsed = JSON.parse(value);
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

/** Plain-language lines for one test's summary. Only the things worth a human's attention. */
export function describeFill(summary: FillSummary): string[] {
  const lines: string[] = [];
  if (summary.result === 'filled') {
    const n = summary.filled ?? 0;
    lines.push(`${summary.test_name}: ${n} score${n === 1 ? '' : 's'} filled into the template's own tables.`);
  } else if (summary.result === 'replaced') {
    lines.push(`${summary.test_name}: the template's score tables were replaced with the uploaded tables.`);
  } else {
    lines.push(`${summary.test_name}: the template has no section for this test, so its results were added as a new block.`);
  }
  const notes: Array<[string[] | undefined, string]> = [
    [summary.not_administered, 'Marked "-" in the score report, left blank'],
    [summary.not_in_template, 'In the score report but not in the template tables (not added)'],
    [summary.not_in_report, 'In the template but not found in the score report, left blank'],
    [summary.ambiguous, 'The score report gave conflicting values, left blank'],
    [summary.unfilled_columns, 'Different kind of score than the column wants, left blank'],
  ];
  for (const [list, label] of notes) {
    if (list && list.length) lines.push(`${label}: ${list.join(', ')}`);
  }
  return lines;
}
