export default function DiagnosisForm({
  diagnoses,
  characteristics,
  selectedDiagnosis,
  values,
  loading,
  onDiagnosisChange,
  onValuesChange,
  onSubmit
}) {
  const diagnosisChars = selectedDiagnosis
    ? Object.keys(diagnoses[selectedDiagnosis]?.characteristics || {})
    : [];

  return (
    <div className="form-grid">
      <label>
        Диагноз
        <select value={selectedDiagnosis} onChange={(e) => onDiagnosisChange(e.target.value)}>
          <option value="">-- Выберите диагноз --</option>
          {Object.keys(diagnoses).map((name) => (
            <option key={name} value={name}>
              {name}
            </option>
          ))}
        </select>
      </label>

      {diagnosisChars.map((charName) => {
        const charInfo = characteristics[charName];
        if (!charInfo) {
          return null;
        }

        return (
          <label key={charName}>
            {charName}
            {charInfo.type === "range" ? (
              <input
                type="number"
                step="0.1"
                min={charInfo.allowed[0]}
                max={charInfo.allowed[1]}
                value={values[charName] ?? ""}
                onChange={(e) =>
                  onValuesChange({
                    ...values,
                    [charName]: e.target.value
                  })
                }
                placeholder={`${charInfo.allowed[0]}–${charInfo.allowed[1]} ${charInfo.unit || ""}`}
              />
            ) : (
              <select
                value={values[charName] ?? ""}
                onChange={(e) =>
                  onValuesChange({
                    ...values,
                    [charName]: e.target.value
                  })
                }
              >
                <option value="">-- выберите --</option>
                {Object.entries(charInfo.allowed).map(([key, value]) => (
                  <option key={key} value={key}>
                    {value}
                  </option>
                ))}
              </select>
            )}
          </label>
        );
      })}

      {selectedDiagnosis && (
        <button type="button" className="primary" onClick={onSubmit} disabled={loading}>
          {loading ? "Анализ..." : "Определить лечение"}
        </button>
      )}
    </div>
  );
}
