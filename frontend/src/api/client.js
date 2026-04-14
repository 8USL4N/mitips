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

export const getTreatments = () => api.get("/treatments");
export const updateTreatmentActions = (id, actions) =>
  api.put(`/treatments/${id}/actions`, { actions });

export const solveDiagnosis = (diagnosisId, patientValues) =>
  api.post("/solver/solve", { diagnosis_id: diagnosisId, patient_values: patientValues });

export const rankDiagnoses = (diagnosisId, patientValues) =>
  api.post("/solver/rank", { diagnosis_id: diagnosisId, patient_values: patientValues });

export default api;
