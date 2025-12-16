import { Link } from 'react-router-dom';
import { FileText, FileStack, Layout, Brain } from 'lucide-react';

export default function HomePage() {
  const features = [
    {
      icon: FileText,
      title: 'New Report',
      description: 'Generate reports with AI',
      link: '/new-report',
      color: 'text-blue-500',
    },
    {
      icon: Layout,
      title: 'Text Editor',
      description: 'Write reports manually with templates and insertable paragraphs',
      link: '/editor',
      color: 'text-purple-500',
    },
    {
      icon: FileStack,
      title: 'Reports',
      description: 'View and manage your generated reports',
      link: '/reports',
      color: 'text-green-500',
    },
  ];

  return (
    <div className="p-8">
      <div className="max-w-6xl mx-auto">
        {/* Header */}
        <div className="mb-12">
          <div className="flex items-center space-x-4 mb-4">
            <Brain size={48} className="text-primary-500" />
            <div>
              <h1 className="text-4xl font-bold text-white">
                Psychological Report Generator
              </h1>
              <p className="text-gray-400 mt-2">
                AI-powered offline tool for creating professional psychological reports
              </p>
            </div>
          </div>
        </div>

        {/* Features Grid */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-12">
          {features.map((feature) => {
            const Icon = feature.icon;
            return (
              <Link
                key={feature.title}
                to={feature.link}
                className="card hover:border-primary-600 transition-colors cursor-pointer group"
              >
                <div className="flex flex-col items-center text-center space-y-4">
                  <div className={`${feature.color} group-hover:scale-110 transition-transform`}>
                    <Icon size={48} />
                  </div>
                  <div>
                    <h3 className="text-xl font-semibold text-white mb-2">
                      {feature.title}
                    </h3>
                    <p className="text-gray-400">{feature.description}</p>
                  </div>
                </div>
              </Link>
            );
          })}
        </div>

        {/* Quick Start */}
        <div className="card bg-gradient-to-r from-primary-900/20 to-purple-900/20 border-primary-700">
          <h2 className="text-2xl font-bold text-white mb-4">Quick Start</h2>
          <ol className="space-y-3 text-gray-300">
            <li className="flex items-start">
              <span className="font-bold text-primary-500 mr-3">1.</span>
              <span>Choose to generate a report with AI or write manually</span>
            </li>
            <li className="flex items-start">
              <span className="font-bold text-primary-500 mr-3">2.</span>
              <span>Select or create a report template</span>
            </li>
            <li className="flex items-start">
              <span className="font-bold text-primary-500 mr-3">3.</span>
              <span>Fill in the required information</span>
            </li>
            <li className="flex items-start">
              <span className="font-bold text-primary-500 mr-3">4.</span>
              <span>Review, edit, and export your professional report</span>
            </li>
          </ol>
        </div>
      </div>
    </div>
  );
}
