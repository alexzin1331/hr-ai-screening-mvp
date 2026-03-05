<h1>HR AI Screening</h1>

<h2>Create vacancy</h2>

<input id="title" placeholder="Vacancy title">

<input id="skills" placeholder="Skills (comma separated)">

<input id="seniority" placeholder="Seniority">

<textarea id="description" placeholder="Job description"></textarea>

<br><br>

<button onclick="createVacancy()">Create vacancy</button>

<hr>

<h2>Upload resumes</h2>

<input type="file" id="file">

<button onclick="uploadResumes()">Upload ZIP</button>

<hr>

<h2>Start screening</h2>

<input id="n" placeholder="Number of candidates">

<button onclick="startScreening()">Contact candidates</button>

<hr>

<h2>Candidates</h2>

<table border="1" id="table"></table>

<script src="app.js"></script>