// Score tables/graphs a psychologist attaches to a test (e.g. WISC-V). Extracted
// from an uploaded Word/PDF score report by the backend, or pasted as HTML.

export interface ScoreItem {
  id: string;
  kind: 'table' | 'image';
  caption: string;
  rows?: string[][];
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
}

export interface TestResultPayload {
  test_name: string;
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
