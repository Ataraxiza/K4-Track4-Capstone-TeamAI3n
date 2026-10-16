const $ = (id) => document.getElementById(id);
const ui = {
  stage: $("stage"), video: $("sourceVideo"), mode: $("modeBadge"), source: $("sourceLabel"),
  connection: $("connectionText"), live: $("liveTag"), fps: $("fpsText"),
  card: $("statusCard"), name: $("statusName"), desc: $("statusDesc"),
  left: $("earLeft"), right: $("earRight"), duration: $("closedDuration"),
  camera: $("cameraBtn"), videoButton: $("videoBtn"), file: $("videoFile"), stop: $("stopSourceBtn"),
  record: $("recordBtn"), stopRecord: $("stopRecordBtn"), download: $("downloadLink"),
  form: $("configForm"), cooldown: $("cooldownInput"), mockPanel: $("mockPanel"), message: $("message"),
};
const ctx = ui.stage.getContext("2d");

let mode = "mock";
let sourceKind = null;
let cameraStream = null;
let videoUrl = null;
let requestPending = false;
let lastRequestAt = 0;
let previousDrawAt = 0;
let processingFps = 0;
let generation = 0;
let mockStatus = "NORMAL";
let result = null;
let recorder = null;
let recordedChunks = [];
let recordingUrl = null;
let audioContext = null;
let audioDestination = null;
let activeGain = null;
let activeOscillators = [];
let soundBusyUntil = 0;
let lastAlertTimestamp = null;

const descriptions = {
  NORMAL: "Mắt mở. Không phát cảnh báo.",
  EYES_CLOSED: "Mắt đang nhắm; chưa đủ thời gian cảnh báo.",
  DROWSY: "Nhắm mắt kéo dài. Cảnh báo đang hoạt động.",
  NO_FACE: "Không nhận diện được khuôn mặt hoặc EAR không hợp lệ.",
};

function message(text, error = false) {
  ui.message.textContent = text;
  ui.message.classList.toggle("error", error);
}

function updateResult(data) {
  result = data;
  ui.card.dataset.status = data.status;
  ui.name.textContent = data.status;
  ui.desc.textContent = descriptions[data.status] || "Trạng thái không xác định.";
  ui.left.textContent = data.ear_left == null ? "—" : Number(data.ear_left).toFixed(3);
  ui.right.textContent = data.ear_right == null ? "—" : Number(data.ear_right).toFixed(3);
  ui.duration.textContent = `${Number(data.closed_duration).toFixed(2)} s`;
  if (data.should_alert) playAlarm(data.timestamp);
  else stopAlarm();
}

function ensureAudio() {
  if (!audioContext) {
    const AudioContextClass = window.AudioContext || window.webkitAudioContext;
    if (!AudioContextClass) return;
    audioContext = new AudioContextClass();
    audioDestination = audioContext.createMediaStreamDestination();
  }
  audioContext.resume().catch(() => message("Trình duyệt chưa cho phép phát âm thanh.", true));
}

function stopAlarm() {
  if (!audioContext || !activeGain) return;
  try {
    activeGain.gain.cancelScheduledValues(audioContext.currentTime);
    activeGain.gain.setValueAtTime(0, audioContext.currentTime);
    for (const oscillator of activeOscillators) oscillator.stop(audioContext.currentTime);
  } catch (_) { /* A short beep may already have finished. */ }
  activeOscillators = [];
  activeGain = null;
  soundBusyUntil = 0;
}

function playAlarm(timestamp) {
  if (!audioContext || audioContext.state !== "running") return;
  const cooldown = Number(ui.cooldown.value) || 0;
  if (audioContext.currentTime < soundBusyUntil) return;
  if (lastAlertTimestamp !== null && timestamp - lastAlertTimestamp < cooldown) return;
  const now = audioContext.currentTime;
  const gain = audioContext.createGain();
  gain.gain.value = 0.16;
  gain.connect(audioContext.destination);
  gain.connect(audioDestination);
  activeGain = gain;
  activeOscillators = [];
  for (const offset of [0, 0.26]) {
    const oscillator = audioContext.createOscillator();
    oscillator.type = "sine";
    oscillator.frequency.value = 740;
    oscillator.connect(gain);
    oscillator.start(now + offset);
    oscillator.stop(now + offset + 0.18);
    activeOscillators.push(oscillator);
  }
  soundBusyUntil = now + 0.44;
  lastAlertTimestamp = timestamp;
}

async function resetSession() {
  generation += 1;
  result = null;
  lastAlertTimestamp = null;
  stopAlarm();
  try { await fetch("/api/reset", {method: "POST"}); }
  catch (_) { message("Không kết nối được Python server.", true); }
}

function stopSource() {
  if (recorder && recorder.state === "recording") recorder.stop();
  if (cameraStream) cameraStream.getTracks().forEach((track) => track.stop());
  cameraStream = null;
  ui.video.pause();
  ui.video.srcObject = null;
  ui.video.removeAttribute("src");
  ui.video.load();
  if (videoUrl) URL.revokeObjectURL(videoUrl);
  videoUrl = null;
  sourceKind = null;
  mockStatus = "NORMAL";
  document.querySelectorAll("[data-mock]").forEach((button) => button.classList.toggle("active", button.dataset.mock === "NORMAL"));
  ui.source.textContent = "Chưa chọn nguồn";
  ui.connection.textContent = "Chọn nguồn để bắt đầu.";
  ui.live.textContent = "CHỜ NGUỒN";
  ui.stop.disabled = true;
  ui.record.disabled = true;
  ui.stopRecord.disabled = true;
  ui.card.dataset.status = "NO_FACE";
  ui.name.textContent = "CHƯA CÓ NGUỒN";
  ui.desc.textContent = "Mở webcam hoặc chọn video để xem demo.";
  ui.left.textContent = "—";
  ui.right.textContent = "—";
  ui.duration.textContent = "0.00 s";
  resetSession();
}

async function startCamera() {
  stopSource();
  ensureAudio();
  if (!navigator.mediaDevices?.getUserMedia) {
    message("Trình duyệt không hỗ trợ webcam trên trang này.", true);
    return;
  }
  try {
    cameraStream = await navigator.mediaDevices.getUserMedia({video: {width: 1280, height: 720}, audio: false});
    ui.video.srcObject = cameraStream;
    await ui.video.play();
    sourceKind = "camera";
    ui.source.textContent = "Webcam trực tiếp";
    ui.connection.textContent = "Webcam đang chạy trên máy này.";
    ui.live.textContent = "LIVE · WEBCAM";
    ui.stop.disabled = false;
    ui.record.disabled = false;
    message("Webcam sẵn sàng. Bạn có thể bắt đầu quay.");
  } catch (error) {
    stopSource();
    message(`Không mở được webcam: ${error.message}`, true);
  }
}

async function startVideo(file) {
  if (!file) return;
  stopSource();
  ensureAudio();
  videoUrl = URL.createObjectURL(file);
  ui.video.src = videoUrl;
  try {
    await ui.video.play();
    sourceKind = "video";
    ui.source.textContent = file.name;
    ui.connection.textContent = "Video dùng thời gian nội dung của file.";
    ui.live.textContent = "VIDEO · FILE";
    ui.stop.disabled = false;
    ui.record.disabled = false;
    message("Video sẵn sàng. Bạn có thể bắt đầu quay.");
  } catch (error) {
    stopSource();
    message(`Không mở được video: ${error.message}`, true);
  } finally {
    ui.file.value = "";
  }
}

function sourceTimestamp() {
  return sourceKind === "video" ? ui.video.currentTime : performance.now() / 1000;
}

async function analyzeFrame() {
  if (!sourceKind || requestPending || ui.video.readyState < 2 || ui.video.paused) return;
  requestPending = true;
  const requestGeneration = generation;
  const payload = new FormData();
  payload.append("timestamp", String(sourceTimestamp()));
  payload.append("mock_status", mockStatus);
  try {
    const response = await fetch("/api/analyze", {method: "POST", body: payload});
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || `HTTP ${response.status}`);
    if (requestGeneration === generation) updateResult(data);
  } catch (error) {
    message(`Phân tích frame lỗi: ${error.message}`, true);
  } finally {
    requestPending = false;
  }
}

function drawFrame(now) {
  ctx.fillStyle = "#071018";
  ctx.fillRect(0, 0, ui.stage.width, ui.stage.height);
  if (sourceKind && ui.video.readyState >= 2) {
    const sourceWidth = ui.video.videoWidth || 960;
    const sourceHeight = ui.video.videoHeight || 540;
    const scale = Math.min(ui.stage.width / sourceWidth, ui.stage.height / sourceHeight);
    const width = sourceWidth * scale;
    const height = sourceHeight * scale;
    const x = (ui.stage.width - width) / 2;
    const y = (ui.stage.height - height) / 2;
    ctx.save();
    if (sourceKind === "camera") {
      ctx.translate(ui.stage.width, 0);
      ctx.scale(-1, 1);
      ctx.drawImage(ui.video, x, y, width, height);
    } else ctx.drawImage(ui.video, x, y, width, height);
    ctx.restore();
  } else {
    ctx.strokeStyle = "#324755";
    ctx.lineWidth = 2;
    ctx.strokeRect(64, 58, ui.stage.width - 128, ui.stage.height - 116);
    ctx.fillStyle = "#a7bbc6";
    ctx.font = "600 26px Segoe UI, sans-serif";
    ctx.textAlign = "center";
    ctx.fillText("Chọn webcam hoặc video để bắt đầu", ui.stage.width / 2, ui.stage.height / 2);
    ctx.textAlign = "left";
  }
  if (result && sourceKind) {
    const color = result.status === "DROWSY" ? "#ff6573" : result.status === "NORMAL" ? "#dcfa69" : "#ffc76e";
    ctx.fillStyle = "#071018df";
    ctx.fillRect(0, ui.stage.height - 94, ui.stage.width, 94);
    ctx.fillStyle = color;
    ctx.fillRect(0, ui.stage.height - 94, 5, 94);
    ctx.font = "800 27px Segoe UI, sans-serif";
    ctx.fillText(result.status, 24, ui.stage.height - 53);
    ctx.fillStyle = "#eef5f8";
    ctx.font = "17px Segoe UI, sans-serif";
    ctx.fillText(`EAR: ${result.ear_left == null ? "—" : Number(result.ear_left).toFixed(3)} / ${result.ear_right == null ? "—" : Number(result.ear_right).toFixed(3)}`, 24, ui.stage.height - 23);
    ctx.textAlign = "right";
    ctx.fillText(`Nhắm: ${Number(result.closed_duration).toFixed(2)} s`, ui.stage.width - 22, ui.stage.height - 23);
    ctx.textAlign = "left";
  }
  if (previousDrawAt && now > previousDrawAt) {
    const currentFps = 1000 / (now - previousDrawAt);
    processingFps = processingFps ? processingFps * 0.85 + currentFps * 0.15 : currentFps;
    ui.fps.textContent = `${processingFps.toFixed(1)} FPS hiển thị`;
  }
  previousDrawAt = now;
  if (sourceKind && now - lastRequestAt > 140) {
    lastRequestAt = now;
    analyzeFrame();
  }
  requestAnimationFrame(drawFrame);
}

function startRecording() {
  if (!sourceKind || !ui.stage.captureStream || !window.MediaRecorder) {
    message("Trình duyệt không hỗ trợ ghi canvas bằng MediaRecorder.", true);
    return;
  }
  ensureAudio();
  if (recordingUrl) URL.revokeObjectURL(recordingUrl);
  ui.download.hidden = true;
  const stream = ui.stage.captureStream(30);
  if (audioDestination) {
    const audioTrack = audioDestination.stream.getAudioTracks()[0];
    if (audioTrack) stream.addTrack(audioTrack);
  }
  const candidates = ["video/webm;codecs=vp9,opus", "video/webm;codecs=vp8,opus", "video/webm"];
  const mimeType = candidates.find((candidate) => MediaRecorder.isTypeSupported(candidate));
  try {
    recorder = new MediaRecorder(stream, mimeType ? {mimeType} : undefined);
    recordedChunks = [];
    recorder.ondataavailable = (event) => { if (event.data.size) recordedChunks.push(event.data); };
    recorder.onstop = () => {
      const blob = new Blob(recordedChunks, {type: recorder.mimeType || "video/webm"});
      recordingUrl = URL.createObjectURL(blob);
      ui.download.href = recordingUrl;
      ui.download.download = `demo-buon-ngu-${new Date().toISOString().replaceAll(":", "-")}.webm`;
      ui.download.hidden = false;
      ui.stopRecord.disabled = true;
      ui.record.disabled = !sourceKind;
      ui.live.classList.remove("recording");
      ui.live.textContent = sourceKind === "camera" ? "LIVE · WEBCAM" : sourceKind === "video" ? "VIDEO · FILE" : "CHỜ NGUỒN";
      message(`Đã ghi ${Math.max(1, Math.round(blob.size / 1024))} KB. Nhấn tải video.`);
      stream.getTracks().forEach((track) => { if (track !== audioDestination?.stream.getAudioTracks()[0]) track.stop(); });
    };
    recorder.start(1000);
    ui.record.disabled = true;
    ui.stopRecord.disabled = false;
    ui.live.classList.add("recording");
    ui.live.textContent = "● ĐANG QUAY";
    message("Đang quay. Nhấn Dừng quay để tải video.");
  } catch (error) {
    message(`Không bắt đầu quay được: ${error.message}`, true);
  }
}

async function saveConfig(event) {
  event.preventDefault();
  const settings = Object.fromEntries(new FormData(ui.form).entries());
  try {
    const response = await fetch("/api/config", {method: "POST", headers: {"Content-Type": "application/json"}, body: JSON.stringify(settings)});
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || `HTTP ${response.status}`);
    await resetSession();
    message("Đã lưu cấu hình mock và reset trạng thái. Chỉ cooldown ảnh hưởng âm báo.");
  } catch (error) { message(`Cấu hình lỗi: ${error.message}`, true); }
}

async function initialize() {
  try {
    const response = await fetch("/api/health");
    const data = await response.json();
    mode = data.mode;
    ui.mode.textContent = mode === "mock" ? "MÔ PHỎNG · CHƯA NHẬN DIỆN" : "NHẬN DIỆN THẬT";
    ui.mockPanel.hidden = mode !== "mock";
    for (const [key, value] of Object.entries(data.settings)) ui.form.elements.namedItem(key).value = value;
    message(mode === "mock" ? "Đang ở chế độ mô phỏng. Mở nguồn rồi chọn trạng thái để thử." : "Backend A/B sẵn sàng. Mở nguồn để bắt đầu.");
  } catch (error) { message(`Không kết nối được localhost: ${error.message}`, true); }
  requestAnimationFrame(drawFrame);
}

ui.camera.addEventListener("click", startCamera);
ui.videoButton.addEventListener("click", () => ui.file.click());
ui.file.addEventListener("change", () => startVideo(ui.file.files[0]));
ui.stop.addEventListener("click", stopSource);
ui.record.addEventListener("click", startRecording);
ui.stopRecord.addEventListener("click", () => { if (recorder?.state === "recording") recorder.stop(); });
ui.form.addEventListener("submit", saveConfig);
document.querySelectorAll("[data-mock]").forEach((button) => button.addEventListener("click", async () => {
  ensureAudio();
  mockStatus = button.dataset.mock;
  document.querySelectorAll("[data-mock]").forEach((item) => item.classList.toggle("active", item === button));
  if (sourceKind) analyzeFrame();
  else {
    const payload = new FormData();
    payload.append("timestamp", String(performance.now() / 1000));
    payload.append("mock_status", mockStatus);
    try {
      const response = await fetch("/api/analyze", {method: "POST", body: payload});
      if (response.ok) updateResult(await response.json());
    } catch (_) { message("Không kết nối được Python server.", true); }
  }
}));
ui.video.addEventListener("ended", () => { ui.live.textContent = "VIDEO · ĐÃ HẾT"; message("Video đã hết. Bạn có thể dừng quay để tải bản ghi."); });
initialize();
