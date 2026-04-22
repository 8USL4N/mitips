import { useEffect, useState } from "react";
import { determineDiagnosis, getBodySystems, getCharacteristics } from "../api/client";
import DiagnosisResult from "../components/DiagnosisResult";
import SymptomsForm from "../components/SymptomsForm";

function cleanValues(values) {
  const result = {};
  for (const [key, value] of Object.entries(values)) {
    if (value === null || value === undefined) {
      continue;
    }
    if (typeof value === "string" && value.trim() === "") {
      continue;
    }
    result[key] = typeof value === "string" ? value.trim() : value;
  }
  return result;
}

function validateRangeValues(values, characteristics) {
  for (const item of characteristics) {
    if (item.type !== "range") {
      continue;
    }

    const key = String(item.id);
    const rawValue = values[key];
    if (rawValue === "" || rawValue === undefined || rawValue === null) {
      continue;
    }

    const value = Number(rawValue);
    if (!Number.isFinite(value)) {
      return `${item.name}: значение должно быть числом`;
    }

    if (!Array.isArray(item.allowed) || item.allowed.length !== 2) {
      return `${item.name}: некорректно настроен допустимый диапазон`;
    }

    const min = Number(item.allowed[0]);
    const max = Number(item.allowed[1]);
    if (!Number.isFinite(min) || !Number.isFinite(max)) {
      return `${item.name}: некорректно настроен допустимый диапазон`;
    }

    if (value < min || value > max) {
      const unitPart = item.unit ? ` ${item.unit}` : "";
      return `${item.name}: значение должно быть в диапазоне ${min}-${max}${unitPart}`;
    }
  }

  return "";
}

export default function SolverPage() {
  const [bodySystems, setBodySystems] = useState([]);
  const [characteristics, setCharacteristics] = useState([]);
  const [values, setValues] = useState({});
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    let isMounted = true;

    async function loadData() {
      try {
        const [characteristicsRes, bodySystemsRes] = await Promise.all([
          getCharacteristics(),
          getBodySystems()
        ]);

        if (!isMounted) {
          return;
        }

        setCharacteristics(characteristicsRes.data);
        setBodySystems(bodySystemsRes.data);
      } catch (err) {
        setError(err.response?.data?.detail || "Не удалось загрузить данные решателя");
      }
    }

    loadData();
    return () => {
      isMounted = false;
    };
  }, []);

  async function onSubmit() {
    const payload = cleanValues(values);
    if (Object.keys(payload).length === 0) {
      setError("Введите хотя бы одно значение характеристики");
      setResult(null);
      return;
    }
    const validationError = validateRangeValues(payload, characteristics);
    if (validationError) {
      setError(validationError);
      setResult(null);
      return;
    }

    setLoading(true);
    setError("");
    try {
      const response = await determineDiagnosis(payload);
      setResult(response.data);
    } catch (err) {
      setResult(null);
      setError(err.response?.data?.detail || "Не удалось определить диагноз");
    } finally {
      setLoading(false);
    }
  }

  return (
    <section className="panel">
      <h2>Решатель</h2>
      <p className="muted">
        Введите известные симптомы пациента. Система определит диагноз или покажет наиболее близкие гипотезы.
      </p>

      <SymptomsForm
        bodySystems={bodySystems}
        characteristics={characteristics}
        values={values}
        loading={loading}
        onValuesChange={setValues}
        onSubmit={onSubmit}
      />

      {error && <div className="alert error">{error}</div>}
      <DiagnosisResult result={result} />
    </section>
  );
}
