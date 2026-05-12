function ResultDiagnosisCard({ item }) {
  return (
    <article className="result-card result-card-primary">
      <h3>
        Итоговый диагноз экспертной системы: {item.diagnosis}
        {item.icd10 ? ` (${item.icd10})` : ""}
      </h3>
      <p>
        Лечение: <strong>{item.treatment_name}</strong>
      </p>

      <h4>План действий</h4>
      <ol>
        {item.actions.map((action, index) => (
          <li key={`${action}-${index}`}>{action}</li>
        ))}
      </ol>
    </article>
  );
}

function RejectedHypothesisCard({ item }) {
  const reasons = Array.isArray(item.rejection_reasons)
    ? item.rejection_reasons
    : (item.explanation || []).filter((row) => !row.match && row.actual !== null && row.actual !== undefined);

  return (
    <article className="result-card result-card-rejected">
      <h4>
        Отклонённая гипотеза: {item.diagnosis}
        {item.icd10 ? ` (${item.icd10})` : ""}
      </h4>
      {reasons.length > 0 ? (
        <table>
          <thead>
            <tr>
              <th>Характеристика</th>
              <th>Ожидалось</th>
              <th>Введено</th>
              <th>Почему не подошло</th>
            </tr>
          </thead>
          <tbody>
            {reasons.map((row, index) => (
              <tr key={`${row.characteristic}-${index}`} className="row-bad">
                <td>{row.characteristic}</td>
                <td>{row.expected}</td>
                <td>{row.actual ?? "не указано"}</td>
                <td>Противоречит критерию диагноза</td>
              </tr>
            ))}
          </tbody>
        </table>
      ) : (
        <p className="muted">Явных противоречий по введённым признакам нет.</p>
      )}
    </article>
  );
}

function selectionMethodLabel(method) {
  if (method === "neural") {
    return "Нейронная сеть";
  }
  if (method === "hypothesis_refutation") {
    return "Опровержение гипотезы";
  }
  return "Fallback";
}

export default function DiagnosisResult({ result }) {
  if (!result) {
    return null;
  }

  const statusClass = `status-banner status-${result.status}`;
  const primary = result.primary;
  const rejectedHypotheses = Array.isArray(result.rejected_hypotheses)
    ? result.rejected_hypotheses
    : [];

  return (
    <div className="result-block">
      <div className={statusClass}>{result.message}</div>

      {result.status === "neural_selected" && (
        <div className="alert">
          Найдено несколько равных не опровергнутых гипотез. Нейронная сеть выбрала итоговый диагноз.
        </div>
      )}

      <div className="alert">
        Метод выбора: <strong>{selectionMethodLabel(result.selection_method)}</strong>
        {typeof result.confidence === "number" && (
          <>
            {" "}
            | Уверенность: <strong>{Math.round(result.confidence * 100)}%</strong>
          </>
        )}
      </div>

      {primary ? (
        <ResultDiagnosisCard item={primary} />
      ) : (
        <article className="result-card result-card-primary">
          <h3>Итоговый диагноз экспертной системы не определён</h3>
          <p className="muted">Все близкие гипотезы были отклонены или данных недостаточно.</p>
        </article>
      )}

      <section className="accordion-list">
        <h3>Отклонённые гипотезы</h3>
        {rejectedHypotheses.length > 0 ? (
          rejectedHypotheses.map((item) => (
            <details key={item.diagnosis_id}>
              <summary>
                {item.diagnosis}
                {item.icd10 ? ` (${item.icd10})` : ""}
              </summary>
              <RejectedHypothesisCard item={item} />
            </details>
          ))
        ) : (
          <p className="muted">Близких отклонённых гипотез с противоречиями нет.</p>
        )}
      </section>
    </div>
  );
}
