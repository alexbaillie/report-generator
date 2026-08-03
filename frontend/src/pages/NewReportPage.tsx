import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Upload, Plus } from 'lucide-react';
import { api } from '../services/api';

function escapeHtml(value: string) {
  return value
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

function ensureTableStyling(html: string) {
  const style = `<style>
table{border-collapse:collapse;width:100%;}
th,td{border:1px solid #9ca3af;padding:4px;vertical-align:top;}
</style>`;
  const trimmed = (html || '').trim();
  if (!trimmed) return '';
  if (trimmed.toLowerCase().includes('<style')) return trimmed;
  return `${style}${trimmed}`;
}

function extractFirstTableFromHtml(html: string) {
  const match = html.match(/<table[\s\S]*?<\/table>/i);
  return match ? match[0] : '';
}

function parseDelimitedTextToHtmlTable(text: string) {
  const raw = (text || '').replace(/\r\n/g, '\n').replace(/\r/g, '\n').trim();
  if (!raw) return '';

  const lines = raw.split('\n').filter(Boolean);
  const hasTabs = lines.some((l) => l.includes('\t'));
  const delimiter = hasTabs ? '\t' : ',';

  const rows = lines.map((line) => line.split(delimiter));
  const maxCols = rows.reduce((m, r) => Math.max(m, r.length), 0);
  const normalized = rows.map((r) => (r.length < maxCols ? [...r, ...new Array(maxCols - r.length).fill('')] : r));

  const body = normalized
    .map((cols) => `<tr>${cols.map((c) => `<td>${escapeHtml(String(c ?? '').trim())}</td>`).join('')}</tr>`)
    .join('');

  return `<table><tbody>${body}</tbody></table>`;
}

async function parseTableFileToHtml(file: File): Promise<string> {
  const name = (file.name || '').toLowerCase();
  const type = (file.type || '').toLowerCase();
  const text = await file.text();

  if (type.includes('html') || name.endsWith('.html') || name.endsWith('.htm')) {
    const table = extractFirstTableFromHtml(text);
    return table || '';
  }

  if (name.endsWith('.tsv')) {
    return parseDelimitedTextToHtmlTable(text);
  }

  if (name.endsWith('.csv') || type.includes('csv')) {
    return parseDelimitedTextToHtmlTable(text);
  }

  if (type.startsWith('text/') || name.endsWith('.txt')) {
    return parseDelimitedTextToHtmlTable(text);
  }

  return '';
}

// The front-page metadata section is structured data for the DOCX title page,
// not narrative prose. It must be passed through verbatim so the Word exporter
// can parse "Label: value" lines to fill the front-page table, title, and
// confidentiality statement. Sending it through the LLM turns it into prose and
// leaves those fields blank.
function isFrontPageMetadataSection(title: string) {
  const normalized = title.trim().toLowerCase();
  return normalized.includes('report metadata') || normalized.includes('front page');
}

function metadataLinesFromInputs(inputs: Record<string, any>): string {
  return Object.entries(inputs)
    .filter(([, value]) => value !== undefined && value !== null && String(value).trim() !== '')
    .map(([key, value]) => `${key}: ${Array.isArray(value) ? value.join(', ') : value}`)
    .join('\n');
}

function PreviewTable({ html }: { html: string }) {
  return (
    <div className="mt-3">
      <div className="text-white text-sm mb-2">Preview Table</div>
      <div
        className="overflow-auto rounded border border-dark-600 bg-dark-800 p-2 text-gray-100"
        dangerouslySetInnerHTML={{ __html: ensureTableStyling(html) }}
      />
    </div>
  );
}

interface TestTableEntry {
  type: string;
  customName: string;
  tableHtml: string;
  description: string;
  files: File[];
}

interface Template {
  id: number;
  name: string;
  description: string;
  template_type: string;
  content: string;
  is_default: boolean;
}

interface SourceDocument {
  id: number;
  filename: string;
  file_type: string;
  uploaded_at: string;
}

interface SectionField {
  label: string;
  type:
    | 'text'
    | 'textarea'
    | 'date'
    | 'date_multi'
    | 'select'
    | 'multi_select'
    | 'checkbox'
    | 'checkboxes'
    | 'file'
    | 'table';
  options?: string[];
  required?: boolean;
  placeholder?: string;
  readOnly?: boolean;
}

interface TemplateSection {
  title: string;
  fields: SectionField[];
}

interface FormData {
  title: string;
  patient_name: string;
  template: string;
  testTableEntries: TestTableEntry[];
  templateData: Record<string, any>;
  report_type: string;
  template_id: string;
  document_ids: number[];
}

export default function NewReportPage() {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(false);
  const [progressMessage, setProgressMessage] = useState('');
  const [templates, setTemplates] = useState<Template[]>([]);
  const [documents, setDocuments] = useState<SourceDocument[]>([]);
  const [documentsLoading, setDocumentsLoading] = useState(true);
  const [documentsError, setDocumentsError] = useState('');
  const [templateSections, setTemplateSections] = useState<TemplateSection[]>([]);
  const [formData, setFormData] = useState<FormData>({
    title: '',
    patient_name: '',
    template: '',
    testTableEntries: [{ type: '', customName: '', tableHtml: '', description: '', files: [] }],
    templateData: {},
    report_type: 'evaluation',
    template_id: '1',
    document_ids: [],
  });

  useEffect(() => {
    loadTemplates();
    loadDocuments();
  }, []);

  const loadTemplates = async () => {
    try {
      const data = await api.getTemplates();
      setTemplates(data);
      // Set default template if available
      const defaultTemplate = data.find((t: Template) => t.is_default);
      if (defaultTemplate) {
        setFormData(prev => ({
          ...prev,
          title: prev.title || defaultTemplate.name,
          report_type: defaultTemplate.template_type,
          template_id: defaultTemplate.id.toString()
        }));
        parseTemplate(defaultTemplate.content);
      }
    } catch (error) {
      console.error('Failed to load templates:', error);
    }
  };

  const loadDocuments = async () => {
    setDocumentsLoading(true);
    setDocumentsError('');
    try {
      const data = await api.getDocuments();
      setDocuments(data);
    } catch (error) {
      console.error('Failed to load documents:', error);
      setDocumentsError('Source documents could not be loaded.');
    } finally {
      setDocumentsLoading(false);
    }
  };

  const parseTemplate = (content: string) => {
    // If content is a JSON schema, parse and use it directly
    try {
      const maybeJson = JSON.parse(content);
      if (Array.isArray(maybeJson)) {
        // Assume array of sections
        setTemplateSections(maybeJson as TemplateSection[]);
        return;
      }
      if (maybeJson && Array.isArray((maybeJson as any).sections)) {
        setTemplateSections((maybeJson as any).sections as TemplateSection[]);
        return;
      }
    } catch {
      // Not JSON, fall back to legacy parser below
    }

    const sections: TemplateSection[] = [];
    const lines = content.split('\n');
    let currentSection: TemplateSection | null = null;

    for (const line of lines) {
      const trimmed = line.trim();
      if (!trimmed || trimmed.startsWith('AI_use:')) continue;

      if (/^\d+\.\s+.+$/.test(trimmed) && !trimmed.includes(':')) {
        if (currentSection) sections.push(currentSection);
        const titleMatch = trimmed.match(/^\d+\.\s+(.+)$/);
        currentSection = { title: titleMatch ? titleMatch[1] : trimmed, fields: [] };
      } else if (/^\d+\.\d+\s+.+$/.test(trimmed) && !trimmed.includes(':')) {
        if (currentSection) sections.push(currentSection);
        const titleMatch = trimmed.match(/^\d+\.\d+\s+(.+)$/);
        currentSection = { title: titleMatch ? titleMatch[1] : trimmed, fields: [] };
      } else if (currentSection && trimmed.includes(':') && trimmed.includes('[')) {
        const colonIndex = trimmed.indexOf(':');
        const label = trimmed.substring(0, colonIndex).trim();
        const typeAnnotation = trimmed.substring(colonIndex + 1).trim();
        const typeMatch = typeAnnotation.match(/\[(\w+)(?::([^]]+))?\]/);
        if (typeMatch) {
          const fieldType = typeMatch[1];
          const options = typeMatch[2];

          let type: SectionField['type'] = 'text';
          let required = false;
          let fieldOptions: string[] | undefined;

          switch (fieldType) {
            case 'text':
              type = 'text';
              required = options?.includes('required') || false;
              break;
            case 'textarea':
              type = 'textarea';
              break;
            case 'date':
              type = 'date';
              required = options?.includes('required') || false;
              break;
            case 'date_multi':
              type = 'date_multi';
              required = options?.includes('required') || false;
              break;
            case 'dropdown':
              type = 'select';
              if (options) {
                fieldOptions = options.split(',').map(opt => opt.trim());
              }
              break;
            case 'multi_select':
              type = 'multi_select';
              if (options) {
                fieldOptions = options.split(',').map(opt => opt.trim());
              }
              break;
            case 'checkboxes':
            case 'checklist':
              type = 'checkboxes';
              if (options) {
                fieldOptions = options.split(',').map(opt => opt.trim());
              }
              break;
            case 'yes_no':
              type = 'select';
              fieldOptions = ['Yes', 'No'];
              break;
            case 'auto_calculated':
            case 'auto_fill':
            case 'auto':
              type = 'text';
              required = false;
              break;
            case 'table_rows':
            case 'structured_table':
            case 'table':
              type = 'table';
              break;
            case 'file_upload':
              type = 'file';
              break;
            default:
              type = 'text';
          }

          currentSection.fields.push({
            label,
            type,
            required,
            options: fieldOptions
          });
        }
      } else if (currentSection && trimmed.endsWith(':')) {
        const label = trimmed.slice(0, -1);
        let type: SectionField['type'] = 'text';
        if (label.toLowerCase().includes('date')) {
          type = 'date';
        } else if (
          label.toLowerCase().includes('summary') ||
          label.toLowerCase().includes('description') ||
          label.toLowerCase().includes('observations') ||
          label.toLowerCase().includes('information')
        ) {
          type = 'textarea';
        }
        currentSection.fields.push({ label, type, required: false });
      }
    }

    if (currentSection) sections.push(currentSection);
    setTemplateSections(sections);
  };

  const handleTemplateChange = (templateId: string) => {
    const selectedTemplate = templates.find(t => t.id.toString() === templateId);
    setFormData(prev => ({
      ...prev,
      title: selectedTemplate ? selectedTemplate.name : '',
      report_type: selectedTemplate ? selectedTemplate.template_type : '',
      template_id: templateId
    }));
    if (selectedTemplate) {
      parseTemplate(selectedTemplate.content);
    } else {
      setTemplateSections([]);
    }
  };

  const handleFileUpload = (index: number) => async (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (files && files.length > 0) {
      const newFiles = Array.from(files);
      let parsedHtml = '';
      try {
        parsedHtml = await parseTableFileToHtml(newFiles[newFiles.length - 1]);
      } catch {
        parsedHtml = '';
      }
      setFormData(prev => ({
        ...prev,
        testTableEntries: prev.testTableEntries.map((entry, i) =>
          i === index
            ? {
              ...entry,
              files: [...entry.files, ...newFiles],
              tableHtml: parsedHtml ? ensureTableStyling(parsedHtml) : entry.tableHtml
            }
            : entry
        )
      }));
    }
  };

  const addTestTable = () => {
    setFormData(prev => ({
      ...prev,
      testTableEntries: [...prev.testTableEntries, { type: '', customName: '', tableHtml: '', description: '', files: [] }]
    }));
  };

  const toggleDocument = (documentId: number) => {
    setFormData(prev => ({
      ...prev,
      document_ids: prev.document_ids.includes(documentId)
        ? prev.document_ids.filter(id => id !== documentId)
        : [...prev.document_ids, documentId]
    }));
  };

  const handleSubmit = async () => {
    const patientName = formData.patient_name.trim();
    if (!formData.template_id) {
      alert('Please choose a template.');
      return;
    }
    if (!patientName) {
      alert('Please enter the patient name.');
      return;
    }

    setLoading(true);
    try {
      const selectedTemplate = templates.find(t => t.id.toString() === formData.template_id);

      // Generate report section by section
      const generatedSections: Record<string, string> = {};

      // First, handle test tables
      for (const entry of formData.testTableEntries) {
        if (entry.files.length > 0 || entry.description || entry.tableHtml) {
          // Generate description for test table
          // For now, just use the description
          const resolvedTestName = entry.type === 'Other'
            ? (entry.customName || 'Other')
            : entry.type;
          const uploaded = entry.files.length > 0
            ? `Uploaded files: ${entry.files.map(f => f.name).join(', ')}`
            : '';
          const combined = [entry.tableHtml, entry.description, uploaded].filter(Boolean).join('\n\n');
          generatedSections[`Test Table: ${resolvedTestName}`] = combined;
        }
      }

      // Generate content for each template section
      for (const section of templateSections) {
        const sectionData = formData.templateData?.[section.title] || {};
        const sectionInputs = Object.entries(sectionData)
          .filter(([_, value]) => value)
          .reduce((acc, [key, value]) => ({ ...acc, [key]: value }), {});

        if (Object.keys(sectionInputs).length > 0) {
          if (isFrontPageMetadataSection(section.title)) {
            // Structured title-page data: pass through verbatim (no LLM) so the
            // DOCX exporter can populate the front-page table and title.
            generatedSections[section.title] = metadataLinesFromInputs(sectionInputs);
          } else {
            // Show progress message
            setProgressMessage(`Generating ${section.title} section...`);

            // Call API to generate section content
            const response = await api.generateReportSection({
              template_id: parseInt(formData.template_id),
              section_name: section.title,
              document_ids: formData.document_ids,
              section_inputs: sectionInputs
            });

            generatedSections[section.title] = response.section_content;
          }
        }
      }

      // Save the report to database
      const reportData = {
        title: formData.title || selectedTemplate?.name || 'Untitled Report',
        patient_name: patientName,
        report_type: formData.report_type || selectedTemplate?.template_type || 'report',
        template_id: parseInt(formData.template_id),
        document_ids: formData.document_ids,
        additional_inputs: generatedSections
      };

      const savedReport = await api.generateReport(reportData);

      // Clear progress message
      setProgressMessage('');

      // Navigate to the created report
      navigate(`/reports/${savedReport.id}`);
    } catch (error) {
      alert('Failed to generate report. Please try again.');
      console.error('Error generating report:', error);
    } finally {
      setLoading(false);
    }
  };

  const isTestsAdministeredSection = (title: string) => title.trim().toLowerCase() === 'tests administered';
  const isDemographicsSection = (title: string) => title.trim().toLowerCase().includes('demographic');
  const isFamilyHistorySection = (title: string) => title.trim().toLowerCase().includes('family history');
  const isPrenatalExposureSection = (title: string) => {
    const normalized = title.trim().toLowerCase();
    return normalized.includes('prenatal exposure') || (normalized.includes('prenatal') && normalized.includes('exposure'));
  };
  const LANGUAGES_AT_HOME_KEY = 'Languages at home';
  const FAMILY_HISTORY_NOTES_KEY = 'Family History Notes';
  const PRENATAL_EXPOSURE_FREQUENCY_KEY = 'Exposure Frequency';
  const PRENATAL_EXPOSURE_DETAILS_KEY = 'Exposure Details';
  const isLanguagesAtHomeFieldLabel = (label: string) => {
    const normalized = label.trim().toLowerCase();
    return normalized === 'languages spoken at home' || normalized === 'languages at home';
  };
  const selectedDocuments = documents.filter(doc => formData.document_ids.includes(doc.id));

  return (
    <div className="p-8">
      <div className="max-w-4xl mx-auto">
        <div className="space-y-6">

          <div>
            <label className="text-white text-lg mb-3 block">Choose template</label>
            <select
              className="input w-full max-w-md"
              value={formData.template_id}
              onChange={(e) => handleTemplateChange(e.target.value)}
            >
              <option value="">Select template</option>
              {templates.map((template) => (
                <option key={template.id} value={template.id.toString()}>
                  {template.name} {template.is_default ? '(Default)' : ''}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label htmlFor="patient-name" className="text-white text-lg mb-3 block">
              Patient name <span className="text-red-400">*</span>
            </label>
            <input
              id="patient-name"
              type="text"
              className="input w-full max-w-md"
              value={formData.patient_name}
              onChange={(e) => setFormData(prev => ({ ...prev, patient_name: e.target.value }))}
              placeholder="Enter the patient's full name"
              autoComplete="off"
              required
            />
          </div>

          <div className="rounded-lg border border-dark-600 bg-dark-800 p-4">
            <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
              <div>
                <h2 className="text-white text-lg">Source documents</h2>
                <p className="text-sm text-gray-400">
                  Select uploaded documents to include in AI report generation.
                </p>
              </div>
              <span className="rounded-full bg-dark-700 px-3 py-1 text-sm text-gray-200">
                {formData.document_ids.length} selected
              </span>
            </div>

            {documentsLoading ? (
              <p className="text-sm text-gray-400">Loading uploaded documents...</p>
            ) : documentsError ? (
              <div className="flex flex-wrap items-center gap-3">
                <p className="text-sm text-red-400">{documentsError}</p>
                <button type="button" className="text-sm text-blue-400 hover:text-blue-300" onClick={loadDocuments}>
                  Try again
                </button>
              </div>
            ) : documents.length === 0 ? (
              <p className="text-sm text-gray-400">
                No uploaded documents are available. Upload documents from the Documents page first.
              </p>
            ) : (
              <div className="max-h-64 space-y-2 overflow-y-auto pr-1">
                {documents.map(doc => {
                  const checked = formData.document_ids.includes(doc.id);
                  return (
                    <label
                      key={doc.id}
                      className={`flex cursor-pointer items-start gap-3 rounded border p-3 transition-colors ${
                        checked
                          ? 'border-blue-500 bg-blue-500/10'
                          : 'border-dark-600 bg-dark-700 hover:border-dark-500'
                      }`}
                    >
                      <input
                        type="checkbox"
                        className="checkbox mt-1"
                        checked={checked}
                        onChange={() => toggleDocument(doc.id)}
                      />
                      <span className="min-w-0">
                        <span className="block break-words text-sm text-white">{doc.filename}</span>
                        <span className="block text-xs text-gray-400">
                          Document #{doc.id}
                          {doc.file_type ? ` | ${doc.file_type}` : ''}
                        </span>
                      </span>
                    </label>
                  );
                })}
              </div>
            )}

            {selectedDocuments.length > 0 && (
              <div className="mt-4 border-t border-dark-600 pt-3">
                <p className="mb-2 text-xs font-medium uppercase tracking-wide text-gray-400">
                  Included in this report
                </p>
                <div className="flex flex-wrap gap-2">
                  {selectedDocuments.map(doc => (
                    <span key={doc.id} className="rounded-full bg-blue-500/20 px-3 py-1 text-sm text-blue-200">
                      {doc.filename}
                    </span>
                  ))}
                </div>
              </div>
            )}
          </div>

          {/* Dynamic Template Form */}
          {templateSections.map((section, sectionIndex) => (
            <div key={sectionIndex} className="mb-6">
              <h3 className="text-white text-lg mb-3 block">
                {isTestsAdministeredSection(section.title)
                  ? 'Tests Administered (Upload or Paste Score Tables)'
                  : section.title}
              </h3>
              <div className="space-y-4">
                {isTestsAdministeredSection(section.title) ? (
                  <div>
                    {formData.testTableEntries.map((entry, index) => (
                      <div key={index} className="mb-6 p-4 border border-dark-600 rounded">
                        <div className="flex items-start gap-3 mb-3">
                          <select
                            className="input flex-1 max-w-md"
                            value={entry.type}
                            onChange={(e) => setFormData(prev => ({
                              ...prev,
                              testTableEntries: prev.testTableEntries.map((ent, i) =>
                                i === index
                                  ? {
                                    ...ent,
                                    type: e.target.value,
                                    customName: e.target.value === 'Other' ? ent.customName : ''
                                  }
                                  : ent
                              )
                            }))}
                          >
                            <option value="">Select test table</option>
                            <option>ADOS-2</option>
                            <option>ABAS-III</option>
                            <option>Aseba</option>
                            <option>ASRS 1.1</option>
                            <option>Beck Youth Inventory</option>
                            <option>Bayley-4</option>
                            <option>Beck Youth Inventory-2</option>
                            <option>Beery VMI-6</option>
                            <option>Bracken-III</option>
                            <option>Bracken-IV</option>
                            <option>Brief</option>
                            <option>CDI-2</option>
                            <option>Children's Colour Trails Test</option>
                            <option>C-TOPP-2</option>
                            <option>CVLT-C</option>
                            <option>DABS</option>
                            <option>DAS-II</option>
                            <option>DKEFS</option>
                            <option>EVT-2</option>
                            <option>GORT</option>
                            <option>Leiter</option>
                            <option>MASC</option>
                            <option>Movement ABC-2</option>
                            <option>Mullen (version 1)</option>
                            <option>NEPSY-II</option>
                            <option>PAI</option>
                            <option>PPVT-4</option>
                            <option>REEL-4</option>
                            <option>Rey Complex Figure Test-1</option>
                            <option>Scared</option>
                            <option>SCQ</option>
                            <option>Sensory Profiles-2</option>
                            <option>SIB-r</option>
                            <option>SLDT-E:NU</option>
                            <option>TOPS</option>
                            <option>TOWL-4</option>
                            <option>TVCF-1</option>
                            <option>Vineland-3</option>
                            <option>WAIS-IV</option>
                            <option>WASI-II</option>
                            <option>WIAT-II</option>
                            <option>WIAT-IV</option>
                            <option>WISC-V</option>
                            <option>Woodcock-Johnson-IV</option>
                            <option>WPPSI-IV</option>
                            <option>WRAML-2</option>
                            <option>WRAML-3</option>
                            <option>WSR-II</option>
                            <option value="Other">Other</option>
                          </select>
                          <button
                            type="button"
                            className="bg-dark-700 p-2 rounded hover:bg-dark-600 transition-colors"
                            onClick={() => document.getElementById(`test-upload-${index}`)?.click()}
                          >
                            <Upload size={24} className="text-gray-300" />
                          </button>
                          <input
                            id={`test-upload-${index}`}
                            type="file"
                            className="hidden"
                            onChange={handleFileUpload(index)}
                            multiple
                          />
                        </div>

                        {entry.type === 'Other' ? (
                          <div className="mb-3">
                            <label className="text-white text-sm mb-2 block">Test Name</label>
                            <input
                              type="text"
                              className="input w-full"
                              value={entry.customName}
                              onChange={(e) => setFormData(prev => ({
                                ...prev,
                                testTableEntries: prev.testTableEntries.map((ent, i) =>
                                  i === index ? { ...ent, customName: e.target.value } : ent
                                )
                              }))}
                            />
                          </div>
                        ) : null}

                        <div className="mb-3">
                          <label className="text-white text-sm mb-2 block">Paste Table</label>
                          <div
                            className="w-full min-h-[120px] rounded border border-dark-600 bg-dark-800 p-2 text-gray-100 overflow-auto"
                            contentEditable
                            suppressContentEditableWarning
                            onPaste={(e) => {
                              const clipboard = e.clipboardData;
                              if (!clipboard) return;
                              const html = clipboard.getData('text/html');
                              const text = clipboard.getData('text/plain');
                              const tableFromHtml = html ? extractFirstTableFromHtml(html) : '';
                              const tableFromText = !tableFromHtml && text ? parseDelimitedTextToHtmlTable(text) : '';
                              const next = tableFromHtml || tableFromText;
                              if (next) {
                                e.preventDefault();
                                const styled = ensureTableStyling(next);
                                setFormData(prev => ({
                                  ...prev,
                                  testTableEntries: prev.testTableEntries.map((ent, i) =>
                                    i === index ? { ...ent, tableHtml: styled } : ent
                                  )
                                }));
                              }
                            }}
                            onInput={(e) => {
                              const html = (e.currentTarget as HTMLDivElement).innerHTML;
                              setFormData(prev => ({
                                ...prev,
                                testTableEntries: prev.testTableEntries.map((ent, i) =>
                                  i === index ? { ...ent, tableHtml: html } : ent
                                )
                              }));
                            }}
                            dangerouslySetInnerHTML={{ __html: entry.tableHtml || '' }}
                          ></div>
                          <div className="text-xs text-gray-400 mt-1">Paste from Excel/Sheets or a table from another document.</div>
                        </div>

                        {entry.files.length > 0 ? (
                          <div className="mb-3 text-sm text-gray-300">
                            {entry.files.map((f, fileIndex) => (
                              <div key={`${f.name}-${fileIndex}`}>{f.name}</div>
                            ))}
                          </div>
                        ) : null}

                        {entry.tableHtml ? <PreviewTable html={entry.tableHtml} /> : null}
                        <div className="mt-3">
                          <label className="text-white text-sm mb-2 block">Notes (optional)</label>
                          <input
                            type="text"
                            className="input w-full"
                            value={entry.description}
                            onChange={(e) => setFormData(prev => ({
                              ...prev,
                              testTableEntries: prev.testTableEntries.map((ent, i) =>
                                i === index ? { ...ent, description: e.target.value } : ent
                              )
                            }))}
                          />
                        </div>
                      </div>
                    ))}
                    <button
                      type="button"
                      className="bg-dark-700 hover:bg-dark-600 text-gray-100 px-4 py-2 rounded flex items-center gap-2"
                      onClick={addTestTable}
                    >
                      <Plus size={20} />
                      Upload another test table
                    </button>
                  </div>
                ) : null}
                {(isDemographicsSection(section.title) || isFamilyHistorySection(section.title)) && !section.fields.some((f) => isLanguagesAtHomeFieldLabel(f.label)) ? (
                  <div>
                    <label className="text-white text-sm mb-2 block">{LANGUAGES_AT_HOME_KEY}</label>
                    <input
                      type="text"
                      className="input w-full"
                      value={formData.templateData?.[section.title]?.[LANGUAGES_AT_HOME_KEY] || ''}
                      onChange={(e) => setFormData(prev => ({
                        ...prev,
                        templateData: {
                          ...prev.templateData,
                          [section.title]: {
                            ...prev.templateData?.[section.title],
                            [LANGUAGES_AT_HOME_KEY]: e.target.value
                          }
                        }
                      }))}
                    />
                  </div>
                ) : null}

                {isFamilyHistorySection(section.title) && !section.fields.some((f) => f.label.trim().toLowerCase() === FAMILY_HISTORY_NOTES_KEY.toLowerCase()) ? (
                  <div>
                    <label className="text-white text-sm mb-2 block">{FAMILY_HISTORY_NOTES_KEY}</label>
                    <textarea
                      className="textarea w-full"
                      rows={4}
                      value={formData.templateData?.[section.title]?.[FAMILY_HISTORY_NOTES_KEY] || ''}
                      onChange={(e) => setFormData(prev => ({
                        ...prev,
                        templateData: {
                          ...prev.templateData,
                          [section.title]: {
                            ...prev.templateData?.[section.title],
                            [FAMILY_HISTORY_NOTES_KEY]: e.target.value
                          }
                        }
                      }))}
                    />
                  </div>
                ) : null}

                {isPrenatalExposureSection(section.title) && !section.fields.some((f) => f.label.trim().toLowerCase() === PRENATAL_EXPOSURE_FREQUENCY_KEY.toLowerCase()) ? (
                  <div>
                    <label className="text-white text-sm mb-2 block">{PRENATAL_EXPOSURE_FREQUENCY_KEY}</label>
                    <select
                      className="input w-full"
                      value={formData.templateData?.[section.title]?.[PRENATAL_EXPOSURE_FREQUENCY_KEY] || ''}
                      onChange={(e) => {
                        const nextValue = e.target.value;
                        const otherKey = `${PRENATAL_EXPOSURE_FREQUENCY_KEY} - Other (specify)`;
                        setFormData(prev => {
                          const prevSection = prev.templateData?.[section.title] || {};
                          const nextSection: Record<string, any> = {
                            ...prevSection,
                            [PRENATAL_EXPOSURE_FREQUENCY_KEY]: nextValue,
                          };

                          if (nextValue !== 'Other') {
                            delete nextSection[otherKey];
                          }

                          return {
                            ...prev,
                            templateData: {
                              ...prev.templateData,
                              [section.title]: nextSection,
                            },
                          };
                        });
                      }}
                    >
                      <option value="">Select</option>
                      <option value="None">None</option>
                      <option value="One-time">One-time</option>
                      <option value="Occasional">Occasional</option>
                      <option value="Weekly">Weekly</option>
                      <option value="Daily">Daily</option>
                      <option value="Unknown">Unknown</option>
                      <option value="Other">Other</option>
                    </select>

                    {(formData.templateData?.[section.title]?.[PRENATAL_EXPOSURE_FREQUENCY_KEY] || '') === 'Other' ? (
                      <input
                        type="text"
                        className="input w-full mt-2"
                        placeholder="Please specify"
                        value={
                          formData.templateData?.[section.title]?.[`${PRENATAL_EXPOSURE_FREQUENCY_KEY} - Other (specify)`] || ''
                        }
                        onChange={(e) => setFormData(prev => ({
                          ...prev,
                          templateData: {
                            ...prev.templateData,
                            [section.title]: {
                              ...prev.templateData?.[section.title],
                              [`${PRENATAL_EXPOSURE_FREQUENCY_KEY} - Other (specify)`]: e.target.value
                            }
                          }
                        }))}
                      />
                    ) : null}
                  </div>
                ) : null}

                {isPrenatalExposureSection(section.title) && !section.fields.some((f) => f.label.trim().toLowerCase() === PRENATAL_EXPOSURE_DETAILS_KEY.toLowerCase()) ? (
                  <div>
                    <label className="text-white text-sm mb-2 block">{PRENATAL_EXPOSURE_DETAILS_KEY}</label>
                    <textarea
                      className="textarea w-full"
                      rows={4}
                      value={formData.templateData?.[section.title]?.[PRENATAL_EXPOSURE_DETAILS_KEY] || ''}
                      onChange={(e) => setFormData(prev => ({
                        ...prev,
                        templateData: {
                          ...prev.templateData,
                          [section.title]: {
                            ...prev.templateData?.[section.title],
                            [PRENATAL_EXPOSURE_DETAILS_KEY]: e.target.value
                          }
                        }
                      }))}
                    />
                  </div>
                ) : null}
                {section.fields.map((field, fieldIndex) => {
                  const forceLanguagesAtHomeText = isLanguagesAtHomeFieldLabel(field.label);
                  return (
                    <div key={fieldIndex}>
                      <label className="text-white text-sm mb-2 block">{field.label}</label>

                      {forceLanguagesAtHomeText ? (
                        <input
                          type="text"
                          className="input w-full"
                          value={
                            formData.templateData?.[section.title]?.[LANGUAGES_AT_HOME_KEY] ||
                            formData.templateData?.[section.title]?.[field.label] ||
                            ''
                          }
                          onChange={(e) => setFormData(prev => ({
                            ...prev,
                            templateData: {
                              ...prev.templateData,
                              [section.title]: {
                                ...prev.templateData?.[section.title],
                                [LANGUAGES_AT_HOME_KEY]: e.target.value,
                                [field.label]: e.target.value
                              }
                            }
                          }))}
                        />
                      ) : null}

                      {!forceLanguagesAtHomeText && field.type === 'text' && (
                        <input
                          type="text"
                          className="input w-full"
                          readOnly={field.label === 'Age at assessment'}
                          value={formData.templateData?.[section.title]?.[field.label] || ''}
                          onChange={(e) => setFormData(prev => ({
                            ...prev,
                            templateData: {
                              ...prev.templateData,
                              [section.title]: {
                                ...prev.templateData?.[section.title],
                                [field.label]: e.target.value
                              }
                            }
                          }))}
                        />
                      )}
                      {/* Other - specify textbox when 'Other' is selected */}
                      {Array.isArray(field.options) && field.options.includes('Other') && (() => {
                        const val = formData.templateData?.[section.title]?.[field.label];
                        const selectedValues: string[] = Array.isArray(val) ? val : (val ? [val] : []);
                        if (selectedValues.includes('Other')) {
                          const otherKey = `${field.label} - Other (specify)`;
                          return (
                            <input
                              type="text"
                              className="input w-full mt-2"
                              placeholder="Please specify"
                              value={formData.templateData?.[section.title]?.[otherKey] || ''}
                              onChange={(e) => setFormData(prev => ({
                                ...prev,
                                templateData: {
                                  ...prev.templateData,
                                  [section.title]: {
                                    ...prev.templateData?.[section.title],
                                    [otherKey]: e.target.value
                                  }
                                }
                              }))}
                            />
                          );
                        }
                        return null;
                      })()}
                      {!forceLanguagesAtHomeText && field.type === 'textarea' && (
                        <textarea
                          className="textarea w-full"
                          rows={3}
                          value={formData.templateData?.[section.title]?.[field.label] || ''}
                          onChange={(e) => setFormData(prev => ({
                            ...prev,
                            templateData: {
                              ...prev.templateData,
                              [section.title]: {
                                ...prev.templateData?.[section.title],
                                [field.label]: e.target.value
                              }
                            }
                          }))}
                        />
                      )}
                      {!forceLanguagesAtHomeText && field.type === 'date' && (
                        <input
                          type="date"
                          className="input w-44"
                          value={formData.templateData?.[section.title]?.[field.label] || ''}
                          onChange={(e) => {
                            const value = e.target.value;
                            setFormData(prev => {
                              const next = {
                                ...prev,
                                templateData: {
                                  ...prev.templateData,
                                  [section.title]: {
                                    ...prev.templateData?.[section.title],
                                    [field.label]: value
                                  }
                                }
                              } as FormData;
                              // Auto-calc Age at assessment when DOB changes
                              if (field.label.toLowerCase() === 'date of birth') {
                                const dob = new Date(value);
                                let refDateStr = prev.templateData?.[section.title]?.['Date(s) of assessment'];
                                let refDate: Date | null = null;
                                if (Array.isArray(refDateStr) && refDateStr.length > 0) {
                                  refDate = new Date(refDateStr[0]);
                                } else if (typeof refDateStr === 'string' && refDateStr) {
                                  refDate = new Date(refDateStr);
                                } else {
                                  refDate = new Date();
                                }
                                if (!isNaN(dob.getTime()) && refDate && !isNaN(refDate.getTime())) {
                                  let age = refDate.getFullYear() - dob.getFullYear();
                                  const m = refDate.getMonth() - dob.getMonth();
                                  if (m < 0 || (m === 0 && refDate.getDate() < dob.getDate())) age--;
                                  next.templateData[section.title]['Age at assessment'] = `${age}`;
                                }
                              }
                              return next;
                            });
                          }}
                        />
                      )}
                      {!forceLanguagesAtHomeText && field.type === 'date_multi' && (
                        <div className="space-y-2">
                          <div className="flex gap-2 items-center flex-wrap">
                            {(
                              Array.isArray(formData.templateData?.[section.title]?.[field.label])
                                ? formData.templateData?.[section.title]?.[field.label]
                                : (formData.templateData?.[section.title]?.[field.label]
                                    ? String(formData.templateData?.[section.title]?.[field.label]).split(',').map(s => s.trim()).filter(Boolean)
                                    : [])
                            ).map((d: string, i: number) => (
                              <div key={i} className="flex items-center gap-2">
                                <input
                                  type="date"
                                  className="input w-44"
                                  value={d}
                                  onChange={(e) => setFormData(prev => {
                                    const arr: string[] = Array.isArray(prev.templateData?.[section.title]?.[field.label])
                                      ? [...prev.templateData?.[section.title]?.[field.label]]
                                      : [];
                                    arr[i] = e.target.value;
                                    return {
                                      ...prev,
                                      templateData: {
                                        ...prev.templateData,
                                        [section.title]: {
                                          ...prev.templateData?.[section.title],
                                          [field.label]: arr
                                        }
                                      }
                                    };
                                  })}
                                />
                                <button
                                  type="button"
                                  className="px-2 py-1 text-xs bg-dark-700 rounded"
                                  onClick={() => setFormData(prev => {
                                    const arr: string[] = Array.isArray(prev.templateData?.[section.title]?.[field.label])
                                      ? [...prev.templateData?.[section.title]?.[field.label]]
                                      : [];
                                    arr.splice(i, 1);
                                    return {
                                      ...prev,
                                      templateData: {
                                        ...prev.templateData,
                                        [section.title]: {
                                          ...prev.templateData?.[section.title],
                                          [field.label]: arr
                                        }
                                      }
                                    };
                                  })}
                                >Remove</button>
                              </div>
                            ))}
                          </div>
                          <div className="flex gap-2">
                            <button
                              type="button"
                              className="px-3 py-1 text-sm bg-dark-700 rounded"
                              onClick={() => setFormData(prev => {
                                const arr: string[] = Array.isArray(prev.templateData?.[section.title]?.[field.label])
                                  ? [...prev.templateData?.[section.title]?.[field.label]]
                                  : [];
                                arr.push('');
                                return {
                                  ...prev,
                                  templateData: {
                                    ...prev.templateData,
                                    [section.title]: {
                                      ...prev.templateData?.[section.title],
                                      [field.label]: arr
                                    }
                                  }
                                };
                              })}
                            >Add date</button>
                            <button
                              type="button"
                              className="px-3 py-1 text-sm bg-dark-700 rounded"
                              onClick={() => setFormData(prev => {
                                const today = new Date();
                                const yyyy = today.getFullYear();
                                const mm = String(today.getMonth() + 1).padStart(2, '0');
                                const dd = String(today.getDate()).padStart(2, '0');
                                const val = `${yyyy}-${mm}-${dd}`;
                                const arr: string[] = Array.isArray(prev.templateData?.[section.title]?.[field.label])
                                  ? [...prev.templateData?.[section.title]?.[field.label]]
                                  : [];
                                arr.push(val);
                                return {
                                  ...prev,
                                  templateData: {
                                    ...prev.templateData,
                                    [section.title]: {
                                      ...prev.templateData?.[section.title],
                                      [field.label]: arr
                                    }
                                  }
                                };
                              })}
                            >Add today</button>
                          </div>
                        </div>
                      )}
                      {!forceLanguagesAtHomeText && field.type === 'select' && (
                        <select
                          className="input w-full"
                          value={formData.templateData?.[section.title]?.[field.label] || ''}
                          onChange={(e) => setFormData(prev => ({
                            ...prev,
                            templateData: {
                              ...prev.templateData,
                              [section.title]: {
                                ...prev.templateData?.[section.title],
                                [field.label]: e.target.value
                              }
                            }
                          }))}
                        >
                          <option value="">Select</option>
                          {(field.options || []).map((opt, i) => (
                            <option key={i} value={opt}>{opt}</option>
                          ))}
                        </select>
                      )}
                      {!forceLanguagesAtHomeText && field.type === 'multi_select' && (
                        <div className="max-h-40 overflow-y-auto border border-dark-700 rounded p-2">
                          {(field.options || []).map((opt, i) => {
                            const selected: string[] = formData.templateData?.[section.title]?.[field.label] || [];
                            const checked = selected.includes(opt);
                            return (
                              <label key={i} className="flex items-center gap-2 py-1">
                                <input
                                  type="checkbox"
                                  className="checkbox"
                                  checked={checked}
                                  onChange={(e) => {
                                    const next = new Set<string>(selected);
                                    if ((e.target as HTMLInputElement).checked) next.add(opt); else next.delete(opt);
                                    setFormData(prev => ({
                                      ...prev,
                                      templateData: {
                                        ...prev.templateData,
                                        [section.title]: {
                                          ...prev.templateData?.[section.title],
                                          [field.label]: Array.from(next)
                                        }
                                      }
                                    }));
                                  }}
                                />
                                <span className="text-gray-200 text-sm">{opt}</span>
                              </label>
                            );
                          })}
                        </div>
                      )}
                      {!forceLanguagesAtHomeText && field.type === 'checkbox' && (
                        <input
                          type="checkbox"
                          className="checkbox"
                          checked={!!formData.templateData?.[section.title]?.[field.label]}
                          onChange={(e) => setFormData(prev => ({
                            ...prev,
                            templateData: {
                              ...prev.templateData,
                              [section.title]: {
                                ...prev.templateData?.[section.title],
                                [field.label]: (e.target as HTMLInputElement).checked
                              }
                            }
                          }))}
                        />
                      )}
                      {!forceLanguagesAtHomeText && field.type === 'checkboxes' && (
                        <div className="max-h-40 overflow-y-auto border border-dark-700 rounded p-2">
                          {(field.options || []).map((opt, i) => {
                            const selected: string[] = formData.templateData?.[section.title]?.[field.label] || [];
                            const checked = selected.includes(opt);
                            return (
                              <label key={i} className="flex items-center gap-2 py-1">
                                <input
                                  type="checkbox"
                                  className="checkbox"
                                  checked={checked}
                                  onChange={(e) => {
                                    const next = new Set<string>(selected);
                                    if ((e.target as HTMLInputElement).checked) next.add(opt); else next.delete(opt);
                                    setFormData(prev => ({
                                      ...prev,
                                      templateData: {
                                        ...prev.templateData,
                                        [section.title]: {
                                          ...prev.templateData?.[section.title],
                                          [field.label]: Array.from(next)
                                        }
                                      }
                                    }));
                                  }}
                                />
                                <span className="text-gray-200 text-sm">{opt}</span>
                              </label>
                            );
                          })}
                        </div>
                      )}
                      {!forceLanguagesAtHomeText && field.type === 'file' && (
                        <input
                          type="file"
                          className="input w-full"
                          onChange={(e) => setFormData(prev => ({
                            ...prev,
                            templateData: {
                              ...prev.templateData,
                              [section.title]: {
                                ...prev.templateData?.[section.title],
                                [field.label]: (e.target as HTMLInputElement).files ? Array.from((e.target as HTMLInputElement).files as FileList).map(f => f.name) : []
                              }
                            }
                          }))}
                          multiple
                        />
                      )}
                      {!forceLanguagesAtHomeText && field.type === 'table' && !isTestsAdministeredSection(section.title) && (
                        <textarea
                          className="textarea w-full"
                          rows={4}
                          placeholder={field.placeholder || 'Paste or enter structured rows'}
                          value={formData.templateData?.[section.title]?.[field.label] || ''}
                          onChange={(e) => setFormData(prev => ({
                            ...prev,
                            templateData: {
                              ...prev.templateData,
                              [section.title]: {
                                ...prev.templateData?.[section.title],
                                [field.label]: e.target.value
                              }
                            }
                          }))}
                        />
                      )}
                    </div>
                  );
                })}
              </div>
            </div>
          ))}


          <div className="flex justify-end pt-4">
            {progressMessage && (
              <div className="text-blue-400 mb-4 mr-4">
                {progressMessage}
              </div>
            )}
            <button
              type="button"
              className="btn btn-primary px-16"
              onClick={handleSubmit}
              disabled={loading || !formData.patient_name.trim() || !formData.template_id}
            >
              {loading ? 'Generating...' : 'Generate Report'}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
                
