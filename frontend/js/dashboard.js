(() => {
  if (!Api.getToken()) { window.location.href = "login.html"; return; }

  const $ = (id) => document.getElementById(id);
  const state = { exercises: [], lifts: [], progressExerciseId: null, metric: "top_weight_kg", progress: null };

  const fmtKg = (n) => `${Number.isInteger(n) ? n : n.toFixed(1)}`;
  const parseDay = (iso) => new Date(`${iso}T00:00:00`);
  const fmtDay = (iso, withYear = true) =>
    parseDay(iso).toLocaleDateString(undefined, { day: "numeric", month: "short", ...(withYear ? { year: "numeric" } : {}) });
  const todayIso = () => {
    const d = new Date();
    return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
  };

  // ---- exercises ----------------------------------------------------------
  function fillSelect(select, keepValue) {
    select.replaceChildren(...state.exercises.map((ex) => h("option", { value: ex.id }, ex.custom ? `${ex.name} (yours)` : ex.name)));
    if (keepValue && state.exercises.some((e) => String(e.id) === String(keepValue))) select.value = keepValue;
  }

  async function loadExercises() {
    state.exercises = await Api.get("/exercises");
    fillSelect($("exercise"), $("exercise").value);
    fillSelect($("progress-exercise"), state.progressExerciseId);
    if (!state.progressExerciseId && state.exercises.length) state.progressExerciseId = state.exercises[0].id;
    $("progress-exercise").value = state.progressExerciseId;
  }

  // ---- history ------------------------------------------------------------
  async function loadLifts() {
    state.lifts = await Api.get("/lifts?limit=200");
    renderHistory();
  }

  function renderHistory() {
    const box = $("history");
    if (!state.lifts.length) {
      box.replaceChildren(h("p", { class: "empty" }, "No lifts yet. Save your first one with the form on the left."));
      return;
    }
    const head = h("thead", {}, h("tr", {}, ["Date", "Exercise", "Weight", "Sets × reps", "Notes", ""].map((t) => h("th", { scope: "col" }, t))));
    const rows = state.lifts.map((l) =>
      h("tr", {},
        h("td", { class: "num" }, fmtDay(l.performed_on)),
        h("td", {}, l.exercise_name),
        h("td", { class: "num" }, `${fmtKg(l.weight_kg)} kg`),
        h("td", { class: "num" }, `${l.sets} × ${l.reps}`),
        h("td", { class: "notes" }, l.notes),
        h("td", { class: "actions" },
          h("button", {
            class: "btn btn-danger", type: "button",
            "aria-label": `Delete ${l.exercise_name} on ${fmtDay(l.performed_on)}`,
            onclick: () => deleteLift(l),
          }, "Delete"))));
    box.replaceChildren(h("table", {}, head, h("tbody", {}, rows)));
  }

  async function deleteLift(lift) {
    if (!window.confirm(`Delete ${lift.exercise_name}, ${fmtKg(lift.weight_kg)} kg on ${fmtDay(lift.performed_on)}?`)) return;
    try {
      await Api.del(`/lifts/${lift.id}`);
      await Promise.all([loadLifts(), loadProgress()]);
    } catch (err) {
      window.alert(err.message);
    }
  }

  // ---- progress -----------------------------------------------------------
  async function loadProgress() {
    if (!state.progressExerciseId) return;
    state.progress = await Api.get(`/lifts/progress?exercise_id=${state.progressExerciseId}`);
    renderStats();
    renderChart();
  }

  function renderStats() {
    const p = state.progress;
    const unit = (v) => (v == null ? "–" : [fmtKg(v), h("small", {}, "kg")]);
    $("stat-best").replaceChildren(...[].concat(unit(p.best_weight_kg)));
    $("stat-1rm").replaceChildren(...[].concat(unit(p.best_est_1rm_kg)));
    $("stat-days").textContent = p.points.length ? String(p.points.length) : "–";
  }

  const SVG = "http://www.w3.org/2000/svg";
  const s = (tag, attrs = {}, text) => {
    const n = document.createElementNS(SVG, tag);
    for (const [k, v] of Object.entries(attrs)) n.setAttribute(k, v);
    if (text != null) n.textContent = text;
    return n;
  };

  function renderChart() {
    const box = $("chart");
    const pts = state.progress.points;
    if (!pts.length) {
      box.replaceChildren(h("p", { class: "empty" }, "Nothing logged for this exercise yet. Save a lift and its progress chart appears here."));
      return;
    }

    const key = state.metric;
    const W = 640, H = 280, L = 48, R = 20, T = 20, B = 34;
    const values = pts.map((p) => p[key]);
    // Round the axis to "nice" numbers so the gridlines read cleanly (e.g. 60, 70, 80).
    let lo = Math.min(...values), hi = Math.max(...values);
    if (lo === hi) { lo -= 5; hi += 5; }
    const raw = (hi - lo) / 3;
    const mag = Math.pow(10, Math.floor(Math.log10(raw)));
    const step = [1, 2, 2.5, 5, 10].map((m) => m * mag).find((c) => c >= raw);
    lo = Math.max(0, Math.floor(lo / step) * step);
    hi = Math.ceil(hi / step) * step;
    if (hi === Math.max(...values)) hi += step; // leave room for the best-weight label
    const ticks = [];
    for (let v = lo; v <= hi + 1e-9; v += step) ticks.push(v);

    const t0 = parseDay(pts[0].date).getTime();
    const t1 = parseDay(pts[pts.length - 1].date).getTime();
    const x = (iso) => (t1 === t0 ? (L + W - R) / 2 : L + ((parseDay(iso).getTime() - t0) / (t1 - t0)) * (W - L - R));
    const y = (v) => T + (1 - (v - lo) / (hi - lo)) * (H - T - B);

    const svg = s("svg", { viewBox: `0 0 ${W} ${H}`, role: "img", "aria-label": `${state.progress.exercise.name} progress chart` });

    for (const v of ticks) {
      svg.append(s("line", { class: "grid", x1: L, x2: W - R, y1: y(v), y2: y(v) }));
      svg.append(s("text", { class: "axis", x: L - 8, y: y(v) + 4, "text-anchor": "end" }, Number.isInteger(v) ? v : v.toFixed(1)));
    }
    const first = pts[0].date, last = pts[pts.length - 1].date;
    const sameYear = first.slice(0, 4) === last.slice(0, 4);
    svg.append(s("text", { class: "axis", x: x(first), y: H - 8, "text-anchor": pts.length === 1 ? "middle" : "start" }, fmtDay(first, !sameYear)));
    if (pts.length > 1) svg.append(s("text", { class: "axis", x: x(last), y: H - 8, "text-anchor": "end" }, fmtDay(last, !sameYear)));

    svg.append(s("polyline", { class: "line", points: pts.map((p) => `${x(p.date)},${y(p[key])}`).join(" ") }));

    const bestValue = Math.max(...values);
    const bestIndex = values.indexOf(bestValue);
    pts.forEach((p, i) => {
      const isBest = i === bestIndex;
      const dot = s("circle", { class: `dot${isBest ? " best" : ""}`, cx: x(p.date), cy: y(p[key]), r: isBest ? 6 : 4.5 });
      dot.append(s("title", {}, `${fmtDay(p.date)}: ${fmtKg(p[key])} kg`));
      svg.append(dot);
    });
    const bp = pts[bestIndex];
    const labelX = Math.min(Math.max(x(bp.date), L + 24), W - R - 24);
    svg.append(s("text", { class: "best-label", x: labelX, y: y(bp[key]) - 13, "text-anchor": "middle" }, `${fmtKg(bestValue)} kg`));

    box.replaceChildren(svg);
  }

  // ---- forms --------------------------------------------------------------
  $("lift-form").addEventListener("submit", async (e) => {
    e.preventDefault();
    const err = $("lift-error"), status = $("lift-status");
    err.textContent = ""; status.textContent = "";
    const btn = e.submitter || e.target.querySelector("button[type=submit]");

    const body = {
      exercise_id: Number($("exercise").value),
      weight_kg: Number($("weight").value),
      reps: parseInt($("reps").value, 10),
      sets: parseInt($("sets").value, 10),
      performed_on: $("date").value || todayIso(),
      notes: $("notes").value,
    };
    if (!body.exercise_id) { err.textContent = "Choose an exercise."; return; }
    if (!(body.weight_kg > 0)) { err.textContent = "Enter the weight in kg."; return; }
    if (!(body.reps >= 1)) { err.textContent = "Enter how many reps you did."; return; }
    if (!(body.sets >= 1)) { err.textContent = "Enter how many sets you did."; return; }

    btn.disabled = true;
    try {
      const saved = await Api.post("/lifts", body);
      status.textContent = `Saved ${saved.exercise_name}, ${fmtKg(saved.weight_kg)} kg.`;
      $("weight").value = ""; $("reps").value = ""; $("notes").value = "";
      state.progressExerciseId = saved.exercise_id;
      $("progress-exercise").value = saved.exercise_id;
      await Promise.all([loadLifts(), loadProgress()]);
      $("weight").focus();
    } catch (ex) {
      err.textContent = ex.message;
    } finally {
      btn.disabled = false;
    }
  });

  $("exercise-form").addEventListener("submit", async (e) => {
    e.preventDefault();
    const err = $("exercise-error");
    err.textContent = "";
    const name = $("new-exercise").value.trim();
    if (!name) { err.textContent = "Enter a name for the exercise."; return; }
    try {
      const ex = await Api.post("/exercises", { name });
      $("new-exercise").value = "";
      await loadExercises();
      $("exercise").value = ex.id;
    } catch (ex2) {
      err.textContent = ex2.message;
    }
  });

  $("progress-exercise").addEventListener("change", (e) => {
    state.progressExerciseId = Number(e.target.value);
    loadProgress();
  });

  document.querySelectorAll(".metric button").forEach((b) =>
    b.addEventListener("click", () => {
      state.metric = b.dataset.metric;
      document.querySelectorAll(".metric button").forEach((o) => o.setAttribute("aria-pressed", String(o === b)));
      if (state.progress) renderChart();
    }));

  $("logout").addEventListener("click", () => { Api.clearToken(); window.location.href = "login.html"; });

  // ---- start --------------------------------------------------------------
  (async function init() {
    $("date").value = todayIso();
    try {
      const me = await Api.get("/auth/me");
      $("who").textContent = me.display_name;
      await loadExercises();
      await Promise.all([loadLifts(), loadProgress()]);
    } catch (err) {
      $("history").replaceChildren(h("p", { class: "error" }, err.message));
    }
  })();
})();
