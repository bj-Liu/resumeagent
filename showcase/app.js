"use strict";
const menu = document.querySelector(".menu-toggle");
const navigation = document.querySelector("#navigation");
function closeMenu() { menu.setAttribute("aria-expanded", "false"); navigation.classList.remove("is-open"); }
menu.addEventListener("click", () => {
  const open = menu.getAttribute("aria-expanded") !== "true";
  menu.setAttribute("aria-expanded", String(open)); navigation.classList.toggle("is-open", open);
});
navigation.addEventListener("click", event => { if (event.target.closest("a")) closeMenu(); });
document.addEventListener("keydown", event => { if (event.key === "Escape") closeMenu(); });
const roles = {
  planner: ["CONTENT → SPECIFICATION", "Give every page a clear job.", "Planner turns the factual profile and design feedback into page specifications, with a shared design language and page-specific content structure.", "User facts, feedback and optional references", "Validated page-specification JSON array", "resumeagent/agents/planner.py"],
  generator: ["SPECIFICATION → SOURCE", "Build pages in parallel.", "Generator implements the page specification as HTML and optional CSS. Runtime owns concurrent workers, retries, model admission and saved artifacts.", "Page specification, user facts and shared design context", "HTML and optional CSS saved through managed tools", "resumeagent/agents/generator.py"],
  refiner: ["SCREENSHOT → REVISION", "Refine what the browser shows.", "Refiner evaluates rendered screenshots and uses visual or user feedback to revise source. Runtime decides whether another iteration is allowed and renders the revision again.", "Screenshot, existing source, facts and feedback", "needs_refinement / feedback, or revised HTML and CSS", "resumeagent/agents/refiner.py"],
  quality: ["INTEGRATED QUALITY GATE", "Check the artifact. Keep the distinction.", "This is an integrated role, not a separate agent class. Refiner supplies visual judgment; Filesystem validates artifacts. Structural validity does not imply visual quality.", "Screenshot judgment and generated files", "A validated artifact or an actionable failure", "Refiner + Filesystem / Runtime validation"]
};
const tabs = Array.from(document.querySelectorAll("[data-role]"));
const targets = ["role-tag", "role-title", "role-description", "role-input", "role-output", "role-source"];
function selectRole(tab) {
  tabs.forEach(item => { const active = item === tab; item.setAttribute("aria-selected", String(active)); item.tabIndex = active ? 0 : -1; });
  roles[tab.dataset.role].forEach((text, index) => { document.getElementById(targets[index]).textContent = text; });
  document.getElementById("role-panel").setAttribute("aria-labelledby", tab.id);
}
tabs.forEach((tab, index) => {
  tab.addEventListener("click", () => selectRole(tab));
  tab.addEventListener("keydown", event => {
    let next;
    if (event.key === "ArrowRight") next = (index + 1) % tabs.length;
    if (event.key === "ArrowLeft") next = (index + tabs.length - 1) % tabs.length;
    if (event.key === "Home") next = 0;
    if (event.key === "End") next = tabs.length - 1;
    if (next !== undefined) { event.preventDefault(); selectRole(tabs[next]); tabs[next].focus(); }
  });
});
document.getElementById("copy-command").addEventListener("click", async () => {
  const status = document.getElementById("copy-status");
  try { await navigator.clipboard.writeText(document.getElementById("client-command").textContent); status.textContent = "Command copied."; }
  catch { status.textContent = "Select the command above to copy it manually."; }
});
async function loadEvidence() {
  try {
    const response = await fetch("data/evidence.json", { cache: "no-cache" });
    if (!response.ok) throw new Error("Evidence unavailable");
    const evidence = await response.json();
    const summary = document.getElementById("evidence-summary");
    summary.replaceChildren();
    const metrics = [
      [String(evidence.tests.passed), "Automated tests passed", `${evidence.tests.total} discovered · ${evidence.tests.skipped} opt-in skip · ${evidence.tests.failures} failures/errors`],
      [`${evidence.benchmark.primary_completed}/${evidence.benchmark.primary_total}`, "Mock workflow Runs completed", `${evidence.benchmark.recovery_completed}/${evidence.benchmark.recovery_total} separate recovery experiments succeeded`],
      ["0", "Paid API calls in release checks", "Real SDK transport and real Selenium checks use mocked model responses."]
    ];
    metrics.forEach(([value, label, detail]) => {
      const metric = document.createElement("div"); metric.className = "metric";
      [["strong", value], ["span", label], ["small", detail]].forEach(([tag, text]) => { const item = document.createElement(tag); item.textContent = text; metric.append(item); });
      summary.append(metric);
    });
    if (evidence.demo.video_url) {
      const url = new URL(evidence.demo.video_url);
      if (url.protocol === "https:") {
        const link = document.getElementById("video-link"); link.href = url.href; link.hidden = false;
        if (/\.(mp4|webm)$/i.test(url.pathname)) {
          const video = document.getElementById("recorded-video"); video.src = url.href; video.hidden = false;
          document.querySelector(".demo-cover > img").hidden = true;
        }
        document.querySelector(".recording-label").textContent = "RECORDED WALKTHROUGH AVAILABLE";
      }
    }
  } catch {
    // The static report remains available when opened without an HTTP server.
    document.getElementById("evidence-summary").setAttribute("aria-label", "Open the linked static release report for test results");
  }
}
loadEvidence();
