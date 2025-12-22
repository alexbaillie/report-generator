import { useState, useRef, useEffect } from 'react';
import { Search, Plus, Save, Upload, Feather, Loader2 } from 'lucide-react';
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
      title: 'Example Paragraph 1',
      content: 'Lorem ipsum dolor sit amet, consectetur adipiscing elit, sed do eiusmod tempor incididunt...',
    },
    {
      title: 'Example Paragraph 2',
      content: 'Lorem ipsum dolor sit amet, consectetur adipiscing elit, sed...',
    },
    {
      title: 'Example Paragraph 3',
      content: 'Lorem ipsum dolor sit amet, consectetur adipiscing elit,...',
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
    if (!aiPrompt.trim() || isGenerating) return;

    setIsGenerating(true);
    try {
      // Call AI API with current content and prompt
      const response = await api.generateText({
        prompt: aiPrompt,
        context: content,
      });

      // Replace content with AI-generated text
      setContent(response.text);
      setAiPrompt('');
    } catch (error) {
      console.error('Error generating text:', error);
      alert('Failed to generate text. Please try again.');
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
            <button className="px-6 py-2 bg-primary-600 hover:bg-primary-700 text-white rounded font-medium transition-colors">
              Generate Report with AI
            </button>
          </div>
        </div>

        {/* Editor */}
        <div className="flex-1 p-8 overflow-y-auto">
          <div className="max-w-4xl mx-auto bg-white rounded shadow-lg min-h-full p-12">
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
