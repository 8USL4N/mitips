import { useState } from "react";
import BodySystemsTab from "../components/KnowledgeEditor/BodySystemsTab";
import CharacteristicsTab from "../components/KnowledgeEditor/CharacteristicsTab";
import DiagnosesTab from "../components/KnowledgeEditor/DiagnosesTab";
import TreatmentsTab from "../components/KnowledgeEditor/TreatmentsTab";

const TABS = [
  "РЎРёСЃС‚РµРјС‹ РѕСЂРіР°РЅРёР·РјР°",
  "РҐР°СЂР°РєС‚РµСЂРёСЃС‚РёРєРё",
  "Р”РёР°РіРЅРѕР·С‹",
  "Р›РµС‡РµРЅРёСЏ"
];

export default function EditorPage() {
  const [activeTab, setActiveTab] = useState("РЎРёСЃС‚РµРјС‹ РѕСЂРіР°РЅРёР·РјР°");

  return (
    <section className="panel">
      <h2>Р РµРґР°РєС‚РѕСЂ Р±Р°Р·С‹ Р·РЅР°РЅРёР№</h2>
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

      {activeTab === "РЎРёСЃС‚РµРјС‹ РѕСЂРіР°РЅРёР·РјР°" && <BodySystemsTab />}
      {activeTab === "РҐР°СЂР°РєС‚РµСЂРёСЃС‚РёРєРё" && <CharacteristicsTab />}
      {activeTab === "Р”РёР°РіРЅРѕР·С‹" && <DiagnosesTab />}
      {activeTab === "Р›РµС‡РµРЅРёСЏ" && <TreatmentsTab />}
    </section>
  );
}
