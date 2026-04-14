import { useEffect, useMemo, useState } from "react";
import { getTreatments, updateTreatmentActions } from "../../api/client";

export default function TreatmentsTab() {
  const [treatments, setTreatments] = useState([]);
  const [selectedId, setSelectedId] = useState("");
  const [actions, setActions] = useState([]);
  const [newAction, setNewAction] = useState("");
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  async function refresh() {
    const response = await getTreatments();
    setTreatments(response.data);
  }

  useEffect(() => {
    refresh().catch(() => setError("Не удалось загрузить лечения"));
  }, []);

  const selectedTreatment = useMemo(
    () => treatments.find((item) => String(item.id) == String(selectedId)),
    [treatments, selectedId]
  );

  function onSelect(id) {
    setSelectedId(id);
    const treatment = treatments.find((item) => String(item.id) === String(id));
    setActions(treatment?.actions || []);
    setMessage("");
    setError("");
  }

  function moveAction(index, direction) {
    const target = index + direction;
    if (target < 0 || target >= actions.length) {
      return;
    }

    const copy = [...actions];
    const [item] = copy.splice(index, 1);
    copy.splice(target, 0, item);
    setActions(copy);
  }

  async function save() {
    if (!selectedId) {
      setError("Выберите лечение");
      return;
    }

    try {
      await updateTreatmentActions(Number(selectedId), actions);
      await refresh();
      setMessage("Лечение обновлено");
      setError("");
    } catch (err) {
      setError(err.response?.data?.detail || "Ошибка сохранения");
      setMessage("");
    }
  }

  return (
    <div className="editor-grid">
      <label>
        Лечение
        <select value={selectedId} onChange={(e) => onSelect(e.target.value)}>
          <option value="">-- выберите --</option>
          {treatments.map((item) => (
            <option key={item.id} value={item.id}>
              {item.name}
            </option>
          ))}
        </select>
      </label>

      {selectedTreatment && <div className="muted">Выбрано: {selectedTreatment.name}</div>}

      <div>
        <p className="muted">Шаги лечения</p>
        <ul className="steps">
          {actions.map((action, index) => (
            <li key={`${action}-${index}`}>
              <span>{action}</span>
              <div className="inline-buttons">
                <button type="button" onClick={() => moveAction(index, -1)}>
                  ↑
                </button>
                <button type="button" onClick={() => moveAction(index, 1)}>
                  ↓
                </button>
                <button
                  type="button"
                  className="danger"
                  onClick={() => setActions(actions.filter((_, i) => i !== index))}
                >
                  удалить
                </button>
              </div>
            </li>
          ))}
        </ul>
      </div>

      <div className="inline-form">
        <input
          value={newAction}
          onChange={(e) => setNewAction(e.target.value)}
          placeholder="Новый шаг лечения"
        />
        <button
          type="button"
          onClick={() => {
            if (!newAction.trim()) {
              return;
            }
            setActions([...actions, newAction.trim()]);
            setNewAction("");
          }}
        >
          Добавить
        </button>
      </div>

      <button type="button" className="primary" onClick={save}>
        Сохранить лечение
      </button>

      {message && <div className="alert ok">{message}</div>}
      {error && <div className="alert error">{error}</div>}
    </div>
  );
}
