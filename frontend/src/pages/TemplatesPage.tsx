import { useState, useEffect } from 'react';
import { Layout, Plus, Edit2, Trash2 } from 'lucide-react';
import { api } from '../services/api';

interface Template {
  id: number;
  name: string;
  description: string;
  template_type: string;
  content: string;
  is_default: boolean;
}

export default function TemplatesPage() {
  const [templates, setTemplates] = useState<Template[]>([]);
  const [showModal, setShowModal] = useState(false);
  const [editingTemplate, setEditingTemplate] = useState<Template | null>(null);
  const [formData, setFormData] = useState({
    name: '',
    description: '',
    template_type: 'intake',
    content: '',
    is_default: false,
  });

  useEffect(() => {
    loadTemplates();
  }, []);

  const loadTemplates = async () => {
    try {
      const data = await api.getTemplates();
      setTemplates(data);
    } catch (error) {
      console.error('Failed to load templates:', error);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    try {
      if (editingTemplate) {
        await api.updateTemplate(editingTemplate.id, formData);
      } else {
        await api.createTemplate(formData);
      }
      
      await loadTemplates();
      handleCloseModal();
    } catch (error) {
      alert('Failed to save template');
      console.error('Error saving template:', error);
    }
  };

  const handleEdit = (template: Template) => {
    setEditingTemplate(template);
    setFormData({
      name: template.name,
      description: template.description,
      template_type: template.template_type,
      content: template.content,
      is_default: template.is_default,
    });
    setShowModal(true);
  };

  const handleDelete = async (id: number) => {
    if (!confirm('Are you sure you want to delete this template?')) return;

    try {
      await api.deleteTemplate(id);
      setTemplates(templates.filter((t) => t.id !== id));
    } catch (error) {
      alert('Failed to delete template');
      console.error('Error deleting template:', error);
    }
  };

  const handleCloseModal = () => {
    setShowModal(false);
    setEditingTemplate(null);
    setFormData({
      name: '',
      description: '',
      template_type: 'intake',
      content: '',
      is_default: false,
    });
  };

  return (
    <div className="p-8">
      <div className="max-w-6xl mx-auto">
        <div className="flex items-center justify-between mb-8">
          <div>
            <h1 className="text-3xl font-bold text-white flex items-center">
              <Layout className="mr-3" size={32} />
              Report Templates
            </h1>
            <p className="text-gray-400 mt-2">
              Manage templates for different types of psychological reports
            </p>
          </div>
          <button
            onClick={() => setShowModal(true)}
            className="btn btn-primary flex items-center"
          >
            <Plus size={20} className="mr-2" />
            New Template
          </button>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {templates.map((template) => (
            <div key={template.id} className="card">
              <div className="flex items-start justify-between mb-4">
                <div className="flex-1">
                  <h3 className="text-xl font-semibold text-white">{template.name}</h3>
                  <p className="text-gray-400 text-sm mt-1">{template.description}</p>
                </div>
                {template.is_default && (
                  <span className="px-2 py-1 bg-primary-600 text-white text-xs rounded">
                    Default
                  </span>
                )}
              </div>

              <div className="mb-4">
                <span className="text-xs px-2 py-1 bg-dark-700 rounded text-gray-300">
                  {template.template_type}
                </span>
              </div>

              <div className="flex space-x-2">
                <button
                  onClick={() => handleEdit(template)}
                  className="btn btn-secondary flex items-center text-sm"
                >
                  <Edit2 size={16} className="mr-1" />
                  Edit
                </button>
                <button
                  onClick={() => handleDelete(template.id)}
                  className="btn bg-red-600 hover:bg-red-700 text-white flex items-center text-sm"
                >
                  <Trash2 size={16} className="mr-1" />
                  Delete
                </button>
              </div>
            </div>
          ))}
        </div>

        {templates.length === 0 && (
          <div className="text-center text-gray-500 mt-12">
            <Layout size={64} className="mx-auto mb-4 opacity-50" />
            <p>No templates yet. Create your first template to get started.</p>
          </div>
        )}
      </div>

      {/* Modal */}
      {showModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-dark-800 rounded-lg p-6 w-full max-w-2xl max-h-[90vh] overflow-auto">
            <h2 className="text-2xl font-bold text-white mb-4">
              {editingTemplate ? 'Edit Template' : 'New Template'}
            </h2>

            <form onSubmit={handleSubmit} className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-2">
                  Template Name
                </label>
                <input
                  type="text"
                  className="input"
                  value={formData.name}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                  required
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-300 mb-2">
                  Description
                </label>
                <input
                  type="text"
                  className="input"
                  value={formData.description}
                  onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-300 mb-2">
                  Template Type
                </label>
                <select
                  className="input"
                  value={formData.template_type}
                  onChange={(e) => setFormData({ ...formData, template_type: e.target.value })}
                  required
                >
                  <option value="intake">Intake Assessment</option>
                  <option value="progress">Progress Note</option>
                  <option value="evaluation">Psychological Evaluation</option>
                  <option value="discharge">Discharge Summary</option>
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-300 mb-2">
                  Template Content / Instructions
                </label>
                <textarea
                  className="textarea"
                  rows={10}
                  value={formData.content}
                  onChange={(e) => setFormData({ ...formData, content: e.target.value })}
                  placeholder="Enter the template structure or instructions for AI generation..."
                  required
                />
              </div>

              <div className="flex items-center">
                <input
                  type="checkbox"
                  id="is_default"
                  checked={formData.is_default}
                  onChange={(e) => setFormData({ ...formData, is_default: e.target.checked })}
                  className="mr-2"
                />
                <label htmlFor="is_default" className="text-sm text-gray-300">
                  Set as default template
                </label>
              </div>

              <div className="flex justify-end space-x-2 pt-4">
                <button
                  type="button"
                  onClick={handleCloseModal}
                  className="btn btn-secondary"
                >
                  Cancel
                </button>
                <button type="submit" className="btn btn-primary">
                  {editingTemplate ? 'Update' : 'Create'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
