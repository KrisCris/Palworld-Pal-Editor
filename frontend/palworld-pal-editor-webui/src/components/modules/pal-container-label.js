export function formatContainerLabel(container, translate, techName = () => "") {
  if (!container) return translate("Editor_Container_Anomaly");

  const ownerPrefix = container.OwnerName ? `${container.OwnerName} · ` : "";
  switch (container.ContainerKind) {
    case "base":
      return container.BaseOrdinal
        ? translate("Editor_Container_Base", [container.BaseOrdinal])
        : container.BaseName || container.ContainerLabel;
    case "party":
      return `${ownerPrefix}${translate("Editor_Container_Party")}`;
    case "storage":
      return `${ownerPrefix}${translate("Editor_Container_Palbox")}`;
    case "dps": {
      const name = techName("DimensionPalStorage");
      return name ? `${ownerPrefix}${name}` : container.ContainerLabel;
    }
    case "global_palbox":
      return techName("GlobalPalStorage") || container.ContainerLabel;
    case "special":
      return container.Shared
        ? translate("Editor_Container_ViewingCage")
        : `${ownerPrefix}${translate("Editor_Container_Special", [container.Size])}`;
    case "unknown":
      return translate("Editor_Container_Unknown", [container.Size]);
    case "anomaly":
      return translate("Editor_Container_Anomaly");
    default:
      return container.ContainerLabel || String(container.ContainerId || "");
  }
}
