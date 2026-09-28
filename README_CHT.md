# DL24 生產線自動化測試工具

## 1. 專案目的

本工具以 Python Tkinter 建立 DL24 電子負載測試介面，透過串列埠控制 Atorch DL24，執行 PCBA 電源輸出與保護功能測試。

主要目標如下：

- 連線並控制 DL24 電子負載。
- 支援 PCBA S/N、JIG ID 與測試模式等資料追蹤。
- 以圖形介面即時顯示測試中的電壓、電流、測試步驟與結果。
- 將每個測試步驟及最終結果寫入 CSV，供生產追溯與後續分析。
- 將測試條件放在 `test_config.json`，讓測試規格可以獨立調整。

## 2. 主要檔案

| 檔案 | 說明 |
| --- | --- |
| `dl24_autotest_02.py` | 主程式，提供 GUI、測試流程、DL24 控制與結果判定。 |
| `test_config.json` | 測試參數與判定門檻設定檔。 |
| `dl24_lib/` | DL24 通訊控制模組，至少需要包含 `__init__.py`。 |
| `production_test_datalog.csv` | 測試結果紀錄檔，程式會以附加方式寫入。 |

備份或移植專案時，應保留主程式、`test_config.json`、`dl24_lib/` 以及既有的 CSV 紀錄。只複製主程式可能造成通訊模組或測試條件遺失。

## 3. 測試模式

### 3.1 FA Direct Mode

此模式適合單一負載條件的直接測試。使用者可以在介面中輸入：

- `Current (A)`：目標負載電流。
- `Duration (Sec)`：負載持續時間。
- `Vmin (V)`：允許的最低輸出電壓。
- `Vmax (V)`：允許的最高輸出電壓。

執行流程：

1. 設定 DL24 負載電流並開啟輸出。
2. 維持設定時間。
3. 讀取測試結束時的電壓與電流。
4. 當 `Vmin <= 測量電壓 <= Vmax` 時判定為 `PASS`，否則為 `FAIL`。
5. 關閉 DL24 並寫入測試紀錄。

FA 模式會將 JIG ID 自動設為 `DIRECT_NO_JIG`，不需要輸入治具編號。

### 3.2 SKYFALL JIG Mode

此模式用於搭配治具逐一測試連接埠 `TBTB`、`TBTC`、`TBTD`。

每個連接埠的測試流程如下：

1. 在 0 A 狀態讀取空載電壓 `V_idle`。
2. 依設定執行固定電流步階，預設為 `1.5 A`、`2.5 A`、`3.0 A`。
3. 在 3.0 A 時依照設定的電壓門檻判定 `PASS`、`BORDERLINE` 或 `FAIL`。
4. 執行動態 OCP 電流爬升，預設從 `3.5 A` 開始，逐步增加至 `4.0 A`。
5. 當輸出電壓降至 OCP 觸發門檻以下時，判定 eFuse 已觸發。
6. 關閉負載，提示使用者重新插拔 Type-C 端子，使 eFuse 復歸。
7. 讀取復歸電壓；達到 `RECOVERY_MIN_VOLT` 時判定復歸成功。
8. 將該連接埠的測試結果寫入 CSV。

選擇所有連接埠時，每測試完一個連接埠，程式會提示使用者將測試線移至下一個連接埠。

## 4. `test_config.json` 的用途

`test_config.json` 是外部測試設定檔，用來保存測試電流、等待時間、電壓門檻與 OCP 條件。程式啟動時會從主程式所在資料夾讀取這個檔案。

使用設定檔的原因：

- 不必為了調整產品規格而修改 Python 程式碼。
- 不同產品或治具可以使用不同的測試門檻。
- 測試條件集中管理，方便審查、備份與版本追蹤。
- 可降低直接修改測試流程程式碼而造成其他功能異常的風險。
- 備份設定檔即可保留當時實際使用的測試規格，避免日後只剩程式卻無法重現測試條件。

若 `test_config.json` 不存在，程式會依照內建的 `DEFAULT_CONFIG` 自動建立一份預設設定檔。若 JSON 格式無法讀取，程式會暫時使用內建預設值；正式測試前仍應修正設定檔格式，並確認實際門檻符合產品規格。

### 4.1 設定欄位說明

#### `SKYFALL_JIG_MODE`

| 欄位 | 說明 |
| --- | --- |
| `STEPS` | 固定電流測試步階，單位為 A。 |
| `STEP_DURATION_SEC` | 每個固定電流步階的持續秒數。 |
| `V3_0A_PASS_MIN` | 3.0 A 測試判定為 PASS 的最低電壓。 |
| `V3_0A_BORDERLINE_MIN` | 3.0 A 測試判定為 BORDERLINE 的最低電壓。低於此值為 FAIL。 |
| `OCP_START_CURRENT` | OCP 測試的起始電流，單位為 A。 |
| `OCP_MAX_CURRENT` | OCP 測試允許爬升到的最大電流，單位為 A。 |
| `OCP_STEP_CURRENT` | OCP 每次增加的電流，單位為 A。 |
| `OCP_TRIP_MAX_VOLT` | 判定 eFuse 觸發的最高電壓，單位為 V。 |
| `RECOVERY_MIN_VOLT` | eFuse 復歸成功所需的最低電壓，單位為 V。 |

#### `FA_DIRECT_MODE`

| 欄位 | 說明 |
| --- | --- |
| `DEFAULT_CURRENT` | FA 模式介面預設電流，單位為 A。 |
| `DEFAULT_DURATION` | FA 模式介面預設測試時間，單位為秒。 |
| `DEFAULT_VMIN` | FA 模式介面預設最低允許電壓，單位為 V。 |
| `DEFAULT_VMAX` | FA 模式介面預設最高允許電壓，單位為 V。 |

### 4.2 修改設定檔注意事項

- 檔案必須是合法 JSON，字串使用雙引號。
- 欄位名稱必須與程式預期名稱完全一致。
- 電流、電壓與時間應使用數值，不要加入單位文字，例如使用 `4.75`，不要使用 `"4.75V"`。
- 修改後重新啟動程式才會載入新設定。
- 變更判定門檻前，應確認產品規格與測試安全條件。

## 5. 安裝環境

建議使用 Python 3.9 以上版本。此工具使用 Python 標準函式庫中的 Tkinter、threading、csv、json 與 os，另外需要安裝 `pyserial` 以進行串列埠通訊。

在 Windows PowerShell 執行：

```powershell
python -m pip install pyserial
```

確認 DL24 使用的 COM Port，例如 `COM3`，以及正確的 Baud Rate。程式目前預設使用 `COM3` 與 `9600`，但仍應依實際設備設定確認。

## 6. 啟動方式

請在專案資料夾中執行：

```powershell
python .\dl24_autotest_02.py
```

啟動後的基本操作：

1. 確認 DL24 已連接電腦並開機。
2. 輸入正確的 COM Port 與 Baud Rate。
3. 選擇 `FA Direct Mode` 或 `SKYFALL JIG Mode`。
4. 輸入 PCBA S/N；SKYFALL 模式另需輸入 JIG ID。
5. SKYFALL 模式選擇測試所有連接埠或單一連接埠。
6. 按下 `START` 開始測試。
7. 測試完成後，在程式所在資料夾查看 `production_test_datalog.csv`。

## 7. 測試紀錄

`production_test_datalog.csv` 會以 UTF-8 編碼保存以下欄位：

```text
Timestamp, PCBA_SN, JIG_ID, Test_Mode, Port_ID,
Step_Current_A, Measured_Volt_V, Measured_Curr_A, Vdrop_mV,
OCP_Status, Step_Result, Final_Port_Result
```

每次測試會追加資料，不會覆蓋既有紀錄。若需要開始新的批次，建議先備份或重新命名既有 CSV，再啟動程式。

## 8. 注意事項

- 測試前確認負載線、Type-C 線材、治具與被測 PCBA 已正確連接。
- OCP 測試可能觸發 eFuse 保護，請依畫面提示完成重新插拔與復歸操作。
- 測試中若需要停止，請按下 `STOP`；程式會嘗試將電流設為 0 A 並關閉 DL24。
- 不要在測試進行中拔除通訊線或任意修改 `test_config.json`。
- 請保留與程式版本相對應的 `test_config.json`，以確保歷史測試結果可重現。
