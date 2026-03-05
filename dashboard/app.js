// Simple frontend logic for HR AI Screening dashboard

async function createVacancy() {
  const title = document.getElementById("title").value.trim();
  const skills = document.getElementById("skills").value.trim();
  const seniority = document.getElementById("seniority").value.trim();
  const description = document.getElementById("description").value.trim();

  if (!title || !skills || !seniority || !description) {
    alert("Пожалуйста, заполните все поля вакансии.");
    return;
  }

  const payload = { title, skills, seniority, description };

  try {
    console.log("createVacancy: sending payload", payload);
    const res = await fetch("/create_vacancy", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(payload),
    });

    const data = await res.json();
    console.log("createVacancy: response", data);

    if (!res.ok) {
      alert("Ошибка при создании вакансии: " + (data.detail || JSON.stringify(data)));
      return;
    }

    alert("Вакансия создана.");
  } catch (e) {
    console.error("createVacancy error", e);
    alert("Ошибка сети при создании вакансии. Проверьте консоль.");
  }
}

async function uploadResumes() {
  const fileInput = document.getElementById("file");
  const file = fileInput.files[0];

  if (!file) {
    alert("Выберите ZIP-файл с резюме.");
    return;
  }

  const formData = new FormData();
  formData.append("file", file);

  try {
    console.log("uploadResumes: uploading file", file.name, file.size);
    const res = await fetch("/upload_resumes", {
      method: "POST",
      body: formData,
    });

    const data = await res.json();
    console.log("uploadResumes: response", data);

    if (!res.ok) {
      alert("Ошибка при загрузке резюме: " + (data.detail || JSON.stringify(data)));
      return;
    }

    alert(
      "Резюме загружены.\n" +
        "Всего кандидатов: " +
        data.parsed +
        "\nОбработано: " +
        data.processed +
        "\nПропущено (формат): " +
        data.skipped_unsupported +
        "\nПропущено (пустые): " +
        data.skipped_empty
    );

    await loadCandidates();
  } catch (e) {
    console.error("uploadResumes error", e);
    alert("Ошибка сети при загрузке резюме. Проверьте консоль.");
  }
}

async function startScreening() {
  const nValue = document.getElementById("n").value.trim();
  const n = parseInt(nValue, 10);

  if (!n || isNaN(n) || n <= 0) {
    alert("Введите положительное число кандидатов для контакта.");
    return;
  }

  const payload = { n };

  try {
    console.log("startScreening: sending payload", payload);
    const res = await fetch("/start_screening", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(payload),
    });

    const data = await res.json();
    console.log("startScreening: response", data);

    if (!res.ok) {
      alert("Ошибка при старте скрининга: " + (data.detail || JSON.stringify(data)));
      return;
    }

    alert(
      "Скрининг запущен.\n" +
        "Запрошено top N: " +
        data.requested_top_n +
        "\nСвязались с: " +
        data.contacted_candidates.join(", ") +
        "\nПропущены без Telegram: " +
        (data.skipped_no_telegram || []).length
    );

    await loadCandidates();
  } catch (e) {
    console.error("startScreening error", e);
    alert("Ошибка сети при запуске скрининга. Проверьте консоль.");
  }
}

async function loadCandidates() {
  try {
    console.log("loadCandidates: fetching /candidates");
    const res = await fetch("/candidates");
    const data = await res.json();
    console.log("loadCandidates: response", data);

    if (!Array.isArray(data)) {
      console.warn("Expected candidates array, got:", data);
    }

    const table = document.getElementById("table");
    table.innerHTML = "";

    // Header
    const header = document.createElement("tr");
    [
      "Name",
      "Score",
      "Telegram",
      "Seniority",
      "Total Experience",
      "English",
      "Salary Expectation",
    ].forEach((title) => {
      const th = document.createElement("th");
      th.textContent = title;
      header.appendChild(th);
    });
    table.appendChild(header);

    if (!Array.isArray(data)) {
      return;
    }

    data.forEach((item) => {
      const candidate = item.data || {};
      const tr = document.createElement("tr");

      const nameTd = document.createElement("td");
      nameTd.textContent = candidate.name || "";
      tr.appendChild(nameTd);

      const scoreTd = document.createElement("td");
      scoreTd.textContent = item.score != null ? item.score : "";
      tr.appendChild(scoreTd);

      const tgTd = document.createElement("td");
      tgTd.textContent = candidate.telegram_username || "";
      tr.appendChild(tgTd);

      const seniorityTd = document.createElement("td");
      seniorityTd.textContent = candidate.seniority_level || "";
      tr.appendChild(seniorityTd);

      const expTd = document.createElement("td");
      expTd.textContent = candidate.total_years_experience || "";
      tr.appendChild(expTd);

      const engTd = document.createElement("td");
      engTd.textContent = candidate.english_level || "";
      tr.appendChild(engTd);

      const salaryTd = document.createElement("td");
      salaryTd.textContent = candidate.salary_expectation || "";
      tr.appendChild(salaryTd);

      table.appendChild(tr);
    });
  } catch (e) {
    console.error("loadCandidates error", e);
  }
}

// Auto-load candidates on page load
document.addEventListener("DOMContentLoaded", () => {
  loadCandidates();
});