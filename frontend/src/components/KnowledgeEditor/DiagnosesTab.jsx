import { useEffect, useState } from "react";
import {
  createDiagnosis,
  deleteDiagnosis,
  getCharacteristics,
  getDiagnosisById,
  getDiagnoses,
  getTreatments,
  updateDiagnosis
} from "../../api/client";

function prettyJson(value) {
  return JSON.stringify(value, null, 2);
}

function criteriaForEdit(criteria) {
  return criteria.map((item) => ({
    characteristic_id: item.characteristic_id,
    expected_enum_key: item.expected_enum_key,
    expected_min: item.expected_min,
    expected_max: item.expected_max
  }));
}

function normalizeCriteria(raw) {
  return raw.map((item) => ({
    characteristic_id: Number(item.characteristic_id),
    expected_enum_key: item.expected_enum_key ?? null,
    expected_min: item.expected_min === null || item.expected_min === undefined || item.expected_min === "" ? null : Number(item.expected_min),
    expected_max: item.expected_max === null || item.expected_max === undefined || item.expected_max === "" ? null : Number(item.expected_max)
  }));
}

export default function DiagnosesTab() {
  const [diagnoses, setDiagnoses] = useState([]);
  const [treatments, setTreatments] = useState([]);
  const [characteristics, setCharacteristics] = useState([]);
  const [selectedId, setSelectedId] = useState("");
  const [form, setForm] = useState({
    name: "",
    icd10: "",
    treatment_id: "",
    criteriaJson: "[]"
  });
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  async function refresh() {
    const [diagnosesRes, treatmentsRes, characteristicsRes] = await Promise.all([
      getDiagnoses(),
      getTreatments(),
      getCharacteristics()
    ]);
    setDiagnoses(diagnosesRes.data);
    setTreatments(treatmentsRes.data);
    setCharacteristics(characteristicsRes.data);
  }

  useEffect(() => {
    refresh().catch(() => setError("Не удалось загрузить данные"));
  }, []);

  async function loadDiagnosis(id) {
    setSelectedId(id);
    setMessage("");
    setError("");

    if (!id) {
      setForm({ name: "", icd10: "", treatment_id: "", criteriaJson: "[]" });
      return;
    }

    try {
      const res = await getDiagnosisById(id);
      const item = res.data;
      setForm({
        name: item.name,
        icd10: item.icd10 || "",
        treatment_id: String(item.treatment_id),
        criteriaJson: prettyJson(criteriaForEdit(item.criteria || []))
      });
    } catch (err) {
      setError(err.response?.data?.detail || "Не удалось загрузить диагноз");
    }
  }

  function buildPayload() {
    const criteria = normalizeCriteria(JSON.parse(form.criteriaJson || "[]"));
    return {
      name: form.name.trim(),
      icd10: form.icd10.trim() ? form.icd10.trim() : null,
      treatment_id: Number(form.treatment_id),
      criteria
    };
  }

  async function saveExisting() {
    if (!selectedId) {
      setError("Выберите диагноз для сохранения");
      return;
    }

    try {
      const payload = buildPayload();
      await updateDiagnosis(Number(selectedId), payload);
      await refresh();
      await loadDiagnosis(selectedId);
      setMessage("Изменения сохранены");
      setError("");
    } catch (err) {
      setError(err.response?.data?.detail || "Ошибка при сохранении");
      setMessage("");
    }
  }

  async function createNew() {
    try {
      const payload = buildPayload();
      const res = await createDiagnosis(payload);
      await refresh();
      await loadDiagnosis(String(res.data.id));
      setMessage("Диагноз добавлен");
      setError("");
    } catch (err) {
      setError(err.response?.data?.detail || "Ошибка при добавлении");
      setMessage("");
    }
  }

  async function removeCurrent() {
    if (!selectedId) {
      setError("Сначала выберите диагноз");
      return;
    }

    try {
      await deleteDiagnosis(Number(selectedId));
      await refresh();
      await loadDiagnosis("");
      setMessage("Диагноз удалён");
      setError("");
    } catch (err) {
      setError(err.response?.data?.detail || "Ошибка при удалении");
      setMessage("");
    }
  }

  return (
    <div className="editor-grid">
      <label>
        Список диагнозов
        <select value={selectedId} onChange={(e) => loadDiagnosis(e.target.value)}>
          <option value="">-- выберите --</option>
          {diagnoses.map((item) => (
            <option key={item.id} value={item.id}>
              {item.name}
            </option>
          ))}
        </select>
      </label>

      <label>
        Название диагноза
        <input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} />
      </label>

      <label>
        Код МКБ-10
        <input value={form.icd10} onChange={(e) => setForm({ ...form, icd10: e.target.value })} />
      </label>

      <label>
        Лечение
        <select
          value={form.treatment_id}
          onChange={(e) => setForm({ ...form, treatment_id: e.target.value })}
        >
          <option value="">-- выберите --</option>
          {treatments.map((item) => (
            <option key={item.id} value={item.id}>
              {item.name}
            </option>
          ))}
        </select>
      </label>

      <label>
        Критерии (JSON)
        <textarea
          rows={10}
          value={form.criteriaJson}
          onChange={(e) => setForm({ ...form, criteriaJson: e.target.value })}
        />
      </label>

      <div className="alert">
        Характеристики для criteria:
        <br />
        {characteristics.map((item) => `${item.id}: ${item.name}`).join(" | ")}
      </div>

      <div className="button-row">
        <button type="button" className="primary" onClick={saveExisting}>
          Сохранить выбранный
        </button>
        <button type="button" onClick={createNew}>
          Создать диагноз
        </button>
        <button type="button" className="danger" onClick={removeCurrent}>
          Удалить выбранный
        </button>
      </div>

      {message && <div className="alert ok">{message}</div>}
      {error && <div className="alert error">{error}</div>}
    </div>
  );
}
