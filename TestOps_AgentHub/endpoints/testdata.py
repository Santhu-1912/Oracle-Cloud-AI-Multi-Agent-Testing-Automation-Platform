import os
import pandas as pd
from typing import Dict, Any
from fastapi import APIRouter, HTTPException

router = APIRouter(prefix="/testdata", tags=["testdata"])

def get_excel_folder():
    """Get the Excel folder path - adjust for endpoints subfolder"""
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(BASE_DIR, "TDM_files")

@router.get("/files")
def list_excel_files() -> Dict[str, Any]:
    """List all Excel files and their sheets"""
    try:
        EXCEL_FOLDER = get_excel_folder()
        print(f"Checking folder: {EXCEL_FOLDER}")
        
        if not os.path.exists(EXCEL_FOLDER):
            return {}
        
        files = [
            f for f in os.listdir(EXCEL_FOLDER)
            if f.endswith((".xlsx", ".xls")) and not f.startswith("~$")
        ]
        
        result = {}
        for file in files:
            path = os.path.join(EXCEL_FOLDER, file)
            try:
                xls = pd.ExcelFile(path)
                result[file] = {
                    "sheets": xls.sheet_names,
                    "size": os.path.getsize(path),
                    "modified": os.path.getmtime(path)
                }
            except Exception as e:
                print(f"Error reading {file}: {e}")
                result[file] = {
                    "sheets": [],
                    "size": 0,
                    "modified": 0,
                    "error": str(e)
                }
        
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error listing Excel files: {str(e)}")

@router.get("/sheet-data/{filename}/{sheetname}")
def get_sheet_data(filename: str, sheetname: str) -> Dict[str, Any]:
    """Get data from a specific sheet in an Excel file"""
    try:
        EXCEL_FOLDER = get_excel_folder()
        path = os.path.join(EXCEL_FOLDER, filename)
        
        if not os.path.exists(path):
            raise HTTPException(status_code=404, detail="File not found")
        
        df = pd.read_excel(path, sheet_name=sheetname)
        data = df.fillna("").to_dict(orient="records")
        columns = list(df.columns)
        
        return {
            "columns": columns, 
            "data": data,
            "total_rows": len(data),
            "total_columns": len(columns),
            "filename": filename,
            "sheetname": sheetname
        }
        
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"File '{filename}' not found")
    except ValueError as e:
        if "Worksheet" in str(e):
            raise HTTPException(status_code=404, detail=f"Sheet '{sheetname}' not found in file '{filename}'")
        else:
            raise HTTPException(status_code=400, detail=f"Error reading Excel file: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing sheet data: {str(e)}")
