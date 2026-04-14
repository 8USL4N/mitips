import { useEffect, useState } from "react";
import { getCharacteristics } from "../../api/client";

export default function CharacteristicsTab() {
  const [characteristics, setCharacteristics] = useState([]);
  const [error, setError] = useState("");

  useEffect(() => {
    getCharacteristics()
      .then((res) => setCharacteristics(res.data))
      .catch(() => setError("Не удалось загрузить характеристики"));
  }, []);

  return (
    <div className="editor-grid">
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

      <div className="alert">Вкладка только для просмотра: изменение типов может сломать правила.</div>
    </div>
  );
}
