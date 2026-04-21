import { useEffect, useState } from "react";
import {
  createTreatment,
  deleteTreatment,
  getTreatmentById,
  getTreatments,
  updateTreatment
} from "../../api/client";
import EditorModeSwitch from "./EditorModeSwitch";

function emptyForm() {
  return { name: "", actions: [] };
}

export default function TreatmentsTab() {
  const [mode, setMode] = useState("create");
  const [treatments, setTreatments] = useState([]);
  const [selectedId, setSelectedId] = useState("");
  const [form, setForm] = useState(emptyForm());
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

  function onModeChange(nextMode) {
    setMode(nextMode);
    setSelectedId("");
    setForm(emptyForm());
    setNewAction("");
    setMessage("");
    setError("");
  }

  async function loadTreatment(id) {
    setSelectedId(id);
    setMessage("");
    setError("");
    if (!id) {
      setForm(emptyForm());
      return;
    }
    try {
      const response = await getTreatmentById(id);
      setForm({ name: response.data.name, actions: response.data.actions || [] });
    } catch (err) {
      setError(err.response?.data?.detail || "Не удалось загрузить лечение");
    }
  }

  function moveAction(index, direction) {
    const target = index + direction;
    if (target < 0 || target >= form.actions.length) {
      return;
    }
    const copy = [...form.actions];
    const [item] = copy.splice(index, 1);
    copy.splice(target, 0, item);
    setForm((prev) => ({ ...prev, actions: copy }));
  }

  function addAction() {
    if (!newAction.trim()) {
      return;
    }
    setForm((prev) => ({ ...prev, actions: [...prev.actions, newAction.trim()] }));
    setNewAction("");
  }

  async function createNew() {
    try {
      const created = await createTreatment({
        name: form.name.trim(),
        actions: form.actions
      });
      await refresh();
      setMode("edit");
      await loadTreatment(String(created.data.id));
      setMessage("Лечение создано");
      setError("");
    } catch (err) {
      setError(err.response?.data?.detail || "Ошибка создания лечения");
      setMessage("");
    }
  }

  async function saveExisting() {
    if (!selectedId) {
      setError("Выберите лечение");
      return;
    }
    try {
      await updateTreatment(Number(selectedId), {
        name: form.name.trim(),
        actions: form.actions
      });
      await refresh();
      await loadTreatment(selectedId);
      setMessage("Лечение обновлено");
      setError("");
    } catch (err) {
      setError(err.response?.data?.detail || "Ошибка сохранения");
      setMessage("");
    }
  }

  async function removeCurrent() {
    if (!selectedId) {
      setError("Выберите лечение");
      return;
    }
    try {
      await deleteTreatment(Number(selectedId));
      await refresh();
      setSelectedId("");
      setForm(emptyForm());
      setMessage("Лечение удалено");
      setError("");
    } catch (err) {
      setError(err.response?.data?.detail || "Ошибка удаления");
      setMessage("");
    }
  }

  const formLocked = mode === "edit" && !selectedId;

  return (
    <div className="editor-grid">
      <EditorModeSwitch mode={mode} onModeChange={onModeChange} entityName="лечение" />

      {mode === "edit" && (
        <label>
          Лечение
          <select value={selectedId} onChange={(e) => loadTreatment(e.target.value)}>
            <option value="">-- выберите --</option>
            {treatments.map((item) => (
              <option key={item.id} value={item.id}>
                {item.name}
              </option>
            ))}
          </select>
        </label>
      )}

      {formLocked && <div className="alert">Выберите лечение для редактирования.</div>}

      <label>
        Название лечения
        <input
          disabled={formLocked}
          value={form.name}
          onChange={(e) => setForm((prev) => ({ ...prev, name: e.target.value }))}
        />
      </label>

      <div>
        <p className="muted">Шаги лечения</p>
        <ul className="steps">
          {form.actions.map((action, index) => (
            <li key={`${action}-${index}`}>
              <span>{action}</span>
              <div className="inline-buttons">
                <button type="button" disabled={formLocked} onClick={() => moveAction(index, -1)}>
                  ↑
                </button>
                <button type="button" disabled={formLocked} onClick={() => moveAction(index, 1)}>
                  ↓
                </button>
                <button
                  type="button"
                  className="danger"
                  disabled={formLocked}
                  onClick={() =>
                    setForm((prev) => ({
                      ...prev,
                      actions: prev.actions.filter((_, i) => i !== index)
                    }))
                  }
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
          disabled={formLocked}
          value={newAction}
          onChange={(e) => setNewAction(e.target.value)}
          placeholder="Новый шаг лечения"
        />
        <button type="button" disabled={formLocked} onClick={addAction}>
          Добавить шаг
        </button>
      </div>

      <div className="button-row">
        {mode === "create" && (
          <button type="button" onClick={createNew}>
            Создать лечение
          </button>
        )}
        {mode === "edit" && (
          <>
            <button type="button" className="primary" onClick={saveExisting} disabled={formLocked}>
              Сохранить изменения
            </button>
            <button type="button" className="danger" onClick={removeCurrent} disabled={formLocked}>
              Удалить лечение
            </button>
          </>
        )}
      </div>

      {message && <div className="alert ok">{message}</div>}
      {error && <div className="alert error">{error}</div>}
    </div>
  );
}
