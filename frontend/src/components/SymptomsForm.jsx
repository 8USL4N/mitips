function CharacteristicInput({ item, value, onChange }) {
  if (item.type === "range") {
    return (
      <input
        type="number"
        step="0.1"
        min={item.allowed[0]}
        max={item.allowed[1]}
        value={value ?? ""}
        onChange={(e) => onChange(e.target.value)}
        placeholder={`${item.allowed[0]}–${item.allowed[1]} ${item.unit || ""}`}
      />
    );
  }

  return (
    <select value={value ?? ""} onChange={(e) => onChange(e.target.value)}>
      <option value="">-- не указано --</option>
      {Object.entries(item.allowed).map(([key, option]) => (
        <option key={key} value={key}>
          {option}
        </option>
      ))}
    </select>
  );
}

function SystemBlock({ title, characteristics, values, onValuesChange }) {
  if (!characteristics.length) {
    return null;
  }

  return (
    <section className="system-block">
      <h4>{title}</h4>
      <div className="form-grid">
        {characteristics.map((item) => {
          const key = String(item.id);
          return (
            <label key={item.id}>
              {item.name}
              <CharacteristicInput
                item={item}
                value={values[key]}
                onChange={(nextValue) =>
                  onValuesChange({
                    ...values,
                    [key]: nextValue
                  })
                }
              />
            </label>
          );
        })}
      </div>
    </section>
  );
}

export default function SymptomsForm({
  bodySystems,
  characteristics,
  values,
  loading,
  onValuesChange,
  onSubmit
}) {
  const characteristicById = {};
  for (const item of characteristics) {
    characteristicById[item.id] = item;
  }

  const assignedIds = new Set();
  for (const system of bodySystems) {
    for (const characteristicId of system.characteristic_ids || []) {
      assignedIds.add(characteristicId);
    }
  }

  const unassigned = characteristics.filter((item) => !assignedIds.has(item.id));

  return (
    <div className="solver-layout">
      {bodySystems.map((system) => {
        const items = (system.characteristic_ids || [])
          .map((id) => characteristicById[id])
          .filter(Boolean);

        return (
          <SystemBlock
            key={system.id}
            title={system.name}
            characteristics={items}
            values={values}
            onValuesChange={onValuesChange}
          />
        );
      })}

      <SystemBlock
        title="Прочие характеристики"
        characteristics={unassigned}
        values={values}
        onValuesChange={onValuesChange}
      />

      <button type="button" className="primary" onClick={onSubmit} disabled={loading}>
        {loading ? "Определение..." : "Определить диагноз"}
      </button>
    </div>
  );
}
