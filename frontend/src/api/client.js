import axios from "axios";

const api = axios.create({
  baseURL: "/api",
  headers: {
    "Content-Type": "application/json"
  }
});

export const getKnowledgeBase = () => api.get("/knowledge/");
export const getDiagnoses = () => api.get("/knowledge/diagnoses");
export const getCharacteristics = () => api.get("/knowledge/characteristics");
export const getTreatments = () => api.get("/knowledge/treatments");

export const solveDiagnosis = (diagnosis, patientValues) =>
  api.post("/solver/solve", { diagnosis, patient_values: patientValues });

export const rankDiagnoses = (patientValues) =>
  api.post("/solver/rank", { diagnosis: "", patient_values: patientValues });

export const addDiagnosis = (name, payload) =>
  api.post(`/knowledge/diagnoses/${encodeURIComponent(name)}`, payload);

export const updateDiagnosis = (name, payload) =>
  api.put(`/knowledge/diagnoses/${encodeURIComponent(name)}`, payload);

export const deleteDiagnosis = (name) =>
  api.delete(`/knowledge/diagnoses/${encodeURIComponent(name)}`);

export const updateTreatment = (name, actions) =>
  api.put(`/knowledge/treatments/${encodeURIComponent(name)}`, { actions });

export default api;
