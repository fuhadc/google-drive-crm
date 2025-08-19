const fileInput = document.getElementById('imageInput');
const previewContainer = document.getElementById('previewContainer');
const uploadForm = document.getElementById('uploadForm');
const progressBar = document.getElementById('uploadProgress');
const dialog = document.getElementById('imageDialog');
const uploadButtonInDialog = document.getElementById('uploadBtnInDialog');
const uploadInfo = document.getElementById('uploadInfo');

// Open Modal
function openDialog() {
  dialog.style.display = 'block';
}

// Close Modal
function closeDialog() {
  dialog.style.display = 'none';
  progressBar.value = 0;
  uploadInfo.textContent = "Waiting to upload...";
}

// Snackbar
function showSnackbar() {
  const snackbar = document.getElementById("snackbar");
  snackbar.className = "show";
  setTimeout(() => snackbar.className = snackbar.className.replace("show", ""), 3000);
}

// When files are selected
fileInput.addEventListener('change', function () {
  previewContainer.innerHTML = '';
  openDialog();

  for (const file of this.files) {
    const reader = new FileReader();
    reader.onload = function (e) {
      const div = document.createElement('div');
      const img = document.createElement('img');
      const name = document.createElement('p');

      img.src = e.target.result;
      name.textContent = file.name;
      name.style.fontSize = '12px';
      name.style.wordBreak = 'break-word';

      div.appendChild(img);
      div.appendChild(name);
      previewContainer.appendChild(div);
    };
    reader.readAsDataURL(file);
  }
});

// Upload via AJAX
uploadButtonInDialog.addEventListener('click', function () {
  const formData = new FormData(uploadForm);
  const totalFiles = fileInput.files.length;
  const xhr = new XMLHttpRequest();

  xhr.open("POST", uploadForm.action, true);
  progressBar.value = 0;
  progressBar.style.display = 'block';
  uploadInfo.textContent = `Uploading 0 of ${totalFiles} images...`;

  xhr.upload.onprogress = function (e) {
    if (e.lengthComputable) {
      const percent = Math.round((e.loaded / e.total) * 100);
      progressBar.value = percent;

      const approxFilesUploaded = Math.round((totalFiles * percent) / 100);
      uploadInfo.textContent = `Uploading ${approxFilesUploaded} of ${totalFiles} images...`;
    }
  };

  xhr.onload = function () {
    if (xhr.status === 200 || xhr.status === 302) {
      progressBar.value = 100;
      uploadInfo.textContent = `Uploaded ${totalFiles} of ${totalFiles} images.`;
      showSnackbar();
      closeDialog();
      setTimeout(() => window.location.href = "/dashboard", 1500);
    } else {
      alert("Upload failed. Please try again.");
      closeDialog();
    }
  };

  xhr.send(formData);
});
