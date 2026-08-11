const API_BASE = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000/api/v1";

export function setToken(token: string) { localStorage.setItem("medresearch_token", token); }
export function getToken() { return localStorage.getItem("medresearch_token"); }
export function clearToken() { localStorage.removeItem("medresearch_token"); }

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const token = getToken();
  const response = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: { "Content-Type": "application/json", ...(token ? { Authorization: `Bearer ${token}` } : {}), ...(options.headers ?? {}) },
  });
  const body = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(body.detail ?? "Request failed");
  return body as T;
}

export const api = {
  register: (email: string, password: string) => request<{id:number;email:string}>("/auth/register", { method:"POST", body:JSON.stringify({email,password}) }),
  login: async (email: string, password: string) => { const result = await request<{access_token:string}>("/auth/login", { method:"POST", body:JSON.stringify({email,password}) }); setToken(result.access_token); return result; },
  search: (q: string, offset = 0) => request<{total:number;papers:Paper[]}>(`/papers/search?q=${encodeURIComponent(q)}&limit=10&offset=${offset}`),
  summarize: (pmid: string) => request<Summary>(`/papers/${pmid}/summarize`, { method:"POST" }),
  patientExplanation: (pmid: string) => request<PatientExplanation>(`/papers/${pmid}/patient-explanation`, { method:"POST" }),
  compare: (pmids: string[]) => request<Comparison>("/papers/compare", { method:"POST", body:JSON.stringify({pmids}) }),
  savePaper: (pmid: string, collection_id?: number) => request<SavedPaper>(`/library/papers/${pmid}`, { method:"POST", body:JSON.stringify({collection_id: collection_id ?? null}) }),
  unsavePaper: (pmid: string) => request<void>(`/library/papers/${pmid}`, { method:"DELETE" }),
  savedPapers: () => request<SavedPaper[]>("/library/papers"),
  collections: () => request<Collection[]>("/library/collections"),
  createCollection: (name: string, description?: string) => request<Collection>("/library/collections", { method:"POST", body:JSON.stringify({name,description}) }),
  history: () => request<SearchHistory[]>("/papers/history"),
  citation: (pmid: string) => request<Citation>(`/papers/${pmid}/citation`),
  workspaces: () => request<Workspace[]>("/workspaces"),
  createWorkspace: (name:string, research_question?:string) => request<Workspace>("/workspaces", {method:"POST", body:JSON.stringify({name,research_question})}),
  addToWorkspace: (workspaceId:number, pmid:string) => request<Workspace>(`/workspaces/${workspaceId}/papers/${pmid}`, {method:"POST"}),
  removeFromWorkspace: (workspaceId:number, pmid:string) => request<Workspace>(`/workspaces/${workspaceId}/papers/${pmid}`, {method:"DELETE"}),
  askWorkspace: (workspaceId:number, question:string) => request<WorkspaceAnswer>(`/workspaces/${workspaceId}/ask`, {method:"POST", body:JSON.stringify({question})}),
  literatureReview: (workspaceId:number) => request<LiteratureReview>(`/workspaces/${workspaceId}/literature-review`, {method:"POST"}),
  reports: (workspaceId:number) => request<ResearchReport[]>(`/workspaces/${workspaceId}/reports`),
  exportReportMarkdown: async (workspaceId:number, reportId:number) => {
    const token = getToken();
    const response = await fetch(`${API_BASE}/workspaces/${workspaceId}/reports/${reportId}/markdown`, {headers: token ? {Authorization:`Bearer ${token}`} : {}});
    if (!response.ok) { const body = await response.json().catch(()=>({})); throw new Error(body.detail ?? "Export failed"); }
    return response.text();
  },
};

export type Paper = { pmid:string; title:string; abstract:string|null; journal:string|null; publication_date:string|null; doi:string|null; authors:string[] };
export type Summary = { overview:string; research_question:string; study_characteristics:{study_type:string;setting:string;population:string;sample_size:string;intervention_or_exposure:string;comparator:string;outcomes:string[]}; study_design:string; population:string; key_findings:string[]; limitations:string[]; clinical_relevance:string; evidence_caveats:string[]; uncertainty:string };
export type PatientExplanation = { plain_language_summary:string; important_terms:string[]; what_the_study_does_not_show:string[]; uncertainty:string };
export type Comparison = { papers:string[]; research_questions:string; populations:string; study_design_comparison:string; interventions_or_exposures:string; outcomes:string; similarities:string[]; differences:string[]; findings_comparison:string; limitations_comparison:string; overall_takeaway:string; uncertainty:string };
export type Citation = { apa:string; mla:string; vancouver:string };
export type Collection = { id:number; name:string; description:string|null; created_at:string; paper_count:number };
export type SavedPaper = { id:number; collection_id:number|null; created_at:string; paper:Paper };
export type SearchHistory = { id:number; query:string; result_count:number; created_at:string };

export type WorkspacePaper = { pmid:string; title:string; journal:string|null; publication_date:string|null; abstract_available:boolean };
export type Workspace = { id:number; name:string; research_question:string|null; created_at:string; papers:WorkspacePaper[] };
export type WorkspaceAnswer = { answer:string; evidence_strength:string; uncertainty:string; sources:{pmid:string; title:string; supporting_excerpt:string}[]; insufficient_evidence:boolean };

export type StudySnapshot = { pmid:string; title:string; study_design:string; population:string; sample_size:string; intervention_or_exposure:string; comparator:string; outcomes:string[]; key_findings:string[]; limitations:string[] };
export type LiteratureReview = { title:string; research_question:string; scope:string; included_studies:StudySnapshot[]; synthesis:string; areas_of_agreement:string[]; areas_of_disagreement:string[]; evidence_gaps:string[]; limitations_of_review:string[]; conclusion:string; uncertainty:string; cited_pmids:string[] };

export type ResearchReport = { id:number; workspace_id:number; title:string; created_at:string; report:LiteratureReview };
