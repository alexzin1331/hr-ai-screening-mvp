// Utility Functions
function showNotification(message, type = 'info') {
    const notification = document.createElement('div');
    notification.className = `notification ${type}`;

    const icon = type === 'success' ? 'check-circle' :
                 type === 'error' ? 'exclamation-circle' : 'info-circle';

    notification.innerHTML = `
        <i class="fas fa-${icon}"></i>
        <span>${message}</span>
    `;

    document.body.appendChild(notification);

    setTimeout(() => {
        notification.remove();
    }, 5000);
}

function setLoading(buttonId, isLoading) {
    const btn = document.getElementById(buttonId);
    if (isLoading) {
        btn.disabled = true;
        btn.innerHTML = '<span class="loading"></span> Processing...';
    } else {
        btn.disabled = false;
        // Restore original button text based on ID
        const originalTexts = {
            'btnCreateVacancy': '<i class="fas fa-plus"></i> Create Vacancy',
            'btnUpload': '<i class="fas fa-upload"></i> Upload & Process',
            'btnScreening': '<i class="fas fa-rocket"></i> Contact Candidates via Telegram'
        };
        btn.innerHTML = originalTexts[buttonId] || 'Submit';
    }
}

function updateFileName() {
    const fileInput = document.getElementById('file');
    const fileName = document.getElementById('fileName');
    if (fileInput.files.length > 0) {
        const file = fileInput.files[0];
        fileName.innerHTML = `<i class="fas fa-file-archive"></i> ${file.name} (${(file.size / 1024 / 1024).toFixed(2)} MB)`;
    } else {
        fileName.innerHTML = '';
    }
}

function updateStats() {
    // Update statistics
    const tableBody = document.getElementById('tableBody');
    const rows = tableBody.querySelectorAll('tr');
    const candidateCount = rows.length > 1 ? rows.length - 1 : 0;

    document.getElementById('statCandidates').textContent = candidateCount;

    // Calculate average score
    if (candidateCount > 0) {
        let totalScore = 0;
        let scoreCount = 0;
        rows.forEach((row, index) => {
            if (index === 0) return; // Skip header
            const scoreCell = row.cells[1];
            if (scoreCell && scoreCell.textContent) {
                const score = parseInt(scoreCell.textContent);
                if (!isNaN(score)) {
                    totalScore += score;
                    scoreCount++;
                }
            }
        });

        if (scoreCount > 0) {
            const avgScore = Math.round(totalScore / scoreCount);
            document.getElementById('statAvgScore').textContent = avgScore;
        }
    }
}

// Main Functions
async function createVacancy() {
    const title = document.getElementById("title").value.trim();
    const skills = document.getElementById("skills").value.trim();
    const seniority = document.getElementById("seniority").value.trim();
    const description = document.getElementById("description").value.trim();

    if (!title || !skills || !seniority || !description) {
        showNotification("Please fill in all required fields", "error");
        return;
    }

    const payload = { title, skills, seniority, description };

    try {
        setLoading('btnCreateVacancy', true);
        console.log("createVacancy: sending payload", payload);

        const res = await fetch("/create_vacancy", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload),
        });

        const data = await res.json();
        console.log("createVacancy: response", data);

        if (!res.ok) {
            throw new Error(data.detail || "Failed to create vacancy");
        }

        showNotification("Vacancy created successfully!", "success");
        document.getElementById('statVacancy').textContent = '✓';

        // Clear form
        document.getElementById("title").value = '';
        document.getElementById("skills").value = '';
        document.getElementById("seniority").value = '';
        document.getElementById("description").value = '';

    } catch (e) {
        console.error("createVacancy error", e);
        showNotification(e.message || "Network error. Check console.", "error");
    } finally {
        setLoading('btnCreateVacancy', false);
    }
}

async function uploadResumes() {
    const fileInput = document.getElementById('file');
    const file = fileInput.files[0];

    if (!file) {
        showNotification("Please select a ZIP file", "error");
        return;
    }

    if (!file.name.endsWith('.zip')) {
        showNotification("Please select a ZIP file", "error");
        return;
    }

    const formData = new FormData();
    formData.append("file", file);

    try {
        setLoading('btnUpload', true);
        console.log("uploadResumes: uploading file", file.name, file.size);

        const res = await fetch("/upload_resumes", {
            method: "POST",
            body: formData,
        });

        const data = await res.json();
        console.log("uploadResumes: response", data);

        if (!res.ok) {
            throw new Error(data.detail || "Failed to upload resumes");
        }

        let message = `✓ Resumes processed successfully!\n`;
        message += `Parsed: ${data.parsed}\n`;
        message += `Processed: ${data.processed}\n`;

        if (data.skipped_unsupported > 0) {
            message += `Skipped (format): ${data.skipped_unsupported}\n`;
        }
        if (data.skipped_empty > 0) {
            message += `Skipped (empty): ${data.skipped_empty}`;
        }

        showNotification(message.replace(/\n/g, ' | '), "success");

        await loadCandidates();

        // Clear file input
        fileInput.value = '';
        updateFileName();

    } catch (e) {
        console.error("uploadResumes error", e);
        showNotification(e.message || "Network error. Check console.", "error");
    } finally {
        setLoading('btnUpload', false);
    }
}

async function startScreening() {
    const nValue = document.getElementById("n").value.trim();
    const n = parseInt(nValue, 10);

    if (!n || isNaN(n) || n <= 0) {
        showNotification("Please enter a positive number", "error");
        return;
    }

    const payload = { n };

    try {
        setLoading('btnScreening', true);
        console.log("startScreening: sending payload", payload);

        const res = await fetch("/start_screening", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload),
        });

        const data = await res.json();
        console.log("startScreening: response", data);

        if (!res.ok) {
            throw new Error(data.detail || "Failed to start screening");
        }

        let message = `✓ Screening started!\n`;
        message += `Contacted: ${data.contacted_candidates.length}\n`;
        message += `Skipped (no Telegram): ${data.skipped_no_telegram.length}`;

        showNotification(message.replace(/\n/g, ' | '), "success");

        await loadCandidates();

    } catch (e) {
        console.error("startScreening error", e);
        showNotification(e.message || "Network error. Check console.", "error");
    } finally {
        setLoading('btnScreening', false);
    }
}

async function loadCandidates() {
    try {
        console.log("loadCandidates: fetching /candidates");

        const res = await fetch("/candidates");
        const data = await res.json();
        console.log("loadCandidates: response", data);

        const tableBody = document.getElementById("tableBody");
        tableBody.innerHTML = "";

        if (!Array.isArray(data) || data.length === 0) {
            tableBody.innerHTML = `
                <tr>
                    <td colspan="7" class="empty-state">
                        <i class="fas fa-inbox"></i>
                        <div>No candidates yet. Upload resumes to get started.</div>
                    </td>
                </tr>
            `;
            updateStats();
            return;
        }

        data.forEach((item) => {
            const candidate = item.data || {};
            const score = item.score || 0;

            const tr = document.createElement("tr");

            // Determine score class
            let scoreClass = 'score-low';
            if (score >= 70) scoreClass = 'score-high';
            else if (score >= 50) scoreClass = 'score-medium';

            tr.innerHTML = `
                <td><strong>${candidate.name || 'N/A'}</strong></td>
                <td><span class="score-badge ${scoreClass}">${score}</span></td>
                <td>${candidate.telegram_username ? '@' + candidate.telegram_username : '<span style="color: #a0aec0">-</span>'}</td>
                <td>${candidate.seniority_level || 'N/A'}</td>
                <td>${candidate.total_years_experience || 'N/A'}</td>
                <td>${candidate.english_level || 'N/A'}</td>
                <td>${candidate.salary_expectation || 'N/A'}</td>
            `;

            tableBody.appendChild(tr);
        });

        updateStats();

    } catch (e) {
        console.error("loadCandidates error", e);
    }
}

// Auto-load candidates on page load
document.addEventListener("DOMContentLoaded", () => {
    loadCandidates();

    // Check health status
    fetch("/health")
        .then(res => res.json())
        .then(data => {
            if (data.vacancy_created) {
                document.getElementById('statVacancy').textContent = '✓';
            }
        })
        .catch(err => console.error("Health check failed", err));
});