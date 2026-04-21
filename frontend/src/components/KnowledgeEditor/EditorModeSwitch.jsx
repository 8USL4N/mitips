export default function EditorModeSwitch({ mode, onModeChange, entityName }) {
  return (
    <div className="mode-switch">
      <button
        type="button"
        className={mode === "create" ? "tab active" : "tab"}
        onClick={() => onModeChange("create")}
      >
        Добавить {entityName}
      </button>
      <button
        type="button"
        className={mode === "edit" ? "tab active" : "tab"}
        onClick={() => onModeChange("edit")}
      >
        Изменить существующий
      </button>
    </div>
  );
}
