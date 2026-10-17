/**
 * Au copier-coller, Chrome sérialise la sélection en HTML en y injectant les
 * styles calculés (dont le `background-color` des badges `.tag`). Collé dans un
 * Google Doc, ce fond coloré est conservé.
 *
 * On intercepte l'évènement `copy` et on réécrit le HTML du presse-papier en
 * neutralisant les fonds, tout en gardant le texte et le reste du formatage.
 */
export function installStripCopyBackground(): void {
  document.addEventListener("copy", (e: ClipboardEvent) => {
    const selection = window.getSelection();
    if (!selection || selection.rangeCount === 0 || selection.isCollapsed) return;
    if (!e.clipboardData) return;

    const container = document.createElement("div");
    for (let i = 0; i < selection.rangeCount; i++) {
      container.appendChild(selection.getRangeAt(i).cloneContents());
    }

    for (const el of container.querySelectorAll<HTMLElement>("*")) {
      el.style.removeProperty("background");
      el.style.removeProperty("background-color");
      el.style.backgroundColor = "transparent";
    }

    e.clipboardData.setData("text/plain", selection.toString());
    e.clipboardData.setData("text/html", container.innerHTML);
    e.preventDefault();
  });
}
