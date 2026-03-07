let selectedFile = null;     
let isVacancyCreated = false; 
const dropZone = document.getElementById('drop-zone');
const fileInput = document.getElementById('file');
const zoneIdle = document.getElementById('zone-idle');
const zoneActive = document.getElementById('zone-active');
const fileNameDisplay = document.getElementById('file-name');

function handleFileSelect(file) {
    if (file && file.name.endsWith('.zip')) {
        selectedFile = file;
        fileNameDisplay.textContent = file.name;
        
        zoneIdle.classList.add('hidden');
        zoneActive.classList.remove('hidden');
        dropZone.classList.add('border-indigo-400', 'bg-indigo-50/30');
    } else if (file) {
        alert("⚠️ Пожалуйста, загрузите архив в формате .ZIP (внутри должны быть PDF или DOCX файлы)");
        clearFile();
    }
}

function clearFile(event) {
    if (event) {
        event.preventDefault();
        event.stopPropagation();
    }
    selectedFile = null;
    fileInput.value = '';
    
    zoneIdle.classList.remove('hidden');
    zoneActive.classList.add('hidden');
    dropZone.classList.remove('border-indigo-400', 'bg-indigo-50/30');
}

fileInput.addEventListener('change', (e) => handleFileSelect(e.target.files[0]));

['dragover', 'dragenter'].forEach(name => {
    dropZone.addEventListener(name, (e) => {
        e.preventDefault();
        dropZone.classList.add('border-indigo-500', 'bg-indigo-100/50');
    });
});

['dragleave', 'drop'].forEach(name => {
    dropZone.addEventListener(name, (e) => {
        e.preventDefault();
        dropZone.classList.remove('border-indigo-500', 'bg-indigo-100/50');
    });
});

dropZone.addEventListener('drop', (e) => {
    const file = e.dataTransfer.files[0];
    handleFileSelect(file);
});


async function createVacancy() {
    const title = document.getElementById("title").value.trim();
    const skills = document.getElementById("skills").value.trim();
    const seniority = document.getElementById("seniority").value;
    const description = document.getElementById("description").value.trim();

    if (!title || !skills || !description) {
        alert("⚠️ Пожалуйста, заполните название, навыки и описание вакансии.");
        return;
    }

    try {
        const res = await fetch("/create_vacancy", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ title, skills, seniority, description }),
        });

        if (res.ok) {
            isVacancyCreated = true;
            alert("✅ Вакансия успешно сохранена! Теперь вы можете загружать резюме.");
        } else {
            alert("❌ Не удалось сохранить вакансию.");
        }
    } catch (e) {
        alert("❌ Ошибка связи с сервером.");
    }
}


async function uploadResumes() {
    if (!isVacancyCreated) {
        alert("⚠️ Внимание: Сначала создайте вакансию (этап 1), чтобы AI понимал критерии отбора кандидатов!");
        return;
    }

    if (!selectedFile) {
        alert("⚠️ Пожалуйста, выберите или перетащите ZIP-файл с резюме.");
        return;
    }

    const btn = document.getElementById("btn-upload");
    const loader = document.getElementById("loader-upload");
    const btnText = btn.querySelector("span");

    btn.disabled = true;
    loader.classList.remove("hidden");
    btnText.textContent = "AI анализирует файлы...";

    const formData = new FormData();
    formData.append("file", selectedFile);

    try {
        const res = await fetch("/upload_resumes", { method: "POST", body: formData });
        
        if (!res.ok) {
            const errorData = await res.json();
            const message = errorData.detail || "Ошибка при анализе файлов";
            alert(`⚠️ Сервер сообщает: ${message}`);
            return;
        }

        const data = await res.json();
        alert(`🎉 Анализ успешно завершен!\nОбработано кандидатов: ${data.processed}`);
        
        await loadCandidates();
        clearFile();            
        
    } catch (e) {
        alert("❌ Критическая ошибка при загрузке. Проверьте соединение.");
    } finally {
        btn.disabled = false;
        loader.classList.add("hidden");
        btnText.textContent = "Начать AI-анализ";
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
            
            let scoreColor = "text-rose-600 bg-rose-50 border-rose-100";
            if (score >= 80) scoreColor = "text-emerald-700 bg-emerald-50 border-emerald-100";
            else if (score >= 50) scoreColor = "text-amber-700 bg-amber-50 border-amber-100";

            const row = document.createElement("tr");
            row.className = "hover:bg-indigo-50/40 transition-all animate__animated animate__fadeInUp";
            row.style.animationDelay = `${index * 0.1}s`;

            row.innerHTML = `
                <td class="py-4 pr-4">
                    <div class="font-bold text-slate-900 text-sm">${c.name || 'Не указано'}</div>
                    <div class="text-[11px] text-slate-400 truncate max-w-[150px]">${c.current_position || 'Должность не определена'}</div>
                </td>
                <td class="py-4">
                    <div class="text-xs font-semibold text-slate-700">${c.total_years_experience || 0}г. опыта</div>
                    <div class="text-[10px] uppercase font-bold text-slate-400">${c.seniority_level || '-'}</div>
                </td>
                <td class="py-4 text-center">
                    <span class="inline-block px-2.5 py-1 rounded-full text-xs font-bold border ${scoreColor}">
                        ${score}%
                    </span>
                </td>
                <td class="py-4">
                    ${c.telegram_username 
                        ? `<a href="https://t.me/${c.telegram_username.replace('@','')}" target="_blank" class="text-indigo-600 hover:text-indigo-800 text-sm font-medium flex items-center gap-1">
                             @${c.telegram_username.replace('@','')}
                           </a>` 
                        : `<span class="text-slate-300 text-xs italic">не найден</span>`
                    }
                </td>
            `;
            list.appendChild(row);
        });
    } catch (e) {
        console.error("Ошибка загрузки кандидатов:", e);
    }
}

async function startScreening() {
    const n = document.getElementById("n").value;

    try {
        const res = await fetch("/start_screening", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ n: parseInt(n) })
        });

        if (res.ok) {
            const data = await res.json();
            alert(`🚀 Рассылка завершена!\nСообщений отправлено: ${data.contacted_candidates.length}`);
        } else {
            alert("❌ Ошибка при попытке связаться с кандидатами.");
        }
    } catch (e) {
        alert("❌ Ошибка сети при рассылке.");
    }
}

document.addEventListener("DOMContentLoaded", loadCandidates);