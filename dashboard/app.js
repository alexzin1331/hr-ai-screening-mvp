const apiPrefix = "/api";

const state = {
    vacancies: [],
    selectedVacancyId: null,
};

let elements = null;

function getElements() {
    if (elements) {
        return elements;
    }
    elements = {
        requestIdLabel: document.getElementById("request-id-label"),
        healthBadge: document.getElementById("health-badge"),
        vacancyStatus: document.getElementById("vacancy-status"),
        title: document.getElementById("title"),
        description: document.getElementById("description"),
        hardSkills: document.getElementById("hard-skills"),
        softSkills: document.getElementById("soft-skills"),
        seniority: document.getElementById("seniority"),
        createVacancyBtn: document.getElementById("create-vacancy-btn"),
        vacancySelect: document.getElementById("vacancy-select"),
        resumeFile: document.getElementById("resume-file"),
        consent: document.getElementById("consent"),
        uploadBtn: document.getElementById("upload-btn"),
        uploadSummary: document.getElementById("upload-summary"),
        candidateTable: document.getElementById("candidate-table"),
        topN: document.getElementById("top-n"),
        refreshBtn: document.getElementById("refresh-btn"),
        outreachBtn: document.getElementById("outreach-btn"),
        exportJsonBtn: document.getElementById("export-json-btn"),
        exportCsvBtn: document.getElementById("export-csv-btn"),
        uiStatus: document.getElementById("ui-status"),
    };
    return elements;
}

function setUiStatus(message, type = "info") {
    const el = getElements().uiStatus;
    if (!el) {
        return;
    }
    el.textContent = message;
    el.dataset.type = type;
}

function setRequestId(response) {
    const requestId = response.headers.get("X-Request-ID") || "-";
    getElements().requestIdLabel.textContent = `request_id: ${requestId}`;
}

function splitCsv(value) {
    return value
        .split(",")
        .map((item) => item.trim())
        .filter(Boolean);
}

async function fetchJson(url, options = {}) {
    const response = await fetch(url, options);
    setRequestId(response);
    const contentType = response.headers.get("content-type") || "";
    const payload = contentType.includes("application/json") ? await response.json() : await response.text();
    if (!response.ok) {
        const message = payload?.error?.message || payload?.detail || "Запрос завершился ошибкой";
        throw new Error(message);
    }
    return payload;
}

async function loadHealth() {
    try {
        await fetchJson("/health/ready");
        getElements().healthBadge.textContent = "Система готова";
    } catch (error) {
        getElements().healthBadge.textContent = `Health error: ${error.message}`;
    }
}

async function loadVacancies() {
    const vacancies = await fetchJson(`${apiPrefix}/vacancies`);
    state.vacancies = vacancies;
    const select = getElements().vacancySelect;
    select.innerHTML = "";
    if (!vacancies.length) {
        const option = document.createElement("option");
        option.value = "";
        option.textContent = "Вакансий пока нет";
        select.appendChild(option);
        state.selectedVacancyId = null;
        return;
    }

    vacancies.forEach((vacancy) => {
        const option = document.createElement("option");
        option.value = vacancy.id;
        option.textContent = `${vacancy.id}: ${vacancy.title}`;
        select.appendChild(option);
    });

    if (!state.selectedVacancyId) {
        state.selectedVacancyId = vacancies[0].id;
    }
    select.value = String(state.selectedVacancyId);
    updateVacancyStatus();
}

function updateVacancyStatus() {
    const vacancy = state.vacancies.find((item) => item.id === Number(state.selectedVacancyId));
    const label = getElements().vacancyStatus;
    label.textContent = vacancy ? `vacancy_id=${vacancy.id} | ${vacancy.title}` : "Не выбрана";
}

async function createVacancy() {
    const el = getElements();
    const payload = {
        title: el.title.value.trim(),
        description: el.description.value.trim(),
        hard_skills: splitCsv(el.hardSkills.value),
        soft_skills: splitCsv(el.softSkills.value),
        seniority: el.seniority.value,
        status: "active",
    };

    if (!payload.title || !payload.description) {
        alert("Заполните title и description.");
        return;
    }

    const vacancy = await fetchJson(`${apiPrefix}/vacancies`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
    });
    state.selectedVacancyId = vacancy.id;
    setUiStatus(`Вакансия ${vacancy.id} создана.`, "success");
    await loadVacancies();
    await loadCandidates();
}

async function uploadResumes() {
    if (!state.selectedVacancyId) {
        alert("Сначала создайте или выберите вакансию.");
        return;
    }
    const el = getElements();
    const fileInput = el.resumeFile;
    const file = fileInput.files[0];
    if (!file) {
        alert("Выберите файл.");
        return;
    }

    const formData = new FormData();
    formData.append("file", file);
    formData.append("consent_to_personal_data_processing", el.consent.checked ? "true" : "false");

    const result = await fetchJson(`${apiPrefix}/vacancies/${state.selectedVacancyId}/resumes`, {
        method: "POST",
        body: formData,
    });
    el.uploadSummary.textContent = JSON.stringify(result, null, 2);
    setUiStatus(`Файлы обработаны. Успешно: ${result.processed}.`, "success");
    await loadCandidates();
}

function renderCandidates(candidates) {
    const tbody = getElements().candidateTable;
    tbody.innerHTML = "";
    if (!candidates.length) {
        const row = document.createElement("tr");
        row.innerHTML = `<td colspan="8" class="empty-cell">Кандидаты ещё не обработаны.</td>`;
        tbody.appendChild(row);
        return;
    }

    candidates.forEach((candidate) => {
        const tr = document.createElement("tr");
        tr.innerHTML = `
            <td>
                <strong>${candidate.full_name || "Не определён"}</strong>
                <div class="subtle">${candidate.email || "-"}</div>
            </td>
            <td>${candidate.current_position || "-"}</td>
            <td>${candidate.total_years_experience ?? "-"} / ${candidate.seniority_level || "-"}</td>
            <td>${candidate.email || "-"}<div class="subtle">${candidate.email_invite_status || "-"}</div></td>
            <td>${candidate.telegram_username ? `@${candidate.telegram_username}` : "не найден"}</td>
            <td><span class="score">${candidate.total_score ?? "-"}</span></td>
            <td>
                <div>candidate: ${candidate.candidate_status}</div>
                <div>contact: ${candidate.contact_status}</div>
                <div>resume: ${candidate.parse_status}</div>
                <div>scoring: ${candidate.scoring_status}</div>
            </td>
            <td>${candidate.summary || candidate.reason || "-"}</td>
        `;
        tbody.appendChild(tr);
    });
}

async function loadCandidates() {
    if (!state.selectedVacancyId) {
        renderCandidates([]);
        return;
    }
    const candidates = await fetchJson(`${apiPrefix}/vacancies/${state.selectedVacancyId}/candidates`);
    renderCandidates(candidates);
}

async function startOutreach() {
    if (!state.selectedVacancyId) {
        alert("Выберите вакансию.");
        return;
    }
    const topN = Number(getElements().topN.value);
    const result = await fetchJson(`${apiPrefix}/vacancies/${state.selectedVacancyId}/send-invites`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ top_n: topN, refresh_invite_token: false }),
    });
    setUiStatus(`Email outreach завершён. sent=${result.sent}, email_missing=${result.email_missing}, invalid=${result.invalid_email}, errors=${result.errors}`, "success");
    alert(`Email invite отправлено: ${result.sent}, без email: ${result.email_missing}, invalid: ${result.invalid_email}, ошибок: ${result.errors}`);
    await loadCandidates();
}

function downloadExport(format) {
    if (!state.selectedVacancyId) {
        alert("Выберите вакансию.");
        return;
    }
    window.open(`${apiPrefix}/vacancies/${state.selectedVacancyId}/export?format=${format}`, "_blank");
}

function attachListeners() {
    const el = getElements();
    el.createVacancyBtn.addEventListener("click", async () => {
        try {
            setUiStatus("Создание вакансии...", "info");
            await createVacancy();
        } catch (error) {
            setUiStatus(`Ошибка создания вакансии: ${error.message}`, "error");
            alert(error.message);
        }
    });
    el.uploadBtn.addEventListener("click", async () => {
        try {
            setUiStatus("Загрузка и обработка резюме...", "info");
            await uploadResumes();
        } catch (error) {
            setUiStatus(`Ошибка загрузки: ${error.message}`, "error");
            alert(error.message);
        }
    });
    el.refreshBtn.addEventListener("click", async () => {
        try {
            setUiStatus("Обновление списка кандидатов...", "info");
            await loadCandidates();
            setUiStatus("Список кандидатов обновлён.", "success");
        } catch (error) {
            setUiStatus(`Ошибка обновления: ${error.message}`, "error");
            alert(error.message);
        }
    });
    el.outreachBtn.addEventListener("click", async () => {
        try {
            setUiStatus("Запуск outreach...", "info");
            await startOutreach();
        } catch (error) {
            setUiStatus(`Ошибка outreach: ${error.message}`, "error");
            alert(error.message);
        }
    });
    el.exportJsonBtn.addEventListener("click", () => downloadExport("json"));
    el.exportCsvBtn.addEventListener("click", () => downloadExport("csv"));
    el.vacancySelect.addEventListener("change", async (event) => {
        state.selectedVacancyId = Number(event.target.value);
        updateVacancyStatus();
        try {
            setUiStatus("Переключение вакансии...", "info");
            await loadCandidates();
            setUiStatus("Вакансия переключена.", "success");
        } catch (error) {
            setUiStatus(`Ошибка загрузки кандидатов: ${error.message}`, "error");
            alert(error.message);
        }
    });
}

async function initDashboard() {
    getElements();
    attachListeners();
    try {
        await loadHealth();
        await loadVacancies();
        await loadCandidates();
        setUiStatus("UI готов к работе.", "success");
    } catch (error) {
        setUiStatus(`Ошибка инициализации dashboard: ${error.message}`, "error");
        console.error(error);
    }
}

if (document.readyState === "loading") {
    window.addEventListener("DOMContentLoaded", initDashboard);
} else {
    initDashboard();
}
