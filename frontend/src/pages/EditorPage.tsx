import { useState, useRef, useEffect } from 'react';
import { Search, Plus, Save, Upload, Feather, Loader2 } from 'lucide-react';
import axios from 'axios';
import { api } from '../services/api';

interface Template {
  id: number;
  name: string;
  description: string;
  template_type: string;
  content: string;
  is_default: boolean;
}

export default function EditorPage() {
  const [content, setContent] = useState('');
  const [searchParagraph, setSearchParagraph] = useState('');
  const [searchTemplate, setSearchTemplate] = useState('');
  const [aiPrompt, setAiPrompt] = useState('');
  const [isGenerating, setIsGenerating] = useState(false);
  const [aiError, setAiError] = useState<string | null>(null);
  const [templates, setTemplates] = useState<Template[]>([]);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

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

  const exampleParagraphs = [
    {
      title: 'Confidentiality Statement',
      content: `This is a CONFIDENTIAL report intended solely for the use of [insert full name], her legal guardian(s), and other specifically named individuals. Requests for copies of this report should be directed to [insert first name]'s legal guardian(s).`,
    },
    {
      title: 'Purpose of Report / Program Context',
      content: `This psychological assessment was completed as part of a multidisciplinary evaluation through the [program name] at the request of [referring professional]. The purpose of this assessment was to evaluate [insert first name]'s current cognitive, academic, adaptive, and social-emotional functioning and to provide recommendations to support her development across home, school, and community settings.`,
    },
    {
      title: 'Diagnostic Criteria Met (Learning Disorders – General)',
      content: `Based on the results of the current assessment, review of background information, and reports from caregivers and teachers, [insert first name] meets diagnostic criteria for Specific Learning Disorder with impairments in [reading / written expression / mathematics]. Given the breadth and severity of difficulties observed across multiple domains, the severity of these learning disorders is considered severe.`,
    },
  ];

  const suggestionPrompts = [
    'Add a confidentiality section',
    'Generate summary section',
  ];

  // Insert template content (replaces all content)
  const handleTemplateClick = (template: Template) => {
    // Extract the template structure from the content (remove AI instructions)
    const content = template.content;
    const structureStart = content.indexOf('Psych Report Template') || content.indexOf('INTAKE ASSESSMENT') || 0;
    const templateStructure = structureStart > 0 ? content.substring(structureStart) : content;
    
    // Remove the final instruction if present
    const endMarker = 'Please fill in each section';
    const endIndex = templateStructure.indexOf(endMarker);
    const cleanStructure = endIndex > 0 ? templateStructure.substring(0, endIndex).trim() : templateStructure;
    
    setContent(cleanStructure);
  };

  // Insert paragraph at cursor position
  const handleParagraphClick = (paragraph: typeof exampleParagraphs[0]) => {
    const textarea = textareaRef.current;
    if (!textarea) return;

    const cursorPos = textarea.selectionStart;
    const textBefore = content.substring(0, cursorPos);
    const textAfter = content.substring(cursorPos);
    
    const newContent = textBefore + '\n\n' + paragraph.content + '\n\n' + textAfter;
    setContent(newContent);

    // Set cursor position after inserted text
    setTimeout(() => {
      const newCursorPos = cursorPos + paragraph.content.length + 4;
      textarea.setSelectionRange(newCursorPos, newCursorPos);
      textarea.focus();
    }, 0);
  };

  // Handle suggestion prompt click
  const handleSuggestionClick = (suggestion: string) => {
    setAiPrompt(suggestion);
  };

  // Handle AI prompt submission
  const handleAiSubmit = async () => {
    console.log('[EditorPage] Generate Report with AI clicked');
    setAiError(null);

    if (isGenerating) return;

    const prompt = aiPrompt.trim();
    if (!prompt) {
      setAiError('Please enter an AI prompt (or click a suggestion prompt) before generating.');
      return;
    }

    setIsGenerating(true);
    try {
      // Call AI API with current content and prompt
      console.log('[EditorPage] Sending AI request to /api/ai/generate-text', {
        prompt,
        contextLength: content.length,
      });

      const response = await api.generateText({
        prompt,
        context: content,
      });

      console.log('[EditorPage] AI response received', response);

      const generatedText =
        (response && typeof response === 'object' && 'text' in response) ? (response as any).text : response;

      if (!generatedText || typeof generatedText !== 'string') {
        throw new Error('AI response was not in the expected format.');
      }

      // Replace content with AI-generated text
      setContent(generatedText);
      setAiPrompt('');
    } catch (error) {
      console.error('[EditorPage] Error generating text:', error);
      if (axios.isAxiosError(error)) {
        // Axios uses "Network Error" when the server is unreachable / connection refused.
        if (!error.response) {
          setAiError('Cannot reach the backend at http://127.0.0.1:8000. Make sure the backend is running, then try again.');
          return;
        }

        const detail = (error.response.data && typeof error.response.data === 'object' && 'detail' in error.response.data)
          ? (error.response.data as any).detail
          : null;

        setAiError(detail || `Backend request failed (${error.response.status}). Please try again.`);
        return;
      }

      const msg = error instanceof Error
        ? error.message
        : 'Failed to generate text. Please try again.';
      setAiError(msg);
    } finally {
      setIsGenerating(false);
    }
  };

  return (
    <div className="flex h-full bg-dark-900">
      {/* Left Sidebar - Paragraphs */}
      <div className="w-64 bg-dark-800 border-r border-dark-700 flex flex-col">
        <div className="p-4 border-b border-dark-700">
          <div className="flex items-center justify-between mb-3">
            <h2 className="text-lg font-semibold text-white">Paragraphs</h2>
            <button className="p-1 hover:bg-dark-700 rounded">
              <Plus size={20} className="text-gray-400" />
            </button>
          </div>
          <div className="relative">
            <input
              type="text"
              placeholder="Search..."
              value={searchParagraph}
              onChange={(e) => setSearchParagraph(e.target.value)}
              className="w-full px-3 py-2 pr-8 bg-dark-700 border-0 rounded text-sm text-gray-100 placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-primary-600"
            />
            <Search size={16} className="absolute right-2 top-1/2 -translate-y-1/2 text-gray-400" />
          </div>
        </div>

        <div className="flex-1 overflow-y-auto p-3">
          {exampleParagraphs.map((para, idx) => (
            <div
              key={idx}
              onClick={() => handleParagraphClick(para)}
              className="mb-3 p-3 bg-dark-700 rounded cursor-pointer hover:bg-dark-600 transition-colors"
            >
              <h3 className="text-sm font-semibold text-white mb-1">{para.title}</h3>
              <p className="text-xs text-gray-400 line-clamp-3">{para.content}</p>
            </div>
          ))}
        </div>

        {/* Templates Section */}
        <div className="border-t border-dark-700">
          <div className="p-4 border-b border-dark-700">
            <div className="flex items-center justify-between mb-3">
              <h2 className="text-lg font-semibold text-white">Templates</h2>
              <button className="p-1 hover:bg-dark-700 rounded">
                <Plus size={20} className="text-gray-400" />
              </button>
            </div>
            <div className="relative">
              <input
                type="text"
                placeholder="Search..."
                value={searchTemplate}
                onChange={(e) => setSearchTemplate(e.target.value)}
                className="w-full px-3 py-2 pr-8 bg-dark-700 border-0 rounded text-sm text-gray-100 placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-primary-600"
              />
              <Search size={16} className="absolute right-2 top-1/2 -translate-y-1/2 text-gray-400" />
            </div>
          </div>

          <div className="p-3 max-h-48 overflow-y-auto">
            {templates
              .filter(template => 
                template.name.toLowerCase().includes(searchTemplate.toLowerCase()) ||
                template.description?.toLowerCase().includes(searchTemplate.toLowerCase())
              )
              .map((template) => (
                <div
                  key={template.id}
                  onClick={() => handleTemplateClick(template)}
                  className="mb-3 p-3 bg-dark-700 rounded cursor-pointer hover:bg-dark-600 transition-colors"
                >
                  <h3 className="text-sm font-semibold text-white mb-1">{template.name}</h3>
                  <p className="text-xs text-gray-400">{template.description || 'No description'}</p>
                </div>
              ))}
          </div>
        </div>
      </div>

      {/* Main Editor Area */}
      <div className="flex-1 flex flex-col bg-dark-900">
        {/* Top Bar */}
        <div className="bg-dark-800 border-b border-dark-700 p-4 flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <Feather size={24} className="text-primary-500" />
            <h1 className="text-xl font-semibold text-white">ReportMate</h1>
          </div>
          <div className="flex items-center space-x-3">
            <button className="p-2 hover:bg-dark-700 rounded transition-colors">
              <Save size={20} className="text-gray-400" />
            </button>
            <button className="p-2 hover:bg-dark-700 rounded transition-colors">
              <Upload size={20} className="text-gray-400" />
            </button>
          </div>
        </div>

        {/* Editor */}
        <div className="flex-1 p-8 overflow-y-auto">
          <div className="max-w-4xl mx-auto bg-white rounded shadow-lg min-h-full p-12">
            {aiError ? (
              <div className="mb-4 rounded border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800">
                {aiError}
              </div>
            ) : null}
            <textarea
              ref={textareaRef}
              value={content}
              onChange={(e) => setContent(e.target.value)}
              placeholder="Start writing..."
              className="w-full h-full min-h-[600px] border-0 focus:outline-none resize-none text-gray-900 text-base leading-relaxed bg-white placeholder-gray-400"
            />
          </div>
        </div>
      </div>

      {/* Right Sidebar - AI Assistant */}
      <div className="w-80 bg-dark-800 border-l border-dark-700 flex flex-col">
        <div className="p-4 border-b border-dark-700">
          <h2 className="text-lg font-semibold text-white">AI Assistant</h2>
        </div>

        <div className="p-4 border-b border-dark-700">
          <div className="relative">
            <input
              type="text"
              placeholder="Prompt..."
              value={aiPrompt}
              onChange={(e) => setAiPrompt(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleAiSubmit()}
              className="w-full px-3 py-2 pr-10 bg-dark-700 border-0 rounded text-sm text-gray-100 placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-primary-600"
            />
            <button 
              onClick={handleAiSubmit}
              disabled={isGenerating}
              className="absolute right-2 top-1/2 -translate-y-1/2 text-gray-400 hover:text-primary-500 disabled:opacity-50"
            >
              {isGenerating ? <Loader2 className="animate-spin" size={16} /> : '▶'}
            </button>
          </div>
        </div>

        <div className="flex-1 overflow-y-auto p-4">
          <div className="mb-6">
            <h3 className="text-sm font-semibold text-white mb-3">Suggestion Prompts</h3>
            <div className="space-y-2">
              {suggestionPrompts.map((prompt, idx) => (
                <button
                  key={idx}
                  onClick={() => handleSuggestionClick(prompt)}
                  className="w-full text-left px-3 py-2 bg-dark-700 hover:bg-dark-600 rounded text-sm text-gray-300 transition-colors"
                >
                  {prompt}
                </button>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
