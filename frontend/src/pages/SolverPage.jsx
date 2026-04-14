import { useEffect, useState } from "react";
import { getCharacteristics, getDiagnoses, solveDiagnosis } from "../api/client";
import DiagnosisForm from "../components/DiagnosisForm";
import TreatmentResult from "../components/TreatmentResult";

export default function SolverPage() {
  const [diagnoses, setDiagnoses] = useState({});
  const [characteristics, setCharacteristics] = useState({});
  const [selectedDiagnosis, setSelectedDiagnosis] = useState("");
  const [values, setValues] = useState({});
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    let isMounted = true;

    async function loadData() {
      try {
        const [diagnosesRes, characteristicsRes] = await Promise.all([
          getDiagnoses(),
          getCharacteristics()
        ]);

        if (!isMounted) {
          return;
        }

        setDiagnoses(diagnosesRes.data);
        setCharacteristics(characteristicsRes.data);
      } catch (err) {
        setError(err.response?.data?.detail || "Не удалось загрузить данные");
      }
    }

    loadData();

    return () => {
      isMounted = false;
    };
  }, []);

  async function onSubmit() {
    if (!selectedDiagnosis) {
      setError("Выберите диагноз");
      return;
    }

    setLoading(true);
    setError("");

    try {
      const res = await solveDiagnosis(selectedDiagnosis, values);
      setResult(res.data);
    } catch (err) {
      setResult(null);
      setError(err.response?.data?.detail || "Не удалось выполнить анализ");
    } finally {
      setLoading(false);
    }
  }

  return (
    <section className="panel">
      <h2>Решатель</h2>
      <p className="muted">
        Выберите диагноз, заполните признаки и получите объяснение соответствия.
      </p>

      <DiagnosisForm
        diagnoses={diagnoses}
        characteristics={characteristics}
        selectedDiagnosis={selectedDiagnosis}
        values={values}
        loading={loading}
        onDiagnosisChange={(name) => {
          setSelectedDiagnosis(name);
          setValues({});
          setResult(null);
          setError("");
        }}
        onValuesChange={setValues}
        onSubmit={onSubmit}
      />

      {error && <div className="alert error">{error}</div>}
      {result && <TreatmentResult result={result} />}
    </section>
  );
}
