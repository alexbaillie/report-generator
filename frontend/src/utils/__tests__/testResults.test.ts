import {
  ScoreItem,
  TestEntryLike,
  buildTestResults,
  countItems,
  describeCounts,
  entriesMissingATest,
  hasAttachedResults,
  isScoreReportFile,
  resolveTestName,
} from '../testResults';

const table = (id: string, selected = true): ScoreItem => ({
  id, kind: 'table', caption: `cap ${id}`, rows: [['a', 'b'], ['1', '2']], selected,
});
const image = (id: string, selected = true): ScoreItem => ({
  id, kind: 'image', caption: '', content_type: 'image/png', data_b64: 'AAAA', width: 10, height: 5, selected,
});
const entry = (over: Partial<TestEntryLike> = {}): TestEntryLike => ({
  type: 'WISC-V', customName: '', tableHtml: '', items: [], ...over,
});

describe('resolveTestName', () => {
  it('uses the chosen test, or the custom name for "Other"', () => {
    expect(resolveTestName(entry())).toBe('WISC-V');
    expect(resolveTestName(entry({ type: 'Other', customName: ' BASC-3 ' }))).toBe('BASC-3');
    expect(resolveTestName(entry({ type: 'Other' }))).toBe('Other');
    expect(resolveTestName(entry({ type: '' }))).toBe('');
  });
});

describe('buildTestResults', () => {
  it('sends only the items the user left selected, without UI-only fields', () => {
    const result = buildTestResults([entry({ items: [table('t1'), table('t2', false), image('g1')] })]);

    expect(result).toHaveLength(1);
    expect(result[0].test_name).toBe('WISC-V');
    expect(result[0].items.map((i) => i.kind)).toEqual(['table', 'image']);
    expect(result[0].items[0]).not.toHaveProperty('selected');
    expect(result[0].items[0]).not.toHaveProperty('id');
    expect(result[0].items[0].rows).toEqual([['a', 'b'], ['1', '2']]);
  });

  it('includes pasted tables, ignoring pasted text that has no table', () => {
    const html = '<table><tr><td>1</td></tr></table>';

    expect(buildTestResults([entry({ tableHtml: html })])[0].pasted_html).toBe(html);
    expect(buildTestResults([entry({ tableHtml: '<p>just text</p>' })])).toEqual([]);
  });

  it('skips tests with nothing attached and entries with no test chosen', () => {
    const result = buildTestResults([
      entry({ type: 'WAIS-IV' }),
      entry({ type: '', items: [table('x')] }),
      entry({ type: 'WRAML-3', items: [table('y')] }),
    ]);

    expect(result.map((r) => r.test_name)).toEqual(['WRAML-3']);
  });

  it('sends nothing for a test whose items were all deselected', () => {
    expect(buildTestResults([entry({ items: [table('t1', false)] })])).toEqual([]);
  });
});

describe('entriesMissingATest', () => {
  it('counts entries that have results but no test chosen', () => {
    expect(entriesMissingATest([entry({ type: '', items: [table('x')] }), entry({ type: '' }), entry({ items: [table('y')] })])).toBe(1);
  });
});

describe('helpers', () => {
  it('describes counts in plain words', () => {
    expect(describeCounts(1, 0)).toBe('1 table');
    expect(describeCounts(3, 1)).toBe('3 tables and 1 graph');
    expect(describeCounts(0, 2)).toBe('2 graphs');
    expect(describeCounts(0, 0)).toBe('');
    expect(countItems([table('a'), image('b'), image('c')])).toEqual({ tables: 1, images: 2 });
  });

  it('recognises Word and PDF score reports only', () => {
    expect(isScoreReportFile({ name: 'WISC.DOCX' })).toBe(true);
    expect(isScoreReportFile({ name: 'scores.pdf' })).toBe(true);
    expect(isScoreReportFile({ name: 'scores.csv' })).toBe(false);
    expect(hasAttachedResults(entry())).toBe(false);
  });
});
