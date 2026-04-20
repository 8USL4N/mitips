function HypothesisCard({ item, title }) {
  return (
    <article className="result-card">
      {title && <h4>{title}</h4>}
      <h3>
        {item.diagnosis}
        {item.icd10 ? ` (${item.icd10})` : ""}
      </h3>
      <p>
        Лечение: <strong>{item.treatment_name}</strong>
      </p>
      <p>
        Совпадений: {item.matched_count}/{item.answered_count} из проверенных, критериев всего: {item.total_count}
      </p>

      <h4>План действий</h4>
      <ol>
        {item.actions.map((action, index) => (
          <li key={`${action}-${index}`}>{action}</li>
        ))}
      </ol>

      <h4>Объяснение</h4>
      <table>
        <thead>
          <tr>
            <th>Характеристика</th>
            <th>Ожидаемое</th>
            <th>Введённое</th>
            <th>Совпало</th>
          </tr>
        </thead>
        <tbody>
          {item.explanation.map((row, index) => (
            <tr key={`${row.characteristic}-${index}`} className={row.match ? "row-ok" : "row-bad"}>
              <td>{row.characteristic}</td>
              <td>{row.expected}</td>
              <td>{row.actual ?? "не указано"}</td>
              <td>{row.match ? "Да" : "Нет"}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </article>
  );
}

function missingSummary(items) {
  const merged = new Set();
  for (const item of items) {
    for (const characteristic of item.missing_characteristics || []) {
      merged.add(characteristic);
    }
  }
  return Array.from(merged);
}

export default function DiagnosisResult({ result }) {
  if (!result) {
    return null;
  }

  const statusClass = `status-banner status-${result.status}`;

  if (result.status === "determined" || result.status === "likely") {
    const item = result.primary;
    if (!item) {
      return null;
    }

    return (
      <div className="result-block">
        <div className={statusClass}>{result.message}</div>
        {result.status === "likely" && item.missing_characteristics.length > 0 && (
          <div className="alert">
            Для однозначного определения не хватает: {item.missing_characteristics.join(", ")}
          </div>
        )}
        <HypothesisCard item={item} />
      </div>
    );
  }

  const mergedMissing = missingSummary(result.alternatives);
  return (
    <div className="result-block">
      <div className={statusClass}>{result.message}</div>
      {mergedMissing.length > 0 && (
        <div className="alert">Введите дополнительные характеристики: {mergedMissing.join(", ")}</div>
      )}
      {result.status === "not_determined" && (
        <div className="alert">Требуется дополнительное обследование для точного диагноза.</div>
      )}
      <div className="accordion-list">
        {result.alternatives.map((item, index) => (
          <details key={item.diagnosis_id} open={index === 0}>
            <summary>
              {item.diagnosis}
              {item.icd10 ? ` (${item.icd10})` : ""}
            </summary>
            <HypothesisCard
              item={item}
              title={result.status === "ambiguous" ? "Кандидат на диагноз" : "Возможная гипотеза"}
            />
          </details>
        ))}
      </div>
    </div>
  );
}
