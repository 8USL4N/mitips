import { useEffect, useMemo, useState } from "react";
import {
  createBodySystem,
  deleteBodySystem,
  getBodySystems,
  getCharacteristics,
  updateBodySystem
} from "../../api/client";
import EditorModeSwitch from "./EditorModeSwitch";

const EMPTY_FORM = { name: "", characteristic_ids: [] };

function toForm(system) {
  return {
    name: system?.name || "",
    characteristic_ids: system?.characteristic_ids || []
  };
}

export default function BodySystemsTab() {
  const [mode, setMode] = useState("create");
  const [systems, setSystems] = useState([]);
  const [characteristics, setCharacteristics] = useState([]);
  const [selectedId, setSelectedId] = useState("");
  const [form, setForm] = useState(EMPTY_FORM);
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
    const [systemsRes, characteristicsRes] = await Promise.all([getBodySystems(), getCharacteristics()]);
    setSystems(systemsRes.data);
    setCharacteristics(characteristicsRes.data);
  }

  useEffect(() => {
    refresh().catch(() => setError("Не удалось загрузить системы организма"));
  }, []);

  function onModeChange(nextMode) {
    setMode(nextMode);
    setMessage("");
    setError("");
    if (nextMode === "create") {
      setSelectedId("");
      setForm(EMPTY_FORM);
    }
  }

  function loadSystem(id) {
    setSelectedId(id);
    setMessage("");
    setError("");
    if (!id) {
      setForm(EMPTY_FORM);
      return;
    }
    const selected = systems.find((item) => String(item.id) === String(id));
    if (!selected) {
      setForm(EMPTY_FORM);
      return;
    }
    setForm(toForm(selected));
  }

  function toggleCharacteristic(id) {
    const exists = form.characteristic_ids.includes(id);
    setForm((prev) => ({
      ...prev,
      characteristic_ids: exists
        ? prev.characteristic_ids.filter((item) => item !== id)
        : [...prev.characteristic_ids, id]
    }));
  }

  function buildPayload() {
    return {
      name: form.name.trim(),
      characteristic_ids: form.characteristic_ids
    };
  }

  async function createNew() {
    try {
      const res = await createBodySystem(buildPayload());
      const created = res.data;
      await refresh();
      setMode("edit");
      setSelectedId(String(created.id));
      setForm(toForm(created));
      setMessage("Система организма добавлена");
      setError("");
    } catch (err) {
      setMessage("");
      setError(err.response?.data?.detail || "Ошибка при создании системы организма");
    }
  }

  async function saveExisting() {
    if (!selectedId) {
      setError("Выберите систему организма");
      setMessage("");
      return;
    }
    try {
      const res = await updateBodySystem(Number(selectedId), buildPayload());
      const updated = res.data;
      await refresh();
      setSelectedId(String(updated.id));
      setForm(toForm(updated));
      setMessage("Система организма обновлена");
      setError("");
    } catch (err) {
      setMessage("");
      setError(err.response?.data?.detail || "Ошибка при сохранении системы организма");
    }
  }

  async function removeCurrent() {
    if (!selectedId) {
      setError("Сначала выберите систему организма");
      return;
    }
    try {
      await deleteBodySystem(Number(selectedId));
      await refresh();
      setSelectedId("");
      setForm(EMPTY_FORM);
      setMessage("Система организма удалена");
      setError("");
    } catch (err) {
      setMessage("");
      setError(err.response?.data?.detail || "Ошибка при удалении системы организма");
    }
  }

  const formLocked = mode === "edit" && !selectedId;

  return (
    <div className="editor-grid">
      <EditorModeSwitch mode={mode} onModeChange={onModeChange} entityName="систему" />

      {mode === "edit" && (
        <label>
          Список систем организма
          <select value={selectedId} onChange={(e) => loadSystem(e.target.value)}>
            <option value="">-- выберите --</option>
            {systems.map((item) => (
              <option key={item.id} value={item.id}>
                {item.name}
              </option>
            ))}
          </select>
        </label>
      )}

      {formLocked && <div className="alert">Выберите систему для редактирования.</div>}

      <label>
        Название системы организма
        <input
          disabled={formLocked}
          value={form.name}
          onChange={(e) => setForm({ ...form, name: e.target.value })}
        />
      </label>

      <div>
        <p className="muted">Связанные характеристики</p>
        <div className="checkbox-grid">
          {characteristics.map((item) => (
            <label key={item.id} className="checkbox-row">
              <input
                type="checkbox"
                disabled={formLocked}
                checked={form.characteristic_ids.includes(item.id)}
                onChange={() => toggleCharacteristic(item.id)}
              />
              <span>{item.name}</span>
            </label>
          ))}
        </div>
      </div>

      <div className="button-row">
        {mode === "create" && (
          <button type="button" onClick={createNew}>
            Создать систему
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

      <table>
        <thead>
          <tr>
            <th>Система</th>
            <th>Характеристики</th>
          </tr>
        </thead>
        <tbody>
          {systems.map((item) => (
            <tr key={item.id}>
              <td>{item.name}</td>
              <td>
                {(item.characteristic_ids || [])
                  .map((id) => characteristicById[id]?.name)
                  .filter(Boolean)
                  .join(", ")}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
