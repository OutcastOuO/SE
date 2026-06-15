# VMS 車輛管理系統 — 混沌測試實驗室

本專案將 FastAPI 車輛管理系統（VMS）打包為 Docker Compose 混沌測試環境，用於測試系統在不同故障情境下的復原能力。本版本為 **應用程式崩潰模擬版**（透過殺掉容器內 PID 1 來模擬 App 崩潰）。

---

## 1. 安裝與啟動教學

### 前置需求
- 已安裝 Docker Desktop (Windows) 或 Docker Engine + Docker Compose v2 (Linux/Ubuntu)
- 至少 4 GB RAM

### 啟動步驟
1. **複製環境設定檔**：
   - **Windows (PowerShell)**:
     ```powershell
     copy .env.example .env
     ```
   - **Linux/Ubuntu**:
     ```bash
     cp .env.example .env
     ```

2. **啟動容器堆疊**：
   ```bash
   docker compose up -d --build
   ```

3. **執行冒煙測試**（確認服務正常）：
   - **Windows (PowerShell)**:
     ```powershell
     .\scripts\smoke-test.ps1
     ```
   - **Linux/Ubuntu**:
     ```bash
     chmod +x ./scripts/*.sh
     ./scripts/smoke-test.sh
     ```

---

## 2. Chaos GUI 使用教學

本專案提供網頁版的 Chaos GUI 控制面板，方便一鍵啟動流量並注入故障。

### 啟動 Chaos GUI
在終端機執行以下指令啟動 GUI 服務：
- **Linux/Ubuntu**:
  ```bash
  ./scripts/start-chaos-gui.sh
  ```
  *(若在遠端 VM 執行，請使用 `HOST=0.0.0.0 ./scripts/start-chaos-gui.sh`)*

- **Windows (PowerShell)**:
  若要直接在本機執行 Python GUI（需先執行 `pip install -r requirements.txt`）：
  ```powershell
  python chaos_gui.py
  ```

### GUI 操作步驟
開啟瀏覽器進入 `http://localhost:8080`，即可使用以下按鈕：
1. **Start Load**：開始向 API 發送持續流量（模擬真實使用者請求）。
2. **Run (實驗選擇區)**：下拉選單選擇故障實驗（`kill` / `restart` / `stop` / `pause` / `delay`），點擊 **Run** 開始注入故障。
3. **Stop Load**：停止發送流量。

---

## 3. 觀察實驗結果

當您透過 GUI 注入故障時，可透過以下管道觀察系統的表現與自動恢復過程：

### A. Grafana 監控儀表板
- **網址**：`http://localhost:3000/d/vms-chaos/vms-chaos-testing`（預設帳密：`admin` / `admin`）
- **觀察指標**：
  - **Request Rate**：注入故障期間，每秒請求數是否歸零。
  - **Availability**：可用性百分比的波動。
  - **API Uptime**：容器因 `kill` 或 `restart` 重啟後，運行時間是否歸零重計。

### B. Prometheus 告警與指標
- **網址**：`http://localhost:9090`
- **常用查詢 (PromQL)**：
  - `up{job="vms-api"}`：確認 API 容器是否存活（1 為存活，0 為異常）。
  - `vms_app_uptime_seconds`：應用程式運作時間。
- **告警狀態**：可切換至 "Alerts" 頁面，觀察當 API 停止時，`VmsApiDown` 告警是否觸發。

### C. Portainer 容器狀態
- **網址**：`http://localhost:9000`
- **觀察重點**：
  - 當點擊 `kill` 實驗時，`vms-api` 容器的狀態應短暫變為重啟中，隨後自動恢復為 `running`（得益於 Docker 的重啟策略 `restart: unless-stopped`）。

---

## 4. 清除環境

測試完畢後，若要停止容器並清除所有監控數據：
```bash
docker compose down -v
```
