import axios from "axios";

const api = axios.create({
  baseURL: "/api",
  headers: {
    "Content-Type": "application/json"
  }
});

export const getDiagnoses = () => api.get("/diagnoses");
export const getDiagnosisById = (id) => api.get(`/diagnoses/${id}`);
export const createDiagnosis = (payload) => api.post("/diagnoses", payload);
export const updateDiagnosis = (id, payload) => api.put(`/diagnoses/${id}`, payload);
export const deleteDiagnosis = (id) => api.delete(`/diagnoses/${id}`);

export const getCharacteristics = () => api.get("/characteristics");

export const getBodySystems = () => api.get("/body-systems");
export const createBodySystem = (payload) => api.post("/body-systems", payload);
export const updateBodySystem = (id, payload) => api.put(`/body-systems/${id}`, payload);
export const deleteBodySystem = (id) => api.delete(`/body-systems/${id}`);

export const getTreatments = () => api.get("/treatments");
export const updateTreatmentActions = (id, actions) =>
  api.put(`/treatments/${id}/actions`, { actions });

export const solveDiagnosis = (diagnosisId, patientValues) =>
  api.post("/solver/solve", { diagnosis_id: diagnosisId, patient_values: patientValues });

export const determineDiagnosis = (patientValues) =>
  api.post("/solver/determine", { patient_values: patientValues });

export default api;
