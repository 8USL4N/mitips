import { useEffect, useState } from "react";
import {
  createCharacteristic,
  deleteCharacteristic,
  getCharacteristicById,
  getCharacteristicUsage,
  getCharacteristics,
  updateCharacteristic
} from "../../api/client";
import EditorModeSwitch from "./EditorModeSwitch";

const EMPTY_RANGE = { allowedMin: "", allowedMax: "", normalMin: "", normalMax: "" };
const EMPTY_ENUM = { options: [{ key: "0", value: "" }], normal: "0" };

function formFromCharacteristic(item) {
  if (item.type === "range") {
    return {
      name: item.name,
      type: "range",
      unit: item.unit || "",
      range: {
        allowedMin: String(item.allowed?.[0] ?? ""),
        allowedMax: String(item.allowed?.[1] ?? ""),
        normalMin: String(item.normal?.[0] ?? ""),
        normalMax: String(item.normal?.[1] ?? "")
      },
      enumState: { options: [{ key: "0", value: "" }], normal: "0" }
    };
  }

  const options = Object.entries(item.allowed || {}).map(([key, value]) => ({ key, value }));
  return {
    name: item.name,
    type: "enum",
    unit: item.unit || "",
    range: EMPTY_RANGE,
    enumState: {
      options: options.length ? options : [{ key: "0", value: "" }],
      normal: String(item.normal ?? "")
    }
  };
}

function emptyForm() {
  return {
    name: "",
    type: "range",
    unit: "",
    range: { ...EMPTY_RANGE },
    enumState: {
      ...EMPTY_ENUM,
      options: EMPTY_ENUM.options.map((item) => ({ ...item }))
    }
  };
}

function buildPayload(form) {
  if (form.type === "range") {
    return {
      name: form.name.trim(),
      type: "range",
      unit: form.unit.trim(),
      allowed: [Number(form.range.allowedMin), Number(form.range.allowedMax)],
      normal: [Number(form.range.normalMin), Number(form.range.normalMax)]
    };
  }

  const allowed = {};
  for (const row of form.enumState.options) {
    if (!row.key.trim()) {
      continue;
    }
    allowed[row.key.trim()] = row.value.trim();
  }
  return {
    name: form.name.trim(),
    type: "enum",
    unit: form.unit.trim(),
    allowed,
    normal: form.enumState.normal
  };
}

export default function CharacteristicsTab() {
  const [mode, setMode] = useState("create");
  const [characteristics, setCharacteristics] = useState([]);
  const [selectedId, setSelectedId] = useState("");
  const [form, setForm] = useState(emptyForm());
  const [usage, setUsage] = useState(null);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  async function refresh() {
    const response = await getCharacteristics();
    setCharacteristics(response.data);
  }

  useEffect(() => {
    refresh().catch(() => setError("Не удалось загрузить характеристики"));
  }, []);

  function onModeChange(nextMode) {
    setMode(nextMode);
    setSelectedId("");
    setForm(emptyForm());
    setUsage(null);
    setMessage("");
    setError("");
  }

  async function loadCharacteristic(id) {
    setSelectedId(id);
    setMessage("");
    setError("");
    if (!id) {
      setForm(emptyForm());
      setUsage(null);
      return;
    }
    try {
      const [detailRes, usageRes] = await Promise.all([
        getCharacteristicById(id),
        getCharacteristicUsage(id)
      ]);
      setForm(formFromCharacteristic(detailRes.data));
      setUsage(usageRes.data);
    } catch (err) {
      setError(err.response?.data?.detail || "Не удалось загрузить характеристику");
    }
  }

  function onTypeChange(type) {
    if (type === "range") {
      setForm((prev) => ({ ...prev, type: "range", range: { ...EMPTY_RANGE } }));
    } else {
      setForm((prev) => ({
        ...prev,
        type: "enum",
        enumState: { options: [{ key: "0", value: "" }], normal: "0" }
      }));
    }
  }

  async function createNew() {
    try {
      const created = await createCharacteristic(buildPayload(form));
      await refresh();
      setMode("edit");
      await loadCharacteristic(String(created.data.id));
      setMessage("Характеристика создана");
      setError("");
    } catch (err) {
      setError(err.response?.data?.detail || "Ошибка при создании характеристики");
      setMessage("");
    }
  }

  async function saveExisting() {
    if (!selectedId) {
      setError("Выберите характеристику");
      return;
    }
    try {
      await updateCharacteristic(Number(selectedId), buildPayload(form));
      await refresh();
      await loadCharacteristic(selectedId);
      setMessage("Изменения сохранены");
      setError("");
    } catch (err) {
      setError(err.response?.data?.detail || "Ошибка при обновлении характеристики");
      setMessage("");
    }
  }

  async function removeCurrent() {
    if (!selectedId) {
      setError("Сначала выберите характеристику");
      return;
    }
    try {
      await deleteCharacteristic(Number(selectedId));
      await refresh();
      setSelectedId("");
      setForm(emptyForm());
      setUsage(null);
      setMessage("Характеристика удалена");
      setError("");
    } catch (err) {
      setError(err.response?.data?.detail || "Ошибка при удалении характеристики");
      setMessage("");
    }
  }

  const formLocked = mode === "edit" && !selectedId;

  return (
    <div className="editor-grid">
      <EditorModeSwitch mode={mode} onModeChange={onModeChange} entityName="характеристику" />

      {mode === "edit" && (
        <label>
          Существующие характеристики
          <select value={selectedId} onChange={(e) => loadCharacteristic(e.target.value)}>
            <option value="">-- выберите --</option>
            {characteristics.map((item) => (
              <option key={item.id} value={item.id}>
                {item.name}
              </option>
            ))}
          </select>
        </label>
      )}

      {formLocked && <div className="alert">Выберите характеристику для редактирования.</div>}

      {mode === "edit" && usage && usage.diagnosis_count > 0 && (
        <div className="alert">
          Эта характеристика используется в диагнозах: {usage.used_in_diagnoses.join(", ")}. Изменение типа или
          удаление enum-ключей может повлиять на критерии.
        </div>
      )}

      <label>
        Название
        <input
          disabled={formLocked}
          value={form.name}
          onChange={(e) => setForm((prev) => ({ ...prev, name: e.target.value }))}
        />
      </label>

      <label>
        Тип
        <select disabled={formLocked} value={form.type} onChange={(e) => onTypeChange(e.target.value)}>
          <option value="range">range</option>
          <option value="enum">enum</option>
        </select>
      </label>

      <label>
        Единица измерения
        <input
          disabled={formLocked}
          value={form.unit}
          onChange={(e) => setForm((prev) => ({ ...prev, unit: e.target.value }))}
        />
      </label>

      {form.type === "range" ? (
        <>
          <label>
            allowed min
            <input
              disabled={formLocked}
              type="number"
              value={form.range.allowedMin}
              onChange={(e) =>
                setForm((prev) => ({ ...prev, range: { ...prev.range, allowedMin: e.target.value } }))
              }
            />
          </label>
          <label>
            allowed max
            <input
              disabled={formLocked}
              type="number"
              value={form.range.allowedMax}
              onChange={(e) =>
                setForm((prev) => ({ ...prev, range: { ...prev.range, allowedMax: e.target.value } }))
              }
            />
          </label>
          <label>
            normal min
            <input
              disabled={formLocked}
              type="number"
              value={form.range.normalMin}
              onChange={(e) =>
                setForm((prev) => ({ ...prev, range: { ...prev.range, normalMin: e.target.value } }))
              }
            />
          </label>
          <label>
            normal max
            <input
              disabled={formLocked}
              type="number"
              value={form.range.normalMax}
              onChange={(e) =>
                setForm((prev) => ({ ...prev, range: { ...prev.range, normalMax: e.target.value } }))
              }
            />
          </label>
        </>
      ) : (
        <div>
          <p className="muted">Варианты enum</p>
          <div className="editor-grid">
            {form.enumState.options.map((row, index) => (
              <div key={`${row.key}-${index}`} className="inline-form">
                <input
                  disabled={formLocked}
                  placeholder="key"
                  value={row.key}
                  onChange={(e) =>
                    setForm((prev) => {
                      const options = [...prev.enumState.options];
                      options[index] = { ...options[index], key: e.target.value };
                      return { ...prev, enumState: { ...prev.enumState, options } };
                    })
                  }
                />
                <input
                  disabled={formLocked}
                  placeholder="название"
                  value={row.value}
                  onChange={(e) =>
                    setForm((prev) => {
                      const options = [...prev.enumState.options];
                      options[index] = { ...options[index], value: e.target.value };
                      return { ...prev, enumState: { ...prev.enumState, options } };
                    })
                  }
                />
                <button
                  type="button"
                  className="danger"
                  disabled={formLocked}
                  onClick={() =>
                    setForm((prev) => {
                      const options = prev.enumState.options.filter((_, i) => i !== index);
                      const safeOptions = options.length ? options : [{ key: "", value: "" }];
                      const safeNormal = safeOptions.some((item) => item.key === prev.enumState.normal)
                        ? prev.enumState.normal
                        : safeOptions[0].key;
                      return {
                        ...prev,
                        enumState: { options: safeOptions, normal: safeNormal }
                      };
                    })
                  }
                >
                  удалить
                </button>
              </div>
            ))}
          </div>

          <button
            type="button"
            disabled={formLocked}
            onClick={() =>
              setForm((prev) => ({
                ...prev,
                enumState: {
                  ...prev.enumState,
                  options: [...prev.enumState.options, { key: "", value: "" }]
                }
              }))
            }
          >
            Добавить вариант
          </button>

          <label>
            Норма
            <select
              disabled={formLocked}
              value={form.enumState.normal}
              onChange={(e) =>
                setForm((prev) => ({ ...prev, enumState: { ...prev.enumState, normal: e.target.value } }))
              }
            >
              {form.enumState.options
                .filter((item) => item.key.trim())
                .map((item) => (
                  <option key={item.key} value={item.key}>
                    {item.key} - {item.value || "(без названия)"}
                  </option>
                ))}
            </select>
          </label>
        </div>
      )}

      <div className="button-row">
        {mode === "create" && (
          <button type="button" onClick={createNew}>
            Создать
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
            <th>ID</th>
            <th>Характеристика</th>
            <th>Тип</th>
            <th>Допустимые значения</th>
            <th>Норма</th>
          </tr>
        </thead>
        <tbody>
          {characteristics.map((item) => (
            <tr key={item.id}>
              <td>{item.id}</td>
              <td>{item.name}</td>
              <td>{item.type}</td>
              <td>
                <code>
                  {Array.isArray(item.allowed)
                    ? JSON.stringify(item.allowed)
                    : Object.entries(item.allowed)
                        .map(([k, v]) => `${k}: ${v}`)
                        .join(", ")}
                </code>
              </td>
              <td>
                <code>{JSON.stringify(item.normal)}</code>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
