#!/usr/bin/env python3

import pandas as pd

def update_excel_structure():
    """Update existing Excel file structure while preserving all data"""
    
    excel_path = 'Goepp Homelab Master.xlsx'
    
    # Load existing data
    try:
        df = pd.read_excel(excel_path, sheet_name='Sheet1')
        print(f"Loaded existing data with {len(df)} applications")
    except FileNotFoundError:
        print("ERROR: No existing Excel file found!")
        return None
    except Exception as e:
        print(f"Error reading existing Excel file: {e}")
        return None
    
    
    # Remove unwanted columns if they exist
    columns_to_remove = ['Update_Count', 'Full_Version', 'Update_Size', 'Update_Details']
    for col in columns_to_remove:
        if col in df.columns:
            df = df.drop(col, axis=1)
    
    # Save the updated DataFrame
    with pd.ExcelWriter(excel_path, engine='openpyxl') as writer:
        df.to_excel(writer, sheet_name='Sheet1', index=False)
        
        # Auto-adjust column widths
        worksheet = writer.sheets['Sheet1']
        for column in worksheet.columns:
            max_length = 0
            column_letter = column[0].column_letter
            for cell in column:
                try:
                    if len(str(cell.value)) > max_length:
                        max_length = len(str(cell.value))
                except:
                    pass
            adjusted_width = min(max_length + 2, 50)
            worksheet.column_dimensions[column_letter].width = adjusted_width
    
    print(f"Updated Excel file: {excel_path}")
    return excel_path

if __name__ == "__main__":
    update_excel_structure()