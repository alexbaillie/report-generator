import {
  ScoreItem,
  TestEntryLike,
  buildTestResults,
  countItems,
  describeCounts,
  describeFill,
  entriesMissingATest,
  hasAttachedResults,
  headerRows,
  isScoreReportFile,
  isSuggested,
  parseFillHeader,
  resolveTestName,
  tableCells,
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

describe('placement mode', () => {
  it('defaults to filling the template and sends the chosen mode', () => {
    expect(buildTestResults([entry({ items: [table('t1')] })])[0].mode).toBe('fill');
    expect(buildTestResults([entry({ items: [table('t1')], mode: 'insert' })])[0].mode).toBe('insert');
  });

  it('sends merges and widths along with the rows', () => {
    const merged: ScoreItem = { ...table('t1'), merges: [[0, 0, 1, 2]], widths: [3, 4] };
    const [item] = buildTestResults([entry({ items: [merged] })])[0].items;
    expect(item.merges).toEqual([[0, 0, 1, 2]]);
    expect(item.widths).toEqual([3, 4]);
  });
});

describe('isSuggested', () => {
  it('only unticks items the extractor flagged', () => {
    expect(isSuggested({})).toBe(true);
    expect(isSuggested({ suggested: true })).toBe(true);
    expect(isSuggested({ suggested: false })).toBe(false);
  });
});

describe('tableCells', () => {
  it('drops merged-over cells and carries the spans', () => {
    const rows = [['Title', '', ''], ['a', 'b', 'c'], ['x', '', 'z']];
    const cells = tableCells(rows, [[0, 0, 1, 3], [1, 0, 2, 1]]);
    expect(cells[0]).toEqual([{ text: 'Title', col: 0, rowSpan: 1, colSpan: 3 }]);
    expect(cells[1].map((c) => c.text)).toEqual(['a', 'b', 'c']);
    expect(cells[1][0].rowSpan).toBe(2);
    expect(cells[2].map((c) => c.text)).toEqual(['', 'z']); // col 0 is covered by the row span above
  });

  it('clamps a span that runs past the rows shown', () => {
    const cells = tableCells([['a', 'b'], ['', 'c'], ['', 'd']], [[0, 0, 3, 1]], 2);
    expect(cells[0][0].rowSpan).toBe(2);
  });
});

describe('headerRows', () => {
  it('treats a full-width one-cell title as a title, not the header', () => {
    const rows = [['Index Scores', '', ''], ['Index', 'Score', 'Percentile'], ['VCI', '100', '50']];
    expect(headerRows(rows, [[0, 0, 1, 3]])).toEqual({ titles: new Set([0]), header: 1 });
  });

  it('uses the first row as the header when it has several cells', () => {
    expect(headerRows([['Index', 'Score'], ['VCI', '100']])).toEqual({ titles: new Set(), header: 0 });
  });
});

describe('fill summary', () => {
  it('parses the response header and ignores junk', () => {
    expect(parseFillHeader('[{"test_name":"WISC-V","result":"filled","filled":3}]')[0].filled).toBe(3);
    expect(parseFillHeader('not json')).toEqual([]);
    expect(parseFillHeader(undefined)).toEqual([]);
  });

  it('describes what was filled and what was left blank', () => {
    const lines = describeFill({
      test_name: 'WISC-V',
      result: 'filled',
      filled: 1,
      not_administered: ['Naming Speed (NSI)'],
      not_in_template: ['Nonverbal'],
    });
    expect(lines[0]).toBe("WISC-V: 1 score filled into the template's own tables.");
    expect(lines.join('\n')).toContain('Naming Speed (NSI)');
    expect(lines.join('\n')).toContain('Nonverbal');
  });
});
