using System;
using System.Diagnostics;
using System.IO;
using System.Windows.Forms;
using System.Text;

class Launcher
{
    [STAThread]
    static void Main(string[] args)
    {
        try
        {
            // 設定工作目錄為執行檔所在路徑
            string appDir = AppDomain.CurrentDomain.BaseDirectory;
            Directory.SetCurrentDirectory(appDir);

            // 優先偵測本機虛擬環境的 Python 執行檔
            string venvPythonW = Path.Combine(appDir, ".venv\\Scripts\\pythonw.exe");
            string venvPython = Path.Combine(appDir, ".venv\\Scripts\\python.exe");
            string pythonPath = "";

            if (File.Exists(venvPythonW))
            {
                pythonPath = venvPythonW;
            }
            else if (File.Exists(venvPython))
            {
                pythonPath = venvPython;
            }
            else
            {
                // 找不到則回退至系統全域環境的 pythonw.exe
                pythonPath = "pythonw.exe";
            }

            string scriptPath = Path.Combine(appDir, "main.py");
            if (!File.Exists(scriptPath))
            {
                MessageBox.Show("錯誤：在此目錄中找不到 main.py 入口檔案。\n請確認執行檔與專案根目錄檔案結構完整。\n目錄路徑：" + appDir, "SPC 啟動錯誤", MessageBoxButtons.OK, MessageBoxIcon.Error);
                return;
            }

            // 組合參數並傳遞（包含將 main.py 作為第一個參數，並轉發命令列傳入的參數）
            StringBuilder argBuilder = new StringBuilder();
            argBuilder.Append("\"").Append(scriptPath).Append("\"");
            foreach (string arg in args)
            {
                argBuilder.Append(" \"").Append(arg.Replace("\"", "\\\"")).Append("\"");
            }

            // 啟動進程
            ProcessStartInfo startInfo = new ProcessStartInfo();
            startInfo.FileName = pythonPath;
            startInfo.Arguments = argBuilder.ToString();
            startInfo.UseShellExecute = false;
            startInfo.CreateNoWindow = true; // 無視窗模式，不顯示黑色命令提示字元
            
            // 設定 PYTHONPATH 環境變數，確保 Python 能正確匯入 app/ 目錄下的模組
            startInfo.EnvironmentVariables["PYTHONPATH"] = appDir;

            using (Process process = Process.Start(startInfo))
            {
                // 成功啟動後，啟動器可直接結束，不佔用背景資源
            }
        }
        catch (Exception ex)
        {
            MessageBox.Show("無法啟動應用程式，錯誤訊息：\n" + ex.Message, "SPC 啟動錯誤", MessageBoxButtons.OK, MessageBoxIcon.Error);
        }
    }
}
