import os
import zipfile
import shutil
from datetime import datetime
from typing import Dict, Any
from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse, FileResponse

router = APIRouter(prefix="/reports", tags=["reports"])

def get_base_dir():
    """Get the base directory - adjust path since we're in endpoints subfolder"""
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

@router.get("/list")
async def list_reports() -> Dict[str, Any]:
    """Extract ZIP files and return sorted reports list"""
    try:
        BASE_DIR = get_base_dir()
        base_folder = os.path.join(BASE_DIR, "data_Recon_Op")
        reports = []
        extraction_log = []
        
        if not os.path.exists(base_folder):
            return {"reports": [], "message": "Reports folder not found", "debug_path": base_folder}
        
        # Get ZIP files directly from base folder
        all_items = os.listdir(base_folder)
        zipfiles = [f for f in all_items if f.endswith('.zip')]
        
        extraction_log.append(f"Found ZIP files: {zipfiles}")
        
        if not zipfiles:
            return {"reports": [], "message": "No ZIP files found", "all_items": all_items}
        
        for zipfile_name in zipfiles:
            try:
                zipfile_path = os.path.join(base_folder, zipfile_name)
                
                # Create extraction folder per ZIP file (use simple naming)
                zip_basename = zipfile_name.replace('.zip', '')
                extract_folder = os.path.join(base_folder, f"{zip_basename}_extracted")
                
                extraction_log.append(f"Processing {zipfile_name}")
                
                # Remove existing extraction folder
                if os.path.exists(extract_folder):
                    shutil.rmtree(extract_folder)
                
                os.makedirs(extract_folder, exist_ok=True)
                
                # Validate ZIP file
                if not zipfile.is_zipfile(zipfile_path):
                    extraction_log.append(f"ERROR: {zipfile_name} is not a valid ZIP file")
                    continue
                
                # Extract ZIP file
                with zipfile.ZipFile(zipfile_path, 'r') as zip_ref:
                    zip_ref.extractall(extract_folder)
                    extracted_files = zip_ref.namelist()
                    extraction_log.append(f"Extracted {len(extracted_files)} files from {zipfile_name}")
                
                # Find Report.html (case insensitive) - keep original name
                report_html_path = None
                for root, dirs, files in os.walk(extract_folder):
                    for file in files:
                        if file.lower() == "report.html":
                            report_html_path = os.path.join(root, file)
                            extraction_log.append(f"Found Report.html at: {report_html_path}")
                            break
                    if report_html_path:
                        break
                
                if not report_html_path:
                    extraction_log.append(f"No Report.html found in {zipfile_name}")
                    continue
                
                # Get file modification time for sorting
                mod_time = os.path.getmtime(report_html_path)
                
                # Use simple ID without special characters
                simple_id = f"report_{len(reports)}"
                
                reports.append({
                    "id": simple_id,  # Simple, unique ID
                    "name": zip_basename,  # Display full ZIP name without .zip
                    "filename": os.path.basename(report_html_path),  # Keep original filename
                    "path": report_html_path,  # Keep original path
                    "folder": zip_basename,  # Display as-is
                    "original_zip": zipfile_name,  # For downloads
                    "modified": mod_time,
                    "modified_date": datetime.fromtimestamp(mod_time).strftime("%Y-%m-%d %H:%M:%S")
                })
                
                extraction_log.append(f"Successfully processed {zipfile_name}")
                
            except Exception as e:
                extraction_log.append(f"Error processing {zipfile_name}: {str(e)}")
        
        # Sort reports by modification time (latest first)
        reports.sort(key=lambda x: x["modified"], reverse=True)
        
        return {
            "reports": reports,
            "total_count": len(reports),
            "message": f"Extracted and found {len(reports)} reports",
            "extraction_log": extraction_log
        }
        
    except Exception as e:
        import traceback
        return {
            "reports": [], 
            "error": str(e), 
            "message": "Error processing reports",
            "traceback": traceback.format_exc()
        }

@router.get("/content/{report_id}")
async def get_report_content(report_id: str):
    """Get HTML content of a specific report"""
    try:
        # Get reports list to find the specific report
        reports_response = await list_reports()
        reports = reports_response.get("reports", [])
        
        # Find the report by its ID
        report = next((r for r in reports if r["id"] == report_id), None)
        if not report:
            raise HTTPException(status_code=404, detail=f"Report with ID '{report_id}' not found")
        
        # Check if report file exists
        if not os.path.exists(report["path"]):
            raise HTTPException(status_code=404, detail=f"Report file not found at {report['path']}")
        
        # Read HTML content
        try:
            with open(report["path"], 'r', encoding='utf-8') as file:
                html_content = file.read()
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Could not read report file: {str(e)}")
        
        return JSONResponse({
            "id": report_id,
            "name": report["name"],
            "content": html_content,
            "modified_date": report["modified_date"],
            "folder": report.get("folder"),
            "original_zip": report.get("original_zip")
        })
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error reading report: {str(e)}")

@router.get("/download/{zip_name}")
def download_zip(zip_name: str):
    """Download the original ZIP file with enhanced debugging"""
    try:
        BASE_DIR = get_base_dir()
        base_folder = os.path.join(BASE_DIR, "data_Recon_Op")
        
        # Debug: List all files in the folder
        if os.path.exists(base_folder):
            available_files = os.listdir(base_folder)
            print(f"Available files in {base_folder}:")
            for f in available_files:
                print(f"  - '{f}' (length: {len(f)})")
        else:
            raise HTTPException(404, f"Base folder not found: {base_folder}")
        
        # Try exact match first
        zip_path = os.path.join(base_folder, zip_name)
        print(f"Looking for exact match: '{zip_name}' (length: {len(zip_name)})")
        print(f"Full path: {zip_path}")
        print(f"Exists: {os.path.exists(zip_path)}")
        
        if os.path.exists(zip_path):
            return FileResponse(zip_path, filename=zip_name, media_type='application/zip')
        
        # Try fuzzy matching if exact match fails
        matching_files = []
        for file in available_files:
            if zip_name.strip() == file.strip():
                matching_files.append(file)
            elif zip_name.replace("'", "") in file or file.replace("'", "") in zip_name:
                matching_files.append(file)
        
        if matching_files:
            actual_file = matching_files[0]
            actual_path = os.path.join(base_folder, actual_file)
            print(f"Found fuzzy match: '{actual_file}'")
            return FileResponse(actual_path, filename=actual_file, media_type='application/zip')
        
        raise HTTPException(404, {
            "error": "ZIP file not found",
            "requested": zip_name,
            "available_files": available_files,
            "base_folder": base_folder
        })
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Download error: {str(e)}")
        raise HTTPException(500, f"Download error: {str(e)}")
