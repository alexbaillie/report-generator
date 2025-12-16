import axios from 'axios';

const API_BASE_URL = 'http://localhost:8000/api';

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

export const api = {
  // Reports
  async generateReport(data: any) {
    const response = await apiClient.post('/reports/generate', data);
    return response.data;
  },

  async getReports() {
    const response = await apiClient.get('/reports/');
    return response.data;
  },

  async getReport(id: number) {
    const response = await apiClient.get(`/reports/${id}`);
    return response.data;
  },

  async deleteReport(id: number) {
    const response = await apiClient.delete(`/reports/${id}`);
    return response.data;
  },

  // Documents
  async uploadDocument(file: File) {
    const formData = new FormData();
    formData.append('file', file);
    
    const response = await apiClient.post('/documents/upload', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    return response.data;
  },

  async getDocuments() {
    const response = await apiClient.get('/documents/');
    return response.data;
  },

  async getDocument(id: number) {
    const response = await apiClient.get(`/documents/${id}`);
    return response.data;
  },

  async deleteDocument(id: number) {
    const response = await apiClient.delete(`/documents/${id}`);
    return response.data;
  },

  // Templates
  async createTemplate(data: any) {
    const response = await apiClient.post('/templates/', data);
    return response.data;
  },

  async getTemplates() {
    const response = await apiClient.get('/templates/');
    return response.data;
  },

  async getTemplate(id: number) {
    const response = await apiClient.get(`/templates/${id}`);
    return response.data;
  },

  async updateTemplate(id: number, data: any) {
    const response = await apiClient.put(`/templates/${id}`, data);
    return response.data;
  },

  async deleteTemplate(id: number) {
    const response = await apiClient.delete(`/templates/${id}`);
    return response.data;
  },

  // AI Text Generation
  async generateText(data: { prompt: string; context: string }) {
    const response = await apiClient.post('/ai/generate-text', data);
    return response.data;
  },
};
