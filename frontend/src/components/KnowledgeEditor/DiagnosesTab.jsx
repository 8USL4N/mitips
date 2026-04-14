import { useEffect, useMemo, useState } from "react";
import {
  addDiagnosis,
  deleteDiagnosis,
  getDiagnoses,
  getTreatments,
  updateDiagnosis
} from "../../api/client";

function prettyJson(value) {
  return JSON.stringify(value, null, 2);
}

export default function DiagnosesTab() {
  const [diagnoses, setDiagnoses] = useState({});
  const [treatments, setTreatments] = useState({});
  const [selected, setSelected] = useState("");
  const [newName, setNewName] = useState("");
  const [form, setForm] = useState({ icd10: "", treatment: "", characteristicsJson: "{}" });
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  async function refresh() {
    const [diagnosesRes, treatmentsRes] = await Promise.all([getDiagnoses(), getTreatments()]);
    setDiagnoses(diagnosesRes.data);
    setTreatments(treatmentsRes.data);
  }

  useEffect(() => {
    refresh().catch(() => setError("Не удалось загрузить диагнозы"));
  }, []);

  const treatmentNames = useMemo(() => Object.keys(treatments), [treatments]);

  function loadDiagnosis(name) {
    setSelected(name);
    setMessage("");
    setError("");

    if (!name) {
      setForm({ icd10: "", treatment: "", characteristicsJson: "{}" });
      return;
    }

    const item = diagnoses[name];
    setForm({
      icd10: item.icd10 || "",
      treatment: item.treatment || "",
      characteristicsJson: prettyJson(item.characteristics || {})
    });
  }

  async function saveExisting() {
    if (!selected) {
      setError("Выберите диагноз для сохранения");
      return;
    }

    try {
      const payload = {
        icd10: form.icd10 || null,
        treatment: form.treatment,
        characteristics: JSON.parse(form.characteristicsJson || "{}")
      };

      await updateDiagnosis(selected, payload);
      await refresh();
      setMessage("Изменения сохранены");
      setError("");
    } catch (err) {
      setError(err.response?.data?.detail || "Ошибка при сохранении");
      setMessage("");
    }
  }

  async function createNew() {
    if (!newName.trim()) {
      setError("Введите название нового диагноза");
      return;
    }

    try {
      const payload = {
        icd10: form.icd10 || null,
        treatment: form.treatment,
        characteristics: JSON.parse(form.characteristicsJson || "{}")
      };

      await addDiagnosis(newName.trim(), payload);
      await refresh();
      loadDiagnosis(newName.trim());
      setNewName("");
      setMessage("Диагноз добавлен");
      setError("");
    } catch (err) {
      setError(err.response?.data?.detail || "Ошибка при добавлении");
      setMessage("");
    }
  }

  async function removeCurrent() {
    if (!selected) {
      setError("Сначала выберите диагноз");
      return;
    }

    try {
      await deleteDiagnosis(selected);
      await refresh();
      loadDiagnosis("");
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
        <select value={selected} onChange={(e) => loadDiagnosis(e.target.value)}>
          <option value="">-- выберите --</option>
          {Object.keys(diagnoses).map((name) => (
            <option key={name} value={name}>
              {name}
            </option>
          ))}
        </select>
      </label>

      <label>
        Новый диагноз
        <input value={newName} onChange={(e) => setNewName(e.target.value)} placeholder="Название" />
      </label>

      <label>
        Код МКБ-10
        <input value={form.icd10} onChange={(e) => setForm({ ...form, icd10: e.target.value })} />
      </label>

      <label>
        Лечение
        <select
          value={form.treatment}
          onChange={(e) => setForm({ ...form, treatment: e.target.value })}
        >
          <option value="">-- выберите --</option>
          {treatmentNames.map((name) => (
            <option key={name} value={name}>
              {name}
            </option>
          ))}
        </select>
      </label>

      <label>
        Характеристики (JSON)
        <textarea
          rows={9}
          value={form.characteristicsJson}
          onChange={(e) => setForm({ ...form, characteristicsJson: e.target.value })}
        />
      </label>

      <div className="button-row">
        <button type="button" className="primary" onClick={saveExisting}>
          Сохранить выбранный
        </button>
        <button type="button" onClick={createNew}>
          Добавить новый
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
