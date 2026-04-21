import { useState } from "react";
import BodySystemsTab from "../components/KnowledgeEditor/BodySystemsTab";
import CharacteristicsTab from "../components/KnowledgeEditor/CharacteristicsTab";
import DiagnosesTab from "../components/KnowledgeEditor/DiagnosesTab";
import TreatmentsTab from "../components/KnowledgeEditor/TreatmentsTab";

const TABS = [
  "Системы организма",
  "Характеристики",
  "Диагнозы",
  "Лечения"
];

export default function EditorPage() {
  const [activeTab, setActiveTab] = useState("Системы организма");

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

      {activeTab === "Системы организма" && <BodySystemsTab />}
      {activeTab === "Характеристики" && <CharacteristicsTab />}
      {activeTab === "Диагнозы" && <DiagnosesTab />}
      {activeTab === "Лечения" && <TreatmentsTab />}
    </section>
  );
}
