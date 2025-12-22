import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Loader2, Upload, Plus } from 'lucide-react';
import { api } from '../services/api';

interface TestTableEntry {
  type: string;
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

interface FormData {
  title: string;
  template: string;
  testTableEntries: TestTableEntry[];
  session_observations: string;
  previous_reports: string;
  other_info: string;
  other_info_description: string;
  report_type: string;
  template_id: string;
  document_ids: number[];
}

export default function NewReportPage() {
  const navigate = useNavigate();
  const [step, setStep] = useState(1);
  const [loading, setLoading] = useState(false);
  const [templates, setTemplates] = useState<Template[]>([]);
  const [formData, setFormData] = useState<FormData>({
    title: 'Neuropsychological Assessment',
    template: '',
    testTableEntries: [{ type: '', description: '', files: [] }],
    session_observations: '',
    previous_reports: '',
    other_info: '',
    other_info_description: '',
    report_type: 'evaluation',
    template_id: '1',
    document_ids: [],
  });

  useEffect(() => {
    loadTemplates();
  }, []);

  const loadTemplates = async () => {
    try {
      const data = await api.getTemplates();
      setTemplates(data);
      // Set default template if available
      const defaultTemplate = data.find((t: Template) => t.is_default);
      if (defaultTemplate) {
        setFormData(prev => ({ ...prev, template_id: defaultTemplate.id.toString() }));
      }
    } catch (error) {
      console.error('Failed to load templates:', error);
    }
  };

  const handleFileUpload = (index: number) => async (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (files && files.length > 0) {
      const newFiles = Array.from(files);
      setFormData(prev => ({
        ...prev,
        testTableEntries: prev.testTableEntries.map((entry, i) =>
          i === index ? { ...entry, files: [...entry.files, ...newFiles] } : entry
        )
      }));
    }
  };

  const handleTextFileUpload = (field: keyof FormData) => async (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (files && files.length > 0) {
      // For text fields, read the first file
      const file = files[0];
      const reader = new FileReader();
      reader.onload = (event) => {
        const content = event.target?.result as string;
        setFormData(prev => ({
          ...prev,
          [field]: content
        }));
      };
      reader.readAsText(file);
    }
  };

  const addTestTable = () => {
    setFormData(prev => ({
      ...prev,
      testTableEntries: [...prev.testTableEntries, { type: '', description: '', files: [] }]
    }));
  };

  const handleSubmit = async () => {
    setLoading(true);
    try {
      await api.generateReport({
        title: formData.title,
        patient_name: '',
        report_type: formData.report_type,
        template_id: parseInt(formData.template_id),
        document_ids: formData.document_ids,
        additional_inputs: {
          session_observations: formData.session_observations,
          previous_reports: formData.previous_reports,
          other_info: formData.other_info,
        },
      });
      alert('Report generated successfully!');
      // Navigate to reports page after clicking OK
      navigate('/reports');
    } catch (error) {
      alert('Failed to generate report. Please try again.');
      console.error('Error generating report:', error);
    } finally {
      setLoading(false);
    }
  };

  const renderStep = () => {
    switch (step) {
      case 1:
        return (
          <div className="space-y-6">
            <div>
              <label className="text-white text-lg mb-3 block">Choose template</label>
              <select
                className="input w-full max-w-md"
                value={formData.template_id}
                onChange={(e) => setFormData({ ...formData, template_id: e.target.value })}
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
              <label className="text-white text-lg mb-3 block">Upload test table or type/paste</label>
              {formData.testTableEntries.map((entry, index) => (
                <div key={index} className="mb-6 p-4 border border-dark-600 rounded">
                  <div className="flex items-start gap-3 mb-3">
                    <select
                      className="input flex-1 max-w-md"
                      value={entry.type}
                      onChange={(e) => setFormData(prev => ({
                        ...prev,
                        testTableEntries: prev.testTableEntries.map((ent, i) =>
                          i === index ? { ...ent, type: e.target.value } : ent
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
                  <textarea
                    className="textarea w-full"
                    rows={4}
                    placeholder=""
                    value={entry.description}
                    onChange={(e) => setFormData(prev => ({
                      ...prev,
                      testTableEntries: prev.testTableEntries.map((ent, i) =>
                        i === index ? { ...ent, description: e.target.value } : ent
                      )
                    }))}
                  />
                </div>
              ))}
            </div>

            <button
              type="button"
              className="bg-dark-700 hover:bg-dark-600 text-gray-100 px-4 py-2 rounded flex items-center gap-2"
              onClick={addTestTable}
            >
              <Plus size={20} />
              Upload another test table
            </button>

            <div className="flex justify-end pt-4">
              <button
                type="button"
                className="btn btn-primary px-16"
                onClick={() => setStep(2)}
              >
                Next
              </button>
            </div>
          </div>
        );

      case 2:
        return (
          <div className="space-y-6">
            <div>
              <label className="text-white text-lg mb-3 block">Upload session observations or type/paste</label>
              <div className="flex items-start gap-3 mb-3">
                <button
                  type="button"
                  className="bg-dark-700 p-2 rounded hover:bg-dark-600 transition-colors"
                  onClick={() => document.getElementById('session-observations-upload')?.click()}
                >
                  <Upload size={24} className="text-gray-300" />
                </button>
              </div>
              <textarea
                className="textarea w-full"
                rows={4}
                value={formData.session_observations}
                onChange={(e) => setFormData({ ...formData, session_observations: e.target.value })}
                placeholder=""
              />
              <input
                id="session-observations-upload"
                type="file"
                className="hidden"
                onChange={handleTextFileUpload('session_observations')}
              />
            </div>

            <div>
              <label className="text-white text-lg mb-3 block">Upload previous reports or type/paste</label>
              <div className="flex items-start gap-3 mb-3">
                <button
                  type="button"
                  className="bg-dark-700 p-2 rounded hover:bg-dark-600 transition-colors"
                  onClick={() => document.getElementById('previous-reports-upload')?.click()}
                >
                  <Upload size={24} className="text-gray-300" />
                </button>
              </div>
              <textarea
                className="textarea w-full"
                rows={4}
                value={formData.previous_reports}
                onChange={(e) => setFormData({ ...formData, previous_reports: e.target.value })}
                placeholder=""
              />
              <input
                id="previous-reports-upload"
                type="file"
                className="hidden"
                onChange={handleTextFileUpload('previous_reports')}
              />
            </div>

            <div>
              <label className="text-white text-lg mb-3 block">Upload other info or type/paste</label>
              <input
                type="text"
                className="input w-full max-w-sm mb-3"
                placeholder="Describe..."
                value={formData.other_info_description}
                onChange={(e) => setFormData({ ...formData, other_info_description: e.target.value })}
              />
              <div className="flex items-start gap-3 mb-3">
                <button
                  type="button"
                  className="bg-dark-700 p-2 rounded hover:bg-dark-600 transition-colors"
                  onClick={() => document.getElementById('other-info-upload')?.click()}
                >
                  <Upload size={24} className="text-gray-300" />
                </button>
              </div>
              <textarea
                className="textarea w-full"
                rows={4}
                value={formData.other_info}
                onChange={(e) => setFormData({ ...formData, other_info: e.target.value })}
                placeholder=""
              />
              <input
                id="other-info-upload"
                type="file"
                className="hidden"
                onChange={handleTextFileUpload('other_info')}
              />
            </div>

            <div className="flex justify-between pt-4">
              <button
                type="button"
                className="btn btn-secondary px-16"
                onClick={() => setStep(1)}
              >
                Previous
              </button>
              <button
                type="button"
                className="btn btn-primary px-16"
                onClick={() => setStep(3)}
              >
                Next
              </button>
            </div>
          </div>
        );

      case 3:
        return (
          <div className="space-y-6">
            <div className="flex items-center justify-center min-h-[400px]">
              <button
                type="button"
                className="btn btn-primary px-12 py-4 text-lg"
                onClick={handleSubmit}
                disabled={loading}
              >
                {loading ? (
                  <span className="flex items-center gap-2">
                    <Loader2 className="animate-spin" size={20} />
                    Analyzing...
                  </span>
                ) : (
                  'Analyze information and prepare report'
                )}
              </button>
            </div>
            <div className="flex justify-start pt-4">
              <button
                type="button"
                className="btn btn-secondary px-16"
                onClick={() => setStep(2)}
                disabled={loading}
              >
                Previous
              </button>
            </div>
          </div>
        );

      default:
        return null;
    }
  };

  return (
    <div className="p-8">
      <div className="max-w-4xl mx-auto">
        {/* Step Indicator */}
        <div className="mb-8">
          <div className="flex items-center justify-center space-x-4">
            {[1, 2, 3].map((stepNumber) => (
              <div key={stepNumber} className="flex items-center">
                <div
                  className={`w-10 h-10 rounded-full flex items-center justify-center font-semibold ${
                    step === stepNumber
                      ? 'bg-primary-600 text-white'
                      : step > stepNumber
                      ? 'bg-green-600 text-white'
                      : 'bg-dark-700 text-gray-400'
                  }`}
                >
                  {stepNumber}
                </div>
                {stepNumber < 3 && (
                  <div
                    className={`w-16 h-1 ${
                      step > stepNumber ? 'bg-green-600' : 'bg-dark-700'
                    }`}
                  />
                )}
              </div>
            ))}
          </div>
          <div className="flex justify-center mt-4">
            <p className="text-gray-400 text-sm">
              Step {step} of 3: {step === 1 ? 'Template & Test Tables' : step === 2 ? 'Additional Information' : 'Generate Report'}
            </p>
          </div>
        </div>

        {renderStep()}
      </div>
    </div>
  );
}
                