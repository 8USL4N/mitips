import { useEffect, useMemo, useState } from "react";
import {
  getCharacteristics,
  getDiagnoses,
  getDiagnosisById,
  solveDiagnosis
} from "../../api/client";
import DiagnosisForm from "../DiagnosisForm";
import TreatmentResult from "../TreatmentResult";

export default function ValidationTab() {
  const [diagnoses, setDiagnoses] = useState([]);
  const [characteristics, setCharacteristics] = useState([]);
  const [selectedDiagnosisId, setSelectedDiagnosisId] = useState("");
  const [selectedDiagnosis, setSelectedDiagnosis] = useState(null);
  const [values, setValues] = useState({});
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const characteristicById = useMemo(() => {
    const map = {};
    for (const item of characteristics) {
      map[item.id] = item;
    }
    return map;
  }, [characteristics]);

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

  async function onDiagnosisChange(id) {
    setSelectedDiagnosisId(id);
    setValues({});
    setResult(null);
    setError("");

    if (!id) {
      setSelectedDiagnosis(null);
      return;
    }

    try {
      const response = await getDiagnosisById(id);
      setSelectedDiagnosis(response.data);
    } catch (err) {
      setError(err.response?.data?.detail || "Не удалось загрузить детали диагноза");
      setSelectedDiagnosis(null);
    }
  }

  async function onSubmit() {
    if (!selectedDiagnosisId) {
      setError("Выберите диагноз");
      return;
    }

    setLoading(true);
    setError("");
    try {
      const response = await solveDiagnosis(Number(selectedDiagnosisId), values);
      setResult(response.data);
    } catch (err) {
      setResult(null);
      setError(err.response?.data?.detail || "Не удалось выполнить проверку эталона");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="editor-grid">
      <div className="alert">
        Режим эксперта: выберите диагноз, введите значения его критериев и проверьте соответствие эталону.
      </div>

      <DiagnosisForm
        diagnoses={diagnoses}
        characteristics={characteristicById}
        selectedDiagnosisId={selectedDiagnosisId}
        selectedDiagnosis={selectedDiagnosis}
        values={values}
        loading={loading}
        onDiagnosisChange={onDiagnosisChange}
        onValuesChange={setValues}
        onSubmit={onSubmit}
      />

      {error && <div className="alert error">{error}</div>}
      {result && <TreatmentResult result={result} />}
    </div>
  );
}
