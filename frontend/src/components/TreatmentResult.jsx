export default function TreatmentResult({ result }) {
  return (
    <div className="result-block">
      <h3>
        Диагноз: {result.diagnosis} {result.icd10 ? `(${result.icd10})` : ""}
      </h3>
      <p>
        Лечение: <strong>{result.treatment_name}</strong>
      </p>
      <p>
        Совпадений: {result.matched_count}/{result.total_count}
      </p>

      <h4>План действий</h4>
      <ol>
        {result.actions.map((action, index) => (
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
          {result.explanation.map((row, index) => (
            <tr key={`${row.characteristic}-${index}`} className={row.match ? "row-ok" : "row-bad"}>
              <td>{row.characteristic}</td>
              <td>{row.expected}</td>
              <td>{row.actual ?? "не указано"}</td>
              <td>{row.match ? "Да" : "Нет"}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
