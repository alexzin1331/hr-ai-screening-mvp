async function createVacancy() {
    const title = document.getElementById("title").value.trim();
    const skills = document.getElementById("skills").value.trim();
    const seniority = document.getElementById("seniority").value.trim();
    const description = document.getElementById("description").value.trim();

    if (!title || !skills || !description) {
        alert("⚠️ Пожалуйста, заполните название, навыки и описание вакансии.");
        return;
    }

    const payload = { title, skills, seniority, description };

    try {
        const res = await fetch("/create_vacancy", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload),
        });

        if (res.ok) {
            alert("✅ Вакансия успешно создана и сохранена в системе!");
        } else {
            const errorData = await res.json();
            alert("❌ Ошибка при создании: " + (errorData.detail || "Неизвестная ошибка"));
        }
    } catch (e) {
        console.error("CreateVacancy error:", e);
        alert("❌ Ошибка сети. Проверьте, запущен ли бэкенд.");
    }
}

async function uploadResumes() {
    const fileInput = document.getElementById("file");
    const btn = document.getElementById("btn-upload");
    const loader = document.getElementById("loader-upload");
    const btnText = btn.querySelector("span");

    if (!fileInput.files[0]) {
        alert("⚠️ Выберите ZIP-файл с резюме для загрузки.");
        return;
    }

    const formData = new FormData();
    formData.append("file", fileInput.files[0]);

    btn.disabled = true;
    loader.classList.remove("hidden");
    btnText.textContent = "AI анализирует файлы...";

    try {
        const res = await fetch("/upload_resumes", {
            method: "POST",
            body: formData,
        });

        if (!res.ok) {
            const errorData = await res.json();
            throw new Error(errorData.detail || "Ошибка сервера");
        }

        const data = await res.json();
        alert(`🎉 Анализ завершен!\nОбработано: ${data.processed}\nПропущено: ${data.skipped_unsupported + data.skipped_empty}`);
        
        await loadCandidates();

    } catch (e) {
        console.error("Upload error:", e);
        alert("❌ Ошибка при обработке: " + e.message);
    } finally {
        btn.disabled = false;
        loader.classList.add("hidden");
        btnText.textContent = "Начать AI-анализ";
        fileInput.value = "";
    }
}

async function loadCandidates() {
    const list = document.getElementById("candidate-list");
    const emptyState = document.getElementById("empty-state");

    try {
        const res = await fetch("/candidates");
        const data = await res.json();

        list.innerHTML = "";

        if (!data || data.length === 0) {
            emptyState.classList.remove("hidden");
            return;
        }

        emptyState.classList.add("hidden");

        data.forEach((item, index) => {
            const c = item.data || {};
            const score = item.score || 0;
            
            let scoreClasses = "text-slate-500 bg-slate-100"; 
            if (score >= 80) scoreClasses = "text-emerald-700 bg-emerald-100 border border-emerald-200";
            else if (score >= 50) scoreClasses = "text-amber-700 bg-amber-100 border border-amber-200";
            else if (score > 0) scoreClasses = "text-rose-700 bg-rose-100 border border-rose-200";

            const row = document.createElement("tr");
            row.className = "hover:bg-indigo-50/30 transition-colors animate__animated animate__fadeInUp";
            row.style.animationDelay = `${index * 0.1}s`; 

            row.innerHTML = `
                <td class="py-4 pr-4">
                    <div class="font-bold text-slate-900">${c.name || "Не указано"}</div>
                    <div class="text-xs text-slate-400 truncate max-w-[200px]" title="${c.current_position || ''}">
                        ${c.current_position || "Должность не определена"}
                    </div>
                </td>
                <td class="py-4">
                    <div class="text-sm font-semibold text-slate-700">${c.total_years_experience || 0}г. опыта</div>
                    <div class="text-[10px] uppercase font-bold text-slate-400 tracking-wider">${c.seniority_level || "-"}</div>
                </td>
                <td class="py-4 text-center">
                    <span class="inline-block px-3 py-1 rounded-full text-sm font-bold shadow-sm ${scoreClasses}">
                        ${score}%
                    </span>
                </td>
                <td class="py-4">
                    ${c.telegram_username 
                        ? `<a href="https://t.me/${c.telegram_username.replace('@', '')}" target="_blank" class="inline-flex items-center gap-1 text-indigo-600 hover:text-indigo-800 font-medium transition-colors">
                             <svg class="w-4 h-4" fill="currentColor" viewBox="0 0 24 24"><path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm4.64 6.8c-.15 1.58-.8 5.42-1.13 7.19-.14.75-.42 1-.68 1.03-.58.05-1.02-.38-1.58-.75-.88-.58-1.38-.94-2.23-1.5-.99-.65-.35-1.01.22-1.59.15-.15 2.71-2.48 2.76-2.69a.2.2 0 00-.05-.18c-.06-.05-.14-.03-.21-.02-.09.02-1.49.95-4.22 2.79-.4.27-.76.41-1.08.4-.36-.01-1.04-.2-1.55-.37-.63-.2-1.12-.31-1.08-.66.02-.18.27-.36.74-.55 2.92-1.27 4.86-2.11 5.83-2.51 2.78-1.16 3.35-1.36 3.73-1.36.08 0 .27.02.39.12.1.08.13.19.14.27-.01.06.01.24 0 .38z"/></svg>
                             @${c.telegram_username.replace('@', '')}
                           </a>` 
                        : `<span class="text-slate-300 text-xs italic italic">не найден</span>`
                    }
                </td>
            `;
            list.appendChild(row);
        });
    } catch (e) {
        console.error("LoadCandidates error:", e);
    }
}

async function startScreening() {
    const nInput = document.getElementById("n");
    const n = parseInt(nInput.value);

    if (!n || n <= 0) {
        alert("⚠️ Введите корректное число кандидатов (TOP N).");
        return;
    }

    try {
        const res = await fetch("/start_screening", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ n }),
        });

        if (res.ok) {
            const data = await res.json();
            alert(`🚀 Успех!\nБот попытался связаться с ${data.contacted_candidates.length} кадидатами.\nПропущено (без TG): ${data.skipped_no_telegram.length}`);
        } else {
            const errorData = await res.json();
            alert("❌ Ошибка рассылки: " + (errorData.detail || "Не удалось отправить сообщения."));
        }
    } catch (e) {
        console.error("Screening error:", e);
        alert("❌ Ошибка сети при попытке рассылки.");
    }
}

document.addEventListener("DOMContentLoaded", () => {
    loadCandidates();
});