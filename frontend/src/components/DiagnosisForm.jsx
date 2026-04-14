export default function DiagnosisForm({
  diagnoses,
  characteristics,
  selectedDiagnosisId,
  selectedDiagnosis,
  values,
  loading,
  onDiagnosisChange,
  onValuesChange,
  onSubmit
}) {
  const criteria = selectedDiagnosis?.criteria || [];

  return (
    <div className="form-grid">
      <label>
        Диагноз
        <select value={selectedDiagnosisId} onChange={(e) => onDiagnosisChange(e.target.value)}>
          <option value="">-- Выберите диагноз --</option>
          {diagnoses.map((item) => (
            <option key={item.id} value={item.id}>
              {item.name}
            </option>
          ))}
        </select>
      </label>

      {criteria.map((criterion) => {
        const characteristic = characteristics[criterion.characteristic_id];
        if (!characteristic) {
          return null;
        }

        const valueKey = String(criterion.characteristic_id);

        return (
          <label key={criterion.id}>
            {criterion.characteristic_name}
            {characteristic.type === "range" ? (
              <input
                type="number"
                step="0.1"
                min={characteristic.allowed[0]}
                max={characteristic.allowed[1]}
                value={values[valueKey] ?? ""}
                onChange={(e) =>
                  onValuesChange({
                    ...values,
                    [valueKey]: e.target.value
                  })
                }
                placeholder={`${characteristic.allowed[0]}–${characteristic.allowed[1]} ${
                  characteristic.unit || ""
                }`}
              />
            ) : (
              <select
                value={values[valueKey] ?? ""}
                onChange={(e) =>
                  onValuesChange({
                    ...values,
                    [valueKey]: e.target.value
                  })
                }
              >
                <option value="">-- выберите --</option>
                {Object.entries(characteristic.allowed).map(([key, value]) => (
                  <option key={key} value={key}>
                    {value}
                  </option>
                ))}
              </select>
            )}
          </label>
        );
      })}

      {selectedDiagnosisId && (
        <button type="button" className="primary" onClick={onSubmit} disabled={loading}>
          {loading ? "Анализ..." : "Определить лечение"}
        </button>
      )}
    </div>
  );
}
