import { useEffect, useMemo, useState } from "react";
import {
  createDiagnosis,
  deleteDiagnosis,
  getDiagnosisById,
  getDiagnoses,
  getCharacteristics,
  updateDiagnosis
} from "../../api/client";
import EditorModeSwitch from "./EditorModeSwitch";

function emptyForm() {
  return {
    name: "",
    icd10: "",
    criteria: []
  };
}

function criteriaFromDetail(criteria) {
  return (criteria || []).map((item) => ({
    characteristic_id: String(item.characteristic_id),
    expected_enum_key: item.expected_enum_key ?? "",
    expected_min: item.expected_min ?? "",
    expected_max: item.expected_max ?? ""
  }));
}

function parseRequiredNumber(value, fieldName) {
  if (value === "" || value === null || value === undefined) {
    throw new Error(`${fieldName} обязательно`);
  }

  const parsed = Number(value);
  if (!Number.isFinite(parsed)) {
    throw new Error(`${fieldName} должно быть числом`);
  }

  return parsed;
}

function validateDiagnosisForm(form, characteristicById) {
  if (!form.name.trim()) {
    return "Название диагноза обязательно";
  }
  for (const item of form.criteria) {
    if (!item.characteristic_id) {
      continue;
    }

    const characteristic = characteristicById[Number(item.characteristic_id)];
    if (!characteristic) {
      continue;
    }

    if (characteristic.type === "range") {
      let expectedMin;
      let expectedMax;
      try {
        expectedMin = parseRequiredNumber(item.expected_min, `${characteristic.name}: expected_min`);
        expectedMax = parseRequiredNumber(item.expected_max, `${characteristic.name}: expected_max`);
      } catch (err) {
        return err.message;
      }

      if (expectedMin > expectedMax) {
        return `${characteristic.name}: expected_min не может быть больше expected_max`;
      }

      if (!Array.isArray(characteristic.allowed) || characteristic.allowed.length !== 2) {
        return `${characteristic.name}: некорректно настроен допустимый диапазон`;
      }

      const allowedMin = Number(characteristic.allowed[0]);
      const allowedMax = Number(characteristic.allowed[1]);
      if (!Number.isFinite(allowedMin) || !Number.isFinite(allowedMax)) {
        return `${characteristic.name}: некорректно настроен допустимый диапазон`;
      }

      if (expectedMin < allowedMin || expectedMax > allowedMax) {
        return `${characteristic.name}: ожидаемый диапазон должен быть внутри ${allowedMin}-${allowedMax}`;
      }
    } else if (!item.expected_enum_key) {
      return `${characteristic.name}: expected_enum_key обязателен`;
    }
  }

  return "";
}

function buildPayload(form, characteristicById) {
  const criteria = form.criteria
    .filter((item) => item.characteristic_id)
    .map((item) => {
      const characteristic = characteristicById[Number(item.characteristic_id)];
      if (!characteristic) {
        return null;
      }
      if (characteristic.type === "range") {
        return {
          characteristic_id: Number(item.characteristic_id),
          expected_enum_key: null,
          expected_min: parseRequiredNumber(item.expected_min, "expected_min"),
          expected_max: parseRequiredNumber(item.expected_max, "expected_max")
        };
      }
      return {
        characteristic_id: Number(item.characteristic_id),
        expected_enum_key: item.expected_enum_key || null,
        expected_min: null,
        expected_max: null
      };
    })
    .filter(Boolean);

  return {
    name: form.name.trim(),
    icd10: form.icd10.trim() ? form.icd10.trim() : null,
    criteria
  };
}

export default function DiagnosesTab() {
  const [mode, setMode] = useState("create");
  const [diagnoses, setDiagnoses] = useState([]);
  const [characteristics, setCharacteristics] = useState([]);
  const [selectedId, setSelectedId] = useState("");
  const [form, setForm] = useState(emptyForm());
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  const characteristicById = useMemo(() => {
    const map = {};
    for (const item of characteristics) {
      map[item.id] = item;
    }
    return map;
  }, [characteristics]);

  async function refresh() {
    const [diagnosesRes, characteristicsRes] = await Promise.all([
      getDiagnoses(),
      getCharacteristics()
    ]);
    setDiagnoses(diagnosesRes.data);
    setCharacteristics(characteristicsRes.data);
  }

  useEffect(() => {
    refresh().catch(() => setError("Не удалось загрузить данные"));
  }, []);

  function onModeChange(nextMode) {
    setMode(nextMode);
    setSelectedId("");
    setForm(emptyForm());
    setMessage("");
    setError("");
  }

  async function loadDiagnosis(id) {
    setSelectedId(id);
    setMessage("");
    setError("");
    if (!id) {
      setForm(emptyForm());
      return;
    }
    try {
      const res = await getDiagnosisById(id);
      const item = res.data;
      setForm({
        name: item.name,
        icd10: item.icd10 || "",
        criteria: criteriaFromDetail(item.criteria)
      });
    } catch (err) {
      setError(err.response?.data?.detail || "Не удалось загрузить диагноз");
    }
  }

  function addCriterion() {
    setForm((prev) => ({
      ...prev,
      criteria: [
        ...prev.criteria,
        {
          characteristic_id: "",
          expected_enum_key: "",
          expected_min: "",
          expected_max: ""
        }
      ]
    }));
  }

  function updateCriterion(index, patch) {
    setForm((prev) => {
      const criteria = [...prev.criteria];
      criteria[index] = { ...criteria[index], ...patch };
      return { ...prev, criteria };
    });
  }

  async function createNew() {
    const validationError = validateDiagnosisForm(form, characteristicById);
    if (validationError) {
      setError(validationError);
      setMessage("");
      return;
    }

    try {
      const payload = buildPayload(form, characteristicById);
      const res = await createDiagnosis(payload);
      await refresh();
      setMode("edit");
      await loadDiagnosis(String(res.data.id));
      setMessage("Диагноз добавлен");
      setError("");
    } catch (err) {
      setError(err.response?.data?.detail || "Ошибка при добавлении");
      setMessage("");
    }
  }

  async function saveExisting() {
    if (!selectedId) {
      setError("Выберите диагноз для сохранения");
      return;
    }

    const validationError = validateDiagnosisForm(form, characteristicById);
    if (validationError) {
      setError(validationError);
      setMessage("");
      return;
    }
    try {
      const payload = buildPayload(form, characteristicById);
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

  async function removeCurrent() {
    if (!selectedId) {
      setError("Сначала выберите диагноз");
      return;
    }
    try {
      await deleteDiagnosis(Number(selectedId));
      await refresh();
      setSelectedId("");
      setForm(emptyForm());
      setMessage("Диагноз удалён");
      setError("");
    } catch (err) {
      setError(err.response?.data?.detail || "Ошибка при удалении");
      setMessage("");
    }
  }

  const formLocked = mode === "edit" && !selectedId;

  return (
    <div className="editor-grid">
      <EditorModeSwitch mode={mode} onModeChange={onModeChange} entityName="диагноз" />

      {mode === "edit" && (
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
      )}

      {formLocked && <div className="alert">Выберите диагноз для редактирования.</div>}

      <label>
        Название диагноза
        <input
          disabled={formLocked}
          value={form.name}
          onChange={(e) => setForm((prev) => ({ ...prev, name: e.target.value }))}
        />
      </label>

      <label>
        Код МКБ-10
        <input
          disabled={formLocked}
          value={form.icd10}
          onChange={(e) => setForm((prev) => ({ ...prev, icd10: e.target.value }))}
        />
      </label>

      <div className="alert">
        Лечение назначается во вкладке «Лечения»: сначала создайте или откройте лечение, затем выберите для него диагноз.
      </div>

      <div>
        <p className="muted">Критерии диагноза</p>
        <div className="editor-grid">
          {form.criteria.map((criterion, index) => {
            const characteristic = characteristicById[Number(criterion.characteristic_id)];
            return (
              <div key={`${criterion.characteristic_id}-${index}`} className="criterion-card">
                <label>
                  Характеристика
                  <select
                    disabled={formLocked}
                    value={criterion.characteristic_id}
                    onChange={(e) =>
                      updateCriterion(index, {
                        characteristic_id: e.target.value,
                        expected_enum_key: "",
                        expected_min: "",
                        expected_max: ""
                      })
                    }
                  >
                    <option value="">-- выберите --</option>
                    {characteristics.map((item) => (
                      <option key={item.id} value={item.id}>
                        {item.name}
                      </option>
                    ))}
                  </select>
                </label>

                {characteristic?.type === "range" && (
                  <div className="inline-form">
                    <input
                      disabled={formLocked}
                      type="number"
                      min={characteristic.allowed?.[0]}
                      max={characteristic.allowed?.[1]}
                      placeholder="expected min"
                      value={criterion.expected_min}
                      onChange={(e) => updateCriterion(index, { expected_min: e.target.value })}
                    />
                    <input
                      disabled={formLocked}
                      type="number"
                      min={characteristic.allowed?.[0]}
                      max={characteristic.allowed?.[1]}
                      placeholder="expected max"
                      value={criterion.expected_max}
                      onChange={(e) => updateCriterion(index, { expected_max: e.target.value })}
                    />
                  </div>
                )}

                {characteristic?.type === "enum" && (
                  <label>
                    expected enum key
                    <select
                      disabled={formLocked}
                      value={criterion.expected_enum_key}
                      onChange={(e) => updateCriterion(index, { expected_enum_key: e.target.value })}
                    >
                      <option value="">-- выберите --</option>
                      {Object.entries(characteristic.allowed || {}).map(([key, value]) => (
                        <option key={key} value={key}>
                          {key} - {value}
                        </option>
                      ))}
                    </select>
                  </label>
                )}

                <button
                  type="button"
                  className="danger"
                  disabled={formLocked}
                  onClick={() =>
                    setForm((prev) => ({
                      ...prev,
                      criteria: prev.criteria.filter((_, i) => i !== index)
                    }))
                  }
                >
                  Удалить критерий
                </button>
              </div>
            );
          })}
        </div>
        <button type="button" disabled={formLocked} onClick={addCriterion}>
          Добавить критерий
        </button>
      </div>

      <div className="button-row">
        {mode === "create" && (
          <button type="button" onClick={createNew}>
            Создать диагноз
          </button>
        )}
        {mode === "edit" && (
          <>
            <button type="button" className="primary" onClick={saveExisting} disabled={formLocked}>
              Сохранить изменения
            </button>
            <button type="button" className="danger" onClick={removeCurrent} disabled={formLocked}>
              Удалить
            </button>
          </>
        )}
      </div>

      {message && <div className="alert ok">{message}</div>}
      {error && <div className="alert error">{error}</div>}
    </div>
  );
}
