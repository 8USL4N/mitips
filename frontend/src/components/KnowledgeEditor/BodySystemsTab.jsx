import { useEffect, useMemo, useState } from "react";
import {
  createBodySystem,
  deleteBodySystem,
  getBodySystems,
  getCharacteristics,
  updateBodySystem
} from "../../api/client";

export default function BodySystemsTab() {
  const [systems, setSystems] = useState([]);
  const [characteristics, setCharacteristics] = useState([]);
  const [selectedId, setSelectedId] = useState("");
  const [form, setForm] = useState({ name: "", characteristic_ids: [] });
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

  function loadSystem(id) {
    setSelectedId(id);
    setMessage("");
    setError("");

    if (!id) {
      setForm({ name: "", characteristic_ids: [] });
      return;
    }

    const selected = systems.find((item) => String(item.id) === String(id));
    if (!selected) {
      setForm({ name: "", characteristic_ids: [] });
      return;
    }

    setForm({
      name: selected.name,
      characteristic_ids: selected.characteristic_ids || []
    });
  }

  function toggleCharacteristic(id) {
    const exists = form.characteristic_ids.includes(id);
    if (exists) {
      setForm({
        ...form,
        characteristic_ids: form.characteristic_ids.filter((item) => item !== id)
      });
      return;
    }
    setForm({
      ...form,
      characteristic_ids: [...form.characteristic_ids, id]
    });
  }

  function buildPayload() {
    return {
      name: form.name.trim(),
      characteristic_ids: form.characteristic_ids
    };
  }

  async function createNew() {
    try {
      const payload = buildPayload();
      const res = await createBodySystem(payload);
      await refresh();
      loadSystem(String(res.data.id));
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
      return;
    }

    try {
      await updateBodySystem(Number(selectedId), buildPayload());
      await refresh();
      loadSystem(selectedId);
      setMessage("Изменения сохранены");
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
      loadSystem("");
      setMessage("Система организма удалена");
      setError("");
    } catch (err) {
      setMessage("");
      setError(err.response?.data?.detail || "Ошибка при удалении системы организма");
    }
  }

  return (
    <div className="editor-grid">
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

      <label>
        Название системы организма
        <input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} />
      </label>

      <div>
        <p className="muted">Связанные характеристики</p>
        <div className="checkbox-grid">
          {characteristics.map((item) => (
            <label key={item.id} className="checkbox-row">
              <input
                type="checkbox"
                checked={form.characteristic_ids.includes(item.id)}
                onChange={() => toggleCharacteristic(item.id)}
              />
              <span>{item.name}</span>
            </label>
          ))}
        </div>
      </div>

      <div className="button-row">
        <button type="button" className="primary" onClick={saveExisting}>
          Сохранить выбранную
        </button>
        <button type="button" onClick={createNew}>
          Создать систему
        </button>
        <button type="button" className="danger" onClick={removeCurrent}>
          Удалить выбранную
        </button>
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
