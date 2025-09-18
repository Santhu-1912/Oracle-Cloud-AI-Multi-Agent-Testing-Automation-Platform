# tools/DataRecon_tool.py

import os
import requests
import re
from langchain.tools import Tool
import os
from dotenv import load_dotenv

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "..", ".env"))

DATARECON_BASE_URL = os.getenv("DATARECON_BASE_URL")
# Use the same host as DATARECON_BASE_URL for your main API
API_BASE_URL = os.getenv("HOST_BASE_URL")

class DataReconProcessor:
    def __init__(self):
        self.input_dir = "data_Recon_In"
        self.output_dir = "data_Recon_Op"
        self.upload_url = f"{DATARECON_BASE_URL}/upload_file/"
        self.testcase_url = f"{DATARECON_BASE_URL}/execute_erp_testcase"
        self.process_invoice_url = f"{API_BASE_URL}/process/invoice-to-payables"
        os.makedirs(self.input_dir, exist_ok=True)
        os.makedirs(self.output_dir, exist_ok=True)

    def get_payables_csv_from_invoice(self) -> dict:
        """Get payables.csv from invoicedata.xlsx processing endpoint and save to data_Recon_In"""
        try:
            response = requests.get(self.process_invoice_url, timeout=60)
            response.raise_for_status()
            
            # Save the CSV content to INPUT directory (data_Recon_In)
            payables_path = os.path.join(self.input_dir, "payables.csv")
            with open(payables_path, "wb") as f:
                f.write(response.content)
            
            return {
                "status": "success",
                "file_path": payables_path,
                "message": "Payables CSV generated from invoicedata.xlsx and saved to data_Recon_In"
            }
            
        except requests.exceptions.RequestException as e:
            return {"status": "error", "message": f"Failed to process invoice data: {e}"}

    def file_exists(self, file_id: str) -> str:
        """Check if the .csv file exists in data_Recon_In"""
        path = os.path.join(self.input_dir, f"{file_id}.csv")
        return path if os.path.exists(path) else None

    def upload_file_to_server(self, file_name: str, file_path: str) -> dict:
        """Upload file to the server using /upload_file/ endpoint"""
        try:
            with open(file_path, 'rb') as f:
                files = {'file': (f"{file_name}.csv", f, 'text/csv')}
                params = {'file_name': file_name}
                response = requests.post(self.upload_url, files=files, params=params, timeout=60)
                response.raise_for_status()

            return {
                "status": "success",
                "message": f"File {file_name}.csv uploaded successfully"
            }

        except requests.exceptions.RequestException as e:
            return {"status": "error", "message": f"Failed to upload file: {e}"}

    def call_testcase_and_save_result(self, test_case_id: str) -> dict:
        """Execute test case and save result to data_Recon_Op"""
        url = f"{self.testcase_url}/{test_case_id}"
        try:
            resp = requests.get(url, timeout=60)
            resp.raise_for_status()

            # Extract filename from Content-Disposition
            content_disp = resp.headers.get("content-disposition", "")
            filename = f"{test_case_id}_result"

            if content_disp:
                match = re.search(r'filename[^;=\\n]*=([^;\\n]*)', content_disp)
                if match:
                    filename_raw = match.group(1).strip().strip('\"').strip("'")
                    filename = filename_raw.replace('%20', ' ')

            if '.' not in filename:
                content_type = resp.headers.get("content-type", "")
                ext = {
                    'application/zip': '.zip',
                    'text/csv': '.csv',
                    'application/octet-stream': '.bin'
                }.get(content_type, '')
                filename = filename + ext

            # Save to OUTPUT directory (data_Recon_Op)
            output_path = os.path.join(self.output_dir, filename)
            with open(output_path, "wb") as f:
                f.write(resp.content)

            return {
                "status": "success",
                "result_file": output_path,
                "filetype": resp.headers.get("content-type", "unknown"),
                "filename": filename,
                "message": f"Test case executed and result saved to {output_path}"
            }

        except requests.RequestException as e:
            return {"status": "error", "message": f"Failed to call test case API: {e}"}

    def process_data_recon(self, file_id: str) -> dict:
        """Process data reconciliation with correct folder structure"""
        
        if file_id.lower() == "payables":
            # Step 1: Generate payables.csv from invoicedata.xlsx and save to data_Recon_In
            print(f"Processing payables from invoicedata.xlsx using {self.process_invoice_url}")
            csv_result = self.get_payables_csv_from_invoice()
            if csv_result["status"] != "success":
                return csv_result
            
            # Step 2: Upload the CSV from data_Recon_In to the recon server
            upload_result = self.upload_file_to_server("payables", csv_result["file_path"])
            if upload_result["status"] != "success":
                return upload_result
            
            # Step 3: Execute test case and save result to data_Recon_Op
            result = self.call_testcase_and_save_result("payables")
            return result
        
        else:
            # Original behavior for non-payables files - check if exists in data_Recon_In
            file_path = self.file_exists(file_id)
            if not file_path:
                return {"status": "error", "message": f"No {file_id}.csv file exists in data_Recon_In"}

            # Step 2: Upload file from data_Recon_In to server
            upload_result = self.upload_file_to_server(file_id, file_path)
            if upload_result["status"] != "success":
                return upload_result

            # Step 3: Call test case API and save result to data_Recon_Op
            result = self.call_testcase_and_save_result(file_id)
            return result

# LangChain/LLM integration wrapper for the tool
data_recon_instance = DataReconProcessor()

def data_recon_func(query: str) -> str:
    try:
        query_lower = query.lower().strip()
        file_name = None

        patterns = [
            r'reconciliation for (\w+)',
            r'reconcile (\w+)',
            r'recon for (\w+)',
            r'data recon (\w+)',
            r'consolidate (\w+)'
        ]

        for pattern in patterns:
            match = re.search(pattern, query_lower)
            if match:
                file_name = match.group(1)
                break

        if not file_name:
            common_files = ['payables', 'receivables', 'suppliers', 'customers', 'invoices']
            for cf in common_files:
                if cf in query_lower:
                    file_name = cf
                    break

        if not file_name:
            return f"Could not extract file name from query: '{query}'. Please specify a file name like 'payables', 'suppliers', etc."

        result = data_recon_instance.process_data_recon(file_name)

        if result.get("status") == "success":
            # Different process info based on file type
            if file_name.lower() == "payables":
                process_steps = (
                    f"1. ✅ Generated payables.csv from invoicedata.xlsx\n"
                    f"2. ✅ Saved CSV to data_Recon_In folder\n"
                    f"3. ✅ Uploaded CSV to recon server\n"
                    f"4. ✅ Test case executed\n"
                    f"5. ✅ Results saved to data_Recon_Op\n\n"
                )
            else:
                process_steps = (
                    f"1. ✅ File found in data_Recon_In\n"
                    f"2. ✅ File uploaded to recon server\n"
                    f"3. ✅ Test case executed\n"
                    f"4. ✅ Results saved to data_Recon_Op\n\n"
                )

            return (
                f"🔄 **DATA RECONCILIATION COMPLETED**\n\n"
                f"✅ **Status:** Success\n"
                f"📁 **Input File:** {file_name}.csv (data_Recon_In)\n"
                f"📄 **Output File:** {result.get('filename', 'Unknown')} (data_Recon_Op)\n"
                f"💾 **Result Path:** {result.get('result_file')}\n"
                f"📊 **File type:** {result.get('filetype')}\n\n"
                f"**Process completed:**\n"
                f"{process_steps}"
                f"💡 You can now review the reconciliation results in data_Recon_Op folder."
            )

        else:
            return f"❌ {result.get('message')}"

    except Exception as e:
        return f"❌ Data reconciliation error: {type(e).__name__}: {e}"

# Tool registration for LLM orchestration
data_recon_tool = Tool(
    name="data_reconciliation",
    description="Processes payables from invoicedata.xlsx or uploads existing files from data_Recon_In, triggers ERP test case, saves results in data_Recon_Op. Input files in data_Recon_In, output files in data_Recon_Op.",
    func=data_recon_func
)
