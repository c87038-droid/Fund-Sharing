# 基金查詢平台 C 版
獨立網站；不要覆蓋私人基金雷達。常用基金為初版的十檔候選清單，名稱、級別及配息頻率仍須核對；未核實 ISIN 已清空。淨值與配息沒有自動同步。

## 部署
1. 解壓縮 ZIP，建立新的 GitHub 公開 repository（例如 fund-partner-share），預設分支 main。將解壓縮後所有檔案與資料夾（含隱藏的 .github）上傳到 repository 根目錄。可用 GitHub Desktop 推送；若 Actions 工作流程檔案未上傳，請另外建立。
2. Settings → Pages → Build and deployment → Source 選 GitHub Actions。
3. Actions → Deploy website → Run workflow（main）。完成後在 Settings → Pages 取得網址。
4. Actions → Update fund catalog → Run workflow（main），成功後會自動重新部署。排程每天 UTC 10:20（台灣 18:20）嘗試更新名錄；GitHub 排程可能延遲或因長期無活動停用。
5. 打開網站確認兩個分頁、基金清單、資料日期，再分享 LINE。若更新失敗，查看 Actions 日誌；舊名錄保留，初次失敗則顯示官方入口。

## 資料與限制
- 全市場名錄來源：https://data.gov.tw/dataset/11639 與 https://data.gov.tw/dataset/43476，政府資料開放授權條款第1版。本站擷取欄位、重新排列。境外每日、境內不定期由來源更新。
- 執行環境無法連線下載 CSV，尚未驗證正式資料的解析及部署。可於 GitHub Actions 首次執行確認。
- data/funds.json 維護常用基金；nav、nav_date、distribution、ex_date、pre_ex_nav、payments_per_year、history、source_url 均須根據已核實且允許再散布的資料填寫。history 格式 [{"date":"YYYY-MM-DD","amount":0.1}]。配息率為配息除以前一日淨值；年化再乘每年配息次數。非報酬率。
- 官方入口為集保首頁，不是每檔基金直接連結。網站沒有客戶資料或登入控制；公開網址可被轉傳。對外招攬前請由公司法遵確認。
