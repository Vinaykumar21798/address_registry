let currentOffset = 0;
const pageLimit = 20;

document.addEventListener("DOMContentLoaded", () => {

    loadStatistics();

    loadAddresses();

    loadDuplicates();

    document
        .getElementById("uploadForm")
        .addEventListener(
            "submit",
            uploadFile
        );

    document
        .getElementById("searchForm")
        .addEventListener(
            "submit",
            performSearch
        );

    document
        .getElementById("exportBtn")
        .addEventListener(
            "click",
            exportCSV
        );

    document
        .getElementById("prevPageBtn")
        .addEventListener("click", async () => {
            if (currentOffset >= pageLimit) {
                currentOffset -= pageLimit;
                await loadAddresses();
            }
        });

    document
        .getElementById("nextPageBtn")
        .addEventListener("click", async () => {
            currentOffset += pageLimit;
            await loadAddresses();
        });

});

async function loadStatistics() {

    const response =
        await fetch(
            "/stats"
        );

    const data =
        await response.json();

    document
        .getElementById("totalDocs")
        .innerText = data.total_documents;

    document
        .getElementById("uniqueAddresses")
        .innerText = data.unique_addresses;

    document
        .getElementById("duplicateFiles")
        .innerText = data.duplicate_files_rejected;

    document
        .getElementById("duplicateAddresses")
        .innerText = data.duplicate_addresses_caught;

}

async function uploadFile(e) {

    e.preventDefault();

    const files =
        document.getElementById(
            "fileInput"
        ).files;

    if (files.length === 0) {
        alert("Select at least one PDF file");
        return;
    }

    const progressDiv =
        document.getElementById(
            "uploadProgress"
        );

    const progressBar =
        document.getElementById(
            "progressBar"
        );

    const progressText =
        document.getElementById(
            "progressText"
        );

    progressDiv.style.display = "block";

    let completed = 0;
    let failed = 0;
    let duplicates = 0;

    const uploadButton = 
        document.querySelector(
            "#uploadForm button"
        );
    
    uploadButton.disabled = true;

    for (let i = 0; i < files.length; i++) {

        const file = files[i];

        progressText.innerText = 
            `Uploading ${i + 1} of ${files.length}: ${file.name}`;

        try {

            const formData =
                new FormData();

            formData.append(
                "file",
                file
            );

            const response =
                await fetch(
                    "/upload",
                    {
                        method: "POST",
                        body: formData
                    }
                );

            const data =
                await response.json();

            if (response.status === 409) {
                duplicates++;
                progressText.innerText += 
                    ` ✗ Duplicate (ID: ${data.detail?.document_id || 'N/A'})`;
            } else if (response.ok) {
                completed++;
                progressText.innerText += 
                    ` ✓ Success`;
            } else {
                failed++;
                progressText.innerText += 
                    ` ✗ Failed: ${data.reason || 'Unknown error'}`;
            }

        } catch (error) {

            failed++;
            progressText.innerText += 
                ` ✗ Error: ${error.message}`;

        }

        const percent = 
            ((i + 1) / files.length) * 100;

        progressBar.style.width = 
            percent + "%";

    }

    uploadButton.disabled = false;

    await loadStatistics();
    await loadAddresses();
    await loadDuplicates();

    const summary = 
        `\n✓ Completed: ${completed}\n✗ Failed: ${failed}\n⚠ Duplicates: ${duplicates}`;

    alert(
        `Upload finished!${summary}`
    );

    progressDiv.style.display = "none";
    progressBar.style.width = "0%";
    progressText.innerText = "";

    document
        .getElementById("fileInput")
        .value = "";

}

async function loadAddresses() {
    const search = document.getElementById("search").value;
    const city = document.getElementById("city").value;
    const state = document.getElementById("state").value;
    const zip = document.getElementById("zip") ? document.getElementById("zip").value : "";

    let url = `/addresses?limit=${pageLimit}&offset=${currentOffset}`;
    
    if (search) url += `&search=${encodeURIComponent(search)}`;
    if (city) url += `&city=${encodeURIComponent(city)}`;
    if (state) url += `&state=${encodeURIComponent(state)}`;
    if (zip) url += `&zip_code=${encodeURIComponent(zip)}`;

    const response = await fetch(url);
    const data = await response.json();

    const table = document.getElementById("addressTable");
    table.innerHTML = "";

    if (data.data && data.data.length > 0) {
        data.data.forEach(address => {
            table.innerHTML += `
                <tr>
                    <td>${address.id}</td>
                    <td>${address.street}</td>
                    <td>${address.city}</td>
                    <td>${address.state}</td>
                    <td>${address.zip}</td>
                </tr>
            `;
        });
    } else {
        table.innerHTML = "<tr><td colspan='5' class='text-center'>No addresses found</td></tr>";
    }

    const total = data.total || 0;
    const paginationInfo = document.getElementById("paginationInfo");
    const prevBtn = document.getElementById("prevPageBtn");
    const nextBtn = document.getElementById("nextPageBtn");

    if (paginationInfo && prevBtn && nextBtn) {
        const start = total === 0 ? 0 : currentOffset + 1;
        const end = Math.min(currentOffset + pageLimit, total);
        paginationInfo.innerText = `Showing ${start} - ${end} of ${total} entries`;

        prevBtn.disabled = currentOffset === 0;
        nextBtn.disabled = currentOffset + pageLimit >= total;
    }
}

async function performSearch(e) {
    if (e) {
        e.preventDefault();
    }
    currentOffset = 0;
    await loadAddresses();
}

async function loadDuplicates() {

    const response =
        await fetch(
            "/duplicates"
        );

    const data =
        await response.json();

    const table =
        document.getElementById(
            "duplicateTable"
        );

    table.innerHTML = "";

    if (data && data.length > 0) {
        data.forEach(
            candidate => {

                table.innerHTML += `
                    <tr>
                        <td>${candidate.id}</td>
                        <td>${candidate.address1_text}</td>
                        <td>${candidate.address2_text}</td>
                        <td>${candidate.score}%</td>
                        <td>
                            <button class="btn btn-sm btn-success" onclick="resolveDuplicate(${candidate.id}, 'merge')">Merge</button>
                            <button class="btn btn-sm btn-warning" onclick="resolveDuplicate(${candidate.id}, 'not_duplicate')">Not Duplicate</button>
                        </td>
                    </tr>
                `;
            }
        );
    } else {
        table.innerHTML = "<tr><td colspan='5' class='text-center text-muted'>No duplicate candidates</td></tr>";
    }
}

async function resolveDuplicate(candidateId, action) {

    try {
        const response =
            await fetch(
                `/duplicates/${candidateId}/resolve`,
                {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json"
                    },
                    body: JSON.stringify({
                        action: action
                    })
                }
            );

        if (response.ok) {
            alert(`Duplicate ${action === 'merge' ? 'merged' : 'marked as not duplicate'} successfully`);
            await loadDuplicates();
            await loadStatistics();
        } else {
            alert("Error resolving duplicate");
        }
    } catch (error) {
        alert(`Error: ${error.message}`);
    }
}

async function exportCSV() {
    
    const search = document.getElementById("search").value;
    const city = document.getElementById("city").value;
    const state = document.getElementById("state").value;
    const zip = document.getElementById("zip") ? document.getElementById("zip").value : "";

    let url = "/export?";
    const params = [];

    if (search) params.push(`search=${encodeURIComponent(search)}`);
    if (city) params.push(`city=${encodeURIComponent(city)}`);
    if (state) params.push(`state=${encodeURIComponent(state)}`);
    if (zip) params.push(`zip_code=${encodeURIComponent(zip)}`);

    if (params.length > 0) {
        url += params.join("&");
    }

    window.location.href = url;
}