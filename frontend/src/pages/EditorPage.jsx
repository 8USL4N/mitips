import { useState } from "react";
import DiagnosesTab from "../components/KnowledgeEditor/DiagnosesTab";
import TreatmentsTab from "../components/KnowledgeEditor/TreatmentsTab";
import CharacteristicsTab from "../components/KnowledgeEditor/CharacteristicsTab";

const TABS = ["Диагнозы", "Лечения", "Характеристики"];

export default function EditorPage() {
  const [activeTab, setActiveTab] = useState("Диагнозы");

  return (
    <section className="panel">
      <h2>Редактор базы знаний</h2>
      <div className="tab-row">
        {TABS.map((tab) => (
          <button
            key={tab}
            type="button"
            className={activeTab === tab ? "tab active" : "tab"}
            onClick={() => setActiveTab(tab)}
          >
            {tab}
          </button>
        ))}
      </div>

      {activeTab === "Диагнозы" && <DiagnosesTab />}
      {activeTab === "Лечения" && <TreatmentsTab />}
      {activeTab === "Характеристики" && <CharacteristicsTab />}
    </section>
  );
}
