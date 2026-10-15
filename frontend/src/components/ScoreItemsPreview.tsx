import { PlacementMode, ScoreItem, countItems, describeCounts, headerRows, tableCells } from '../utils/testResults';

const PREVIEW_ROWS = 8;

interface Props {
  items: ScoreItem[];
  notes: string[];
  mode: PlacementMode;
  onModeChange: (mode: PlacementMode) => void;
  onToggle: (id: string) => void;
  onSetAll: (selected: boolean) => void;
}

function TablePreview({ rows, merges }: { rows: string[][]; merges?: number[][] }) {
  const cells = tableCells(rows, merges, PREVIEW_ROWS);
  const { titles, header } = headerRows(rows, merges);
  return (
    <div className="overflow-auto rounded border border-dark-600">
      <table className="text-xs text-gray-100 w-full">
        <tbody>
          {cells.map((row, r) => (
            <tr
              key={r}
              className={r === header ? 'bg-dark-700 font-semibold' : titles.has(r) ? 'font-semibold text-center' : ''}
            >
              {row.map((cell) => (
                <td
                  key={cell.col}
                  rowSpan={cell.rowSpan}
                  colSpan={cell.colSpan}
                  className="border border-dark-600 px-2 py-1 whitespace-pre-line align-top"
                >
                  {cell.text}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
      {rows.length > PREVIEW_ROWS ? (
        <div className="text-xs text-gray-400 px-2 py-1">+ {rows.length - PREVIEW_ROWS} more rows</div>
      ) : null}
    </div>
  );
}

export default function ScoreItemsPreview({ items, notes, mode, onModeChange, onToggle, onSetAll }: Props) {
  if (items.length === 0 && notes.length === 0) return null;

  const { tables, images } = countItems(items);
  const included = countItems(items.filter((item) => item.selected));
  let tableNumber = 0;
  let graphNumber = 0;

  return (
    <div className="mb-3 rounded border border-dark-600 p-3" data-testid="score-items-preview">
      {items.length > 0 ? (
        <>
          <div className="flex flex-wrap items-center justify-between gap-2 mb-3">
            <div className="text-sm text-gray-200">
              Found {describeCounts(tables, images)}.{' '}
              <span className="text-gray-400">
                {describeCounts(included.tables, included.images) || 'Nothing'} will be added to the Word
                report under this test.
              </span>
            </div>
            <div className="flex gap-2 text-xs">
              <button type="button" className="underline text-gray-300" onClick={() => onSetAll(true)}>
                Select all
              </button>
              <button type="button" className="underline text-gray-300" onClick={() => onSetAll(false)}>
                Clear
              </button>
            </div>
          </div>

          {tables > 0 ? (
            <fieldset className="mb-3 text-sm text-gray-200" data-testid="placement-mode">
              <legend className="text-gray-400 mb-1">How should the tables go into the Word report?</legend>
              <label className="flex items-start gap-2 mb-1 cursor-pointer">
                <input
                  type="radio"
                  className="mt-1"
                  name={`placement-${items[0]?.id}`}
                  checked={mode === 'fill'}
                  onChange={() => onModeChange('fill')}
                />
                <span>
                  <span className="text-white">Fill the template&apos;s own tables</span> (recommended) — the
                  template keeps its exact look; only its blank score cells are filled in. Anything that
                  can&apos;t be matched is left blank and listed after you download.
                </span>
              </label>
              <label className="flex items-start gap-2 cursor-pointer">
                <input
                  type="radio"
                  className="mt-1"
                  name={`placement-${items[0]?.id}`}
                  checked={mode === 'insert'}
                  onChange={() => onModeChange('insert')}
                />
                <span>
                  <span className="text-white">Insert the score report&apos;s tables as they are</span> — replaces
                  the template&apos;s blank tables with the selected tables.
                </span>
              </label>
            </fieldset>
          ) : null}

          <div className="space-y-3">
            {items.map((item) => {
              const label =
                item.kind === 'table' ? `Table ${++tableNumber}` : `Graph ${++graphNumber}`;
              return (
                <label
                  key={item.id}
                  className={`block rounded border p-2 cursor-pointer ${
                    item.selected ? 'border-blue-500' : 'border-dark-600 opacity-60'
                  }`}
                >
                  <div className="flex items-start gap-2">
                    <input
                      type="checkbox"
                      className="mt-1"
                      checked={item.selected}
                      onChange={() => onToggle(item.id)}
                      aria-label={`Include ${label}`}
                    />
                    <div className="flex-1 min-w-0">
                      <div className="text-sm text-white mb-1">
                        {label}
                        {item.caption ? <span className="text-gray-400"> — {item.caption}</span> : null}
                        {item.kind === 'table' && item.rows ? (
                          <span className="text-gray-500 text-xs">
                            {' '}
                            ({item.rows.length} rows × {item.rows[0]?.length ?? 0} columns)
                          </span>
                        ) : null}
                      </div>
                      {item.kind === 'table' && item.rows ? (
                        <TablePreview rows={item.rows} merges={item.merges} />
                      ) : item.data_b64 ? (
                        <img
                          alt={item.caption || label}
                          className="max-h-48 rounded bg-white"
                          src={`data:${item.content_type || 'image/png'};base64,${item.data_b64}`}
                        />
                      ) : null}
                    </div>
                  </div>
                </label>
              );
            })}
          </div>
        </>
      ) : null}

      {notes.map((note, i) => (
        <div key={i} className="mt-2 text-xs text-yellow-300">
          {note}
        </div>
      ))}
    </div>
  );
}
